import logging

import inject

from pysaic.config import Config
from pysaic.controllers.game import remove_money_from_player
from pysaic.entities import (
    OutgoingMessage,
    OutgoingQueue,
    IncomingQueue,
    IncomingEvent,
)
from pysaic.enums import AppEventEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.state import State
from pysaic.ui.app import App
from pysaic.use_cases.ui.our_priv_message import OurPrivMessageUseCase

logger = logging.getLogger(__name__)


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
        }

    @classmethod
    def handle(cls, state, config, ui: "App", command, params):
        instance = cls(state, config, ui)
        instance.execute(command, params)

    def execute(self, command, params):
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

        logger.info("Sending private message to %r: %r", target, content)
        message = OutgoingMessage(target, content)
        OurPrivMessageUseCase(
            self.state.chat_users,
            self.ui,
            message,
            self.state.chat_users[self.config.nick],
        ).execute()
        outgoing_queue.put_nowait(message)

    @inject.autoparams()
    def handle_unknown(self, params, incoming_queue: IncomingQueue):
        logger.warning("Unknown command %r", params)
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Unknown command {params!r}",
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

        self.send_money_to_target(target, int(amount))
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Payed {amount} to {target}."
            )
        )

    @inject.autoparams()
    def send_money_to_target(
        self,
        target,
        amount,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        if not self.state.is_game_running:
            logger.debug("Game is not running in order to send money.")
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "You need to be in game to send money."
                )
            )
            return

        if self.config.block_money_transfer:
            logger.debug("Money transfer is blocked.")
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "Money transfer is blocked. Change it in the settings."
                )
            )
            return

        if not self.state.money_enough(amount):
            logger.debug("Not enough money to send.")
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "You don't have enough money to send."
                )
            )
            return

        outgoing_queue.put_nowait(
            OutgoingMessage(
                target=target,
                content=f"{self.config.current_faction.value} pay {END_OF_ACTOR_CHARACTER} {amount}",
            )
        )
        remove_money_from_player(
            self.config.nick, target, amount  # replace with state.nick
        )
