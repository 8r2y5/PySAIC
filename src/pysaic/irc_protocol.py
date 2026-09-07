import asyncio
import concurrent.futures
import logging
import socket
from asyncio import AbstractEventLoop
from itertools import cycle
from typing import Optional, Sequence, Tuple, Union, cast

import inject
from asyncirc.protocol import IrcProtocol, SASLMechanism
from asyncirc.server import BaseServer, ConnectedServer, Server
from asyncirc.util.backoff import AsyncDelayer
from irclib.parser import Message

from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum, InformationType

SEND_TYPE = Union[str, bytes]


logger = logging.getLogger(__name__)


async def _internal_ping(conn: "PySaicIrcProtocol", message: Message) -> None:
    # difference between asyncirc and pysaic this use await to send PONG
    await conn.async_send(f"PONG {message.parameters}")


class PySaicIrcProtocol(IrcProtocol):
    def __init__(
        self,
        servers: Sequence[Server],
        nick: str,
        user: Optional[str] = None,
        realname: Optional[str] = None,
        certpath: Optional[str] = None,
        sasl_auth: Optional[Tuple[str, str]] = None,
        sasl_mech: Optional[SASLMechanism] = None,
        logger: Optional[logging.Logger] = None,
        loop: Optional[AbstractEventLoop] = None,
    ) -> None:
        super().__init__(
            servers=servers,
            nick=nick,
            user=user,
            realname=realname,
            certpath=certpath,
            sasl_auth=sasl_auth,
            sasl_mech=sasl_mech,
            logger=logger,
            loop=loop,
        )

        # to not copy whole __init__ method from IrcProtocol and change it
        for hook, (cmd, handler) in self.handlers.items():
            if cmd == "PONG":
                # noinspection PyTypeChecker
                self.handlers[hook] = (
                    cmd,
                    _internal_ping,
                )

    @inject.autoparams()
    async def connect(self, incoming_queue: IncomingQueue) -> None:
        delay_in_sec = 10
        delay_in_sec_on_failure = 300
        delayer = AsyncDelayer(delay_in_sec)
        for server in cycle(self.servers):
            async with delayer:
                server_address = f"{server.host}:{server.port}"
                self.logger.info("Attempting to connect to %s", server_address)
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Trying to connect to the server {server_address}.",
                        type=InformationType.debug,
                    )
                )
                if await self._connect(server):
                    incoming_queue.put_nowait(
                        IncomingEvent.create_information_event(
                            f"Connected to the server {server_address}, waiting for response...",
                            type=InformationType.debug,
                        )
                    )
                    self.logger.info(
                        "Connected successfully to %s", server_address
                    )
                    break
                else:
                    incoming_queue.put_nowait(
                        IncomingEvent.create_error_event(
                            f"Failed to connect to server. Retrying in {delay_in_sec_on_failure} seconds."
                        )
                    )
                    self.logger.warning(
                        "Failed to connect to %s, retrying in %d seconds",
                        server_address,
                        delay_in_sec_on_failure,
                    )
                    await asyncio.sleep(delay_in_sec_on_failure)

    @inject.autoparams()
    def connection_lost(
        self, exc: Optional[Exception], incoming_queue: IncomingQueue
    ) -> None:
        self.logger.warning("Connection lost")
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                AppEventEnum.CONNECTION_TO_SERVER_ISSUE,
                "Connection lost with the server.",
            )
        )
        super().connection_lost(exc)

    @inject.autoparams()
    async def _connect(
        self, server: BaseServer, incoming_queue: IncomingQueue
    ) -> bool:
        self._connected_future = self.loop.create_future()
        self.quit_future = self.loop.create_future()
        self._server = ConnectedServer(server)
        if self.logger:
            connection = self.server.connection
            if self.connected:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Reconnecting to {connection.host}:{connection.port}.",
                        type=InformationType.debug,
                    )
                )
                self.logger.info(
                    "Reconnecting to %s:%s", connection.host, connection.port
                )
            else:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Connecting to {connection.host}:{connection.port}.",
                        type=InformationType.debug,
                    )
                )
                self.logger.info(
                    "Connecting to %s:%s", connection.host, connection.port
                )

        fut = self._server.connection.do_connect(self)
        try:
            await asyncio.wait_for(fut, 60)
        except asyncio.TimeoutError:
            if self.logger:
                self.logger.exception(
                    "Connection timeout occurred while connecting to %s:%s",
                    self.server.connection.host,
                    self.server.connection.port,
                )
            incoming_queue.put_nowait(
                IncomingEvent.create_app_event(
                    AppEventEnum.CONNECTION_TO_SERVER_ISSUE,
                    "Connection timeout.",
                )
            )

            return False
        except (ConnectionError, socket.gaierror) as e:
            if self.logger:
                self.logger.exception(
                    "Error occurred while connecting to %s:%s (%s)",
                    self.server.connection.host,
                    self.server.connection.port,
                    e,
                )
            incoming_queue.put_nowait(
                IncomingEvent.create_app_event(
                    AppEventEnum.CONNECTION_TO_SERVER_ISSUE,
                    "Could not connect to server.",
                )
            )

            return False

        if self.logger:
            self.logger.info(
                "Connected to %s:%s",
                self.server.connection.host,
                self.server.connection.port,
            )
        return True

    def send(self, text: SEND_TYPE) -> concurrent.futures.Future:
        """Send a raw line to the server"""
        return asyncio.run_coroutine_threadsafe(self._send(text), self.loop)

    async def async_send(self, text: SEND_TYPE) -> asyncio.Future:
        return asyncio.wrap_future(self.send(text), loop=self.loop)

    def connection_made(self, transport: "asyncio.BaseTransport") -> None:
        """Called by the event loop when the connection has been established"""
        if not self.server:
            msg = "Server not set during connection_made()"
            raise ValueError(msg)

        self._transport = cast(asyncio.Transport, transport)
        self._connected = True
        self._connected_future.set_result(None)
        self.send("CAP LS 302")
        if self.server.password:
            self.send(f"PASS {self.server.password}")

        self.send(f"NICK {self.nick}")
        self.send(f"USER {self.user} 0 * :{self.realname}")
