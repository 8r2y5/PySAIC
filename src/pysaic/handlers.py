import asyncio
import logging
from functools import wraps

import inject
from irclib.parser import Message

from pysaic.config import Config
from pysaic.entities import (
    AppEvent,
    IncomingEvent,
    IncomingMessage,
    IncomingQueue,
    InformationEvent,
    IrcEvent,
    IrcUser,
    OutgoingCommand,
    OutgoingMessage,
    OutgoingQueue,
)
from pysaic.enums import AppEventEnum, IrcEvents
from pysaic.log.utils import escape_stand_and_end
from pysaic.router.incoming_router import IncomingRouter
from pysaic.state import State
from pysaic.use_cases.common import join_previous_channel

logger = logging.getLogger(__name__)


@inject.autoparams()
async def put_disconnected(payload, incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent(
            author="",
            target="",
            event=AppEvent(
                what=AppEventEnum.DISCONNECTED_FROM_PDA_NETWORK,
                payload=payload,
            ),
        )
    )


async def handle_welcome_message(
    conn, _message, config, state, outgoing_queue
):
    fogger = logger.getChild("handle_welcome_message")
    state.got_welcome_message.set()

    if state.fake_disconnect is False:
        fogger.info(
            'Joining previous channel "%s"', config.server.previous_channel
        )
        join_previous_channel()
    else:
        fogger.info("Fake disconnect is enabled, not joining previous channel")


@inject.autoparams()
async def handle_nickname_in_use(
    conn,
    _message,
    config,
    incoming_queue: IncomingQueue,
    state: State,
    outgoing_queue: OutgoingQueue,
):
    password = config.password
    logger.warning('Nick "%s" is already in use', state.nick)
    temp_nick = f"{state.nick}_"
    logger.info("Trying temporary nick %r", temp_nick)
    await conn._send(
        f"NICK {temp_nick}"
    )  # Change nick immediately, so we don't get stuck
    await incoming_queue.put(
        IncomingEvent.create_app_event(
            what=AppEventEnum.NICKNAME_CHANGED,
            payload={"nick": temp_nick},
        )
    )
    if not password:
        return

    if not state.got_welcome_message.is_set():
        await incoming_queue.put(
            IncomingEvent.create_information_event(
                content=f"Nick {config.nick!r} is already in use. Trying to recover it after initialization."
            )
        )
    await state.got_welcome_message.wait()
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            content=f"Starting to recover nick {config.nick!r}."
        )
    )
    logger.info("Trying to recover nick %r", config.nick)
    await outgoing_queue.put(
        OutgoingMessage(
            target="NickServ", content=f"RECOVER {config.nick} {password}"
        )
    )


@inject.autoparams
async def identify(password, outgoing_queue: OutgoingQueue):
    if not password:
        logger.error("No password provided")
        return
    logger.info("Identifying")
    await outgoing_queue.put(
        OutgoingMessage(target="NickServ", content=f"IDENTIFY {password}")
    )


async def handle_ctcp(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingMessage(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            content=message.parameters[1],
        )
    )


async def handle_notice(conn, message, config, incoming_queue, state):
    if (
        message.prefix
        and message.prefix.nick == "NickServ"
        and message.parameters[0] == state.nick
    ):
        await handle_notice_from_NickServ(
            conn, message, incoming_queue, config.password, state, config
        )
    elif message.parameters[1].startswith("\x01") and message.parameters[
        1
    ].endswith("\x01"):
        await handle_ctcp(conn, message, incoming_queue)


def flood_protection(coro):
    @wraps(coro)
    async def wrapper(*args, **kwargs):
        logger.info(
            "Flood protection: waiting 1 second before calling %r", coro
        )
        await asyncio.sleep(1)  # wait a bit to avoid collisions and flooding
        return await coro(*args, **kwargs)

    return wrapper


async def identified(incoming_queue, state):
    logger.info("Identified")
    state.is_author_authorized.set()
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            content="Successfully identified with NickServ."
        )
    )


@flood_protection
async def release_nick(incoming_queue, outgoing_queue, config):
    logger.info("Nickname hold released")
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            content="Nickname hold released, trying to recover it."
        )
    )
    await outgoing_queue.put(
        OutgoingMessage(
            target="NickServ",
            content=f"RELEASE {config.nick} {config.password}",
        )
    )


