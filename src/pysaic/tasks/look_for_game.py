import asyncio
import logging
import os
from pathlib import Path

import psutil

from pysaic.entities import AppEvent, IncomingEvent
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)


def find_game_process():
    logger.debug("Looking for game process in the system processes")
    for p in psutil.process_iter():
        try:
            if "AnomalyDX" in p.name():
                return p.pid
        except psutil.NoSuchProcess:
            continue
    return None


async def look_for_game_process(loop, incoming_queue, config, state):
    last_status = False
    logger.debug("Starting look for game process")
    pid = None
    while True:
        is_game_running = False
        game_path = None
        if pid:
            if psutil.pid_exists(pid):
                is_game_running = True
            else:
                logger.info("Game process is not running anymore")
                pid = None
        else:
            logger.debug("Looking for game process in the system via pool")
            pid = await asyncio.to_thread(find_game_process)
            if pid:
                is_game_running = True
                try:
                    game_path = (
                        Path(os.path.dirname(psutil.Process(pid).exe())) / ".."
                    ).resolve()
                except psutil.NoSuchProcess:
                    logger.error("Game process not found")
                    pid = None
                    continue

        if last_status != is_game_running:
            last_status = is_game_running
            incoming_queue.put_nowait(
                IncomingEvent(
                    author="",
                    target="",
                    event=AppEvent(
                        what=AppEventEnum.IN_GAME,
                        payload=(is_game_running, game_path),
                    ),
                )
            )
        await asyncio.sleep(5)
