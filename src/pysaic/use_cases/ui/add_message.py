import logging
from tkinter import END

from pysaic.controllers.game import add_channel_message_to_game
from pysaic.enums import FactionsEnum, HistoryMessageEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER, START_OF_ACTOR_CHARACTER
from pysaic.use_cases.irc_mode_to_user_type import parsed_mode_to_name
from pysaic.use_cases.text import make_content_malformed
from pysaic.use_cases.ui.use_case import UiUseCase
from pysaic.use_cases.ui.utils import (
    enable_disable,
    get_faction_actor,
    normalize_content,
)

logger = logging.getLogger(__name__)


class AddMessageUseCase(UiUseCase):
    def execute(self):
        if self.state.should_malform_messages is True:
            self.event.content = make_content_malformed(self.event.content)
        self._add_channel_message()
        self._add_channel_message_to_game()

    def _add_channel_message(self):
        logger.debug("Adding channel message: %r", self.event)
        author_nick = self.event.author.nick
        highlight = (
            author_nick != self.state.nick
            and self.state.nick in self.event.content
        ) or author_nick == "NickServ"
        additional_tags = ["Highlight"] if highlight else []
        show_popup = self.ui.should_show_popups and highlight

        # tab_id = self.event.target  # multiple channels support?
        self.ui.tabbed_chat.notify_new_message("main")

        with enable_disable(self.messages_list):
            self._add_date_to_message()
            if START_OF_ACTOR_CHARACTER in self.event.content:
                self._add_death_message(additional_tags)
            else:
                self._add_user_and_faction_color()
                self._add_content_to_message(self.event, show_popup)

            if highlight:
                line_num = self.messages_list.index("end-1c").split(".")[0]
                self.messages_list.tag_add("Highlight", f"{line_num}.0", "end")

    def _add_death_message(self, additional_tags=None):
        if additional_tags is None:
            additional_tags = []
        author, faction_actor, content = (
            self._get_death_message_author_and_content()
        )
        if self.state.fake_disconnect is True:
            content = make_content_malformed(content)

        try:
            faction_tag = FactionsEnum(faction_actor).name
        except ValueError:
            faction_tag = FactionsEnum.Anonymous.name

        self.messages_list.insert(
            END,
            author,
            [faction_tag] + additional_tags,
        )
        content = content.lstrip("\n")
        self.messages_list.insert(
            END,
            f": {content}",
            ["Text"] + additional_tags,
        )

    def _add_channel_message_to_game(self):
        if START_OF_ACTOR_CHARACTER in self.event.content:
            author, faction_actor, content = (
                self._get_death_message_author_and_content()
            )
        else:
            author, content = self.event.author.nick, normalize_content(
                self.event.content
            )
            try:
                faction_actor = get_faction_actor(self.chat_users[author])
            except KeyError:
                # self._readd_user_to_chat_users()
                try:
                    faction_actor = get_faction_actor(self.chat_users[author])
                except KeyError:
                    # happens in edge cases when user was deleted from
                    # the list before message was processed
                    faction_actor = "Anonymous"

        user = self.chat_users.get(
            author, self.state.player.create_chat_user()
        )
        user.name = author
        self.state.add_message(HistoryMessageEnum.channel, user, content)

        add_channel_message_to_game(
            faction_actor=faction_actor,
            author=author,
            icon_id=user.avatar,
            reputation_author=user.reputation,
            rank_author=user.rank,
            highlight=str(self.state.nick in self.event.content),
            user_type=parsed_mode_to_name(user.irc_mode),
            content=content,
        )

    def _get_death_message_author_and_content(self):
        author = self.event.content.split(START_OF_ACTOR_CHARACTER, 1)[0]
        faction_actor = self.event.content.split(START_OF_ACTOR_CHARACTER, 1)[
            1
        ].split(END_OF_ACTOR_CHARACTER, 1)[0]
        content = self.event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        return author, faction_actor, normalize_content(content)
