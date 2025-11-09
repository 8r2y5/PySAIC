import logging
from datetime import UTC, datetime, timedelta
from logging import LogRecord
from tkinter import END

from pysaic.controllers.game import (
    ask_for_actor_status,
    ask_for_handshake,
    set_ingame_display_setting,
)
from pysaic.entities import (
    IncomingEvent,
    OutgoingCommand,
    OutgoingJoin,
    OutgoingPart,
)
from pysaic.enums import AppEventEnum
from pysaic.log import escape_stand_and_end
from pysaic.router.router import Router
from pysaic.router.utils import send_saic_afk, send_saic_avatar
from pysaic.settings import ANOMALY_DIR_PATH, GAMEDATA_PATH, WORKDIR
from pysaic.tasks.afk import ensure_afk_tasks_are_running, stop_afk_tasks
from pysaic.use_cases.command import CommandUseCase
from pysaic.use_cases.common import join_previous_channel
from pysaic.use_cases.ui.our_message import OurMessageUseCase
from pysaic.use_cases.ui.utils import enable_disable, normalize_content

logger = logging.getLogger(__name__)


class AppEventRouter(Router):
    def route(self):
        if self.event.event.what != AppEventEnum.RAW_IRC_MESSAGE:
            logger.debug("Handling AppEvent: %r", self.event)
        # TODO: replace with dict mapping or or add them dynamically
        if self.event.event.what == AppEventEnum.UPDATE_USERS:
            self._update_crc_users_data()
        elif self.event.event.what == AppEventEnum.ACTOR_UPDATE:
            self._handle_actor_update()
        elif self.event.event.what == AppEventEnum.IN_GAME:
            self._handle_in_game()

        # TODO: fix this mess
        # TODO: i dont even know if this is correct or what to change
        elif (
            self.event.event.what == AppEventEnum.DISCONNECTED_FROM_PDA_NETWORK
        ):
            self._handle_disconnected_from_channel()

        elif self.event.event.what == AppEventEnum.UPDATE_UI_USERS_LIST:
            self._handle_update_ui_users_list()
        elif self.event.event.what == AppEventEnum.OPTIONS_UPDATED:
            self._handle_options_updated()
        elif self.event.event.what == AppEventEnum.OUR_MESSAGE:
            OurMessageUseCase(
                self.state,
                self.config,
                self.ui,
                self.outgoing_queue,
                self.incoming_queue,
            ).execute(self.event.event.payload)
        elif self.event.event.what == AppEventEnum.COMMAND:
            self._handle_command()
        elif self.event.event.what == AppEventEnum.NICKNAME_CHANGED:
            self._handle_nickname_changed()
        elif self.event.event.what == AppEventEnum.CONNECTION_TO_SERVER_ISSUE:
            self._handle_connection_to_server_issue()
        elif self.event.event.what == AppEventEnum.NEW_VERSION:
            self._add_information_text(
                f"New version available: {self.event.event.payload}"
            )

        # TODO: merge those into one
        elif self.event.event.what == AppEventEnum.GAME_CHANNEL_CHANGE:
            self._handle_game_channel_change(self.event.event.payload)
        elif self.event.event.what == AppEventEnum.CHANGE_CHANNEL:
            self._handle_app_channel_change()

        elif self.event.event.what == AppEventEnum.CHECK_AFK:
            self._handle_afk_check()

        elif self.event.event.what == AppEventEnum.SET_NOT_AFK:
            self._set_user_not_afk()

        elif self.event.event.what == AppEventEnum.SET_AFK:
            self._set_user_not_afk()

        elif self.event.event.what == AppEventEnum.TOGGLE_AFK:
            self._handle_toggle_afk()

        elif self.event.event.what == AppEventEnum.FOCUS:
            self._handle_focus_window()

        elif self.event.event.what == AppEventEnum.RAW_IRC_MESSAGE:
            self._handle_raw_irc_message()

        else:
            logger.warning("Unknown AppEvent: %r", self.event)

    def _handle_in_game(self):
        payload = self.event.event.payload
        logger.debug("Handling IN_GAME event, %r", payload)
        if payload[0] is True:
            self._handle_in_game_true(payload[1])
            self._add_information_text(
                f"Found game process, {self.state.game_location}. "
                f"Waiting for game to respond..."
            )

        else:
            self.state.is_game_running, self.state.game_location = payload
            self.state.player.reset()
            self.state.got_first_handshake.clear()

        self.chat_users.set_user(
            self.state.nick, self.state.player.create_chat_user()
        )

        self._handle_user_state_according_to_game_process()

        self._update_ui_user_list()
        self._update_crc_users_data()
        self._send_amogus_message()

    def _handle_disconnected_from_channel(self):
        if self.event.event.payload in ("Surge", "Underground"):
            self._add_error_text("Lost connection to the network.")
        self.ui.disable_input()
        self.state.set_not_in_channel()
        self.state.player.irc_mode = ""

    def _handle_update_ui_users_list(self):
        logger.debug("Handling UPDATE_UI_USERS_LIST event")
        self._update_ui_user_list()

    def _update_faction_setting(self):
        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            try:
                user = self.chat_users[self.config.nick]
            except KeyError:
                return

        if self.config.current_faction != user.faction:
            try:
                self.chat_users.update_user_faction(
                    self.state.nick, self.config.current_faction
                )
            except KeyError:
                logger.warning('Having no user for nick "%s"', self.state.nick)
                self.chat_users.set_user(
                    self.state.nick, self.state.player.create_chat_user()
                )
            self.state.player.faction = self.config.current_faction
            self._send_amogus_message()

    def _update_ingame_display_setting(self):
        set_ingame_display_setting(self.config.in_game_users_display.name)

    def _update_nick_from_options(self):
        logger.debug("Updating nick")
        self.outgoing_queue.put_nowait(
            OutgoingCommand.create_nick_command(self.config.nick)
        )
        user = self.chat_users.pop(self.state.nick, None)
        if user is not None:
            user.name = self.config.nick
        else:
            user = self.state.player.create_chat_user()
        self.chat_users.set_user(self.state.nick, user)
        self.state.nick = self.config.nick
        self.config.save_config()
        self._update_ui_user_list()
        self._send_amogus_message()
        self._add_information_text(f"Nick changed to {self.state.nick!r}")

    def _handle_options_updated(self):
        logger.debug("Handling OPTIONS_UPDATED event")
        self._add_information_text("Options have been updated.")

        self._update_crc_users_data()
        self._update_faction_setting()
        self._update_ingame_display_setting()
        self._update_ui_user_list()

        if self.state.nick != self.config.nick:
            self._update_nick_from_options()

        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            # happens when user is not connected to channel
            # update will be handled with SAICSYNC
            pass
        else:
            if user.avatar != self.config.current_avatar:
                self.chat_users[self.state.nick].avatar = (
                    self.state.player.get_avatar(myself=True)
                )
                send_saic_avatar(self.state, self.outgoing_queue, self.config)

    def _handle_command(self):
        content = self.event.event.payload
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

    def _handle_nickname_changed(self):
        logger.debug("Handling NICKNAME_CHANGED event")
        new_nick = self.event.event.payload["nick"]

        if new_nick in self.chat_users:
            self._handle_nickname_changed_collision(new_nick)
            return

        self.chat_users.pop(self.state.nick, None)
        if self.config.password:
            if new_nick == self.config.nick:
                logger.debug(
                    "Changing back to original nick %r from %r",
                    self.state.nick,
                    self.config.nick,
                )
            else:
                logger.debug(
                    'Recovering nick to "%s", temporary switching to %r',
                    self.config.nick,
                    new_nick,
                )
            self.state.nick = new_nick
        else:
            logger.debug(
                "I have no password, not recovering, changing %r -> %r",
                self.state.nick,
                new_nick,
            )
            self.config.nick = self.state.nick = new_nick
            self.config.save_config()

        self.chat_users[new_nick] = self.state.player.create_chat_user()
        self._update_ui_user_list()
        self._add_information_text(f"Nick changed to {self.state.nick!r}")

    def _handle_connection_to_server_issue(self):
        self._add_information_text(
            f"Connection problem: {self.event.event.payload}"
        )
        self.state.got_welcome_message.clear()
        self.ui.disable_input()
        self.state.set_not_in_channel()
        self.state.is_author_authorized.clear()
        self._update_ui_user_list()
        self._update_crc_users_data()

    def _handle_game_channel_change(self, payload):
        part = OutgoingPart(channel=self.config.server.previous_channel)
        self.config.server.previous_channel = {
            channel.description: channel.name
            for channel in self.config.server.channels
        }[payload]
        self.config.save_config()
        self.outgoing_queue.put_nowait(part)
        logger.debug('Game asks to join channel "%s"', payload)
        self.outgoing_queue.put_nowait(
            OutgoingJoin(channel=self.config.server.previous_channel)
        )
        self._add_information_text(f"Channel changed to {payload}")

    def _handle_app_channel_change(self):
        self._handle_game_channel_change(
            {
                channel.name: channel.description
                for channel in self.config.server.channels
            }[self.event.event.payload]
        )

    def _handle_afk_check(self):
        logger.debug("Handling AFK check, status is %r", self.state.player.afk)
        if (
            not self.state.player.last_ask_update
            or (self.state.player.last_ask_update + timedelta(minutes=10))
            > datetime.now(UTC)
            or self.state.player.afk is True
        ):
            return

        self._set_user_afk()

    def _handle_user_state_according_to_game_process(self):
        if self.state.is_game_running:
            ensure_afk_tasks_are_running()

            if (
                self.state.got_welcome_message.is_set()
                and not self.state.is_in_channel.is_set()
                and self.state.fake_disconnect is False
            ):
                join_previous_channel()
        else:
            logger.debug("Game is not running, stopping AFK tasks")
            stop_afk_tasks()
            if not self.state.is_in_channel.is_set():
                ask_for_actor_status()
                self.state.is_currently_under_network_destruction = False
                logger.debug("Joining previous channel")
                join_previous_channel()

    def _set_user_afk(self):
        self._change_afk_value(True)

    def _set_user_not_afk(self):
        self._change_afk_value(False)

    def _change_afk_value(self, value: bool):
        if value is True and not self.state.player.afk:
            self._add_information_text("You are now marked as AFK.")
        elif value is False and self.state.player.afk:
            self._add_information_text("You are not longer marked as AFK.")

        prev_value = self.state.player.afk
        self.state.player.afk = value
        try:
            self.chat_users[self.state.nick].afk = value
        except KeyError:
            # it happens when user is not in connected to the channel
            # upon connection everything will be made up to date
            pass
        else:
            if prev_value != value:
                send_saic_afk(self.state, self.outgoing_queue, self.config)
                self._update_ui_user_list()

    def _handle_toggle_afk(self):
        self._change_afk_value(not self.state.player.afk)

    def _handle_in_game_true(self, payload):
        self.state.is_game_running = True
        logger.info("Game is running, location: %s", payload)

        if ANOMALY_DIR_PATH and ANOMALY_DIR_PATH.exists():
            self.state.game_location = ANOMALY_DIR_PATH
            logger.info(
                "Using ANOMALY_DIR_PATH instead: %s",
                self.state.game_location,
            )

        elif payload and (payload / "gamedata").exists():
            self.state.game_location = payload
            logger.info("Using payload location: %s", payload)

        elif GAMEDATA_PATH.exists():
            # GAMEDATA_PATH is a path to the gamedata directory
            # so we use WORKDIR instead, because part of code that communicates
            # with the game expects it to be in Anomaly
            self.state.game_location = (GAMEDATA_PATH / "..").resolve()
            logger.info(
                "Using my location as a base for path: %s",
                self.state.game_location,
            )

        else:
            logger.critical(
                "No game location found, using default "
                "WORKDIR: %r, "
                "ANOMALY_DIR_PATH: %r, "
                "GAMEDATA_PATH: %r",
                WORKDIR,
                ANOMALY_DIR_PATH,
                GAMEDATA_PATH,
            )
            self._add_error_text(
                "Could not find game location. "
                "Please install PySAIC in the game directory. "
                "If you use modified exes as mod, please move them into "
                "Anomaly/bin."
            )
            self.state.is_game_running = False
            return

        ask_for_handshake(self.state.id)
        ask_for_actor_status()

    def _handle_nickname_changed_collision(self, new_nick):
        nick_with_underscore = f"{new_nick}_"
        logger.warning(
            "Nick %r is already in use, changing to %r instead",
            new_nick,
            nick_with_underscore,
        )
        self._add_information_text(
            f'Nick "{new_nick}" is already in use, changing to "{nick_with_underscore}" instead.'
        )
        if self.state.nick in self.chat_users:
            if user := self.chat_users.pop(self.state.nick, None):
                user.name = nick_with_underscore
                self.chat_users[nick_with_underscore] = user
        self.incoming_queue.put_nowait(
            OutgoingCommand.create_nick_command(self.state.nick)
        )
        self.incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                AppEventEnum.NICKNAME_CHANGED,
                {
                    "nick": nick_with_underscore,
                    "got_password": self.event.event.payload.get(
                        "got_password"
                    ),
                },
            )
        )

    def _handle_raw_irc_message(self):
        if self.config.irc_window is not True:
            return

        record: LogRecord = self.event.event.payload
        content = normalize_content(
            escape_stand_and_end(record.message)
        ).replace(self.config.password, "********")
        date_time = datetime.fromtimestamp(record.created).strftime("%H:%M:%S")
        with enable_disable(self.ui.irc_messages_list):
            self.ui.irc_messages_list.insert(
                END, f"[{date_time}] {content}\n", ["Text"]
            )

    def _handle_focus_window(self):
        logger.info("Focusing main window")
        self.ui.lift_and_focus()
