import asyncio
import logging

import aiohttp
from packaging.version import Version
from yarl import URL

from pysaic import settings
from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)


def _check_for_update(incoming_queue: IncomingQueue, url: URL):
    newest_version = Version(url.path.split("/").pop())

    if (
        newest_version.pre and not settings.CURRENT_VERSION.pre
    ) or newest_version <= settings.CURRENT_VERSION:
        return

    logger.info("New version available: %s", url)
    incoming_queue.put_nowait(
        IncomingEvent.create_app_event(AppEventEnum.NEW_VERSION, url)
    )


async def _check_url(incoming_queue: IncomingQueue, url: str):
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, allow_redirects=True) as response:
                if response.status == 200:
                    _check_for_update(incoming_queue, response.url)
                else:
                    logger.warning(
                        "Failed to get release on %r. Http status: %d",
                        url,
                        response.status,
                    )
    except Exception:
        logger.exception("Failed to get latest release")


async def update_checker(incoming_queue: IncomingQueue):
    urls = ["https://github.com/8r2y5/PySAIC/releases/latest"]
    if settings.CURRENT_VERSION.pre:
        urls.append(
            "https://github.com/8r2y5/PySAIC/releases/tag/"
            f"{settings.CURRENT_VERSION.base_version}"
            f"b{settings.CURRENT_VERSION.pre[1]+1}"
        )
    while True:
        for url in urls:
            await _check_url(incoming_queue, url)
            await asyncio.sleep(5)
        await asyncio.sleep(1200)
