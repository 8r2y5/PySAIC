import logging
from tkinter import END

from pysaic.controllers.game import add_dm_message_to_game
from pysaic.enums import FactionsEnum
from pysaic.use_cases import irc_mode_to_user_type
from pysaic.use_cases.ui.utils import (
    add_content_of_message_to_messages_list,
    enable_disable,
)

logger = logging.getLogger(__name__)


class OurPrivMessageUseCase:
    @property
    def hyperlinks(self):
        return self.ui.hyperlinks

    @property
    def messages_list(self):
        return self.ui.messages_list

    def __init__(self, chat_users, ui, outgoing_message, chat_user):
        self.chat_users = chat_users
        self.ui = ui
        self.outgoing_message = outgoing_message
        self.chat_user = chat_user

    def execute(self):
        self._add_our_priv_message()
        add_dm_message_to_game(
            author_faction_actor=self.chat_user.faction.value,
            user_type=irc_mode_to_user_type.get(self.chat_user.irc_mode),
            author=self.chat_user.name,
            icon_id=self.chat_user.avatar,
            reputation_author=self.chat_user.reputation,
            rank_author=self.chat_user.rank,
            receiver=self.outgoing_message.target,
            content=self.outgoing_message.content,
        )

    def _add_our_priv_message(self):
        logger.info("Adding our priv message: %r", self.outgoing_message)
        with enable_disable(self.messages_list):
            self.messages_list.insert(
                END, f"[{self._add_message_date()}] ", "Time"
            )
            self.messages_list.insert(
                END, f"{self.chat_user.name}", self.chat_user.faction.name
            )
            self.messages_list.insert(END, " -> ", "DM")
            target = self.outgoing_message.target
            self.messages_list.insert(
                END, f"{target}", self._get_target_faction_name(target)
            )
            add_content_of_message_to_messages_list(
                self.messages_list,
                self.hyperlinks,
                f": {self.outgoing_message.content}",
                ["Text"],
            )

    def _add_message_date(self):
        return self.outgoing_message.created_at.strftime("%H:%M:%S")

    def _get_target_faction_name(self, target):
        return (
            self.chat_users[target].faction.name
            if target in self.chat_users
            else FactionsEnum.Anonymous.name
        )
