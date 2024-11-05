import asyncio
import logging
from datetime import datetime
from random import randint

import inject

from pysaic.config import Config
from pysaic.controllers.game import add_setting_to_game
from pysaic.crc_strings.use_case import DeathMessageUseCase
from pysaic.entities import (
    AppEvent,
    IncomingEvent,
    IncomingMessage,
    OutgoingMessage,
    OutgoingPart,
    GameEvent,
)
from pysaic.enums import AppEventEnum
from pysaic.events.enum import GameEvents
from pysaic.handlers import join_previous_channel
from pysaic.script_reader.entities import (
    ConnectionLost,
    Death,
    Handshake,
    Money,
)
from pysaic.state import State

logger = logging.getLogger(__name__)

SECONDS_BETWEEN_DEATHS = 30


class PlayerDiedUseCase:
    @property
    def nick(self):
        return self.config.nick

    @property
    def channel(self):
        return self.config.server.previous_channel

    def __init__(
        self,
        config,
        death: Death,
        incoming_queue,
        outgoing_queue,
    ):
        self.death = death
        self.config = config
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    @inject.autoparams()
    async def execute(self, state: State):
        now = datetime.now()
        if (
            state.last_death is not None
            and (now - state.last_death).total_seconds()
            < SECONDS_BETWEEN_DEATHS
        ):
            logger.debug("Ignoring death message because of cooldown")
            return
        else:
            state.last_death = now

        try:
            message = DeathMessageUseCase(self.nick, self.death).execute()
        except Exception:
            logger.exception("Could not generate death message")
            return

        logger.debug("Player death message: %r", message)

        async def send_later():
            await asyncio.sleep(randint(3, SECONDS_BETWEEN_DEATHS))
            await self.incoming_queue.put(
                IncomingMessage(
                    author=self.nick,
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

        await send_later()


class GameHandshakeUseCase:
    def __init__(
        self,
        config: Config,
        handshake: Handshake,
        incoming_queue,
    ):
        self.handshake = handshake
        self.config = config
        self.incoming_queue = incoming_queue

    async def execute(self):
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
        self._ask_for_actor_status()
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
            str(self.config.disconnect_when_blowout_or_underground).title(),
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

    def _ask_for_actor_status(self):
        add_setting_to_game("ActorStatus", "")


class GameChannelMessageUseCase:
    def __init__(
        self,
        config,
        channel_message,
        incoming_queue,
        outgoing_queue,
    ):
        self.config = config
        self.channel_message = channel_message
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    @inject.autoparams()
    async def execute(self, state: State):
        logger.info("Channel message: %r", self.channel_message)

        if state.is_in_channel is False:
            logger.debug("Not in channel, ignoring message")
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
        await self.incoming_queue.put(
            IncomingMessage(
                author=self.channel_message.sender.name,
                target=self.config.server.previous_channel,
                content=self.channel_message.message,
            )
        )
        if not self.channel_message.message.startswith("/"):
            await self.outgoing_queue.put(
                OutgoingMessage(
                    target=self.config.server.previous_channel,
                    content=self.channel_message.message,
                )
            )


class MoneyChangeUseCase:
    def __init__(
        self,
        money: Money,
        incoming_queue,
        outgoing_queue,
    ):
        self.money = money
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    async def execute(self):
        logger.info("Money change: %r", self.money)
        await self.incoming_queue.put(
            IncomingEvent(
                author="",
                target="",
                event=GameEvent(
                    what=GameEvents.MONEY_CHANGE,
                    payload=self.money.amount,
                ),
            )
        )


class ConnectionLostUseCase:
    def __init__(
        self,
        config: Config,
        entity: ConnectionLost,
        incoming_queue,
        outgoing_queue,
    ):
        self.entity = entity
        self.config = config
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue

    @inject.autoparams()
    async def execute(self, state: State):
        if (
            self.entity.lost is True
            and self.config.disconnect_when_blowout_or_underground
        ):
            if state.fake_disconnect:
                return

            state.fake_disconnect = True
            outgoing_message = OutgoingPart(
                channel=self.config.server.previous_channel,
                content=self.entity.reason,
            )
        elif self.entity is False or self.entity.lost is False:
            if not state.fake_disconnect:
                return

            state.fake_disconnect = False
            join_previous_channel()
        else:
            return

        await self.outgoing_queue.put(outgoing_message)


async def actor_status_use_case(
    actor_status,
    incoming_queue,
):
    await incoming_queue.put(
        IncomingEvent(
            author="",
            target="",
            event=GameEvent(
                what=GameEvents.ACTOR_UPDATE,
                payload=(True, actor_status.value),
            ),
        )
    )


async def channel_change_use_case(
    channel_change,
    incoming_queue,
):
    await incoming_queue.put(
        IncomingEvent.create_app_event(
            AppEventEnum.GAME_CHANNEL_CHANGE,
            channel_change.channel_description,
        )
    )
