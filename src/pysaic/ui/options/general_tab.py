import logging
from tkinter import (
    Frame,
    StringVar,
    Radiobutton,
    Label,
    Entry,
    NORMAL,
    DISABLED,
)
import inject

from pysaic.config import FactionSetting
from pysaic.enums import FactionsEnum
from pysaic.entities import IncomingQueue, IncomingEvent
from pysaic.ui.utils import add_separator
from pysaic.use_cases.nick import sanitize_nick

logger = logging.getLogger(__name__)


class GeneralTab(Frame):
    def __init__(self, master, options):
        super().__init__(
            master, background=options.background_color, padx=5, pady=5
        )
        self.options = options
        self.config = options.config
        self.grid_columnconfigure(0, weight=1)

        self.faction_var = StringVar(
            self.options.main_window, value=self.config.faction_setting
        )
        self.static_faction_var = StringVar(
            self.options.main_window,
            value=self.config.current_faction.name.replace("_", " "),
        )

        @self.options.add_save_callback
        def save_faction_settings():
            logger.debug("Faction setting: %r", self.faction_var.get())
            self.config.faction_setting = FactionSetting(
                self.faction_var.get()
            )
            if self.config.faction_setting == FactionSetting.Static:
                logger.debug(
                    "Current faction: %r", self.static_faction_var.get()
                )
                self.config.current_faction = FactionsEnum[
                    self.static_faction_var.get().replace(" ", "_")
                ]

        self._setup_ui()

    def _setup_ui(self):
        row_index = 0
        add_separator(
            self,
            self.options.background_color,
            self.options.text_color,
            row_index,
            "Faction Settings",
            font=self.options.font_normal_size,
        )
        row_index += 1
        self._create_faction_settings(row_index)
        row_index += 1
        add_separator(
            self,
            self.options.background_color,
            self.options.text_color,
            row_index,
            "Account Details",
            font=self.options.font_normal_size,
        )
        row_index += 1
        self._create_account_details(row_index)

    def _create_faction_settings(self, row):
        frame = Frame(self, background=self.options.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))

        frame.grid_columnconfigure(0, weight=1)

        sync_radio = Radiobutton(
            frame,
            text="Sync game faction",
            value=FactionSetting.GameSynced.value,
            variable=self.faction_var,
            command=self._update_faction_ui,
            **self.options.default_style_kwargs,
        )
        sync_radio.grid(row=0, column=0, sticky="w")

        static_frame = Frame(frame, background=self.options.background_color)
        static_frame.grid(row=1, column=0, sticky="w")

        static_radio = Radiobutton(
            static_frame,
            text="Static faction",
            value="Static",
            variable=self.faction_var,
            command=self._update_faction_ui,
            **self.options.default_style_kwargs,
        )
        static_radio.grid(row=0, column=0, sticky="w", padx=(0, 20))

        options = sorted(
            [faction.name.replace("_", " ") for faction in FactionsEnum]
        )
        self.faction_options_menu = self.options._create_option_menu(
            static_frame, self.static_faction_var, options, 15
        )
        self.faction_options_menu.grid(
            row=0, column=1, sticky="e", padx=(5, 0)
        )

        self._update_faction_ui()

    def _update_faction_ui(self):
        selection = self.faction_var.get()
        logger.debug("Setting faction to %r", selection)
        if selection == FactionSetting.GameSynced.value:
            self.faction_options_menu.config(state=DISABLED)
        else:
            self.faction_options_menu.config(state=NORMAL)

    def _create_account_details(self, row):
        frame = Frame(self, background=self.options.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        Label(
            frame,
            text="Name:",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=0, column=0, sticky="w")
        self.name_entry = Entry(
            frame,
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
            insertbackground=self.config.colors.content.text,
        )
        self.name_entry.insert(0, self.config.nick)
        self.name_entry.grid(row=0, column=1, sticky="we", padx=5)

        Label(
            frame,
            text="Password:",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.password_entry = Entry(
            frame,
            background=self.options.background_color,
            foreground=self.options.text_color,
            show="*",
            font=self.options.font_normal_size,
            insertbackground=self.config.colors.content.text,
        )
        self.password_entry.insert(0, self.config.password)
        self.password_entry.grid(row=0, column=3, sticky="we", padx=5)

        @self.options.add_save_callback
        def save_account_details():
            logger.debug("Name: %r", self.name_entry.get())
            new_nick = sanitize_nick(self.name_entry.get())
            if new_nick != self.name_entry.get():
                inject.instance(IncomingQueue).put_nowait(
                    IncomingEvent.create_error_event(
                        f'Invalid nickname. Using old one: "{self.name_entry.get()}". '
                        "Available characters are a-zA-Z0-9_{}[]\\|^-"
                    )
                )
            else:
                self.config.nick = new_nick

            logger.debug("Password: %r", self.password_entry.get())
            self.config.password = self.password_entry.get()
