import logging
from contextlib import suppress
from tkinter import END

from pysaic.use_cases.common import join_previous_channel
from pysaic.config import Config, FactionSetting
from pysaic.controllers.game import (
    add_channel_message_to_game,
    add_dm_message_to_game,
    add_error_message_to_game,
    add_information_message_to_game,
    add_users_list_to_game,
    ask_for_actor_status,
)
from pysaic.entities import (
    AppEvent,
    ChatUser,
    ErrorEvent,
    IncomingEvent,
    IncomingMessage,
    InformationEvent,
    IrcEvent,
    OutgoingNotice,
    GameEvent,
    OutgoingNick,
    OutgoingPart,
    OutgoingJoin,
)
from pysaic.enums import AppEventEnum, FactionsEnum, IrcEvents
from pysaic.events.enum import GameEvents
from pysaic.script_reader.entities import Handshake
from pysaic.settings import (
    END_OF_ACTOR_CHARACTER,
    START_OF_ACTOR_CHARACTER,
    APP_IDENTITY,
    SUPPORTED_SCRIPT_VERSION,
)
from pysaic.state import ChatUsers, State
from pysaic.ui.app import App
from pysaic.use_cases.ui.add_dm_message import AddDmMessage
from pysaic.use_cases.ui.command import CommandUseCase
from pysaic.use_cases.ui.mode_change import ModeChangeUseCase
from pysaic.use_cases.ui.money_transfer import IncomingMoneyTransferUseCase
from pysaic.use_cases.ui.our_message import OurMessageUseCase
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase
from pysaic.use_cases.ui.utils import (
    enable_disable,
    get_faction_actor,
    normalize_content,
    prepare_date,
)

logger = logging.getLogger(__name__)


