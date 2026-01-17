import logging
from typing import Callable

import inject

from pysaic.config import Config
from pysaic.entities import ChatUsers, OutgoingCTCP, OutgoingQueue
from pysaic.enums import SAICCTCPEnum
from pysaic.state import State

logger = logging.getLogger(__name__)


def send_saic_afk(state: State, outgoing_queue: OutgoingQueue, config: Config):
    if not state.is_in_channel.is_set():
        logger.debug(
            "Not in channel, not sending %s message", SAICCTCPEnum.SAICAFK
        )
        return

    logger.info(
        'Sending "%s" message, %r', SAICCTCPEnum.SAICAFK, state.player.afk
    )
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"{SAICCTCPEnum.SAICAFK} 1/{int(state.player.afk)}",
        )
    )


def send_saic_avatar(
    state: State, outgoing_queue: OutgoingQueue, config: Config
):
    if not state.is_in_channel.is_set():
        logger.debug(
            "Not in channel, not sending %s message", SAICCTCPEnum.SAICAVATAR
        )
        return

    logger.info(
        'Sending "%s" message, %r',
        SAICCTCPEnum.SAICAVATAR,
        state.player.get_avatar(),
    )
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"{SAICCTCPEnum.SAICAVATAR} 1/{state.player.get_avatar()}",
        )
    )


@inject.autoparams()
def send_saic_state(
    state: State, outgoing_queue: OutgoingQueue, config: Config
):
    if not state.is_in_channel.is_set():
        logger.debug(
            "Not in channel, not sending %s message", SAICCTCPEnum.SAICSTATE
        )
        return

    logger.info('Sending "%s" message', SAICCTCPEnum.SAICSTATE)
    outgoing_queue.put_nowait(
        OutgoingCTCP(
            target=config.server.previous_channel,
            content=f"{SAICCTCPEnum.SAICSTATE} 1/{state.get_player_state()}",
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
