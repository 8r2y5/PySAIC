import logging

from pysaic.entities import (
    OutgoingMessage,
    OutgoingQuery,
    OutgoingNotice,
    OutgoingNick,
    OutgoingPart,
    OutgoingJoin,
    OutgoingQueue,
)
from pysaic.handlers import put_disconnected, put_connected
from pysaic.state import State

logger = logging.getLogger(__name__)


async def outgoing_queue_processing(
    irc,
    outgoing_queue: OutgoingQueue,
    state: State,
):
    logger.debug("Starting outgoing queue processing")
    while True:
        event = await outgoing_queue.get()
        # replace with a switch statement
        if isinstance(event, (OutgoingMessage, OutgoingQuery)):
            irc.send(f"PRIVMSG {event.target} :{event.content}")
        elif isinstance(event, OutgoingNotice):
            irc.send(f"NOTICE {event.target} :{event.content}")
        elif isinstance(event, OutgoingNick):
            irc.send(f"NICK {event.nick}")
        elif isinstance(event, OutgoingPart):
            logger.info(
                'Parting channel "%s", reason: %s',
                event.channel,
                event.content,
            )
            state.set_not_in_channel()
            await put_disconnected()
            irc.send(f"PART {event.channel} :{event.content}")
        elif isinstance(event, OutgoingJoin):
            logger.info('Joining channel "%s"', event.channel)
            irc.send(f"JOIN {event.channel}")
            await put_connected()
            state.set_in_channel()
        elif event is None:
            break
        else:
            logger.error("Unknown event type: %r", event)
        outgoing_queue.task_done()
    logger.info("Outgoing queue processing stopped")