@flood_protection
async def released_nick(incoming_queue, outgoing_queue, config):
    logger.info("Previous connection has been killed, trying to recover it")
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            f"Previous connection has been killed, switching nick to {config.nick}."
        )
    )
    await outgoing_queue.put(
        OutgoingMessage(
            target="NickServ",
            content=f"RELEASE {config.nick} {config.password}",
        )
    )
    # nick update should be handled by IrcEvents.NICK


@flood_protection
async def nick_is_free(incoming_queue, outgoing_queue, config):
    logger.info("Nickname is free, switching to it")
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            f"Nickname {config.nick!r} is now free, switching to it."
        )
    )
    await outgoing_queue.put(OutgoingCommand.create_nick_command(config.nick))
    # nick update should be handled by IrcEvents.NICK


@flood_protection
async def nick_is_not_held(incoming_queue, outgoing_queue, config):
    logger.info("Nickname %r isn't being held, switching to it", config.nick)
    await incoming_queue.put(
        IncomingEvent.create_information_event(
            content=f"Nickname {config.nick!r} isn't being held, switching..."
        )
    )
    await outgoing_queue.put(OutgoingCommand.create_nick_command(config.nick))


@inject.autoparams()
async def handle_notice_from_NickServ(
    conn,
    message,
    incoming_queue,
    password,
    state: State,
    config: Config,
    outgoing_queue: OutgoingQueue,
):
    await incoming_queue.put(
        IncomingMessage(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            content=message.parameters[1],
            service=True,
        )
    )

    if message.parameters[1].startswith(
        "This nickname is registered and protected."
    ):
        await identify(password)

    elif (
        message.parameters[1] == "Password accepted -- you are now recognized."
    ):
        await identified(incoming_queue, state)

    elif (
        message.parameters[1]
        == "Services' hold on your nickname has been released."
    ):
        await release_nick(incoming_queue, outgoing_queue, config)

    elif message.parameters[1].startswith(
        "The user claiming your nickname has been killed."
    ):
        await released_nick(incoming_queue, outgoing_queue, config)

    elif (
        message.parameters[1]
        == f"Nickname \x02{config.nick}\x02 isn't currently in use."
    ):
        await nick_is_free(incoming_queue, outgoing_queue, config)

    elif (
        message.parameters[1]
        == f"Nickname \x02{config.nick}\x02 isn't being held."
    ):
        await nick_is_not_held(incoming_queue, outgoing_queue, config)

    elif message.parameters[1] == "You are not logged in.":
        logger.warning("Could not identify: not logged in")
        await incoming_queue.put(
            IncomingEvent.create_information_event(
                content="Could not identify: not logged in."
            )
        )

    elif message.parameters[1] == "Incorrect password.":
        logger.error("Could not identify: incorrect password")
        await incoming_queue.put(
            IncomingEvent.create_information_event(
                content="Could not identify: incorrect password."
            )
        )

    elif message.parameters[1] == "Your nickname isn't registered.":
        logger.error(
            "Could not identify: %r nickname isn't registered", state.nick
        )
        await incoming_queue.put(
            IncomingEvent.create_information_event(
                content=f"Could not identify: nickname {state.nick!r} isn't registered."
            )
        )


async def handle_part_event(conn, message, incoming_queue):
    reasons = {
        "Surge": "caught in emission.",
        "Underground": "went underground.",
    }
    try:
        left_type = message.parameters[1]
    except IndexError:
        left_type = None
    await incoming_queue.put(
        IncomingEvent(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents.PART,
                payload={
                    "reason": reasons.get(left_type, "has left the channel."),
                    "target": message.parameters[0],
                },
            ),
        )
    )


async def handle_end_of_names(conn, message, incoming_queue, config):
    logger.info("Asking about user data")
    channel = message.parameters[1]

    await incoming_queue.put(
        IncomingEvent.create_irc_event(
            IrcEvents.END_OF_NAMES, {"channel": channel}
        )
    )


