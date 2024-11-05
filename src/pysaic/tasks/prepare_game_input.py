import asyncio
import logging

from pysaic.script_reader.aiowatch import game_files_watcher
from pysaic.state import State

logger = logging.getLogger(__name__)


async def prepare_game_input_watcher(loop, config, state: State):
    logger.debug("Starting game input watcher")
    while state.game_location is None:
        await asyncio.sleep(1)

    if state.game_related_tasks:
        logger.warning(
            "There are already game related tasks: %r",
            state.game_related_tasks,
        )
        for task in state.game_related_tasks:
            logger.info("Cancelling task %r", task)
            task.cancel()

    observer_task = loop.run_in_executor(
        None,
        game_files_watcher,
        state.game_location / "gamedata" / "configs",
        loop,
        False,
    )
    # reduce number of tasks, everything could be done in observer
    state.game_related_tasks = [observer_task]
