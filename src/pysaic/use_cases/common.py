import inject

from pysaic.config import Config
from pysaic.entities import OutgoingJoin, OutgoingQueue


@inject.autoparams()
def join_previous_channel(outgoing_queue: OutgoingQueue, config: Config):
    outgoing_queue.put_nowait(
        OutgoingJoin(channel=config.server.previous_channel)
    )
