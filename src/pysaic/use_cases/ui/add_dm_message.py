import logging
from tkinter import END

from pysaic.controllers.game import add_dm_message_to_game
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.use_cases.irc_mode_to_user_type import parsed_mode_to_name
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
            self._add_content_to_message(
                self.event, show_popup=self.ui.should_show_popups
            )
            self.messages_list.see(END)

    def _add_dm_message_to_game(self):
        try:
            content = self.event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = self.event.content
        try:
            user = self.chat_users.get(
                self.event.author.nick, self.chat_users[self.state.nick]
            )
        except KeyError:
            user = self.state.player.create_chat_user()
        add_dm_message_to_game(
            author_faction_actor=get_faction_actor(user),
            user_type=parsed_mode_to_name(user.irc_mode),
            # self.event.author.nick is already cleared out of irc mode
            author=self.event.author.nick,
            icon_id=user.avatar,
            reputation_author=user.rank,
            rank_author=user.reputation,
            receiver=self.event.target,
            content=normalize_content(content),
        )
