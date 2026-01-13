import asyncio
import logging
from typing import Callable, Coroutine, Optional, Sequence

import inject
from irclib.parser import Message

from pysaic.config import Config
from pysaic.entities import (
    IncomingEvent,
    IncomingMessage,
    IncomingQueue,
    IrcUser,
    OutgoingCommand,
    OutgoingMessage,
    OutgoingQueue,
)
from pysaic.enums import AppEventEnum, HistoryMessageEnum, IrcEvents
from pysaic.irc_protocol import PySaicIrcProtocol
from pysaic.state import State
from pysaic.ui.app import App
from pysaic.use_cases.money_transfer import send_money_use_case
from pysaic.use_cases.ui.our_priv_message import OurPrivMessageUseCase

logger = logging.getLogger(__name__)


class HooksHandler:
    def __init__(
        self,
        listen_events: Sequence[IrcEvents],
        end_events: Sequence[IrcEvents],
        timeout_message: str,
        timeout: int = 60,
        custom_handler: Optional[
            Callable[[PySaicIrcProtocol, Message], Coroutine[None, None, None]]
        ] = None,
    ):
        self.listen_events = listen_events
        self.end_events = end_events
        self.timeout_message = timeout_message
        self.timeout = timeout
        self.hooks = []
        self.seen_end = False
        self.handler = custom_handler or self._handler

    @inject.autoparams()
    def __enter__(self, irc: PySaicIrcProtocol):
        for event in self.listen_events:
            # noinspection PyTypeChecker
            self.hooks.append(irc.register(event, self.handler))
        return self

    @inject.autoparams()
    def __exit__(
        self,
        exc_type,
        exc_val,
        exc_tb,
        async_loop: asyncio.AbstractEventLoop,
    ):
        async_loop.create_task(self.unhook_on_timeout())

    @inject.autoparams()
    async def _handler(
        self, conn, message, incoming_queue: IncomingQueue, state: State
    ):
        if message.command in self.end_events:
            for hook in self.hooks:
                conn.unregister(hook)
            self.seen_end = True
            # we still want to send that information to user so no return

        author = IrcUser.from_prefix(message.prefix)
        incoming_queue.put_nowait(
            IncomingMessage(
                author=author,
                target=state.nick,
                content=f"{message.command} "
                + ", ".join([repr(x) for x in message.parameters]),
                service=True,
            )
        )

    @inject.autoparams()
    async def unhook_on_timeout(
        self, irc: PySaicIrcProtocol, incoming_queue: IncomingQueue
    ):
        await asyncio.sleep(self.timeout)
        if not self.seen_end:
            for hook in self.hooks:
                irc.unregister(hook)
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(self.timeout_message)
            )


