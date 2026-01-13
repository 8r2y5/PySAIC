import asyncio
import logging
from asyncio import CancelledError

logger = logging.getLogger(__name__)


async def update_app(app):
    logger.debug("Starting ui update task")
    while True:
        app.update()
        try:
            await asyncio.sleep(0.01)
        except CancelledError:
            break
    logger.debug("Stopping ui update task")
