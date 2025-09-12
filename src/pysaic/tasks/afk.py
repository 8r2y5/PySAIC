import asyncio
import logging
from asyncio import AbstractEventLoop, sleep
from datetime import UTC, datetime

import inject

from pysaic.controllers.game import add_setting_to_game
from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum
from pysaic.state import State

logger = logging.getLogger(__name__)

AFK_GAME_PING_TASK = "afk_game_ping_task"
AFK_SET_TASK = "afk_set_task"


@inject.autoparams()
async def afk_game_ping_task(state: State):
    state.player.afk = False
    state.player.last_ask_update = datetime.now(UTC)

    while True:
        await sleep(120)
        if state.player.afk is False:
            add_setting_to_game("AFK", "AFK")


@inject.autoparams()
async def afk_set_task(incoming_queue: IncomingQueue):
    while True:
        await sleep(300)
        await incoming_queue.put(
            IncomingEvent.create_app_event(
                AppEventEnum.CHECK_AFK,
                None,
            )
        )


def get_my_tasks():
    return [
        task
        for task in asyncio.all_tasks()
        if task.get_name() in (AFK_GAME_PING_TASK, AFK_SET_TASK)
    ]


def stop_afk_tasks():
    logger.info("Stopping afk tasks")
    tasks = get_my_tasks()
    for task in tasks:
        logger.info("Stopping task %s", task.get_name())
        task.cancel()
        logger.info("Task %s stopped", task.get_name())


@inject.autoparams()
def ensure_afk_tasks_are_running(loop: AbstractEventLoop):
    tasks = get_my_tasks()
    tasks = {task.get_name(): task for task in tasks}
    if AFK_GAME_PING_TASK not in tasks:
        logger.info("Starting afk_game_ping_task")
        loop.create_task(afk_game_ping_task(), name=AFK_GAME_PING_TASK)

    if AFK_SET_TASK not in tasks:
        logger.info("Starting afk_set_task")
        loop.create_task(afk_set_task(), name=AFK_SET_TASK)
