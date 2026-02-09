import asyncio
import logging

import inject

from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum
from pysaic.script_reader.router import parse_line
from pysaic.state import State

logger = logging.getLogger(__name__)
HOST = "127.0.0.1"
PORT = 9754
GAME_PORT = 8008  # Corrected port to match Lua script

# Global queue for game messages
game_message_queue = asyncio.Queue()


class GameClientProtocol(asyncio.Protocol):
    def __init__(self, message_queue):
        self.message_queue = message_queue
        self.transport = None
        self.logger = logger.getChild("game")

    @inject.autoparams()
    def connection_made(
        self, transport, state: State
    ):
        self.transport = transport
        state.game_transport = transport
        self.logger.debug(
            "Game connection made from %s",
            transport.get_extra_info("peername"),
        )

    def data_received(self, data):
        message = data.decode()
        self.logger.debug("Game data received: %r", message)
        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue
            # Put messages into the queue instead of creating tasks
            self.message_queue.put_nowait(line)

    @inject.autoparams()
    def connection_lost(
        self, exc, state: State
    ):
        self.logger.debug("Game connection lost")
        state.game_transport = None
        self.transport = None


class PySAICClientProtocol(asyncio.Protocol):
    def __init__(self, incoming_queue):
        self.incoming_queue = incoming_queue
        self.transport = None
        self.logger = logger.getChild("client")

    @inject.autoparams()
    def connection_made(self, transport, state: State):
        self.transport = transport
        # Do not overwrite game_transport here
        self.logger.debug(
            "Connection made from %s", transport.get_extra_info("peername")
        )

    @inject.autoparams()
    def data_received(self, data, state: State):
        message = data.decode()
        self.logger.debug("Data received: %r", message)

        # Handle multiple messages in one packet or split messages
        for line in message.splitlines():
            line = line.strip()
            if not line:
                continue

            command = line.lower()
            self.logger.debug("Command parsed: %r", command)
            if command == "focus":
                self.logger.debug("Processing focus command.")
                self.incoming_queue.put_nowait(
                    IncomingEvent.create_app_event(AppEventEnum.FOCUS, None)
                )
                self.transport.write(b"OK\n")
            else:
                # This protocol is for app-level commands, not game messages
                self.logger.warning("Unknown command received: %r", line)

    @inject.autoparams()
    def connection_lost(self, exc, state: State):
        self.logger.debug("Connection lost")
        self.transport = None

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


def get_game_server(loop):
    coro = loop.create_server(
        lambda: GameClientProtocol(game_message_queue), HOST, GAME_PORT
    )
    server = loop.run_until_complete(coro)
    logger.info("Game server serving on %s", server.sockets[0].getsockname())
    return server


@inject.autoparams()
async def game_message_processor(
    incoming_queue: IncomingQueue,
):
    logger.debug("Starting game message processor")
    while True:
        message = await game_message_queue.get()
        if message is None:  # Sentinel for shutdown
            break
        await parse_line(message, incoming_queue)
        game_message_queue.task_done()


async def ask_instance_to_focus():
    try:
        reader, writer = await asyncio.open_connection(HOST, PORT)
        message = "focus\n"
        logger.debug("Send: %r", message)
        writer.write(message.encode())
        await writer.drain()
        logger.debug("Closing the connection to the server.")
        writer.close()
        await writer.wait_closed()
    except ConnectionRefusedError:
        logger.info("Could not connect to existing instance to focus.")
