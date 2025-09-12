import logging

import inject

from pysaic.config import Config
from pysaic.entities import OutgoingJoin, OutgoingQueue

logger = logging.getLogger(__name__)


@inject.autoparams()
def join_previous_channel(outgoing_queue: OutgoingQueue, config: Config):
    logger.info("Joining previous channel %r", config.server.previous_channel)
    outgoing_queue.put_nowait(
        OutgoingJoin(channel=config.server.previous_channel)
    )
