import asyncio
import logging
from asyncio import Queue
from dataclasses import asdict
from functools import partial
from pprint import pprint
from random import choice

from pysaic.tasks.common import close_everything_callback

import inject

from pysaic.config import Config
from pysaic.crc_strings.use_case import (
    DeathMessageUseCase,
    TravelMessageUseCase,
)
from pysaic.entities import (
    ChatUser,
    ErrorEvent,
    IncomingEvent,
    IncomingMessage,
    IncomingQueue,
    InformationEvent,
    IrcUser,
    OutgoingQueue,
)
from pysaic.enums import FactionsEnum, SAICStateEnum
from pysaic.router.incoming_router import IncomingRouter
from pysaic.script_reader.entities import Death
from pysaic.settings import APP_IDENTITY
from pysaic.state import State
from pysaic.tasks.app import update_app
from pysaic.tasks.incoming_queue import incoming_queue_processing
from pysaic.ui.app import App
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase

logger = logging.getLogger(__name__)


def gen_chat_users():
    return {
        f"user_{x}": ChatUser(
            name=f"user_{x}",
            faction=choice(list(FactionsEnum)),
            in_game=choice([True, False]),
            afk=choice([True, False, False]),
            state=choice(
                (
                    SAICStateEnum.ok,
                    SAICStateEnum.ok,
                    SAICStateEnum.emission,
                    SAICStateEnum.underground,
                )
            ),
        )
        for x in range(30)
    }


def get_priv_msg(users):
    return IncomingMessage(
        author=IrcUser(choice(users).name),
        target=choice(users).name,
        content="".join(
            [choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(10)]
        ),
    )


def gen_info(users):
    return IncomingEvent(
        author="pysaic",
        target="#channel",
        event=InformationEvent(
            content="Info: "
            + "".join(
                [choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(10)]
            ),
        ),
    )


def gen_error(users):
    return IncomingEvent(
        author="pysaic",
        target="#channel",
        event=ErrorEvent(
            content="Error: "
            + "".join(
                [choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(10)]
            ),
        ),
    )


def gen_channel_msg(users):
    return IncomingMessage(
        author=IrcUser(choice(users).name),
        target="#channel",
        content="".join(
            [choice("qwertyuiopasdfghjklzxcvbnm") for _ in range(10)]
        ),
    )


def get_random_event(users):
    return choice(
        [
            get_priv_msg,
            gen_channel_msg,
            gen_info,
            gen_error,
            # gen_death_msg,
        ]
    )(users)


def gen_messages(state, config, app):
    users = list(state.chat_users.values())
    for x in range(10):
        event = get_random_event(users)
        IncomingRouter.handle_event(state, config, app, event)


def setup_inject(binder, app, state, incoming_queue, outgoing_queue, config):
    binder.bind(App, app)
    binder.bind(State, state)
    binder.bind(IncomingQueue, incoming_queue)
    binder.bind(OutgoingQueue, outgoing_queue)
    binder.bind(Config, config)


def gen_death_message(state, config, app):
    death = Death(
        user_actor="actor_bandit",
        location="l10_limansk",
        death_by="MONOLITH",
        meta="sim_default_monolith_1",
    )
    use_case = DeathMessageUseCase(state, config, "Mock_Death", death)
    IncomingRouter.handle_event(
        state,
        config,
        app,
        IncomingMessage(
            author=IrcUser("Mock_Death"),
            target="#channel",
            content=use_case.execute(),
        ),
    )


def get_travel_message(state, config, app):
    travel_use_case = TravelMessageUseCase(
        state, config, "Mock_Travel", "l10_limansk"
    )
    IncomingRouter.handle_event(
        state,
        config,
        app,
        IncomingMessage(
            author=IrcUser("Mock_Death"),
            target="#channel",
            content=travel_use_case.execute(),
        ),
    )


def mock_ui():
    logger = logging.getLogger("pysaic")
    logger.setLevel(logging.DEBUG)
    handler = logging.StreamHandler()
    handler.setLevel(logging.DEBUG)
    formatter = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    incoming_queue = Queue()
    outgoing_queue = Queue()
    config = Config.load_config()
    state = State(config)
    app = App(state, config, incoming_queue, outgoing_queue)
    app.title(f"Mock {APP_IDENTITY}")
    inject.configure(
        partial(
            setup_inject,
            app=app,
            state=state,
            incoming_queue=incoming_queue,
            outgoing_queue=outgoing_queue,
            config=config,
        )
    )
    state.chat_users.update(**gen_chat_users())
    state.chat_users[config.nick] = ChatUser(
        name=config.nick, faction=config.current_faction, in_game=True
    )
    gen_messages(state, config, app)
    gen_death_message(state, config, app)
    get_travel_message(state, config, app)
    UpdateUsersUseCase(state, app).execute()
    pprint(asdict(config))
    loop = asyncio.get_event_loop()
    prepared_callback = partial(close_everything_callback)
    app_update_task = loop.create_task(update_app(app), name="AppUpdateTask")
    app_update_task.add_done_callback(prepared_callback)
    incoming_queue_processing_task = loop.create_task(
        incoming_queue_processing(state, incoming_queue, app, config),
        name="IncomingQueueProcessingTask",
    )
    incoming_queue_processing_task.add_done_callback(prepared_callback)
    app.enable_input()
    try:
        loop.run_until_complete(app_update_task)
    except KeyboardInterrupt:
        pass

    while incoming_queue.qsize():
        print(incoming_queue.get_nowait())


if __name__ == "__main__":
    mock_ui()
