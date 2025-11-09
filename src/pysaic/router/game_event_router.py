import asyncio
import logging
from datetime import UTC, datetime
from random import randint
from typing import Callable

import inject

from pysaic.crc_strings.use_case import TravelMessageUseCase
from pysaic.entities import (
    IncomingEvent,
    IncomingMessage,
    IrcUser,
    OutgoingCTCP,
    OutgoingMessage,
)
from pysaic.enums import AppEventEnum, LocationEnum, RankEnum, ReputationEnum
from pysaic.events.enum import GameEvents
from pysaic.router.router import Router, send_only_when_connected
from pysaic.router.utils import generic_send_saic_message
from pysaic.script_reader.entities import Achievement, Handshake
from pysaic.settings import LOCATIONS_FOR_ENUM_PATH, SUPPORTED_SCRIPT_VERSION

logger = logging.getLogger(__name__)

_INVALID_VALUE = object()


class GameEventRouter(Router):
    def route(self):
        if self.event.event.what == GameEvents.ACTOR_UPDATE:
            self._handle_actor_update()
        elif self.event.event.what == GameEvents.MONEY_CHANGE:
            self._handle_money_change()
        elif self.event.event.what == GameEvents.HANDSHAKE:
            self._handle_game_handshake()
        elif self.event.event.what == GameEvents.PLAYER_LOCATION:
            self._handle_player_location()
        elif self.event.event.what == GameEvents.ACHIEVEMENT:
            self._handle_new_achievement()
        elif self.event.event.what == GameEvents.RANK:
            self._handle_rank()
        elif self.event.event.what == GameEvents.REPUTATION:
            self._handle_reputation()
        elif self.event.event.what == GameEvents.AFK:
            # this if exists only so logger doesn't complain about missing handler
            pass
        else:
            logger.warning("Unknown game event: %r", self.event)
        # this should be always at the end since game is sending signals
        self._handle_not_afk()

    def _handle_money_change(self):
        self.state.player.money = int(self.event.event.payload)

    def _handle_game_handshake(self):
        payload: Handshake = self.event.event.payload
        if payload.version in SUPPORTED_SCRIPT_VERSION:
            return

        logger.error("Unsupported handshake version: %r", payload.version)
        self._add_error_text("Please update your game script.")

    def _send_saic_location(self):
        logger.info('Sending "SAICLOC" message')
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=self.config.server.previous_channel,
                content=f"SAICLOC 1/{self.state.player.location.name}",
            )
        )

    def _handle_player_generic_field_update(
        self,
        field_name: str,
        method: Callable,
        callback: Callable,
        exception_handler: Callable,
    ):
        try:
            value = method(self.event.event.payload)
        except Exception as error:
            logger.debug(
                "Invalid %r value: %r",
                field_name,
                self.event.event.payload,
                exc_info=True,
            )
            if not exception_handler(error):
                raise
            return

        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            # it happens when user is not in connected to the channel
            setattr(self.state.player, field_name, value)
        else:
            if getattr(user, field_name) == value:
                logger.debug(
                    "Value for field %r is the same, skipping update",
                    field_name,
                )
                return
            setattr(user, field_name, value)
            self._update_crc_users_data()
            setattr(self.state.player, field_name, value)
            callback()

    def _handle_player_location(self):
        logger.debug("Handling PLAYER_LOCATION event")

        def exception_handler(_error):
            if self.event.event.payload == "fake_start":
                self._send_saic_location()
            else:
                logger.exception(
                    "Unknown location: %r", self.event.event.payload
                )
                self._add_error_text(
                    f"Unknown location: {self.event.event.payload}. "
                    f"Please add it to {LOCATIONS_FOR_ENUM_PATH} and "
                    f"restart the app."
                )
            return True

        try:
            user = self.chat_users[self.state.nick]
        except KeyError:
            pass
        else:
            if (
                user.location != LocationEnum.unknown
                and self.event.event.payload
                not in ("fake_start", "", LocationEnum.unknown.name)
                and user.location.name != self.event.event.payload
            ):
                if randint(0, 49) == 0:
                    self._notify_chat_about_location_change()

        self._handle_player_generic_field_update(
            "location",
            method=lambda payload: LocationEnum[payload],
            callback=self._send_saic_location,
            exception_handler=exception_handler,
        )

    @inject.autoparams
    def _handle_new_achievement(self, loop: asyncio.AbstractEventLoop):
        async def _post_achievement_to_chat():
            while not self.state.is_in_channel.is_set():
                await asyncio.sleep(5)
            payload: Achievement = self.event.event.payload
            content = f'Just unlocked achievement "{payload.name}".'
            self.outgoing_queue.put_nowait(
                OutgoingMessage(
                    target=self.config.server.previous_channel,
                    content=content,
                )
            )
            self.incoming_queue.put_nowait(
                IncomingMessage(
                    author=IrcUser(self.nick, None, None),
                    target=self.config.server.previous_channel,
                    content=content,
                )
            )
        loop.create_task(_post_achievement_to_chat())

    def _handle_rank(self):
        logger.debug("Handling GAME_RANK event")
        self._handle_player_generic_field_update(
            "rank",
            method=lambda payload: RankEnum(payload),
            callback=self._send_saic_rank,
            exception_handler=lambda _error: True,
        )

    def _handle_reputation(self):
        logger.debug("Handling GAME_REPUTATION event")
        self._handle_player_generic_field_update(
            "reputation",
            method=lambda payload: ReputationEnum[payload],
            callback=self._send_saic_reputation,
            exception_handler=lambda _error: True,
        )

    @send_only_when_connected
    def _send_saic_reputation(self):
        generic_send_saic_message(
            self.outgoing_queue,
            self.config.server.previous_channel,
            "SAICREP",
            lambda user: f"1/{user.reputation.value}",
            self.state,
            self.chat_users,
        )
        # logger.info('Sending "SAICREP" message')
        # try:
        #     user = self.chat_users[self.nick]
        # except KeyError:
        #     logger.exception("User was missing in chat_users.")
        #     user = self._readd_user_to_chat_users()
        #
        # self.outgoing_queue.put_nowait(
        #     OutgoingCTCP(
        #         target=self.config.server.previous_channel,
        #         content=f"SAICREP 1/{user.reputation.value}",
        #     )
        # )

    @send_only_when_connected
    def _send_saic_rank(self):
        generic_send_saic_message(
            self.outgoing_queue,
            self.config.server.previous_channel,
            "SAICRANK",
            lambda user: f"1/{user.rank}",
            self.state,
            self.chat_users,
        )
        # logger.info('Sending "SAICRANK" message')
        # try:
        #     user = self.chat_users[self.nick]
        # except KeyError:
        #     logger.exception("User was missing in chat_users.")
        #     user = self._readd_user_to_chat_users()
        #
        # self.outgoing_queue.put_nowait(
        #     OutgoingCTCP(
        #         target=self.config.server.previous_channel,
        #         content=f"SAICRANK 1/{user.rank}",
        #     )
        # )

    def _handle_not_afk(self):
        logger.debug("Handling NOT_AFK event")
        self.state.player.last_ask_update = datetime.now(UTC)
        if self.state.player.afk is False:
            return

        self.incoming_queue.put_nowait(
            IncomingEvent.create_app_event(AppEventEnum.SET_NOT_AFK, None)
        )

    def _notify_chat_about_location_change(self):
        logger.info(
            "Sending travel message to %s",
            self.config.server.previous_channel,
        )
        message = TravelMessageUseCase(
            self.state,
            self.config,
            self.nick,
            self.event.event.payload,
        ).execute()
        if not message:
            logger.warning("Travel message is empty, skipping sending")
            return
        logger.debug("Travel message: %r", message)
        self.incoming_queue.put_nowait(
            IncomingMessage(
                author=IrcUser(self.nick, None, None),
                target=self.config.server.previous_channel,
                content=message,
            )
        )
        self.outgoing_queue.put_nowait(
            OutgoingMessage(
                target=self.config.server.previous_channel,
                content=message,
            )
        )