async def handle_channel_topic(conn, message, incoming_queue):
    topic = message.parameters[-1]
    logger.debug("Channel topic: %r", topic)

    await incoming_queue.put(
        IncomingEvent(
            author="pysaic",
            target=message.parameters[1],
            event=InformationEvent(
                content=f"Channel's topic: {topic}",
            ),
        )
    )


async def handle_simple_event(_conn, message, incoming_queue, state: State):
    # if not state.is_in_channel.is_set():
    #     state.is_in_channel.set()

    await incoming_queue.put(
        IncomingEvent(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            event=IrcEvent(type=IrcEvents(message.command)),
        )
    )


async def handle_nick_change_event(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingEvent(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents(message.command),
                payload={"new_nick": message.parameters[0]},
            ),
        )
    )


async def handle_names(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[2],
            event=IrcEvent(
                type=IrcEvents(message.command),
                payload={
                    "nicks": [
                        nick for nick in message.parameters[3].split() if nick
                    ]
                },
            ),
        )
    )


async def handle_user_banned(conn, message, incoming_queue):
    logger.error("User banned: %r", message.parameters[1])
    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[1],
            event=IrcEvent(
                type=IrcEvents.BANNED_FROM_CHANNEL,
                payload=message.parameters[0],
            ),
        )
    )


async def handle_command(conn, message, message_list):
    pass


async def handle_privmsg(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingMessage(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            content=message.parameters[1]
            .replace("\n", "")
            .replace("\r", "")
            .replace("\\n", ""),
        )
    )


async def handle_mode(_conn, message, incoming_queue):
    if len(message.parameters) < 3:
        return

    await incoming_queue.put(
        IncomingEvent(
            author=IrcUser.from_prefix(message.prefix),
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents(message.command),
                payload={
                    "parameters": message.parameters[1:],
                    "mode": message.parameters[1],
                    "nick": message.parameters[2],
                },
            ),
        )
    )


async def handle_kick(conn, message, config, incoming_queue):
    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents.KICK,
                payload={
                    "kicked_nick": message.parameters[1],
                    "reason": message.parameters[2],
                },
            ),
        )
    )
    if message.parameters[1] == config.nick:
        await conn._send(f"JOIN {config.server.previous_channel}")


def handle_incoming_event(state, event, ui, pysaic_config):
    IncomingRouter.handle_event(state, pysaic_config, ui, event)


async def log_all_events(_conn, message: Message, *args):
    # if (
    #     message.command == "PRIVMSG"
    #     and message.parameters[0].startswith("NickServ")
    #     or message.prefix and message.prefix.nick == "NickServ"
    # ):
    #     return

    logger.info(
        "%s -> %s :%s",
        message.prefix.mask if message.prefix else None,
        message.command,
        tuple(
            escape_stand_and_end(parameter) for parameter in message.parameters
        ),
    )


@inject.autoparams()
async def not_in_a_channel(_conn, message, incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent.create_irc_event(
            IrcEvents.NOT_IN_THE_CHANNEL, message.parameters[-1]
        )
    )


@inject.autoparams()
async def handle_message_of_the_day(
    _conn, message, incoming_queue: IncomingQueue
):
    await incoming_queue.put(
        IncomingEvent.create_irc_event(message.command, "")
    )


@inject.autoparams()
async def handle_error_in_nickname(
    _conn, message, incoming_queue: IncomingQueue, config: Config
):
    logger.error("Error in nickname: %r", message.parameters[0])
    await incoming_queue.put(
        IncomingEvent.create_irc_event(
            what=IrcEvents.ERROR_IN_NICKNAME,
            payload={
                "nick": config.nick,
                "error": message.parameters[0],
            },
        )
    )


@inject.autoparams()
async def handle_welcome(conn, message, incoming_queue: IncomingQueue):
    logger.info("Received welcome message")
    await incoming_queue.put(
        IncomingEvent.create_irc_event(
            what=IrcEvents.WELCOME,
            payload={
                "message": (
                    message.parameters[1]
                    if len(message.parameters) > 1
                    else ""
                ),
                "your_nick": (
                    message.parameters[0]
                    if len(message.parameters) > 0
                    else ""
                ),
                "server": message.prefix.mask if message.prefix else "",
            },
        )
    )
