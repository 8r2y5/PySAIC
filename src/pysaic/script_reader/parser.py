import logging

import inject

from pysaic.config import Config
from pysaic.entities import IncomingQueue, OutgoingQueue
from pysaic.script_reader.entities import (
    ChannelMessage,
    Handshake,
    Death,
    ConnectionLost,
    Money,
    ActorStatus,
    ChannelChange,
)
from pysaic.use_cases.game import (
    GameChannelMessageUseCase,
    GameHandshakeUseCase,
    PlayerDiedUseCase,
    ConnectionLostUseCase,
    MoneyChangeUseCase,
    actor_status_use_case,
    channel_change_use_case,
)

logger = logging.getLogger(__name__)


@inject.autoparams()
async def parse_line(
    line,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
):
    try:
        type, rest = line.split("/", 1)
    except Exception:
        logger.exception("Error parsing line: %r", line)
        return
    else:
        logger.info("Got line: %r", line)

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
            config, Handshake.from_line(rest), incoming_queue
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
    else:
        logger.warning("Unknown type: %r/%r", type, rest)
