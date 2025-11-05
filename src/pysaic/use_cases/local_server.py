import asyncio
import logging

from pysaic.entities import IncomingEvent
from pysaic.enums import AppEventEnum

logger = logging.getLogger(__name__)
HOST = "127.0.0.1"
PORT = 9754


class PySAICClientProtocol(asyncio.Protocol):
    def __init__(self, incoming_queue):
        self.incoming_queue = incoming_queue
        self.transport = None
        self.logger = logger.getChild("client")

    def connection_made(self, transport):
        self.transport = transport
        self.logger.debug(
            "Connection made from %s", transport.get_extra_info("peername")
        )

    def data_received(self, data):
        message = data.decode()
        self.logger.debug("Data received: %r", message)
        command = message.strip().lower()
        self.logger.debug("Command parsed: %r", command)
        if command == "focus":
            self.logger.debug("Processing focus command.")
            self.incoming_queue.put_nowait(
                IncomingEvent.create_app_event(AppEventEnum.FOCUS, None)
            )
            self.transport.write(b"OK\n")
        else:
            self.logger.debug("Unknown command received.")
            self.transport.write(b"ERROR: Unknown command\n")

        self.transport.close()
        self.logger.debug("Connection closed.")

    def write_reply(self, fut):
        reply = fut.result()
        self.transport.write(reply.encode())


def get_pysaic_localserver(loop, incoming_queue):
    coro = loop.create_server(
        lambda: PySAICClientProtocol(incoming_queue), HOST, PORT
    )
    server = loop.run_until_complete(coro)
    logger.info("Serving on %s", server.sockets[0].getsockname())
    return server


async def ask_instance_to_focus():
    reader, writer = await asyncio.open_connection(HOST, PORT)
    message = "focus\n"
    logger.debug("Send: {!r}".format(message))
    writer.write(message.encode())
    await writer.drain()
    logger.debug("Closing the connection to the server.")
    writer.close()
    await writer.wait_closed()
