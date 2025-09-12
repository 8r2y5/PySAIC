import asyncio
import logging

import aiohttp
from packaging.version import Version

from pysaic import settings
from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)


def _check_for_update(incoming_queue, url):
    newest_version = Version(url.path.split("/").pop())
    current_version = Version(settings.VERSION)

    if (
        newest_version.pre and not current_version.pre
    ) or newest_version <= current_version:
        return

    logger.info("New version available: %s", url)
    incoming_queue.put_nowait(
        IncomingEvent.create_app_event(AppEventEnum.NEW_VERSION, url)
    )


async def update_checker(incoming_queue: IncomingQueue):
    while True:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    "https://github.com/8r2y5/PySAIC/releases/latest"
                ) as response:
                    if response.status == 200:
                        _check_for_update(incoming_queue, response.url)
                    else:
                        logger.warning(
                            "Failed to get latest release. Http status: %d",
                            response.status,
                        )
        except ValueError:
            # happens during pre-release versions
            pass
        except Exception:
            logger.exception("Failed to get latest release")

        await asyncio.sleep(600)
