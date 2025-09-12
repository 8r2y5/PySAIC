import asyncio
import logging

from pysaic.entities import (
    IncomingEvent,
    IncomingQueue,
    OutgoingCommand,
    OutgoingCTCP,
    OutgoingJoin,
    OutgoingMessage,
    OutgoingPart,
    OutgoingQuery,
    OutgoingQueue,
)
from pysaic.events.enum import GameEvents
from pysaic.handlers import put_disconnected
from pysaic.state import State

logger = logging.getLogger(__name__)


async def handle_part(event, state, irc):
    if state.is_in_channel.is_set():
        logger.debug(
            'Parting channel "%s", reason: %r',
            event.channel,
            event.content,
        )
        part_command = f"PART {event.channel}"
        if event.content:
            part_command += f" :{event.content}"

        state.set_not_in_channel()
        await put_disconnected(event.content)
        await irc.async_send(part_command)
    else:
        logger.debug(
            'Tried to part channel "%s", but not in a channel.',
            event.channel,
        )


async def handle_send_message(event, irc):
    content = event.content.replace("\n", "")
    await irc.async_send(f"PRIVMSG {event.target} :{content}")


async def handle_join(event, state, irc):
    logger.info('Joining channel "%s"', event.channel)
    if state.is_in_channel.is_set():
        logger.warning(
            'Tried to join channel "%s", but already in a channel.',
            event.channel,
        )
        return

    await irc.async_send(f"JOIN {event.channel}")


async def handle_outgoing_command(event, irc):
    logger.debug(
        "Handling outgoing command: %r, %r", event.command, event.args
    )
    await irc.async_send(str(event))


async def outgoing_queue_processing(
    irc,
    outgoing_queue: OutgoingQueue,
    incoming_queue: IncomingQueue,
    state: State,
    loop: asyncio.BaseEventLoop,
):
    logger.debug("Starting outgoing queue processing")
    last_time = loop.time()
    while True:
        event = await outgoing_queue.get()
        logger.debug("Processing event: %r", event)
        await state.got_welcome_message.wait()
        if event is None:
            break

        now = loop.time()
        difference = now - last_time
        # rate limiting to 1 second per message, so we don't get kicked
        if last_time and difference < 1:
            await asyncio.sleep(1 - difference)

        # replace with a switch statement
        if isinstance(event, (OutgoingMessage, OutgoingQuery)):
            await handle_send_message(event, irc)
            await incoming_queue.put(
                IncomingEvent.create_game_event(
                    GameEvents.AFK, "outgoing queue"
                )
            )
        elif isinstance(event, OutgoingCTCP):
            await irc.async_send(
                f"{event.send_as} {event.target} :{event.content}"
            )
        elif isinstance(event, OutgoingCommand):
            await handle_outgoing_command(event, irc)
        elif isinstance(event, OutgoingPart):
            await handle_part(event, state, irc)
        elif isinstance(event, OutgoingJoin):
            await handle_join(event, state, irc)
        else:
            logger.error("Unknown event type: %r", event)
        outgoing_queue.task_done()
        last_time = loop.time()
    logger.info("Outgoing queue processing stopped")
