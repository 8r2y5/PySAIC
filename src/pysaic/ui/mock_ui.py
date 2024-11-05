import logging
from asyncio import Queue
from functools import partial
from random import choice

import inject

from pysaic.config import Config
from pysaic.entities import (
    ChatUser,
    ErrorEvent,
    IncomingEvent,
    IncomingMessage,
    InformationEvent,
    IncomingQueue,
    OutgoingQueue,
)
from pysaic.enums import FactionsEnum
from pysaic.state import State
from pysaic.ui.app import App
from pysaic.use_cases.ui.incoming_event import IncomingNewEventUseCase
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase


def gen_chat_users():
    return {
        f"user_{x}": ChatUser(
            name=f"user_{x}",
            faction=choice(list(FactionsEnum)),
            in_game=choice([True, False]),
        )
        for x in range(30)
    }


def get_priv_msg(users):
    return IncomingMessage(
        author=choice(users).name,
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
        author=choice(users).name,
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
        IncomingNewEventUseCase.handle_event(state, config, app, event)


def setup_inject(binder, app, state, incoming_queue, outgoing_queue, config):
    binder.bind(App, app)
    binder.bind(State, state)
    binder.bind(IncomingQueue, incoming_queue)
    binder.bind(OutgoingQueue, outgoing_queue)
    binder.bind(Config, config)


def mock_ui():
    logging.basicConfig(level=logging.DEBUG)
    incoming_queue = Queue()
    outgoing_queue = Queue()
    config = Config.load_config()
    state = State(config)
    app = App(state, config, incoming_queue, outgoing_queue)
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
    UpdateUsersUseCase(state, app).execute()
    app.enable_input()
    app.mainloop()
    while incoming_queue.qsize():
        print(incoming_queue.get_nowait())


if __name__ == "__main__":
    mock_ui()
