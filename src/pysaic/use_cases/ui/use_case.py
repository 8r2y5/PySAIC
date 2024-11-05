from tkinter import END

from pysaic.entities import IncomingMessage
from pysaic.enums import FactionsEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.use_cases.ui.utils import normalize_content, prepare_date


class UiUseCase:
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
        self._add_colored_user_to_message(self.event.author)

    def _add_target_and_faction_color(self):
        self._add_colored_user_to_message(self.event.target)

    def _add_content_to_message(self, event: IncomingMessage):
        try:
            content = event.content.split(END_OF_ACTOR_CHARACTER, 1)[1]
        except IndexError:
            content = event.content
        self.messages_list.insert(
            END,
            f": {normalize_content(content)}{self._add_new_line_if_necessary(content)}",
            "Text",
        )

    @staticmethod
    def _add_new_line_if_necessary(content):
        return "" if content.endswith("\n") else "\n"

    def _get_faction_color(self, author) -> str:
        if "NickServ" in author:
            return self.chat_users[self.config.nick].faction.name
        try:
            return str(
                self.chat_users[author].faction.name
                or FactionsEnum.Anonymous.name
            )
        except (KeyError, ValueError, AttributeError):
            return FactionsEnum.Anonymous.name
