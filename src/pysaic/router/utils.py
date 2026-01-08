import logging
from typing import Callable

from pysaic.config import Config
from pysaic.entities import ChatUsers, OutgoingCTCP, OutgoingQueue
from pysaic.state import State

logger = logging.getLogger(__name__)


def send_saic_afk(state: State, outgoing_queue: OutgoingQueue, config: Config):
    if not state.is_in_channel.is_set():
        logger.debug("Not in channel, not sending SAICAFK message")
        return

    logger.info('Sending "SAICAFK" message, %r', state.player.afk)
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"SAICAFK 1/{int(state.player.afk)}",
        )
    )


def send_saic_avatar(
    state: State, outgoing_queue: OutgoingQueue, config: Config
):
    if not state.is_in_channel.is_set():
        logger.debug("Not in channel, not sending SAICAVATAR message")
        return

    logger.info('Sending "SAICAVATAR" message, %r', state.player.get_avatar())
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"SAICAVATAR 1/{state.player.get_avatar()}",
        )
    )


def send_saic_status(
    state: State, outgoing_queue: OutgoingQueue, config: Config
):
    if not state.is_in_channel.is_set():
        logger.debug("Not in channel, not sending SAICSTATUS message")
        return

    logger.info('Sending "SAICSTATUS" message')
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"SAICSTATUS 1/{state.player.status.value}",
        )
    )


def generic_send_saic_message(
    outgoing_queue: OutgoingQueue,
    previous_channel: str,
    message_type: str,
    content_callback: Callable,
    state: State,
    chat_users: ChatUsers,
):
    logger.debug('Sending "%s" message', message_type)
    try:
        user = chat_users[state.nick]
    except KeyError:
        logger.exception("User was missing in chat_users.")
        return

    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=previous_channel,
            content=f"{message_type} {content_callback(user)}",
        )
    )
