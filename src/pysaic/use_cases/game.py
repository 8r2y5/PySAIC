# effectively this is scripts router and should be refactored so all logic
# is handled in the same way

import asyncio
import logging
from asyncio import AbstractEventLoop
from datetime import datetime
from random import randint

import inject

from pysaic.config import Config
from pysaic.controllers.game import (
    add_setting_to_game,
    add_signal_state,
    ask_for_actor_status,
    set_ingame_display_setting,
)
from pysaic.crc_strings.use_case import DeathMessageUseCase
from pysaic.entities import (
    AppEvent,
    GameEvent,
    IncomingEvent,
    IncomingMessage,
    IncomingQueue,
    IrcUser,
    OutgoingMessage,
    OutgoingPart,
    OutgoingQueue,
)
from pysaic.enums import AppEventEnum, DisconnectOnNetworkDestructionSetting
from pysaic.events.enum import GameEvents
from pysaic.handlers import join_previous_channel
from pysaic.script_reader.entities import (
    Achievement,
    ConnectionLost,
    Death,
    Handshake,
    Money,
    Rank,
    Reputation,
)
from pysaic.state import State
from pysaic.use_cases.text import make_content_malformed

logger = logging.getLogger(__name__)

SECONDS_BETWEEN_DEATHS = 30

# by trail and error, game shows "Connection lost" message after 10 seconds
# even that signal is sent immediately after disconnect.
SLEEP_TIME_BEFORE_DISCONNECT = 10


class PlayerDiedUseCase:
    @property
    def channel(self):
        return self.config.server.previous_channel

    def __init__(
        self,
        config,
        death: Death,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        self.death = death
        self.config = config
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    @inject.autoparams()
    async def execute(self, state: State):
        if self.config.death_reports is False:
            logger.info("Death reporting is disabled, ignoring death message")
            return

        now = datetime.now()
        if (
            state.last_death is not None
            and (now - state.last_death).total_seconds()
            < SECONDS_BETWEEN_DEATHS
        ):
            logger.info("Ignoring death message because of cooldown")
            return
        else:
            state.last_death = now

        try:
            message = DeathMessageUseCase(
                state, self.config, state.nick, self.death
            ).execute()
        except Exception:
            logger.exception("Could not generate death message")
            return

        logger.debug("Player death message: %r", message)

        async def send_later():
            await asyncio.sleep(randint(3, SECONDS_BETWEEN_DEATHS))
            await self.incoming_queue.put(
                IncomingMessage(
                    author=IrcUser(state.nick, None, None),
                    target=self.channel,
                    content=message,
                )
            )
            await self.outgoing_queue.put(
                OutgoingMessage(
                    target=self.channel,
                    content=message,
                )
            )

        await self.incoming_queue.put(
            IncomingEvent.create_game_event(GameEvents.AFK, "death message")
        )
        await send_later()


class GameHandshakeUseCase:
    def __init__(
        self,
        state: State,
        config: Config,
        handshake: Handshake,
        incoming_queue: IncomingQueue,
    ):
        self.state = state
        self.handshake = handshake
        self.config = config
        self.incoming_queue = incoming_queue

    async def execute(self):
        logger.info("Game handshake: %r", self.handshake)

        if self.state.id == self.handshake.handshake_id:
            if not self.state.got_first_handshake.is_set():
                self.state.got_first_handshake.set()
                self.incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        "Got response from game. Chat is now synced with game.",
                    )
                )
        # if else then messages are not sent during this "session"
        # meaning it they would be from previous gaming session or
        # after restarting up or perhaps game just asking for information.

        await self.incoming_queue.put(
            IncomingEvent(
                author="pysaic",
                target=self.config.server.previous_channel,
                event=GameEvent(
                    what=GameEvents.HANDSHAKE, payload=self.handshake
                ),
            )
        )
        self._send_settings_to_game()
        ask_for_actor_status()
        await self.incoming_queue.put(
            IncomingEvent(
                author="pysaic",
                target=self.config.server.previous_channel,
                event=AppEvent(what=AppEventEnum.UPDATE_USERS),
            )
        )

    def _send_settings_to_game(self):
        add_setting_to_game("NewsDuration", str(self.config.news_duration))
        add_setting_to_game("ChatKey", self.config.chat_key.upper())
        add_setting_to_game(
            "NickAutoCompleteKey",
            self.config.nick_auto_complete_key.upper(),
        )
        add_setting_to_game("NewsSound", str(self.config.news_sound).title())
        add_setting_to_game("CloseChat", str(self.config.close_chat).title())
        add_setting_to_game(
            "DisconnectWhenBlowoutOrUnderground",
            str(True).title(),
        )
        add_setting_to_game(
            "CurrentChannel", self.config.server.previous_channel
        )
        add_setting_to_game(
            "Channels",
            ",".join(
                f"{channel.name} = {channel.description}"
                for channel in self.config.server.channels
            ),
        )
        set_ingame_display_setting(self.config.in_game_users_display.name)
        add_signal_state(str(self.state.fake_disconnect))


