import asyncio
import logging
from datetime import datetime
from random import randint
from typing import cast

import inject

from pysaic.config import Config
from pysaic.controllers.game import trigger_hazard_in_game
from pysaic.entities import ChatUser, IncomingQueue
from pysaic.enums import NetworkDestroyReasonEnum
from pysaic.state import State

logger = logging.getLogger(__name__)


@inject.autoparams()
def handle_synced_hazards(
    raw_reason: str | None,
    nick: str,
    loop: asyncio.AbstractEventLoop,
    config: Config,
    state: State,
    incoming_queue: IncomingQueue,
):
    if not config.sync_hazards:
        logger.debug("Synced hazards are disabled")
        return

    if state.got_first_handshake.is_set() is False:
        logger.debug("First handshake not received, skipping")
        return

    if (
        state.is_currently_under_network_destruction
        != NetworkDestroyReasonEnum.none
    ):
        logger.debug("Currently under network destruction, skipping")
        return

    if user := state.chat_users.get(nick):
        user = cast(ChatUser, user)
        if not user.in_game:
            logger.debug("User %s is not in game, skipping", nick)
            return

        if user.afk:
            logger.debug("User %s is AFK", nick)
            return

    if not state.player.in_game:
        logger.debug("We are not in game, skipping")
        return

    if state.player.afk:
        logger.debug("We are AFK, skipping")
        return

    if not raw_reason:
        logger.debug("Reason is empty")
        return

    normalized = raw_reason.strip()
    if normalized.lower() == "emission":
        hazard_name = "Blowout"
        hazard_type = "Surge"
    elif normalized.lower() == "psy_storm":
        hazard_name = "Psy Storm"
        hazard_type = "PsyStorm"
    else:
        logger.debug("Unhandled hazard reason: %r", normalized)
        return

    now = datetime.now()
    cooldown_seconds = config.sync_hazards_cooldown * 60
    if (
        state.last_synced_hazard is not None
        and (now - state.last_synced_hazard).total_seconds() < cooldown_seconds
    ):
        logger.info(
            "Ignoring %s from %s due to cooldown (%.1fs remaining)",
            hazard_name,
            nick,
            cooldown_seconds
            - (now - state.last_synced_hazard).total_seconds(),
        )
        return

    logger.debug("Processing synced hazard: %s from %s", hazard_name, nick)
    state.last_synced_hazard = now
    warning_msg = (
        f"{hazard_name} is coming from {nick}, "
        "it will arrive in approximately 10 sec"
    )
    incoming_queue.create_information_event(warning_msg)

    async def _task():
        sleep_time = randint(6, 14)
        logger.debug("Triggering %s in %s", hazard_type, sleep_time)
        await asyncio.sleep(sleep_time)
        trigger_hazard_in_game(hazard_type)

    loop.create_task(_task(), name="trigger_hazard_in_game")
