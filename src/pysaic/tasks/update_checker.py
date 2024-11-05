import asyncio
import logging

import aiohttp

from pysaic import settings
from pysaic.entities import IncomingQueue, IncomingEvent
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)


async def update_checker(incoming_update: IncomingQueue):
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://github.com/8r2y5/PySAIC/releases/latest"
                ) as response:
                    if response.status == 200:
                        newest_version = tuple(
                            map(
                                int,
                                response.url.path.split("/").pop().split("."),
                            )
                        )
                        current_version = tuple(
                            map(int, settings.VERSION.split("."))
                        )
                        for index in range(3):
                            if newest_version[index] > current_version[index]:
                                logger.info(
                                    "New version available: %s", response.url
                                )
                                incoming_update.put_nowait(
                                    IncomingEvent.create_app_event(
                                        AppEventEnum.NEW_VERSION, response.url
                                    )
                                )
                                break
                    else:
                        logger.warning(
                            "Failed to get latest release. Http status: %d",
                            response.status,
                        )
        except Exception:
            logger.exception("Failed to get latest release")

        await asyncio.sleep(600)
