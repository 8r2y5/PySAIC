import logging

import inject

from pysaic.config import Config
from pysaic.controllers.game import ask_for_handshake
from pysaic.entities import IncomingEvent, IncomingQueue, OutgoingQueue
from pysaic.script_reader.entities import (
    AFK,
    Achievement,
    ActorStatus,
    ChannelChange,
    ChannelMessage,
    ConnectionLost,
    Death,
    Handshake,
    Location,
    Money,
    Rank,
    Reputation,
)
from pysaic.state import State
from pysaic.use_cases.game import (
    ConnectionLostUseCase,
    GameChannelMessageUseCase,
    GameHandshakeUseCase,
    MoneyChangeUseCase,
    PlayerDiedUseCase,
    achievement_use_case,
    actor_status_use_case,
    afk_use_case,
    channel_change_use_case,
    location_use_case,
    rank_use_case,
    reputation_use_case,
)

logger = logging.getLogger(__name__)


@inject.autoparams()
async def _parse_line(
    line: str,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    state: State,
):
    try:
        type, rest = line.split("/", 1)
    except Exception:
        logger.exception("Error parsing line: %r", line)
        return
    else:
        logger.info("Got line: %r", line)

    if not state.got_first_handshake.is_set() and type != Handshake.in_file_id:
        logger.debug(
            "Not processing line %r, waiting for first handshake",
            line,
        )
        ask_for_handshake(state.id)
        return

    # replace with a switch statement
    if type == ChannelMessage.in_file_id:
        await GameChannelMessageUseCase(
            config,
            ChannelMessage.from_line(config.nick, rest),
            incoming_queue,
            outgoing_queue,
        ).execute()
    elif type == Handshake.in_file_id:
        await GameHandshakeUseCase(
            state, config, Handshake.from_line(rest), incoming_queue
        ).execute()
    elif type == Death.in_file_id:
        await PlayerDiedUseCase(
            config,
            Death.from_line(rest),
            incoming_queue,
            outgoing_queue,
        ).execute()
    elif type == ConnectionLost.in_file_id:
        await ConnectionLostUseCase(
            config,
            ConnectionLost.from_line(rest),
            incoming_queue,
            outgoing_queue,
        ).execute()
    elif type == Money.in_file_id:
        await MoneyChangeUseCase(
            Money.from_line(rest), incoming_queue, outgoing_queue
        ).execute()
    elif type == ActorStatus.in_file_id:
        await actor_status_use_case(
            ActorStatus.from_line(rest), incoming_queue
        )
    elif type == ChannelChange.in_file_id:
        await channel_change_use_case(
            ChannelChange.from_line(rest), incoming_queue
        )
    elif type == Location.in_file_id:
        await location_use_case(Location.from_line(rest), incoming_queue)

    elif type == Achievement.in_file_id:
        await achievement_use_case(Achievement.from_line(rest), incoming_queue)
    elif type == Reputation.in_file_id:
        await reputation_use_case(Reputation.from_line(rest), incoming_queue)

    elif type == Rank.in_file_id:
        await rank_use_case(Rank.from_line(rest), incoming_queue)

    elif type == AFK.in_file_id:
        await afk_use_case(AFK.from_line(rest), incoming_queue)

    else:
        logger.warning("Unknown type: %r/%r", type, rest)


async def parse_line(line, incoming_queue: IncomingQueue):
    try:
        await _parse_line(line)
    except Exception:
        logger.critical("Cannot parse %r", line, exc_info=True)
        incoming_queue.put_nowait(
            IncomingEvent.create_error_event(
                "Received malformed information from game"
            )
        )
