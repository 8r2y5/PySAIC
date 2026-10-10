import asyncio
import logging

import inject

from pysaic.entities import IncomingQueue
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)


class PySAICTransportProxy:
    def __init__(self, transport):
        self.__dict__["_transport"] = transport

    def close(self):
        logger.debug(
            "Closing connection with %s",
            self._transport.get_extra_info("peername"),
        )
        self._transport.close()

    def __getattr__(self, name):
        return getattr(self._transport, name)

    def __setattr__(self, name, value):
        setattr(self._transport, name, value)


class GameClientProtocol(asyncio.Protocol):
    def __init__(self, message_queue):
        self.message_queue = message_queue
        self.transport: None | PySAICTransportProxy = None
        self.logger = logger.getChild("game")

    @inject.autoparams()
    def connection_made(
        self, transport: asyncio.BaseTransport, incoming_queue: IncomingQueue
    ):
        self.transport = PySAICTransportProxy(transport)
        incoming_queue.create_app_event(
            AppEventEnum.GAME_TRANSPORT_CREATED, self.transport
        )
        self.logger.debug(
            "Game connection made from %s",
            self.transport.get_extra_info("peername"),
        )

    def data_received(self, data):
        message = data.decode()
        self.logger.debug("Game data received: %r", message)
        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue
            self.message_queue.put_nowait(line)

    @inject.autoparams()
    def connection_lost(self, exc, incoming_queue: IncomingQueue):
        self.logger.debug("Game connection lost")
        incoming_queue.create_app_event(
            AppEventEnum.GAME_TRANSPORT_DELETED, None
        )
        self.transport = None
