import logging

import inject

from pysaic.entities import OutgoingQueue, IncomingQueue

logger = logging.getLogger(__name__)


@inject.autoparams()
def close_everything_callback(
    task, outgoing_queue: OutgoingQueue, incoming_queue: IncomingQueue
):
    logger.info("Closing everything because of %r", task)
    incoming_queue.put_nowait(None)
    outgoing_queue.put_nowait(None)
    error = task.exception()

    try:
        task.result()
    except Exception as e:
        logger.error("error while getting task result: %s", e, exc_info=True)

    if error:
        logger.warning("error in task: %s", error, exc_info=True)
    else:
        logger.info("task %s finished, there was no error", task.get_name())