class GameChannelMessageUseCase:
    def __init__(
        self,
        config,
        channel_message,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        self.config = config
        self.channel_message = channel_message
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.logger = logger.getChild("channel_message")

    @inject.autoparams()
    async def execute(self, state: State):
        self.logger.info("Channel message: %r", self.channel_message)

        await self.incoming_queue.put(
            IncomingEvent.create_game_event(GameEvents.AFK, "game message")
        )

        if state.is_in_channel is False:
            self.logger.debug("Not in channel, ignoring message")
            await self.incoming_queue.put(
                IncomingEvent.create_error_event(
                    "Not connected to network yet."
                )
            )
            return

        await self.incoming_queue.put(
            IncomingEvent(
                author=self.channel_message.sender.name,
                target=self.config.server.previous_channel,
                event=AppEvent(
                    what=AppEventEnum.ACTOR_UPDATE,
                    payload=self.channel_message.sender.type,
                ),
            )
        )

        # this has to be last because previous ones will update player faction.
        # if order will be different then player will send message as
        # "previous" faction.
        original_content = content = self.channel_message.message.strip(" ")
        if state.should_malform_messages and not content.startswith("/"):
            self.logger.info(
                "Fake disconnect is set, making content malformed: %r", content
            )
            content = make_content_malformed(content)
        await self.incoming_queue.put(
            IncomingMessage(
                author=IrcUser(self.channel_message.sender.name),
                target=self.config.server.previous_channel,
                content=content,
            )
        )
        # we should only send message if it wasn't a command because it could
        # be private message or some other command that should not be sent
        if not original_content.startswith("/"):
            await self.outgoing_queue.put(
                OutgoingMessage(
                    target=self.config.server.previous_channel,
                    content=content,
                )
            )


class MoneyChangeUseCase:
    def __init__(
        self,
        money: Money,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        self.money = money
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    async def execute(self):
        logger.info("Money change: %r", self.money)
        await self.incoming_queue.put(
            IncomingEvent.create_game_event(
                what=GameEvents.MONEY_CHANGE,
                payload=self.money.amount,
            )
        )


class ConnectionLostUseCase:
    def __init__(
        self,
        config: Config,
        entity: ConnectionLost,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        self.entity = entity
        self.config = config
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    @inject.autoparams()
    async def execute(self, state: State):
        logger.info(
            "Connection lost: %r, should_disconnect: %s, should_malform: %s",
            self.entity,
            self._should_disconnect_on_network_destruction(),
            self._should_only_malform_messages(),
        )
        if state.is_currently_under_network_destruction == self.entity.lost:
            logger.info(
                "Already in the desired state, ignoring",
            )
            return
        state.is_currently_under_network_destruction = self.entity.lost
        if self.entity.lost is True:
            if self._should_disconnect_on_network_destruction():
                self._do_full_disconnect()
            elif self._should_only_malform_messages():
                self._do_only_malform_messages()
        elif self.entity.lost is False:
            self._dont_disconnect()

    def _should_disconnect_on_network_destruction(self):
        return (
            self.config.disconnect_when_blowout_or_underground
            == DisconnectOnNetworkDestructionSetting.Always
        )

    @inject.autoparams()
    def _do_full_disconnect(self, state: State, loop: AbstractEventLoop):
        if state.is_in_channel.is_set() is False:
            logger.debug("Already faking disconnect, ignoring")
            return

        async def _task(reason):
            if reason == "Surge":
                logger.debug(
                    "Waiting for %d seconds before disconnecting",
                    SLEEP_TIME_BEFORE_DISCONNECT,
                )
                await asyncio.sleep(SLEEP_TIME_BEFORE_DISCONNECT)

            add_signal_state(str(True))
            await self.outgoing_queue.put(
                OutgoingPart(
                    channel=self.config.server.previous_channel,
                    content=reason,
                )
            )

        logger.debug("Faking disconnect with reason: %r", self.entity.reason)
        loop.create_task(_task(self.entity.reason), name="fake_disconnect")

    @inject.autoparams()
    def _dont_disconnect(self, state: State):
        logger.debug("Connection lost is False, not faking disconnect")

        add_signal_state(str(state.fake_disconnect))
        join_previous_channel()

    def _should_only_malform_messages(self):
        return (
            self.config.disconnect_when_blowout_or_underground
            == DisconnectOnNetworkDestructionSetting.MalformSignalOnly
        )

    @inject.autoparams()
    def _do_only_malform_messages(self, state: State, loop: AbstractEventLoop):
        logger.debug("Only malforming messages on connection lost")

        async def _task(reason):
            if reason == "Surge":
                content = "[PDA SYSTEM] // Regional communications grid disrupted. Seek shelter immediately."
            else:
                content = "[PDA SYSTEM] // Weak signal detected. Communications may be unreliable."

            await asyncio.sleep(SLEEP_TIME_BEFORE_DISCONNECT)
            self.incoming_queue.create_error_event(content)

        add_signal_state(str(state.fake_disconnect))
        logger.debug("Set fake disconnect to False for malforming messages")
        loop.create_task(
            _task(self.entity.reason), name="malform_only_disconnect"
        )


async def actor_status_use_case(actor_status, incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            what=GameEvents.ACTOR_UPDATE,
            payload=(True, actor_status.value),
        )
    )


async def channel_change_use_case(
    channel_change, incoming_queue: IncomingQueue
):
    await incoming_queue.put(
        IncomingEvent.create_app_event(
            AppEventEnum.GAME_CHANNEL_CHANGE,
            channel_change.channel_description,
        )
    )


async def location_use_case(location, incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            GameEvents.PLAYER_LOCATION,
            location.name,
        )
    )


async def achievement_use_case(
    achievement: Achievement,
    incoming_queue: IncomingQueue,
):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            GameEvents.ACHIEVEMENT,
            achievement,
        )
    )


async def reputation_use_case(
    reputation: Reputation,
    incoming_queue: IncomingQueue,
):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            GameEvents.REPUTATION,
            reputation.value,
        )
    )


async def rank_use_case(
    rank: Rank,
    incoming_queue: IncomingQueue,
):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            GameEvents.RANK,
            rank.value,
        )
    )


async def afk_use_case(
    afk: str,
    incoming_queue: IncomingQueue,
):
    await incoming_queue.put(
        IncomingEvent.create_game_event(
            GameEvents.AFK,
            afk,
        )
    )
