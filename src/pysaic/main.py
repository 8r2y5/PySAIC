import asyncio
import logging
import logging.config
from asyncio import CancelledError, Queue
from functools import partial
from typing import Optional

import inject
from asyncirc.protocol import IrcProtocol
from asyncirc.server import Server

from pysaic.config import Config
from pysaic.entities import (
    IncomingEvent,
    IncomingQueue,
    OutgoingQueue,
)
from pysaic.enums import IrcEvents, AppEventEnum
from pysaic.handlers import (
    handle_channel_topic,
    handle_end_of_names,
    handle_kick,
    handle_mode,
    handle_names,
    handle_nick_change_event,
    handle_nickname_in_use,
    handle_notice,
    handle_part_event,
    handle_privmsg,
    handle_simple_event,
    handle_user_banned,
    handle_welcome_message,
    log_all_events,
)
from pysaic.settings import get_log_config, APP_IDENTITY
from pysaic.state import State
from pysaic.tasks.incoming_queue import incoming_queue_processing
from pysaic.tasks.look_for_game import look_for_game_process
from pysaic.tasks.outgoing_queue import outgoing_queue_processing
from pysaic.tasks.prepare_game_input import prepare_game_input_watcher
from pysaic.tasks.update_checker import update_checker
from pysaic.ui.app import App

logger = logging.getLogger("pysaic")


class PySaicIrcProtocol(IrcProtocol):
    @inject.autoparams()
    def connection_lost(
        self, exc: Optional[Exception], incoming_queue: IncomingQueue
    ) -> None:
        logger.warning("Connection lost")
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                AppEventEnum.RECONNECTING_TO_SERVER, "Connection lost"
            )
        )
        super().connection_lost(exc)


def set_up_irc_client(loop, config):
    logger.debug("Setting up irc client")
    irc = PySaicIrcProtocol(
        [Server(config.server.host, config.server.port)],
        nick=config.nick,
        loop=loop,
        logger=logger.getChild("irc_protocol"),
        realname=APP_IDENTITY,
    )

    irc.register("*", log_all_events)

    irc.register(
        IrcEvents.ERROR_NICKNAME_IN_USE.value,
        partial(handle_nickname_in_use, config=config),
    )

    return irc


async def update_app(app):
    logger.debug("Starting ui update task")
    while True:
        app.update()
        try:
            await asyncio.sleep(0.01)
        except CancelledError:
            break
    logger.debug("Stopping ui update task")


def bind_incoming_queue(irc, incoming_queue, config, state, outgoing_queue):
    logger.debug("Binding incoming queue")
    irc.register(
        IrcEvents.WELCOME.value,
        partial(
            handle_welcome_message,
            config=config,
            state=state,
            outgoing_queue=outgoing_queue,
        ),
    )
    irc.register(
        IrcEvents.MODE.value,
        partial(handle_mode, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.PRIVMSG.value,
        partial(handle_privmsg, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.PART.value,
        partial(handle_part_event, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.QUIT.value,
        partial(
            handle_simple_event, incoming_queue=incoming_queue, state=state
        ),
    )
    irc.register(
        IrcEvents.JOIN.value,
        partial(
            handle_simple_event, incoming_queue=incoming_queue, state=state
        ),
    )
    irc.register(
        IrcEvents.NICK.value,
        partial(handle_nick_change_event, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.USER.value,
        partial(handle_nick_change_event, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.NOTICE.value,
        partial(
            handle_notice,
            incoming_queue=incoming_queue,
            config=config,
            state=state,
        ),
    )
    irc.register(
        IrcEvents.END_OF_NAMES.value,
        partial(
            handle_end_of_names,
            incoming_queue=incoming_queue,
            config=config,
        ),
    )
    irc.register(
        IrcEvents.NAMES.value,
        partial(handle_names, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.CHANNEL_TOPIC.value,
        partial(
            handle_channel_topic, incoming_queue=incoming_queue, config=config
        ),
    )
    irc.register(
        IrcEvents.TOPIC.value,
        partial(handle_channel_topic, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.BANNED_FROM_CHANNEL.value,
        partial(handle_user_banned, incoming_queue=incoming_queue),
    )
    irc.register(
        IrcEvents.KICK.value,
        partial(handle_kick, config=config, incoming_queue=incoming_queue),
    )


def put_as_incoming_simple_event(content, queue, event_class):
    queue.put_nowait(
        IncomingEvent("pysaic", "pysaic", event=event_class(content))
    )


def setup_inject(
    binder,
    app,
    state,
    incoming_queue,
    outgoing_queue,
    config,
    loop,
):
    logger.debug("Configuring inject")
    binder.bind(App, app)
    binder.bind(State, state)
    binder.bind(IncomingQueue, incoming_queue)
    binder.bind(OutgoingQueue, outgoing_queue)
    binder.bind(Config, config)
    binder.bind(asyncio.AbstractEventLoop, loop)


def close_everything_callback(*args, outgoing_queue):
    logger.info("Closing everything because of %r", args)
    outgoing_queue.put_nowait(None)


def main():
    logging.config.dictConfig(get_log_config())
    logger.info("Starting %s", APP_IDENTITY)
    config = Config.load_config()
    state = State(config)
    loop = asyncio.get_event_loop()
    incoming_queue = Queue()
    outgoing_queue = Queue()
    irc = set_up_irc_client(loop, config)

    bind_incoming_queue(irc, incoming_queue, config, state, outgoing_queue)

    logger.debug("Creating app")
    app = App(state, config, incoming_queue, outgoing_queue)

    incoming_queue.put_nowait(
        IncomingEvent.create_information_event(
            f"Starting {APP_IDENTITY}. Connecting..."
        )
    )
    prepared_callback = partial(
        close_everything_callback, outgoing_queue=outgoing_queue
    )
    app_update_task = loop.create_task(update_app(app))
    app_update_task.add_done_callback(prepared_callback)
    outgoing_process_task = loop.create_task(
        outgoing_queue_processing(irc, outgoing_queue, state)
    )
    loop.create_task(prepare_game_input_watcher(loop, config, state))
    looking_for_game_task = loop.create_task(
        look_for_game_process(loop, incoming_queue, config, state)
    )
    looking_for_game_task.add_done_callback(prepared_callback)

    loop.create_task(irc.connect())
    incoming_queue_processing_task = loop.create_task(
        incoming_queue_processing(state, incoming_queue, app, config)
    )
    incoming_queue_processing_task.add_done_callback(prepared_callback)
    inject.configure(
        partial(
            setup_inject,
            app=app,
            state=state,
            incoming_queue=incoming_queue,
            outgoing_queue=outgoing_queue,
            config=config,
            loop=loop,
        )
    )
    loop.create_task(update_checker(incoming_queue))
    logger.debug("Entering start processing")
    try:
        loop.run_until_complete(outgoing_process_task)
    finally:
        logger.info("Stopping")

        logger.info("Cancelling tasks")
        outgoing_process_task.cancel()
        app_update_task.cancel()
        for task in asyncio.all_tasks(loop):
            task.cancel()

        logger.info("Quitting irc")
        irc._quitting = True
        loop.run_until_complete(irc._send("QUIT Safe"))

        loop.close()

    app.quit()


if __name__ == "__main__":
    main()
