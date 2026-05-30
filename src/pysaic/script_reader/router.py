import logging
from typing import Callable, Dict

import inject

from pysaic.config import Config
from pysaic.controllers.game import ask_for_handshake
from pysaic.entities import IncomingEvent, IncomingQueue, OutgoingQueue
from pysaic.script_reader.entities import (
    AFK,
    Achievement,
    ActorStatus,
    ChannelChange,
    ChannelMessage,
    ConnectionLost,
    Death,
    Handshake,
    Location,
    Money,
    Rank,
    Reputation,
    Item,
)
from pysaic.script_reader.handlers import (
    _handle_channel_message,
    _handle_handshake,
    _handle_death,
    _handle_connection_lost,
    _handle_money,
    _handle_actor_status,
    _handle_channel_change,
    _handle_location,
    _handle_achievement,
    _handle_reputation,
    _handle_rank,
    _handle_afk,
    _handle_item,
)
from pysaic.state import State

logger = logging.getLogger(__name__)


class Router:
    def __init__(self):
        self._handlers: Dict[str, Callable] = {}

    def register_handler(self, in_file_id: str, handler: Callable):
        self._handlers[in_file_id] = handler

    @inject.autoparams()
    async def dispatch(
        self,
        line: str,
        config: Config,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
        state: State,
    ):
        try:
            type_id, rest = line.split("/", 1)
        except Exception:
            logger.exception("Error parsing line: %r", line)
            return
        else:
            logger.info("Got line: %r", line)

        if (
            not state.got_first_handshake.is_set()
            and type_id != Handshake.in_file_id
        ):
            logger.debug(
                "Not processing line %r, waiting for first handshake",
                line,
            )
            ask_for_handshake(state.id)
            return

        if handler := self._handlers.get(type_id):
            await handler(rest, config, incoming_queue, outgoing_queue, state)
        else:
            logger.warning("Unknown type: %r/%r", type_id, rest)


router = Router()


# Register handlers
router.register_handler(ChannelMessage.in_file_id, _handle_channel_message)
router.register_handler(Handshake.in_file_id, _handle_handshake)
router.register_handler(Death.in_file_id, _handle_death)
router.register_handler(ConnectionLost.in_file_id, _handle_connection_lost)
router.register_handler(Money.in_file_id, _handle_money)
router.register_handler(ActorStatus.in_file_id, _handle_actor_status)
router.register_handler(ChannelChange.in_file_id, _handle_channel_change)
router.register_handler(Location.in_file_id, _handle_location)
router.register_handler(Achievement.in_file_id, _handle_achievement)
router.register_handler(Reputation.in_file_id, _handle_reputation)
router.register_handler(Rank.in_file_id, _handle_rank)
router.register_handler(AFK.in_file_id, _handle_afk)
router.register_handler(Item.in_file_id, _handle_item)


async def parse_line(line, incoming_queue: IncomingQueue):
    try:
        await router.dispatch(line)
    except Exception:
        logger.critical("Cannot parse %r", line, exc_info=True)
        incoming_queue.put_nowait(
            IncomingEvent.create_error_event(
                "Received malformed information from game"
            )
        )
