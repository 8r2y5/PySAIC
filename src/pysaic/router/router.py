import logging
from functools import wraps
from tkinter import END

from pysaic.config import Config, FactionSetting
from pysaic.controllers.game import (
    add_error_message_to_game,
    add_information_message_to_game,
    add_users_list_to_game,
    ask_for_actor_status,
)
from pysaic.entities import (
    ChatUser,
    ChatUsers,
    ErrorEvent,
    IncomingEvent,
    InformationEvent,
    OutgoingCTCP,
)
from pysaic.enums import AvatarEnum, FactionsEnum
from pysaic.router.utils import send_saic_avatar
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.state import State
from pysaic.ui.hyper_links import HyperlinkManager
from pysaic.use_cases.avatar import calculate_icon_based_on_faction_and_name
from pysaic.use_cases.common import join_previous_channel
from pysaic.use_cases.text import make_content_malformed
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase
from pysaic.use_cases.ui.utils import (
    add_content_of_message_to_messages_list,
    enable_disable,
    normalize_content,
    prepare_date,
)

logger = logging.getLogger(__name__)


def send_only_when_connected(method):
    @wraps(method)
    def _wrapper(self):
        if self.state.is_in_channel.is_set():
            method(self)
            return
        else:
            logger.debug(
                '"%s" was not sent, user is not in channel',
                method.__qualname__,
            )

    return _wrapper


class Router:
    def __init__(self, state: State, config, ui, event):
        self.state = state
        self.config = config
        self.ui = ui
        self.event = event

    @classmethod
    def handle(cls, state: State, config: Config, ui, event: IncomingEvent):
        cls(state, config, ui, event).route()

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
    def incoming_queue(self):
        return self.ui.incoming_queue

    @property
    def hyperlinks(self) -> HyperlinkManager:
        return self.ui.hyperlinks

    @property
    def nick(self):
        return self.state.nick

    def _update_ui_user_list(self):
        UpdateUsersUseCase(self.state, self.ui).execute()

    def _add_information_text(self, text):
        event = InformationEvent(content=normalize_content(text))

        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self._add_content_of_message(event.content, tags=["Information"])

        add_information_message_to_game(event.content)

    def _add_error_text(self, text):
        event = ErrorEvent(content=normalize_content(text))

        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self._add_content_of_message(event.content, tags=["Error"])
        add_error_message_to_game(event.content)

    def _add_date_to_message(
        self, event: object, additional_tags=None
    ) -> None:
        if additional_tags is None:
            additional_tags = []
        self.messages_list.insert(
            END,
            f"[{prepare_date(event)}] ",
            ["Time"] + additional_tags,
        )

    @send_only_when_connected
    def _send_amogus_message(self):
        logger.info('Sending "AMOGUS" message')
        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            logger.exception("User was missing in chat_users.")
            user = self._readd_user_to_chat_users()

        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=self.config.server.previous_channel,
                content=f"AMOGUS {user.name}/{user.faction}/{user.in_game}",
            )
        )

    def _readd_user_to_chat_users(self):
        user = self.state.player.create_chat_user()
        self.chat_users.add_user(self.state.nick, user)
        if (
            not self.state.is_in_channel.is_set()
            and self.state.is_game_running
            and self.state.fake_disconnect
        ):
            ask_for_actor_status()
            return user

        mlogger = logger.getChild("_readd_user_to_chat_users")
        mlogger.info("Joining previous channel")
        if not self.state.is_in_channel.is_set():
            if not self.state.fake_disconnect:
                join_previous_channel()
        return user

    def _add_information_event(self, event):
        logger.debug("Adding information event: %r", event)
        tag, game_callback = (
            (
                "Error",
                add_error_message_to_game,
            )
            if isinstance(event.event, ErrorEvent)
            else (
                "Information",
                add_information_message_to_game,
            )
        )
        with enable_disable(self.messages_list):
            self._add_date_to_message(event)
            self._add_content_of_message(
                event.event.content,
                tags=[tag],
            )

        if event.target != "only_chat":
            game_callback(event.event.content)

    def _add_user_and_faction_color(
        self, user: str, service=False, additional_tags=None
    ):
        if additional_tags is None:
            additional_tags = []
        if service:
            additional_tags.append("Highlight")
        additional_tags = additional_tags + [self._get_faction_color(user)]
        additional_tags = list(set(additional_tags))
        self.messages_list.insert(
            END,
            user,
            additional_tags,
        )

    def _get_faction_color(self, author) -> str:
        if "NickServ" == author:
            return self.chat_users[self.state.nick].faction.name
        try:
            return str(self.chat_users[author].faction.name)
        except KeyError:
            return FactionsEnum.Anonymous.name

    @staticmethod
    def _add_new_line_if_necessary(content):
        return "" if content.endswith("\n") else "\n"

    def _add_content_to_message(
        self, event, additional_tags=None, show_popup=False
    ):
        if additional_tags is None:
            additional_tags = []
        try:
            content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = event.content

        if self.state.should_malform_messages:
            content = make_content_malformed(content)

        normalized_content = normalize_content(content)
        self._add_content_of_message(
            f": {normalized_content}", ["Text"] + additional_tags
        )
        if show_popup:
            self.ui.show_popup(
                f"New message from {event.author.nick}",
                f"{prepare_date(event)}: {normalized_content}",
            )

    @send_only_when_connected
    def _send_saicsync_message(self):
        # SAIC: 1/location/avatar/rank/reputation/away<1/0>
        logger.info('Sending "SAICSYNC" message')
        user = self.chat_users[self.state.nick]
        saic_message = "/".join(
            (
                "1",  # version
                user.location.name,
                self.state.player.get_avatar(),
                user.rank,
                str(user.reputation),
                "0",
            )
        )
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=self.config.server.previous_channel,
                content=f"SAICSYNC {saic_message}",
            )
        )

    def _update_crc_users_data(self):
        add_users_list_to_game(self.chat_users.values())

    def route(self):
        raise NotImplementedError

    def _handle_actor_update(self):
        payload = self.event.event.payload
        if isinstance(payload, tuple):
            payload = payload[1]
        logger.debug("Handling ACTOR_UPDATE event")
        if self.config.faction_setting != FactionSetting.GameSynced:
            logger.info(
                'Faction setting is not "GameSynced", skipping actor update, %r',
                self.config.faction_setting,
            )
            return

        try:
            user = self.chat_users[self.state.nick]
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
        self.chat_users.set_user(self.state.nick, user)
        self.current_actor = user.faction
        self.config.current_faction = user.faction
        self.state.player.faction = user.faction
        self._update_avatar()
        self.config.save_config()

        self._update_crc_users_data()
        self._send_amogus_message()
        self._update_ui_user_list()

    def _update_avatar(self):
        if self.config.avatar != AvatarEnum.faction_and_name_based:
            return

        logger.debug(
            "Updating avatar, current: %r", self.config.current_avatar
        )
        value = calculate_icon_based_on_faction_and_name(
            self.state.player.faction.value, self.state.nick
        )
        if value == self.config.current_avatar:
            logger.debug("Avatar is already set to %r, skipping update", value)
            return
        self.config.current_avatar = value
        self.state.player.avatar = value
        try:
            self.chat_users[self.state.nick].avatar = value
        except KeyError:
            pass
        send_saic_avatar(self.state, self.outgoing_queue, self.config)

    def _add_content_of_message(self, content, tags):
        add_content_of_message_to_messages_list(
            self.messages_list, self.hyperlinks, content, tags
        )
