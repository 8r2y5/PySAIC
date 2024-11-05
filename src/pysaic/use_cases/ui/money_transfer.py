import logging
import re
from asyncio import Queue
from tkinter import END

import inject

from pysaic.config import Config
from pysaic.controllers.game import (
    add_money_to_user,
    remove_money_from_player,
)
from pysaic.entities import (
    OutgoingMessage,
    IncomingQueue,
    IncomingEvent,
)
from pysaic.enums import FactionsEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.state import State
from pysaic.use_cases.ui.use_case import UiUseCase
from pysaic.use_cases.ui.utils import enable_disable, normalize_content

incoming_money_transfer_regexp = re.compile(
    rf"actor_\w+ pay {END_OF_ACTOR_CHARACTER} (\d+)"
)

logger = logging.getLogger(__name__)


class IncomingMoneyTransferUseCase(UiUseCase):
    def execute(self):
        if not self.state.is_game_running:
            logger.warning("Game is not running")
            return

        if self.config.block_money_transfer:
            logger.warning("Money transfer is blocked")
            return

        if not self.event.content.startswith("actor_"):
            logger.warning(
                "Content does not start with 'actor_': %r",
                self.event.content,
            )
            return

        match = incoming_money_transfer_regexp.match(self.event.content)
        if not match:
            logger.warning(
                "Content does not match the regexp: %r",
                self.event.content,
            )
            return

        amount = match.group(1)

        with enable_disable(self.messages_list):
            self._add_message_to_ui(amount)

        add_money_to_user(self.event.author, amount)

    def _add_content_to_message(self, content: str):
        self.messages_list.insert(
            END,
            f": {normalize_content(content)}{self._add_new_line_if_necessary(content)}",
            "Information",
        )

    def _add_message_to_ui(self, amount):
        self._add_date_to_message()
        self._add_user_and_faction_color()
        self._add_content_to_message(f"have send you {amount} RUB.")
        self.messages_list.see(END)


@inject.autoparams()
def send_money_use_case(
    target,
    amount,
    outgoing_queue: Queue,
    config: Config,
    state: State,
    incoming_queue: IncomingQueue,
):
    if not state.is_game_running:
        logger.debug("Game is not running in order to send money.")
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                "You need to be in game to send money."
            )
        )
        return

    if config.block_money_transfer:
        logger.debug("Money transfer is blocked.")
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                "Money transfer is blocked. Change it in the settings."
            )
        )
        return

    if not state.money_enough(amount):
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
            content=f"{FactionsEnum(config.current_faction).value} pay {END_OF_ACTOR_CHARACTER} {amount}",
        )
    )
    remove_money_from_player(
        config.nick, target, amount  # replace with state.nick
    )
