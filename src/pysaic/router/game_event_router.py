import asyncio
import logging
from asyncio import Task
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
from pysaic.enums import (
    AppEventEnum,
    LocationEnum,
    RankEnum,
    ReputationEnum,
    SAICCTCPEnum,
)
from pysaic.events.enum import GameEvents
from pysaic.router.router import Router, send_only_when_connected
from pysaic.router.utils import generic_send_saic_message
from pysaic.script_reader.entities import Achievement, Handshake
from pysaic.settings import LOCATIONS_FOR_ENUM_PATH, SUPPORTED_SCRIPT_VERSION

logger = logging.getLogger(__name__)


def sync_callback_handler(task: Task):
    try:
        task.result()
    except Exception:
        logger.exception(
            "Error during player data sync",
        )


class GameEventRouter(Router):
    async def _send_sync(self, callback):
        await asyncio.sleep(1.0)
        if not self.state.is_in_channel.is_set():
            return

        with self.state.state_lock:
            try:
                changes = self.state.pending_updates
                self.state.pending_updates = {}

                if not changes:
                    return

                logger.debug("Syncing changes: %s", changes)

                if len(changes) == 1:
                    callback()
                else:
                    self._send_saicsync_message()
            except Exception:
                logger.exception("Failed to sync player data: %s")
            finally:
                self.state.player_update_task = None

    def route(self):
        match self.event.event.what:
            case GameEvents.ACTOR_UPDATE:
                self._handle_actor_update()
            case GameEvents.MONEY_CHANGE:
                self._handle_money_change()
            case GameEvents.HANDSHAKE:
                self._handle_game_handshake()
            case GameEvents.PLAYER_LOCATION:
                self._handle_player_location()
            case GameEvents.ACHIEVEMENT:
                self._handle_new_achievement()
            case GameEvents.RANK:
                self._handle_rank()
            case GameEvents.REPUTATION:
                self._handle_reputation()
            case GameEvents.AFK:
                # this if exists only so logger doesn't complain about missing handler
                pass
            case _:
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
        logger.info('Sending "%s" message', SAICCTCPEnum.SAICLOC)
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=self.config.server.previous_channel,
                content=f"{SAICCTCPEnum.SAICLOC} 1/{self.state.player.location.name}",
            )
        )

    @inject.autoparams()
    def _handle_player_generic_field_update(
        self,
        field_name: str,
        method: Callable,
        callback: Callable,
        exception_handler: Callable,
        loop: asyncio.AbstractEventLoop,
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
            self.state.player_changed_values_queue.put_nowait(
                (field_name, value)
            )

            with self.state.state_lock:
                self.state.pending_updates[field_name] = value

                if (
                    self.state.player_update_task is None
                    or self.state.player_update_task.done()
                ):
                    self.state.player_update_task = (
                        asyncio.run_coroutine_threadsafe(
                            self._send_sync(callback), loop
                        )
                    )
                    self.state.player_update_task.add_done_callback(
                        sync_callback_handler
                    )

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
            await self.state.is_in_channel.wait()
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

    # noinspection PyTypeHints
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
            SAICCTCPEnum.SAICREP,
            lambda user: f"1/{user.reputation.value}",
            self.state,
            self.chat_users,
        )

    @send_only_when_connected
    def _send_saic_rank(self):
        generic_send_saic_message(
            self.outgoing_queue,
            self.config.server.previous_channel,
            SAICCTCPEnum.SAICRANK,
            lambda user: f"1/{user.rank}",
            self.state,
            self.chat_users,
        )

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
