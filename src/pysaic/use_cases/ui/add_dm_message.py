import logging
from tkinter import END

from pysaic.controllers.game import add_dm_message_to_game
from pysaic.enums import HistoryMessageEnum
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
    def __init__(self, state, config, ui, event):
        super().__init__(state, config, ui, event)
        self._tab = None

    @property
    def messages_list(self):
        if self._tab:
            return self._tab.messages_list
        return super().messages_list

    @property
    def hyperlinks(self):
        if self._tab:
            return self._tab.hyperlinks
        return super().hyperlinks

    def execute(self):
        if (
            self.event.author.nick not in self.state.chat_users
            and not self.event.service
        ):
            logger.debug(
                "Ignoring DM from %r because they are not in chat users",
                self.event.author.nick,
            )
            return

        self.state.last_private_message_from = self.event.author.nick

        tab_id = self.event.author.nick
        self.ui.tabbed_chat.add_tab(tab_id, tab_id, is_app_tab=True)
        self._tab = self.ui.tabbed_chat.get_tab(tab_id)
        self.ui.tabbed_chat.notify_new_message(tab_id)

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

    def _add_dm_message_to_game(self):
        try:
            content = self.event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = self.event.content
        if self.event.author.nick == self.state.nick:
            user = self.state.player.create_chat_user()
        else:
            try:
                user = self.chat_users.get(
                    self.event.author.nick, self.chat_users[self.state.nick]
                )
            except KeyError:
                user = self.state.player.create_chat_user()

        history_user = user.copy()
        history_user.name = self.event.author.nick
        self.state.add_message(
            HistoryMessageEnum.dm_from, history_user, content
        )

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
