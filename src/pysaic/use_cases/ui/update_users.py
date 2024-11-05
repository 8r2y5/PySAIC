import logging
from tkinter import END, Scrollbar, Text

import inject

from pysaic.config import Config
from pysaic.controllers.ui.user_list import DISPLAY_MODES_MAP
from pysaic.ui.app import App
from pysaic.use_cases.ui.utils import enable_disable

logger = logging.getLogger(__name__)


class UpdateUsersUseCase:
    @property
    def scroll_bar(self) -> Scrollbar:
        return self.ui.users_list_scroll

    @property
    def users_list(self) -> Text:
        return self.ui.users_list

    @property
    def chat_users(self):
        return self.state.chat_users

    def __init__(self, state, ui: App):
        self.state = state
        self.ui = ui
        # self.config = ui.config

    @inject.autoparams()
    def execute(self, config: Config):
        self.ui.position = self.scroll_bar.get()
        logger.info("Updating users list")
        with enable_disable(self.users_list, tail=False):
            self.users_list.delete("0.0", END)

            DISPLAY_MODES_MAP[config.user_list_display](
                self.users_list, self.chat_users
            ).write()

        if len(self.ui.position) == 2:
            self.users_list.yview_moveto(self.ui.position[0])
