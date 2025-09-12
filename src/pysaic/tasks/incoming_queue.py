import asyncio
import logging

from pysaic.handlers import handle_incoming_event
from pysaic.state import State

logger = logging.getLogger(__name__)


async def incoming_queue_processing(
    state: State, incoming_queue, ui, pysaic_config
):
    # Gateway/Router for incoming events

    logger.debug("Starting incoming queue processing")
    stop = False
    while not stop:
        await asyncio.sleep(0.25)
        while not incoming_queue.empty():
            event = incoming_queue.get_nowait()
            if event is None:
                stop = True
                break

            try:
                handle_incoming_event(state, event, ui, pysaic_config)
            except Exception:
                logger.exception("Could not handle event %r", event)
                raise
            incoming_queue.task_done()

    logger.debug("Stopping incoming queue processing")
