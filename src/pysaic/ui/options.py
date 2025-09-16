import logging
import os
from pathlib import Path
from tkinter import (
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    OptionMenu,
    Radiobutton,
    StringVar,
    Toplevel,
)
from tkinter.ttk import Separator, Style, Spinbox

import inject

from pysaic.config import Config, FactionSetting, InGameUserDisplayEnum
from pysaic.controllers.ui.user_list import DISPLAY_MODES_MAP
from pysaic.entities import AppEvent, IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum, DeathReportTypeEnum, FactionsEnum
from pysaic.ui.avatar_options import AvatarOptions
from pysaic.use_cases.nick import sanitize_nick

logger = logging.getLogger(__name__)

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


def create_separator(frame):
    return Separator(frame, orient="horizontal", style="white.TSeparator")


class Options:
    def __init__(self, config: Config, main_window):
        self.config = config
        self.main_window = main_window
        self.options_window = Toplevel(self.main_window)
        self.options_window.title("Options")
        self.options_window.configure(bg=self.main_window.cget("bg"))
        height = 500
        width = 430
        self.options_window.geometry(f"{width}x{height}+100+100")
        self.options_window.minsize(width, height)
        self.options_window.iconbitmap(PATH / "crcr_icon_new.ico")
        self.main_window.options_button.config(state="disabled")

        self.background_color = self.main_window.cget("bg")
        self.text_color = "ghost white"
        self.default_style_kwargs = {
            "background": self.background_color,
            "foreground": self.text_color,
            "activebackground": self.background_color,
            "activeforeground": self.text_color,
            "selectcolor": self.background_color,
        }

    def __del__(self):
        self.main_window.options_button.config(state="normal")

    def main(self):
        self.options_window.grid_columnconfigure(0, weight=1)
        self.options_window.grid_rowconfigure(0, weight=1)

        self._configure_style()

        main_frame = Frame(
            self.options_window, background=self.background_color
        )
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        main_frame.grid_columnconfigure(0, weight=1)

        row_index = 0
        self._add_separator(main_frame, row_index, "Faction Settings")
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_faction_settings(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._add_separator(main_frame, row_index, "Account Details")
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_account_details(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._add_separator(main_frame, row_index, "Client Configuration")
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_client_config(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._add_separator(main_frame, row_index, "Display Options")
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_display_options(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._add_separator(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_buttons(main_frame, row_index)

    def _configure_style(self):
        style = Style()
        style.configure("white.TSeparator", background="white")
        style.configure(
            "TSpinbox",
            fieldbackground=self.background_color,
            background=self.background_color,
            foreground=self.text_color,
            arrowcolor=self.text_color,
        )

    def _add_separator(self, master, row, section_name=""):
        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="ew", pady=(0, 5))
        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=1)

        if section_name:
            create_separator(frame).grid(row=0, column=0, sticky="ew")

            Label(
                frame,
                text=section_name,
                background=self.background_color,
                foreground=self.text_color,
            ).grid(row=0, column=1, padx=10, sticky="n")

            create_separator(frame).grid(row=0, column=2, sticky="ew")
        else:
            create_separator(frame).grid(
                row=0, column=0, sticky="ew", columnspan=3
            )

    def _create_faction_settings(self, master, row):
        self.faction_var = StringVar(
            self.main_window, value=self.config.faction_setting
        )
        self.static_faction_var = StringVar(
            self.main_window,
            value=self.config.current_faction.name.replace("_", " "),
        )

        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="w", pady=(0, 5))

        frame.grid_columnconfigure(0, weight=1)

        sync_radio = Radiobutton(
            frame,
            text="Sync game faction",
            value=FactionSetting.GameSynced.value,
            variable=self.faction_var,
            command=self._update_faction_ui,
            **self.default_style_kwargs,
        )
        sync_radio.grid(row=0, column=0, sticky="w")

        static_frame = Frame(frame, background=self.background_color)
        static_frame.grid(row=1, column=0, sticky="w")

        static_radio = Radiobutton(
            static_frame,
            text="Static faction",
            value="Static",
            variable=self.faction_var,
            command=self._update_faction_ui,
            **self.default_style_kwargs,
        )
        static_radio.grid(row=0, column=0, sticky="w", padx=(0, 20))

        options = sorted(
            [faction.name.replace("_", " ") for faction in FactionsEnum]
        )
        self.faction_options_menu = OptionMenu(
            static_frame,
            self.static_faction_var,
            *options,
        )
        self.faction_options_menu.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=15,
        )
        self.faction_options_menu["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        self.faction_options_menu.grid(
            row=0, column=1, sticky="e", padx=(5, 0)
        )

        self._update_faction_ui()

    def _update_faction_ui(self):
        selection = self.faction_var.get()
        logger.debug("Setting faction to %r", selection)
        if selection == FactionSetting.GameSynced.value:
            self.faction_options_menu["state"] = "disabled"
        else:
            self.faction_options_menu["state"] = "normal"

    def _create_account_details(self, master, row):
        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(1, weight=1)
        frame.grid_columnconfigure(3, weight=1)

        Label(
            frame,
            text="Name:",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=0, sticky="w")
        self.name_entry = Entry(
            frame,
            background=self.background_color,
            foreground=self.text_color,
        )
        self.name_entry.insert(0, self.config.nick)
        self.name_entry.grid(row=0, column=1, sticky="we", padx=5)

        Label(
            frame,
            text="Password:",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.password_entry = Entry(
            frame,
            background=self.background_color,
            foreground=self.text_color,
            show="*",
        )
        self.password_entry.insert(0, self.config.password)
        self.password_entry.grid(row=0, column=3, sticky="we", padx=5)

    def _create_client_config(self, master, row):
        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(0, weight=1)

        self.disconnect_during_emission_or_when_underground_var = BooleanVar(
            value=self.config.disconnect_when_blowout_or_underground
        )
        Checkbutton(
            frame,
            text="Disconnect during emission or when underground",
            variable=self.disconnect_during_emission_or_when_underground_var,
            **self.default_style_kwargs,
        ).grid(row=0, column=0, sticky="w")

        self.block_money_transfer_var = BooleanVar(
            value=self.config.block_money_transfer
        )
        Checkbutton(
            frame,
            text="Block money transfer",
            variable=self.block_money_transfer_var,
            **self.default_style_kwargs,
        ).grid(row=1, column=0, sticky="w")

        self.sound_notification_var = BooleanVar(value=self.config.news_sound)
        Checkbutton(
            frame,
            text="Sound notification",
            variable=self.sound_notification_var,
            **self.default_style_kwargs,
        ).grid(row=2, column=0, sticky="w")

        news_duration_frame = Frame(frame, background=self.background_color)
        news_duration_frame.grid(row=3, column=0, sticky="w")

        Label(
            news_duration_frame,
            text="Notification duration (in milliseconds):",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=0, sticky="w")
        self.news_duration_spinbox = Spinbox(
            news_duration_frame,
            from_=1000,
            to=20000,
            increment=25,
            width=10,
        )
        self.news_duration_spinbox.delete(0, "end")
        self.news_duration_spinbox.insert(0, str(self.config.news_duration))
        self.news_duration_spinbox.grid(row=0, column=1, sticky="w")

    def _create_display_options(self, master, row):
        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(0, weight=0)  # labels do not stretch
        frame.grid_columnconfigure(
            1, weight=1
        )  # checkboxes and option menus can stretch
        frame.grid_columnconfigure(
            2, weight=1
        )  # last column should also be stretchable

        # Chat App list display
        Label(
            frame,
            text="Chat App list display",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=0, sticky="w", pady=2)
        self.user_list_display_var = StringVar(
            frame, value=self.config.user_list_display
        )
        user_list_display_option = OptionMenu(
            frame,
            self.user_list_display_var,
            *DISPLAY_MODES_MAP.keys(),
        )
        user_list_display_option.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=32,
        )
        user_list_display_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        user_list_display_option.grid(
            row=0, column=1, sticky="e", pady=2, padx=(5, 0), columnspan=2
        )

        # In-game list display
        Label(
            frame,
            text="In-game list display",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=1, column=0, sticky="w", pady=2)
        self.in_game_display_var = StringVar(
            frame, value=self.config.in_game_users_display
        )
        in_game_options = [enum.value for enum in InGameUserDisplayEnum]
        in_game_display_option = OptionMenu(
            frame,
            self.in_game_display_var,
            *in_game_options,
        )
        in_game_display_option.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=15,
        )
        in_game_display_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        in_game_display_option.grid(
            row=1, column=2, sticky="e", pady=2, padx=(5, 0)
        )

        # Death report
        Label(
            frame,
            text="Death report",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=2, column=0, sticky="w", pady=2)

        self.report_death_var = BooleanVar(value=self.config.death_reports)
        Checkbutton(
            frame,
            text="Report death?",
            variable=self.report_death_var,
            command=self._toggle_death_report_type,
            **self.default_style_kwargs,
        ).grid(row=2, column=1, sticky="w", pady=2)

        self.death_report_type_var = StringVar(
            frame, value=self.config.death_report_type
        )
        death_report_options = [enum.value for enum in DeathReportTypeEnum]
        self.death_report_type_option = OptionMenu(
            frame,
            self.death_report_type_var,
            *death_report_options,
        )
        self.death_report_type_option.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=15,
        )
        self.death_report_type_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        self.death_report_type_option.grid(row=2, column=2, sticky="e", pady=2)

        self._toggle_death_report_type()

        # Notification options
        Label(
            frame,
            text="Popup settings",
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=3, column=0, sticky="w", pady=2)
        self.notification_on_ping_var = BooleanVar(
            value=self.config.pop_up_on_ping
        )
        logger.debug("Pop up on ping: %r", self.config.pop_up_on_ping)
        Checkbutton(
            frame,
            text="Show popup on ping",
            variable=self.notification_on_ping_var,
            **self.default_style_kwargs,
        ).grid(row=3, column=1, sticky="w", pady=2)
        self.notification_popop_sound_var = BooleanVar(
            value=self.config.pop_up_sound
        )
        logger.debug("Play sound on ping: %r", self.config.pop_up_sound)
        Checkbutton(
            frame,
            text="Play sound on ping",
            variable=self.notification_popop_sound_var,
            **self.default_style_kwargs,
        ).grid(row=3, column=2, sticky="e", pady=2)

    def _toggle_death_report_type(self):
        self.death_report_type_option["state"] = (
            "normal" if self.report_death_var.get() else "disabled"
        )

    def _create_buttons(self, master, row):
        frame = Frame(
            master,
            background=self.background_color,
        )
        frame.grid(row=row, column=0, columnspan=2, sticky="we", pady=5)

        frame.grid_columnconfigure(0, weight=1)
        frame.grid_columnconfigure(1, weight=0)
        frame.grid_columnconfigure(2, weight=0)
        frame.grid_columnconfigure(3, weight=0)

        Button(
            frame,
            text="Join Discord",
            command=lambda: os.system("start https://discord.gg/KjNHXCkHr9"),
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=0, sticky="w")

        Button(
            frame,
            text="Avatar Creator",
            command=lambda: AvatarOptions(
                self.config, self.main_window
            ).main(),
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=1, sticky="n", padx=5)

        Button(
            frame,
            text="Save",
            command=self.save_options,
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=2, sticky="e", padx=5)

        Button(
            frame,
            text="Cancel",
            command=self._destroy_this_window,
            background=self.background_color,
            foreground=self.text_color,
        ).grid(row=0, column=3, sticky="e", padx=(5, 0))

    @inject.autoparams()
    def save_options(self, incoming_queue: IncomingQueue):
        logger.debug("Saving options")
        self._update_config_from_ui()
        logger.debug("Saving config")
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent(
                author="",
                target="",
                event=AppEvent(what=AppEventEnum.OPTIONS_UPDATED),
            )
        )
        self._destroy_this_window()

    def _update_config_from_ui(self):
        logger.debug("Faction setting: %r", self.faction_var.get())
        self.config.faction_setting = FactionSetting(self.faction_var.get())
        if self.config.faction_setting == FactionSetting.Static:
            logger.debug("Current faction: %r", self.static_faction_var.get())
            self.config.current_faction = FactionsEnum[
                self.static_faction_var.get().replace(" ", "_")
            ]

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

        logger.debug(
            "disconnect_during_emission_or_when_underground: %r",
            self.disconnect_during_emission_or_when_underground_var.get(),
        )
        self.config.disconnect_when_blowout_or_underground = (
            self.disconnect_during_emission_or_when_underground_var.get()
        )

        logger.debug(
            "block_money_transfer: %r", self.block_money_transfer_var.get()
        )
        self.config.block_money_transfer = self.block_money_transfer_var.get()

        logger.debug(
            "sound_notification: %r", self.sound_notification_var.get()
        )
        self.config.news_sound = self.sound_notification_var.get()

        try:
            self.config.news_duration = int(self.news_duration_spinbox.get())
        except ValueError:
            # Handle the case where the input is not a valid integer.
            # You might want to log an error or reset to a default value.
            logger.error("Invalid notification duration format.")
            self.news_duration_spinbox.delete(0, "end")
            self.news_duration_spinbox.insert(
                0, str(self.config.news_duration)
            )

        logger.debug("user_list_display: %r", self.user_list_display_var.get())
        self.config.user_list_display = self.user_list_display_var.get()

        logger.debug(
            "in_game_users_display: %r", self.in_game_display_var.get()
        )
        self.config.in_game_users_display = InGameUserDisplayEnum(
            self.in_game_display_var.get()
        )
        logger.debug(
            "report death? %s, death_report_type: %r",
            self.report_death_var.get(),
            self.death_report_type_var.get(),
        )
        self.config.death_report_type = DeathReportTypeEnum(
            self.death_report_type_var.get()
        )
        self.config.death_reports = self.report_death_var.get()

        logger.debug(
            "notification_on_ping: %r", self.notification_on_ping_var.get()
        )
        self.config.pop_up_on_ping = self.notification_on_ping_var.get()
        logger.debug(
            "notification_popop_sound: %r",
            self.notification_popop_sound_var.get(),
        )
        self.config.pop_up_sound = self.notification_popop_sound_var.get()

    def _destroy_this_window(self):
        logger.debug("Destroying options window")
        self.options_window.destroy()
        self.main_window.focus()
