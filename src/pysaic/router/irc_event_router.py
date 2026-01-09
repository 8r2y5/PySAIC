import logging
import re
from contextlib import suppress
from tkinter import END

import inject

from pysaic.config import Config
from pysaic.crc_strings.use_case import random_name
from pysaic.entities import (
    ChatUser,
    IncomingEvent,
    IrcUser,
    OutgoingCommand,
    OutgoingCTCP,
)
from pysaic.enums import FactionsEnum, IrcEvents
from pysaic.irc_protocol import PySaicIrcProtocol
from pysaic.router.router import Router
from pysaic.state import State
from pysaic.use_cases.ui.mode_change import ModeChangeUseCase
from pysaic.use_cases.ui.utils import enable_disable

logger = logging.getLogger(__name__)

BAN_REGEXP = re.compile(r"You are banned \((#\w+)\)")


class IrcEventRouter(Router):
    @classmethod
    def handle(cls, state: State, config: Config, ui, event: IncomingEvent):
        cls(state, config, ui, event).route()

    def route(self):
        # TODO: replace with dict mapping or or add them dynamically
        if self.event.event.type == IrcEvents.JOIN:
            self._user_joined_use_case()
        elif self.event.event.type in [IrcEvents.PART, IrcEvents.QUIT]:
            self._handle_part_or_quit()
        elif self.event.event.type == IrcEvents.NICK:
            self._user_nick_change()
        elif self.event.event.type == IrcEvents.USER:
            self._handle_nick_changed_by_server()
        elif self.event.event.type == IrcEvents.NAMES:
            self._add_names(self.event.event.payload["nicks"])
        elif self.event.event.type == IrcEvents.NOTICE:
            self._handle_notice()
        elif self.event.event.type == IrcEvents.END_OF_NAMES:
            self._handle_end_of_names()
        elif self.event.event.type == IrcEvents.BANNED_FROM_CHANNEL:
            self._hande_user_is_banned()
        elif self.event.event.type == IrcEvents.NOT_IN_THE_CHANNEL:
            self._handle_not_in_channel()
        elif self.event.event.type == IrcEvents.KICK:
            self._handle_user_is_kicked()
        elif self.event.event.type == IrcEvents.Message_of_the_Day_Start:
            self._handle_message_of_the_day_start()
        elif self.event.event.type == IrcEvents.Message_of_the_Day_End:
            self._handle_message_of_the_day_end()
        elif self.event.event.type == IrcEvents.MODE:
            ModeChangeUseCase.handle(
                self.state, self.ui, self.chat_users, self.event
            )
        elif self.event.event.type == IrcEvents.ERROR_IN_NICKNAME:
            self._handle_error_in_nickname()
        else:
            self._add_error_text(
                f"Unknown IRC event: {self.event.event.type!r}"
            )
            logger.warning("Unknown IRC event: %r", self.event)
            return
        self._update_crc_users_data()

    def _user_joined_use_case(self):
        self._add_names([self.event.author.nick], single=True)
        if self.event.author.nick == self.state.nick:
            return
        self._add_information_text(f"{self.event.author.nick} has logged in.")

    def _handle_part_or_quit(self):
        with suppress(KeyError):
            self.chat_users.remove_user(self.event.author.nick)
        self._update_ui_user_list()

        if self.event.author.nick == self.state.nick:
            return

        if self.event.event.type == IrcEvents.PART:
            if self.event.event.payload:
                self._add_information_text(
                    f"{self.event.author.nick} {self.event.event.payload['reason']}"
                )
            else:
                self._add_information_text(
                    f"{self.event.author.nick} has left the channel."
                )
        else:
            self._add_information_text(f"{self.event.author.nick} has quit.")

    def _user_nick_change(self):
        new_nick = self.event.event.payload["new_nick"]
        logger.debug(
            "User nick change: %r -> %r", self.event.author.nick, new_nick
        )

        try:
            previous_chat_user = self.chat_users.pop(self.event.author.nick)
        except KeyError:
            if self.event.author.nick == self.state.nick:
                previous_chat_user = self.state.player.create_chat_user()
            else:
                previous_chat_user = self.chat_users.update_or_create(
                    self.event.author.nick, FactionsEnum.Anonymous.value
                )

        self.chat_users.set_user(
            new_nick,
            ChatUser(
                name=new_nick,
                faction=previous_chat_user.faction,
                in_game=previous_chat_user.in_game,
                location=previous_chat_user.location,
                rank=previous_chat_user.rank,
                reputation=previous_chat_user.reputation,
                irc_user=self.event.author,
            ),
        )
        self._add_information_text(
            f"{self.event.author.nick!r} is know now as {new_nick!r}."
        )
        logger.debug(
            "User nick change processed: %r -> %r (state: %r, config: %r)",
            self.event.author.nick,
            new_nick,
            self.state.nick,
            self.config.nick,
        )
        if self.event.author.nick == self.state.nick:
            self.state.nick = new_nick
        self._update_ui_user_list()

    def _handle_nick_changed_by_server(self):
        new_nick = self.event.event.payload["new_nick"]
        logger.debug(
            "User nick was changed by server: %r -> %r",
            self.event.author,
            new_nick,
        )
        previous_chat_user = self.chat_users.pop(self.event.author)
        self.chat_users[new_nick] = ChatUser(
            name=new_nick,
            faction=previous_chat_user.faction,
            in_game=previous_chat_user.in_game,
            location=previous_chat_user.location,
        )
        self._add_information_text(
            f"Network server renamed you to {new_nick!r}."
        )
        self._update_ui_user_list()

    def _handle_notice(self):
        if self.event.author == "NickServ":
            self._add_dm_message(service=True)

    def _add_dm_message(self, service=False):
        logger.debug("Adding dm message: %r", self.event)
        with enable_disable(self.messages_list):
            self._add_date_to_message(self.event)
            self._add_user_and_faction_color(
                self.event.author.nick, service=service
            )
            self.messages_list.insert(END, " -> ", "DM")
            self._add_user_and_faction_color(self.event.target)
            self._add_content_to_message(self.event)

    def _handle_end_of_names(self):
        self._add_information_text("Connected to the channel.")

        self.ui.enable_input()
        self.state.set_in_channel()
        self._ask_others_for_user_data()
        self._send_user_data_as_privmsg()

    def _hande_user_is_banned(self):
        logger.debug("User banned: %r", self.event.event.payload)
        self._add_error_text(
            f"{self.event.event.payload} has been banned from the channel."
        )

    def _handle_not_in_channel(self):
        ban_match_result = BAN_REGEXP.match(self.event.event.payload)
        if ban_match_result:
            channel_name = next(
                (
                    channel.description
                    for channel in self.config.server.channels
                    if ban_match_result.group(1) == channel.name
                ),
                None,
            )
            if channel_name is None:
                logger.error(
                    "Channel name not found for %r", ban_match_result.group(1)
                )
                self._add_error_text("You are banned on channel.")
                return

            self._add_error_text(f"You are banned on {channel_name!r}.")

    def _handle_user_is_kicked(self):
        self._add_information_event(
            IncomingEvent.create_information_event(
                content=(
                    f"{self.event.event.payload['kicked_nick']} was kicked by "
                    f"{self.event.author}: "
                    f"{self.event.event.payload['reason']}"
                )
            )
        )
        self.state.chat_users.remove_user(
            self.event.event.payload["kicked_nick"]
        )
        self._update_ui_user_list()

    def _add_names(self, names, single=False):
        for name in names:
            user_mode, key_name = re.match(r"^([%&@*+]?)(.+)$", name).groups()
            if key_name in self.chat_users:
                continue

            logger.debug("Adding name: %r, %r, %r", name, user_mode, key_name)
            if name == self.state.nick:
                self.state.player.irc_mode = user_mode
                chat_user = self.state.player.create_chat_user()
                chat_user.faction = self.config.current_faction
                self.state.player.faction = self.config.current_faction
            else:
                chat_user = ChatUser(name=key_name, irc_mode=user_mode)

            if single is True and isinstance(self.event.author, IrcUser):
                chat_user.irc_user = self.event.author

            self.chat_users.add_user(key_name, chat_user)
        self._update_ui_user_list()

    def _ask_others_for_user_data(self):
        logger.debug("Asking others for user data")
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=self.config.server.previous_channel,
                content="USERDATA",
                send_as=IrcEvents.PRIVMSG,
            )
        )

    def _send_user_data_as_privmsg(self):
        logger.debug("Sending USERDATA as privmsg to channel")
        self._send_amogus_message()
        self._send_saicsync_message()

    def _handle_message_of_the_day_start(self):
        self._add_information_text("Received response from the server.")

    def _handle_message_of_the_day_end(self):
        self._add_information_text("Finishing initialization.")
        for command in self.config.server.commands:
            logger.info("Sending server command: %r", command)
            self.outgoing_queue.put_nowait(
                OutgoingCommand(
                    command=command.format(nick=self.nick), args=[]
                )
            )
        # self.outgoing_queue.put_nowait(
        #     OutgoingCommand(
        #         command=IrcEvents.MODE,
        #         args=[f"{self.nick} +x"],
        #     )
        # )

    @inject.autoparams()
    def _handle_error_in_nickname(self, irc: PySaicIrcProtocol):
        logger.warning(
            "Received error in nickname: %r", self.event.event.payload
        )
        self.ui.disable_input()
        self.state.set_not_in_channel()
        previous_user = self.state.chat_users.pop(self.nick, None)
        self.state.player.nick = self.config.nick = random_name().replace(
            " ", "_"
        )
        self.config.save_config()

        self._add_error_text(
            "Error in nickname - changing it to a random one. Please wait."
        )
        self.outgoing_queue.put_nowait(
            OutgoingCommand(command=IrcEvents.NICK, args=self.nick)
        )
        if previous_user:
            self.chat_users.add_user(self.nick, previous_user)
        irc.nick = self.nick