class IncomingNewEventUseCase:
    @property
    def current_actor(self) -> FactionsEnum:
        return self.config.current_faction

    @current_actor.setter
    def current_actor(self, value):
        self.ui.current_actor = value

    @property
    def chat_users(self) -> ChatUsers[str, ChatUser]:
        return self.state.chat_users

    @property
    def messages_list(self):
        return self.ui.messages_list

    @property
    def outgoing_queue(self):
        return self.ui.outgoing_queue

    @property
    def nick(self):
        return self.config.nick

    def __init__(
        self,
        state: State,
        config: Config,
        ui: App,
        event,
    ):
        self.state = state
        self.event = event
        self.ui = ui
        self.config: Config = config
        self.handlers = {
            IncomingMessage: self._add_message,
            IncomingEvent: self._add_event,
        }

    @classmethod
    def handle_event(cls, state, config: Config, ui: App, event):
        cls(state, config, ui, event=event)()

    def __call__(self):
        logger.debug("Handling event: %r", self.event)
        handler = self.handlers.get(type(self.event), self._not_found_handler)
        try:
            handler(self.event)
        except Exception:
            logger.critical(
                "Error handling event: %r", self.event, exc_info=True
            )
            self._add_error_text(
                "Error occurred, please provide error logs to creator."
            )

    def _add_message(self, event):
        logger.debug("Handling message: %r", event)
        if event.content.startswith("/"):
            command, *params = event.content[1:].split(" ")
            CommandUseCase.handle(
                self.state,
                self.config,
                self.ui,
                command,
                " ".join(params),
            )
            return

        if event.content.startswith("\x01") and event.content.endswith("\x01"):
            self._handle_ctcp(event)
            return

        elif event.target.startswith("#"):
            self._add_channel_message(event)
            self._add_channel_message_to_game(event)
        else:
            if event.content.startswith("actor_"):
                IncomingMoneyTransferUseCase(
                    self.state, self.config, self.ui, event
                ).execute()
                return

            AddDmMessage(self.state, self.config, self.ui, event).execute()

    def __str__(self):
        return f"IncomingNewEvent: {self.event}"

    def _add_channel_message(self, event: IncomingMessage):
        logger.debug("Adding channel message: %r", event)
        highlight = (
            event.author != self.nick and self.nick in event.content
        ) or event.author == "NickServ"
        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            if START_OF_ACTOR_CHARACTER in event.content:
                self._add_death_message(event)
            else:
                self._add_user_and_faction_color(event.author)
                self._add_content_to_message(event)

            if highlight:
                self.messages_list.tag_add(
                    "Highlight", END + "-2l", END + "-1l"
                )
            self.messages_list.see(END)

    def _add_dm_message(self, event: IncomingMessage, service=False):
        logger.debug("Adding dm message: %r", event)
        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self._add_user_and_faction_color(event.author, service)
            self.messages_list.insert(END, " -> ", "DM")
            self._add_user_and_faction_color(event.target)
            self._add_content_to_message(event)
            self.messages_list.see(END)

    def _add_event(self, event):
        # TODO: replace with dict mapping or or add them dynamically
        if isinstance(event.event, IrcEvent):
            self._add_irc_event(event)
        elif isinstance(event.event, InformationEvent):
            self._add_information_event(event)
        elif isinstance(event.event, AppEvent):
            self._handle_app_event(event)
        elif isinstance(event.event, GameEvent):
            self._handle_game_event(event)
        else:
            logger.warning("Unknown event: %r", event)

    def _not_found_handler(self, event):
        logger.warning("Handler not found for event: %r", event)

    def _add_irc_event(self, event: IncomingEvent):
        # TODO: replace with dict mapping or or add them dynamically
        if event.event.type == IrcEvents.JOIN:
            self._user_joined_use_case(event)
        elif event.event.type in [IrcEvents.PART, IrcEvents.QUIT]:
            self._handle_part_or_quit(event)
        elif event.event.type == IrcEvents.NICK:
            self._user_nick_change(event)
        elif event.event.type == IrcEvents.USER:
            self._handle_nick_changed_by_server(event)
        elif event.event.type == IrcEvents.NAMES:
            self._add_names(event.event.payload["nicks"])
        elif event.event.type == IrcEvents.NOTICE:
            self._handle_notice(event)
        elif event.event.type == IrcEvents.END_OF_NAMES:
            self._send_user_data_as_privmsg()
        elif event.event.type == IrcEvents.BANNED_FROM_CHANNEL:
            self._hande_user_is_banned(event)
        elif event.event.type == IrcEvents.KICK:
            self._handle_user_is_kicked(event)
        elif event.event.type == IrcEvents.MODE:
            ModeChangeUseCase.handle(
                self.state, self.ui, self.chat_users, event
            )
        else:
            logger.warning("Unknown IRC event: %r", event)
        self._update_crc_users_data()

    def _add_names(self, names):
        for name in names:
            key_name = name.lstrip("%@+")
            if key_name in self.chat_users:
                continue

            logger.debug("Adding name: %r", name)
            chat_user = ChatUser(name=name)
            if name == self.nick:
                chat_user.faction = self.config.current_faction
                chat_user.in_game = self.state.is_game_running

            self.chat_users.add_user(key_name, chat_user)
        self._update_ui_user_list()

    def _add_information_event(self, event):
        logger.debug("Adding information event: %r", event)
        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self.messages_list.insert(
                END, f"{event.event.content}\n", "Information"
            )
        add_information_message_to_game(event.event.content)

    def _add_information_text(self, text):
        event = InformationEvent(content=normalize_content(text))

        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self.messages_list.insert(END, f"{event.content}\n", "Information")
        add_information_message_to_game(event.content)

    def _handle_ctcp(self, event):
        message = event.content[1:-1]
        logger.debug("Handling CTCP: %r", message)
        if message in ("VERSION", "CLIENTINFO"):
            self._send_ctcp_version(event)
        elif message.startswith("PING"):
            self._send_ctcp_ping(event)
        elif message.startswith("USERDATA"):
            self._send_user_data(event)
        elif message.startswith("AMOGUS"):
            self._parse_amogus(message)
        else:
            logger.warning("Unknown CTCP: %r", message)

    def _send_ctcp_version(self, event):
        logger.debug("Sending CTCP VERSION")
        self.outgoing_queue.put_nowait(
            OutgoingNotice(
                target=event.author,
                content=f"\x01VERSION {APP_IDENTITY}\x01",
            )
        )

    def _send_ctcp_ping(self, event):
        logger.debug("Sending CTCP PING")
        self.outgoing_queue.put_nowait(
            OutgoingNotice(
                target=event.author,
                content=f"\x01PING {event.created_at.timestamp()}\x01",
            )
        )

    def _send_user_data(self, event):
        logger.debug("Sending USERDATA")
        self._send_amogus_message()

    def _get_faction_color(self, author) -> str:
        if "NickServ" in author:
            return self.chat_users[self.nick].faction.name
        try:
            return str(self.chat_users[author].faction.name)
        except KeyError:
            return FactionsEnum.Anonymous.name

    @staticmethod
    def _add_new_line_if_necessary(content):
        return "" if content.endswith("\n") else "\n"

    def _add_date_to_message(self, event):
        self.messages_list.insert(
            END,
            f"[{prepare_date(event)}] ",
            "Time",
        )

    def _add_content_to_message(self, event):
        try:
            content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = event.content
        self.messages_list.insert(
            END,
            f": {normalize_content(content)}{self._add_new_line_if_necessary(content)}",
            "Text",
        )

    def _add_user_and_faction_color(self, user, service=False):
        self.messages_list.insert(
            END,
            user,
            self._get_faction_color(user),
            "Highlight" if service else None,
        )

    def _handle_part_or_quit(self, event):
        with suppress(KeyError):
            self.chat_users.remove_user(event.author)
        self._update_ui_user_list()

        if event.event.type == IrcEvents.PART:
            if event.event.payload:
                self._add_information_text(
                    f"{event.author} {event.event.payload['reason']}"
                )
            else:
                self._add_information_text(
                    f"{event.author} has left the channel."
                )
        else:
            self._add_information_text(f"{event.author} has quit.")

    def _handle_notice(self, event):
        if event.author == "NickServ":
            self._add_dm_message(event, service=True)

    def _parse_amogus(self, content):
        _, data = content.split(" ", 1)
        author, faction, in_game = data.split("/")
        logger.debug("Parsing AMOGUS: %r", data)
        should_update = False

        user = self.chat_users.get(author)
        if user is None:
            should_update = True
            user = ChatUser(name=author)

        try:
            faction = FactionsEnum(faction)
        except Exception:
            logger.exception("Error parsing faction - %r", faction)
            return
        else:
            if user.faction != faction:
                should_update = True
                user.faction = faction

        in_game = in_game.lower() == "true"
        if user.in_game != in_game:
            should_update = True
            user.in_game = in_game

        if not should_update:
            return

        self.chat_users.set_user(author, user)
        self._update_crc_users_data()
        self._update_ui_user_list()

    def _add_death_message(self, event):
        author, faction_actor, content = (
            self._get_death_message_author_and_content(event)
        )
        # print(author, faction_actor, content)
        self.messages_list.insert(
            # END, author, self._get_faction_color(event.author)
            END,
            author,
            FactionsEnum(faction_actor).name,
        )
        self.messages_list.insert(
            END,
            f": {content}{self._add_new_line_if_necessary(content)}",
            "Text",
        )

    def _add_channel_message_to_game(self, event):
        if START_OF_ACTOR_CHARACTER in event.content:
            author, faction_actor, content = (
                self._get_death_message_author_and_content(event)
            )
        else:
            author, content = event.author, normalize_content(event.content)
            faction_actor = get_faction_actor(self.chat_users[author])

        add_channel_message_to_game(
            faction_actor=faction_actor,
            author=author,
            highlight=str(self.nick in event.content),
            content=content,
        )

    def _update_crc_users_data(self):
        add_users_list_to_game(self.chat_users.values())

    @staticmethod
    def _get_death_message_author_and_content(event):
        author = event.content.split(START_OF_ACTOR_CHARACTER, 1)[0]
        faction_actor = event.content.split(START_OF_ACTOR_CHARACTER, 1)[
            1
        ].split(END_OF_ACTOR_CHARACTER, 1)[0]
        content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        return author, faction_actor, normalize_content(content)

    def _handle_app_event(self, event):
        logger.debug("Handling AppEvent: %r", event)
        # TODO: replace with dict mapping or or add them dynamically
        if event.event.what == AppEventEnum.UPDATE_USERS:
            self._update_crc_users_data()
        elif event.event.what == AppEventEnum.ACTOR_UPDATE:
            self._handle_actor_update(event.event.payload)
        elif event.event.what == AppEventEnum.IN_GAME:
            self._handle_in_game(event.event.payload)

        # TODO: fix this mess
        elif event.event.what == AppEventEnum.CONNECTED:
            self._handle_connected_to_channel()
        elif event.event.what == AppEventEnum.DISCONNECTED_FROM_PDA_NETWORK:
            self._handle_disconnected_from_channel()

        elif event.event.what == AppEventEnum.UPDATE_UI_USERS_LIST:
            self._handle_update_ui_users_list()
        elif event.event.what == AppEventEnum.OPTIONS_UPDATED:
            self._handle_options_updated()
        elif event.event.what == AppEventEnum.OUR_MESSAGE:
            OurMessageUseCase(
                self.state,
                self.config,
                self.ui,
                self.outgoing_queue,
            ).execute(event.event.payload)
        elif event.event.what == AppEventEnum.COMMAND:
            self._handle_command(event)

        elif event.event.what == AppEventEnum.NICKNAME_CHANGED:
            self._handle_nickname_changed(event.event.payload)
        elif event.event.what == AppEventEnum.RECONNECTING_TO_SERVER:
            self._handle_reconnecting_to_server()
        elif event.event.what == AppEventEnum.NEW_VERSION:
            self._add_information_text(
                f"New version available: {event.event.payload}"
            )

        # merge those
        elif event.event.what == AppEventEnum.GAME_CHANNEL_CHANGE:
            self._handle_game_channel_change(event.event.payload)
        elif event.event.what == AppEventEnum.CHANGE_CHANNEL:
            self._handle_app_channel_change(event.event.payload)

        else:
            logger.warning("Unknown AppEvent: %r", event)

    def _handle_actor_update(self, payload):
        logger.debug("Handling ACTOR_UPDATE event")
        if self.config.faction_setting != FactionSetting.GameSynced:
            logger.info(
                'Faction setting is not "GameSynced", skipping actor update, %r',
                self.config.faction_setting,
            )
            return

        try:
            user = self.chat_users[self.nick]
        except KeyError:
            logger.exception("User was missing in chat_users.")
            user = self._readd_user_to_chat_users()

        if user.in_game:
            try:
                if FactionsEnum(payload).value == self.current_actor.value:
                    return
            except Exception:
                logger.exception(
                    "Could not validate actor %r, current: %r",
                    payload,
                    self.current_actor,
                )
                raise

        logger.debug("Changing actor to %r", payload)
        user.faction = FactionsEnum(payload)
        user.in_game = True
        self.chat_users.set_user(self.nick, user)
        self.current_actor = user.faction
        self.config.current_faction = user.faction
        self._update_crc_users_data()
        self._send_amogus_message()
        self._update_ui_user_list()
        self.config.save_config()

    def _handle_in_game(self, payload):
        logger.debug("Handling IN_GAME event, %r", payload)
        self.state.is_game_running, self.state.game_location = payload

        if user := self.chat_users.get_user(self.nick):
            user.in_game = self.state.is_game_running
            self.chat_users.set_user(self.nick, user)
        else:
            self.chat_users.add_user(
                self.nick,
                ChatUser(
                    name=self.nick,
                    faction=self.config.current_faction,
                    in_game=self.state.is_game_running,
                ),
            )

        if self.state.is_game_running:
            ask_for_actor_status()

        self._update_ui_user_list()
        self._update_crc_users_data()
        self._send_amogus_message()

    def _add_dm_message_to_game(self, event):
        try:
            content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = event.content

        add_dm_message_to_game(
            author_faction_actor=get_faction_actor(
                self.chat_users.get(event.author, self.chat_users[self.nick])
            ),
            author=event.author,
            receiver=event.target,
            content=normalize_content(content),
        )

    def _send_user_data_as_privmsg(self):
        logger.debug("Sending USERDATA as privmsg to channel")
        self._send_amogus_message()

    def _user_nick_change(self, event):
        new_nick = event.event.payload["new_nick"]
        logger.debug("User nick change: %r -> %r", event, new_nick)
        previous_chat_user = self.chat_users.pop(event.author)
        self.chat_users[new_nick] = ChatUser(
            name=new_nick,
            faction=previous_chat_user.faction,
            in_game=previous_chat_user.in_game,
        )
        self._add_information_text(
            f"{event.author!r} is know now as {new_nick!r}."
        )
        self._update_ui_user_list()

    def _hande_user_is_banned(self, event):
        logger.debug("User banned: %r", event.event.payload)
        self._add_error_text(
            f"{event.event.payload} has been banned from the channel."
        )

    def _add_error_text(self, text):
        event = ErrorEvent(content=normalize_content(text))

        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self.messages_list.insert(END, f"{text}\n", "Error")
        add_error_message_to_game(event.content)

    def _user_joined_use_case(self, event):
        self._add_names([event.author])
        self._add_information_text(f"{event.author} has logged in")

    def _handle_connected_to_channel(self):
        self._add_information_text("Connected to the network.")
        self.ui.enable_input()
        self.state.set_in_channel()
        self._send_amogus_message()

    def _handle_disconnected_from_channel(self):
        self._add_error_text("Lost connection to the network.")
        self.ui.disable_input()
        self.state.set_not_in_channel()

    def _handle_game_event(self, event):
        if event.event.what == GameEvents.ACTOR_UPDATE:
            self._handle_actor_update(event.event.payload[1])
        elif event.event.what == GameEvents.MONEY_CHANGE:
            self._handle_money_change(event.event.payload)
        elif event.event.what == GameEvents.HANDSHAKE:
            self._handle_game_handshake(event.event.payload)
        else:
            logger.warning("Unknown game event: %r", event)

    def _handle_nick_changed_by_server(self, event: IncomingEvent):
        new_nick = event.event.payload["new_nick"]
        logger.debug(
            "User nick was changed by server: %r -> %r", event, new_nick
        )
        previous_chat_user = self.chat_users.pop(event.author)
        self.chat_users[new_nick] = ChatUser(
            name=new_nick,
            faction=previous_chat_user.faction,
            in_game=previous_chat_user.in_game,
        )
        self._add_information_text(
            f"Network server renamed you to {new_nick!r}."
        )
        self._update_ui_user_list()

    def _handle_update_ui_users_list(self):
        logger.debug("Handling UPDATE_UI_USERS_LIST event")
        self._update_ui_user_list()

    def _handle_options_updated(self):
        logger.debug("Handling OPTIONS_UPDATED event")
        self._add_information_text("Options have been updated.")
        self._update_crc_users_data()
        self._update_faction_setting()
        self._update_ui_user_list()

        if self.state.nick != self.config.nick:
            self._update_nick_from_options()

    def _update_ui_user_list(self):
        UpdateUsersUseCase(self.state, self.ui).execute()

    def _update_faction_setting(self):
        try:
            user = self.chat_users[self.nick]
        except KeyError:
            user = self.chat_users[self.state.nick]

        if self.config.current_faction != user.faction:
            self.chat_users.update_user_faction(
                self.nick, self.config.current_faction
            )
            self._send_amogus_message()

    def _send_amogus_message(self):
        logger.info('Sending "AMOGUS" message')
        try:
            user = self.chat_users[self.nick]
        except KeyError:
            logger.exception("User was missing in chat_users.")
            user = self._readd_user_to_chat_users()

        self.outgoing_queue.put_nowait(
            OutgoingNotice(
                target=self.config.server.previous_channel,
                content=(
                    f"\x01AMOGUS {self.nick}/{user.faction}/{user.in_game}\x01"
                ),
            )
        )

    def _handle_command(self, event):
        content = event.event.payload
        logger.debug("Command: %r", content)
        try:
            command, params = content.split(" ", 1)
        except ValueError:
            command = content
            params = None

        CommandUseCase.handle(
            self.state,
            self.config,
            self.ui,
            command,
            params,
        )

    def _handle_money_change(self, payload):
        self.state.player_money = int(payload)

    def _handle_game_handshake(self, payload: Handshake):
        if payload.version == SUPPORTED_SCRIPT_VERSION:
            return

        logger.error("Unsupported handshake version: %r", payload.version)
        self._add_error_text("Please update your chat mod.")

    def _handle_user_is_kicked(self, event):
        self._add_information_event(
            IncomingEvent.create_information_event(
                content=f"{event.event.payload['kicked_nick']} was kicked by {event.author}: {event.event.payload['reason']}"
            )
        )
        self.state.chat_users.remove_user(event.event.payload["kicked_nick"])
        self._update_ui_user_list()

    def _update_nick_from_options(self):
        logger.debug("Updating nick")
        self.outgoing_queue.put_nowait(
            OutgoingNick(
                nick=self.config.nick,
            )
        )
        self.state.nick = self.config.nick
        self.config.save_config()
        self._update_ui_user_list()
        self._send_amogus_message()
        self._add_information_text(f"Nick changed to {self.state.nick!r}")

    def _handle_nickname_changed(self, payload):
        logger.debug("Handling NICKNAME_CHANGED event")
        new_nick = payload["nick"]
        old = self.state.nick
        try:
            previous_chat_user = self.chat_users.pop(old)
        except KeyError:
            self.chat_users.add_user(
                new_nick,
                ChatUser(
                    name=new_nick,
                    faction=self.config.current_faction,
                    in_game=self.state.is_game_running,
                ),
            )
        else:
            self.chat_users[new_nick] = ChatUser(
                name=new_nick,
                faction=previous_chat_user.faction,
                in_game=previous_chat_user.in_game,
            )

        self.state.nick = self.config.nick = new_nick
        self.config.save_config()
        self._update_ui_user_list()
        self._add_information_text(f"Nick changed to {self.state.nick!r}")

    def _readd_user_to_chat_users(self):
        ask_for_actor_status()
        user = ChatUser(
            name=self.nick,
            faction=self.config.current_faction,
            in_game=self.state.is_game_running,
        )
        self.chat_users.add_user(self.nick, user)
        if not self.state.is_in_channel.is_set():
            join_previous_channel()

        return user

    def _handle_reconnecting_to_server(self):
        self._add_information_text(
            "Connection lost with the server, trying to reconnect."
        )
        self.ui.disable_input()
        self.state.set_not_in_channel()
        self._update_ui_user_list()
        self._update_crc_users_data()

    def _handle_game_channel_change(self, payload: str):
        part = OutgoingPart(channel=self.config.server.previous_channel)
        self.config.server.previous_channel = {
            channel.description: channel.name
            for channel in self.config.server.channels
        }[payload]
        self.config.save_config()
        self.outgoing_queue.put_nowait(part)
        self.outgoing_queue.put_nowait(
            OutgoingJoin(channel=self.config.server.previous_channel)
        )
        self._add_information_text(f"Channel changed to {payload}")

    def _handle_app_channel_change(self, payload):
        self._handle_game_channel_change(
            {
                channel.name: channel.description
                for channel in self.config.server.channels
            }[payload]
        )
