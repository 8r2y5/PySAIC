import logging
from tkinter import END

from pysaic.controllers.game import add_dm_message_to_game
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.use_cases.ui.use_case import UiUseCase
from pysaic.use_cases.ui.utils import (
    enable_disable,
    get_faction_actor,
    normalize_content,
)

logger = logging.getLogger(__name__)


class AddDmMessage(UiUseCase):
    def execute(self):
        self._add_dm_message()
        self._add_dm_message_to_game()

    def _add_dm_message(self):
        logger.debug("Adding dm message: %r", self.event)
        with enable_disable(self.messages_list):
            self._add_date_to_message()
            self._add_user_and_faction_color()
            self.messages_list.insert(END, " -> ", "DM")
            self._add_target_and_faction_color()
            self._add_content_to_message(self.event)
            self.messages_list.see(END)

    def _add_dm_message_to_game(self):
        try:
            content = self.event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = self.event.content
        add_dm_message_to_game(
            author_faction_actor=get_faction_actor(
                self.chat_users.get(
                    self.event.author, self.chat_users[self.config.nick]
                )
            ),
            author=self.event.author,
            receiver=self.event.target,
            content=normalize_content(content),
        )