class CommandUseCase:
    def __init__(self, state: State, config: Config, ui: App):
        self.state = state
        self.config = config
        self.ui = ui
        self.users_list = ui.users_list
        self.chat_users = state.chat_users
        self.commands = {
            "exit": self.handle_exit,
            "msg": self.handle_priv_msg,
            "m": self.handle_priv_msg,
            "w": self.handle_priv_msg,
            "priv": self.handle_priv_msg,
            "dm": self.handle_priv_msg,
            "help": self.handle_help,
            "commands": self.handle_commands,
            "nick": self.handle_nick,
            "pay": self.handle_pay,
            "block": self.handle_block,
            "blockword": self.handle_blockword,
            "afk": self.handle_afk,
            "quit": self.handle_exit,
            "mode": self.handle_mode,
            "whois": self.handle_whois,
            "who": self.handle_who,
            "whowas": self.handle_whowas,
            "kick": self.handle_kick,
            "smite": self.handle_kick,
            "reply": self.handle_reply,
            "r": self.handle_reply,
        }

    @classmethod
    def handle(cls, state, config, ui: "App", command, params):
        instance = cls(state, config, ui)
        instance.execute(command, params)

    def execute(self, command, params):
        logger.debug("Executing command: %r with params: %r", command, params)
        self.commands.get(command, self.handle_unknown)(params)

    @inject.autoparams()
    def handle_exit(self, _params, incoming_queue: IncomingQueue):
        """
        Exits the application. Usage: /exit
        """
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(AppEventEnum.EXIT, None)
        )
        self.ui.on_close()

    @inject.autoparams()
    def handle_priv_msg(self, params, outgoing_queue: OutgoingQueue):
        """
        Sends private message to a user. Usage: /msg <user> <message>
        """
        try:
            target, content = params.split(" ", 1)
        except (ValueError, AttributeError):
            self.handle_help("msg")
            return

        if not content:
            self.handle_help("msg")
            return

        target = target.lstrip("@")
        logger.info("Sending private message to %r: %r", target, content)
        self.state.last_private_message_from = target
        message = OutgoingMessage(target, content)
        OurPrivMessageUseCase(
            self.state.chat_users,
            self.ui,
            message,
            self.state.chat_users[self.state.nick],
        ).execute()
        outgoing_queue.put_nowait(message)
        history_user = (
            self.chat_users.get(target) or self.state.player.create_chat_user()
        )
        history_user.name = target
        self.state.add_message(HistoryMessageEnum.dm_to, history_user, content)

    @inject.autoparams()
    def handle_unknown(self, params, incoming_queue: IncomingQueue):
        logger.warning("Unknown command %r", params)
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Unknown command {params!r}",
            )
        )

    @inject.autoparams()
    def handle_afk(self, params, incoming_queue: IncomingQueue):
        """
        Toggles AFK state. Usage: /afk
        """
        logger.info("Handling AFK command with params: %r", params)
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                AppEventEnum.TOGGLE_AFK,
                params.strip() if params else None,
            )
        )

    @inject.autoparams()
    def handle_commands(self, _params, incoming_queue: IncomingQueue):
        """
        Shows list of available commands. Usage: /commands
        """
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Available commands: {', '.join(self.commands.keys())}.",
            )
        )

    @inject.autoparams()
    def handle_help(self, params, incoming_queue: IncomingQueue):
        if not params or params not in self.commands or params == "help":
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "Usage /help <command>, list of available commands: /commands",
                )
            )
            return

        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                self.commands[params].__doc__.strip(),
            )
        )

    @inject.autoparams()
    def handle_nick(self, params, incoming_queue: IncomingQueue):
        """
        Change nick. Usage /nick <nick>
        """
        if not params:
            self.handle_help("nick")
            return

        nick = params.split(" ")[0]
        if not nick:
            self.handle_help("nick")
            return

        self.config.nick = nick
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(AppEventEnum.OPTIONS_UPDATED, None)
        )

    @inject.autoparams()
    def handle_pay(self, params, incoming_queue: IncomingQueue):
        """
        Pay to user. Usage: /pay <user> <amount>
        """
        if self.config.block_money_transfer:
            incoming_queue.put_nowait(
                IncomingEvent.create_error_event(
                    "Money transfer is blocked. Check settings."
                )
            )
            return

        try:
            target, amount = params.split(" ", 1)
        except ValueError:
            self.handle_help("pay")
            return

        if not amount or not amount.isdigit():
            self.handle_help("pay")
            return

        if send_money_use_case(target, int(amount)):
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"{self.state.nick} has sent money to {target}: {amount} RUB.",
                    target="only_chat",
                )
            )

    @inject.autoparams()
    def handle_block(
        self, params, config: Config, incoming_queue: IncomingQueue
    ):
        """
        Blocks messages from the user. Usage: /block <add/del/list> <user>
        """
        if not params:
            self.handle_help("block")
            return

        if params == "list":
            if not config.blocked_users:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        "No users are blocked."
                    )
                )
            else:
                blocked_list = ", ".join(config.blocked_users.keys())
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Blocked users: {blocked_list}"
                    )
                )
            return

        try:
            sub, rest = params.split(" ", 1)
        except (AttributeError, ValueError):
            self.handle_help("block")
            return

        rest = rest.lstrip("@")
        if sub == "add":
            if rest in config.blocked_users:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"{rest!r} is already blocked."
                    )
                )
                return
            config.blocked_users[rest] = set()
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Blocked messages from {rest!r}"
                )
            )
        elif sub == "del":
            if rest not in config.blocked_users:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"{rest!r} is not blocked."
                    )
                )
                return
            del config.blocked_users[rest]
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"{rest!r} is unblocked."
                )
            )
        else:
            self.handle_help("block")

    @inject.autoparams()
    def handle_blockword(
        self, params, config: Config, incoming_queue: IncomingQueue
    ):
        """
        Blocks that contain word. Usage: /block <add/del/list> <word>
        """
        if not params:
            self.handle_help("handle_blockword")
            return

        if params == "list":
            if not config.blocked_words:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        "No words are blocked."
                    )
                )
            else:
                blocked_list = ", ".join(config.blocked_words)
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Blocked words: {blocked_list}"
                    )
                )
            return

        try:
            sub, rest = params.split(" ", 1)
        except (AttributeError, ValueError):
            self.handle_help("handle_blockword")
            return

        rest = rest.strip(" ")
        if sub == "add":
            if rest in self.commands:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"{rest!r} is a command and cannot be blocked."
                    )
                )
                return

            if rest in config.blocked_words:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"{rest!r} is already in blocked words."
                    )
                )
                return
            config.blocked_words.append(rest)
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Blocked messages contaning {rest!r}"
                )
            )
        elif sub == "del":
            if rest not in config.blocked_words:
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"{rest!r} is not blocked words list."
                    )
                )
                return
            del config.blocked_words[rest]
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"{rest!r} was remove from blocked words."
                )
            )
        else:
            self.handle_help("handle_blockword")

    @inject.autoparams()
    def handle_mode(
        self,
        content,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Change user mode. Usage: /mode <modes>
        """
        if not content or content.strip() == "":
            self.handle_help("mode")
            return

        with HooksHandler(
            listen_events=[
                IrcEvents.RPL_UMODEIS,
                IrcEvents.RPL_ENDOFMODE,
                IrcEvents.ERR_UMODEUNKNOWNFLAG,
                IrcEvents.RPL_CREATIONTIME,
                IrcEvents.ERR_NOSUCHNICK,
                IrcEvents.RPL_BANLIST,
                IrcEvents.RPL_ENDOFBANLIST,
                IrcEvents.MODE,
            ],
            end_events=[
                IrcEvents.RPL_ENDOFMODE,
                IrcEvents.ERR_NOSUCHNICK,
                IrcEvents.RPL_ENDOFBANLIST,
                IrcEvents.MODE,
            ],
            timeout_message=f"MODE for {content} timed out. Unhooking.",
            timeout=10,
        ):
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Sending MODE {content}"
                )
            )
            outgoing_queue.put_nowait(
                OutgoingCommand(command=IrcEvents.MODE, args=[content])
            )

    @inject.autoparams()
    def handle_whois(
        self,
        params,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Get info about user. Usage: /whois <user>
        """
        if not params or params.strip() == "":
            self.handle_help("whois")
            return

        with HooksHandler(
            listen_events=[
                IrcEvents.ERR_NOSUCHNICK,
                IrcEvents.RPL_ENDOFWHOIS,
                IrcEvents.RPL_USERIP,
                IrcEvents.RPL_WHOISCHANNELS,
                IrcEvents.RPL_WHOISHOST,
                IrcEvents.RPL_WHOISIDLE,
                IrcEvents.RPL_WHOISSERVER,
                IrcEvents.RPL_WHOISUSER,
            ],
            end_events=[IrcEvents.RPL_ENDOFWHOIS, IrcEvents.ERR_NOSUCHNICK],
            timeout_message=f"WHOIS for {params} timed out. Unhooking.",
        ):
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Sending WHOIS {params}"
                )
            )
            outgoing_queue.put_nowait(
                OutgoingCommand(command=IrcEvents.WHOIS, args=[params])
            )

    @inject.autoparams()
    def handle_who(
        self,
        params,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Get info about users in channel. Usage: /who <channel>
        """
        if not params or params.strip() == "":
            self.handle_help("who")
            return

        with HooksHandler(
            listen_events=[
                IrcEvents.RPL_WHOREPLY,
                IrcEvents.RPL_ENDOFWHO,
                IrcEvents.ERR_NOSUCHNICK,
            ],
            end_events=[IrcEvents.RPL_ENDOFWHO, IrcEvents.ERR_NOSUCHNICK],
            timeout_message=f"WHO for {params} timed out. Unhooking.",
        ):
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(f"Sending WHO {params}")
            )
            outgoing_queue.put_nowait(
                OutgoingCommand(command=IrcEvents.WHO, args=[params])
            )

    @inject.autoparams()
    def handle_whowas(
        self,
        params,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Get info about users in channel. Usage: /who <channel>
        """
        if not params or params.strip() == "":
            self.handle_help("whowas")
            return

        with HooksHandler(
            listen_events=[
                IrcEvents.RPL_WHOWASUSER,
                IrcEvents.RPL_WHOISSERVER,
                IrcEvents.RPL_ENDOFWHOWAS,
                IrcEvents.ERR_WASNOSUCHNICK,
            ],
            end_events=[
                IrcEvents.RPL_ENDOFWHOWAS,
                IrcEvents.ERR_WASNOSUCHNICK,
            ],
            timeout_message=f"WHOWAS for {params} timed out. Unhooking.",
        ):
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Sending WHOWAS {params}"
                )
            )

            outgoing_queue.put_nowait(
                OutgoingCommand(command=IrcEvents.WHOWAS, args=[params])
            )

    @inject.autoparams()
    def handle_kick(
        self,
        params,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Kick user from channel. Usage: /kick <user> [reason]
        """
        if not params or params.strip() == "":
            self.handle_help("kick")
            return

        try:
            target, reason = params.split(" ", 1)
        except ValueError:
            target, reason = params, self.state.nick

        target = target.lstrip("@")

        if target not in self.chat_users:
            incoming_queue.put_nowait(
                IncomingEvent.create_error_event(
                    f"User {target!r} not found in chat users."
                )
            )
            return

        with HooksHandler(
            listen_events=[
                IrcEvents.ERR_CHANOPRIVSNEEDED,
                IrcEvents.ERR_NOSUCHNICK,
                IrcEvents.ERR_NOTONCHANNEL,
            ],
            end_events=[
                IrcEvents.ERR_CHANOPRIVSNEEDED,
                IrcEvents.ERR_NOSUCHNICK,
                IrcEvents.ERR_NOTONCHANNEL,
            ],
            timeout_message=f"KICK for {target} timed out. Unhooking.",
        ):
            outgoing_queue.put_nowait(
                OutgoingCommand(
                    command=IrcEvents.KICK,
                    args=[self.config.server.previous_channel, target, reason],
                )
            )

    @inject.autoparams()
    def handle_reply(self, params, incoming_queue: IncomingQueue):
        """
        Reply to last private message. Usage: /reply <message>
        """
        last_private = self.state.last_private_message_from
        if not last_private:
            incoming_queue.put_nowait(
                IncomingEvent.create_error_event(
                    "No one has sent you a private message yet."
                )
            )
            return

        if not params or params.strip() == "":
            self.handle_help("reply")
            return

        self.handle_priv_msg(f"{last_private} {params.strip()}")
