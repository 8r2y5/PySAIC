import asyncio
import logging
import logging.config
import sys
from asyncio import CancelledError, Queue
from contextlib import suppress
from functools import partial

import inject
from asyncirc.server import Server

from pysaic.config import Config
from pysaic.entities import IncomingEvent, IncomingQueue, OutgoingQueue
from pysaic.enums import IrcEvents

from pysaic.irc_protocol import PySaicIrcProtocol
from pysaic.log.handlers import PySAICIRCLoggingHandler
from pysaic.use_cases.local_server import (
    get_pysaic_localserver,
    ask_instance_to_focus,
)
from pysaic.settings import (
    APP_IDENTITY,
    GAMEDATA_PATH,
    WORKDIR,
    get_log_config,
)
from pysaic.state import State
from pysaic.use_cases.get_user_for_irc import get_user_for_irc
from pysaic.use_cases.notification_registry import (
    check_and_register_uri_protocol,
)

logger = logging.getLogger("pysaic")


def set_up_irc_client(loop, config):
    from pysaic.handlers import log_all_events
    from pysaic.handlers import handle_nickname_in_use

    logger.debug("Setting up irc client")
    irc = PySaicIrcProtocol(
        [
            Server(
                config.server.host,
                config.server.port,
                password=config.server.password,
            )
        ],
        nick=config.nick,
        user=get_user_for_irc(),
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
    from pysaic.handlers import (
        handle_channel_topic,
        handle_end_of_names,
        handle_error_in_nickname,
        handle_kick,
        handle_message_of_the_day,
        handle_mode,
        handle_names,
        handle_nick_change_event,
        handle_notice,
        handle_part_event,
        handle_privmsg,
        handle_simple_event,
        handle_user_banned,
        handle_welcome_message,
        not_in_a_channel,
    )

    logger.debug("Binding incoming queue")
    irc.register(
        IrcEvents.Message_of_the_Day_End.value,
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
        partial(handle_channel_topic, incoming_queue=incoming_queue),
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
    irc.register(
        IrcEvents.NOT_IN_THE_CHANNEL.value,
        not_in_a_channel,
    )
    irc.register(
        IrcEvents.Message_of_the_Day_Start.value,
        handle_message_of_the_day,
    )
    irc.register(
        IrcEvents.Message_of_the_Day_End.value,
        handle_message_of_the_day,
    )
    irc.register(IrcEvents.ERROR_IN_NICKNAME.value, handle_error_in_nickname)


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
    irc: PySaicIrcProtocol,
):
    logger.debug("Configuring inject")
    from pysaic.ui.app import App

    binder.bind(App, app)
    binder.bind(State, state)
    binder.bind(IncomingQueue, incoming_queue)
    binder.bind(OutgoingQueue, outgoing_queue)
    binder.bind(Config, config)
    binder.bind(asyncio.AbstractEventLoop, loop)
    binder.bind(PySaicIrcProtocol, irc)


@inject.autoparams()
def close_everything_callback(
    task, outgoing_queue: OutgoingQueue, incoming_queue: IncomingQueue
):
    logger.info("Closing everything because of %r", task)
    incoming_queue.put_nowait(None)
    outgoing_queue.put_nowait(None)
    error = task.exception()

    try:
        task.result()
    except Exception as e:
        logger.error("error while getting task result: %s", e, exc_info=True)

    if error:
        logger.warning("error in task: %s", error, exc_info=True)
    else:
        logger.info("task %s finished, there was no error", task.get_name())


def initialize_logging():
    if (WORKDIR / "logging.conf").exists():
        with suppress(Exception):
            logging.config.fileConfig(
                WORKDIR / "logging.conf", disable_existing_loggers=False
            )
            return
    logging.config.dictConfig(get_log_config())


def main():
    incoming_queue = Queue()
    loop = asyncio.new_event_loop()
    try:
        pysaic_localserver = get_pysaic_localserver(loop, incoming_queue)
    except OSError:
        logger.error("Another instance of PySAIC is already running. Exiting.")
        loop.run_until_complete(ask_instance_to_focus())
        sys.exit(0)
    success = check_and_register_uri_protocol()
    if not success:
        pysaic_localserver.close()
        loop.close()
        sys.exit(1)
    initialize_logging()
    logger.info("Starting %s", APP_IDENTITY)
    logger.debug("WORKDIR: %s", WORKDIR)
    logger.debug("GAMEDATA_PATH: %s", GAMEDATA_PATH)
    config = Config.load_config()
    state = State(config)

    if config.irc_window:
        pysaic_irc_logger_handler = PySAICIRCLoggingHandler(incoming_queue)
        irc_protocol = logging.getLogger("pysaic.irc_protocol")
        irc_protocol.addHandler(pysaic_irc_logger_handler)
        irc_protocol.setLevel(logging.DEBUG)
        irc_protocol.info("IRC logging handler initialized")
        logging.getLogger("pysaic.handlers").addHandler(
            pysaic_irc_logger_handler
        )
    outgoing_queue = Queue()
    irc = set_up_irc_client(loop, config)

    bind_incoming_queue(irc, incoming_queue, config, state, outgoing_queue)

    logger.debug("Creating app")
    from pysaic.ui.app import App

    app = App(state, config, incoming_queue, outgoing_queue)
    prepared_callback = partial(close_everything_callback)
    from pysaic.tasks.prepare_game_input import prepare_game_input_watcher

    loop.create_task(prepare_game_input_watcher(loop, state))
    from pysaic.tasks.look_for_game import look_for_game_process

    looking_for_game_task = loop.create_task(
        look_for_game_process(loop, incoming_queue, config, state)
    )
    looking_for_game_task.add_done_callback(prepared_callback)
    app_update_task = loop.create_task(update_app(app))
    app_update_task.add_done_callback(prepared_callback)
    from pysaic.tasks.outgoing_queue import outgoing_queue_processing

    outgoing_process_task = loop.create_task(
        outgoing_queue_processing(
            irc, outgoing_queue, incoming_queue, state, loop
        )
    )

    from pysaic.tasks.incoming_queue import incoming_queue_processing

    incoming_queue_processing_task = loop.create_task(
        incoming_queue_processing(state, incoming_queue, app, config)
    )
    incoming_queue_processing_task.add_done_callback(prepared_callback)
    loop.create_task(irc.connect())
    inject.configure(
        partial(
            setup_inject,
            app=app,
            state=state,
            incoming_queue=incoming_queue,
            outgoing_queue=outgoing_queue,
            config=config,
            loop=loop,
            irc=irc,
        )
    )
    from pysaic.tasks.update_checker import update_checker

    loop.create_task(update_checker(incoming_queue))
    incoming_queue.put_nowait(
        IncomingEvent.create_information_event(f"Starting {APP_IDENTITY}.")
    )
    logger.debug("Entering start processing")
    try:
        loop.run_until_complete(outgoing_process_task)
    finally:
        pysaic_localserver.close()
        loop.run_until_complete(pysaic_localserver.wait_closed())
        logger.info("Stopping")

        logger.info("Cancelling tasks")
        outgoing_process_task.cancel()
        app_update_task.cancel()
        for task in asyncio.all_tasks(loop):
            task.cancel()

        logger.info("Quitting irc")
        irc._quitting = True
        future = loop.create_future()
        quit_task = loop.create_task(irc._send("QUIT Safe"))
        quit_task.add_done_callback(lambda _: future.set_result(None))
        loop.run_until_complete(asyncio.wait_for(future, timeout=10))

        loop.close()

    app.quit()
    sys.exit(0)


if __name__ == "__main__":
    main()
