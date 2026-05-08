import logging
from tkinter import END

from pysaic.entities import IncomingMessage
from pysaic.enums import FactionsEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.ui.hyper_links import HyperlinkManager
from pysaic.use_cases.ui.utils import (
    add_content_of_message_to_messages_list,
    normalize_content,
    prepare_date,
)

logger = logging.getLogger(__name__)


class UiUseCase:
    @property
    def hyperlinks(self) -> HyperlinkManager:
        return self.ui.hyperlinks

    @property
    def messages_list(self):
        return self.ui.messages_list

    @property
    def chat_users(self):
        return self.state.chat_users

    def __init__(self, state, config, ui, event):
        self.state = state
        self.event = event
        self.ui = ui
        self.config = config

    def execute(self):
        raise NotImplementedError

    def _add_date_to_message(self):
        self.messages_list.insert(
            END, f"[{prepare_date(self.event)}] ", "Time"
        )

    def _add_colored_user_to_message(self, user):
        self.messages_list.insert(END, user, self._get_faction_color(user))

    def _add_user_and_faction_color(self):
        self._add_colored_user_to_message(self.event.author.nick)

    def _add_target_and_faction_color(self):
        self._add_colored_user_to_message(self.event.target)

    def _add_content_to_message(
        self, event: IncomingMessage, show_popup=False
    ):
        try:
            content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = event.content

        normalized_content = normalize_content(content)
        add_content_of_message_to_messages_list(
            self.messages_list,
            self.hyperlinks,
            f": {normalized_content}",
            ["Text"],
        )
        if show_popup:
            self.ui.show_popup(
                f"Private message from {event.author.nick}",
                f"{prepare_date(event)}: {normalized_content}",
            )

    def _get_faction_color(self, author) -> list[str]:
        if "NickServ" == author:
            try:
                return self.chat_users[self.state.nick].faction.name
            except (KeyError, ValueError, AttributeError):
                return [FactionsEnum.Anonymous.name]
        try:
            return [
                str(
                    self.chat_users[author].faction.name
                    or FactionsEnum.Anonymous.name
                )
            ] + (["OwnMessage"] if author == self.state.nick else [])
        except (KeyError, ValueError, AttributeError):
            return [FactionsEnum.Anonymous.name]
