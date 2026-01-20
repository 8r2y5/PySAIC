import logging
import re
from tkinter import END

import inject

from pysaic.config import Config
from pysaic.controllers.game import add_money_to_user, remove_money_from_player
from pysaic.entities import (
    IncomingEvent,
    IncomingQueue,
    OutgoingMessage,
    OutgoingQueue,
)
from pysaic.enums import FactionsEnum, HistoryMessageEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.state import State
from pysaic.use_cases.ui.use_case import UiUseCase
from pysaic.use_cases.ui.utils import enable_disable, normalize_content

incoming_money_transfer_regexp = re.compile(
    rf"actor_\w+ pay {END_OF_ACTOR_CHARACTER}[ ]?(\d+)"
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

        user = self.chat_users.get(
            self.event.author.nick, self.chat_users[self.state.nick]
        )

        history_user = user.copy()
        history_user.name = self.event.author.nick
        self.state.add_message(
            HistoryMessageEnum.money_recv, history_user, str(amount)
        )

        add_money_to_user(
            self.event.author.nick, user.reputation, user.rank, amount
        )

    def _add_content_to_message(self, content: str):
        self.messages_list.insert(
            END,
            f": {normalize_content(content)}",
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
    outgoing_queue: OutgoingQueue,
    config: Config,
    state: State,
    incoming_queue: IncomingQueue,
) -> bool:
    if not state.is_game_running:
        logger.debug("Game is not running in order to send money.")
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                "You need to be in game to send money."
            )
        )
        return False

    if config.block_money_transfer:
        logger.debug("Money transfer is blocked.")
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                "Money transfer is blocked. Change it in the settings."
            )
        )
        return False

    if target.startswith("@"):
        target = target[1:]

    target_user = state.chat_users.get(target)
    if not target_user:
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"{target!r} is not in the chat."
            )
        )
        return False

    if target_user.in_game is False:
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"{target!r} is not in game."
            )
        )
        return False

    if not state.money_enough(amount):
        logger.debug("Not enough money to send.")
        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                "You don't have enough money to send."
            )
        )
        return False

    logger.debug("Sending money %r to %r", amount, target)
    outgoing_queue.put_nowait(
        OutgoingMessage(
            target=target,
            content=(
                f"{FactionsEnum(config.current_faction).value} pay "
                f"{END_OF_ACTOR_CHARACTER} "
                f"{amount}"
            ),
        )
    )
    user = state.chat_users.get(target) or state.player.create_chat_user()
    user.name = target
    state.add_message(HistoryMessageEnum.money_sent, user, str(amount))
    remove_money_from_player(state.player, target, amount)
    return True
