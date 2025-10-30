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

    def connection_made(self, transport):
        peername = transport.get_extra_info("peername")
        print("Connection from {}".format(peername))
        self.transport = transport

    def data_received(self, data):
        message = data.decode()
        print("Data received: {!r}".format(message))
        self.incoming_queue.put_nowait(
            IncomingEvent.create_app_event(AppEventEnum.FOCUS, None)
        )
        self.transport.write(b"OK\n")
        self.transport.close()

    def write_reply(self, fut):
        reply = fut.result()
        print("Send: {!r}".format(reply))
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
    print("Send: {!r}".format(message))
    writer.write(message.encode())
    await writer.drain()
    print("Close the connection")
    writer.close()
    await writer.wait_closed()
