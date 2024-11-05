import asyncio
import logging

import inject
from irclib.parser import Message

from pysaic.entities import (
    AppEvent,
    IncomingEvent,
    IncomingMessage,
    InformationEvent,
    IrcEvent,
    IncomingQueue,
)
from pysaic.enums import AppEventEnum, IrcEvents
from pysaic.log.utils import escape_stand_and_end
from pysaic.state import State
from pysaic.use_cases.common import join_previous_channel
from pysaic.use_cases.ui.incoming_event import IncomingNewEventUseCase

logger = logging.getLogger(__name__)


@inject.autoparams()
async def put_connected(incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent(
            author="",
            target="",
            event=AppEvent(what=AppEventEnum.CONNECTED),
        )
    )


@inject.autoparams()
async def put_disconnected(incoming_queue: IncomingQueue):
    await incoming_queue.put(
        IncomingEvent(
            author="",
            target="",
            event=AppEvent(what=AppEventEnum.DISCONNECTED_FROM_PDA_NETWORK),
        )
    )


async def handle_welcome_message(
    conn, _message, config, state, outgoing_queue
):
    logger.info("Waiting for identification to complete")
    state.got_welcome_message.set()
    join_previous_channel()


@inject.autoparams()
async def handle_nickname_in_use(
    conn, _message, config, incoming_queue: IncomingQueue
):
    password = config.password
    nick = config.nick
    logger.warning('Nick "%s" is already in use', nick)
    temp_nick = f"{nick}_"
    conn.send(f"NICK {temp_nick}")
    await asyncio.sleep(1)
    conn.send(f'USER "{temp_nick}" 0 * :{temp_nick}')
    if not password:
        config.nick = temp_nick
        config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.NICKNAME_CHANGED,
                payload={"nick": temp_nick},
            )
        )
        return

    incoming_queue.put_nowait(
        IncomingEvent.create_information_event(
            content=f"Nick {nick} is already in use. Trying to recover it."
        )
    )
    await asyncio.sleep(1)
    conn.send(f"PRIVMSG NickServ :RECOVER {nick} {password}")
    await asyncio.sleep(1)
    conn.send(f"PRIVMSG NickServ :RELEASE {nick} {password}")
    await asyncio.sleep(1)
    conn.send(f"NICK {nick}")
    await asyncio.sleep(1)
    conn.send(f'USER "{nick}" 0 * :{nick}')
    await asyncio.sleep(1)
    identify(conn, password)


def identify(conn, password):
    if not password:
        logger.error("No password provided")
        return
    logger.info("Identifying")
    conn.send(f"PRIVMSG NickServ :IDENTIFY {password}")


async def handle_ctcp(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingMessage(
            author=message.prefix.nick,
            target=message.parameters[0],
            content=message.parameters[1],
        )
    )


async def handle_notice(conn, message, config, incoming_queue, state):
    if (
        message.prefix
        and message.prefix.nick == "NickServ"
        and message.parameters[0] == config.nick
    ):
        await handle_notice_from_NickServ(
            conn, message, incoming_queue, config.password, state
        )
    elif message.parameters[1].startswith("\x01") and message.parameters[
        1
    ].endswith("\x01"):
        await handle_ctcp(conn, message, incoming_queue)


async def handle_notice_from_NickServ(
    conn, message, incoming_queue, password, state: State
):
    if message.parameters[1].startswith(
        "This nickname is registered and protected."
    ):
        identify(conn, password)

    elif (
        message.parameters[1] == "Password accepted -- you are now recognized."
    ):
        logger.info("Identified")
        state.is_author_authorized.set()

    await incoming_queue.put(
        IncomingMessage(
            author="NickServ",
            target=message.parameters[0],
            content=message.parameters[1],
            service=True,
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
            author=message.prefix.nick,
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


async def handle_end_of_names(conn, _message, incoming_queue, config):
    logger.info("Asking about user data")
    conn.send(f"PRIVMSG {config.server.previous_channel} :\001USERDATA\001")
    await incoming_queue.put(
        IncomingEvent(
            author="pysaic",
            target=config.server.previous_channel,
            event=AppEvent(what=AppEventEnum.UPDATE_USERS),
        )
    )


async def handle_channel_topic(conn, message, incoming_queue, config):
    await incoming_queue.put(
        IncomingEvent(
            author="pysaic",
            target=config.server.previous_channel,
            event=InformationEvent(
                content=f"Channel's topic: {message.parameters[2]}"
            ),
        )
    )


async def handle_simple_event(_conn, message, incoming_queue, state: State):
    if not state.is_in_channel.is_set():
        state.is_in_channel.set()

    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[0],
            event=IrcEvent(type=IrcEvents[message.command]),
        )
    )


async def handle_nick_change_event(_conn, message, incoming_queue):
    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents[message.command],
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
                payload={"nicks": filter(bool, message.parameters[3].split())},
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
            author=message.prefix.nick,
            target=message.parameters[0],
            content=message.parameters[1],
        )
    )
    # logger.info(
    #     "Received message from %s: %s",
    #     message.prefix.nick,
    #     message.parameters[1],
    # )


async def handle_mode(_conn, message, incoming_queue):
    if len(message.parameters) < 3:
        return

    await incoming_queue.put(
        IncomingEvent(
            author=message.prefix.nick,
            target=message.parameters[0],
            event=IrcEvent(
                type=IrcEvents[message.command],
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
            # event=InformationEvent(
            #     f"{message.parameters[1]} was kicked by {message.prefix.nick}: {message.parameters[2]}"
            # ),
        )
    )
    if message.parameters[1] == config.nick:
        conn.send(f"JOIN {config.server.previous_channel}")


def handle_incoming_event(state, event, ui, pysaic_config):
    IncomingNewEventUseCase.handle_event(state, pysaic_config, ui, event)


def handle_not_in_channel(state, outgoing_queue, config):
    state.is_in_channel.clear()
    join_previous_channel(outgoing_queue, config)


def log_event(message):
    logger.info(
        "%s -> %s :%s",
        message.prefix.mask if message.prefix else None,
        message.command,
        tuple(
            escape_stand_and_end(parameter) for parameter in message.parameters
        ),
    )


async def log_all_events(_conn, message: Message, *args):
    log_event(message)


# @inject.autoparams()
# def handle_actor_update(
#     payload,
#     state: State,
#     incoming_queue: IncomingQueue,
#     outgoing_queue: OutgoingQueue,
#     config: Config,
# ):
#     name, actor = payload
#     user = state.chat_users.update_or_create(name, actor)
#     if state.chat_users.needs_update:
#         state.chat_users.needs_update = False
#         UpdateUsersUseCase(self.state, self.ui).execute()
#         incoming_queue.put_nowait(
#             IncomingEvent(
#                 author="pysaic",
#                 target=config.server.previous_channel,
#                 event=AppEvent(what=AppEventEnum.UPDATE_USERS),
#             )
#         )
#         outgoing_queue.put_nowait(
#             OutgoingNotice(
#                 target=config.server.previous_channel,
#                 content=f"\x01AMOGUS {user.name}/{user.faction}/{user.in_game}\x01",
#             )
#         )
