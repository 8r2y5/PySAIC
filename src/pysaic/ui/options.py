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
    DISABLED,
    NORMAL,
)
from tkinter.font import Font
from tkinter.ttk import Spinbox

import inject

from pysaic.config import (
    Config,
    FactionSetting,
    InGameUserDisplayEnum,
    InGameUserDisplayOrderEnum,
)
from pysaic.controllers.ui.user_list import DISPLAY_MODES_MAP
from pysaic.entities import AppEvent, IncomingEvent, IncomingQueue
from pysaic.enums import (
    AppEventEnum,
    DeathReportTypeEnum,
    DisconnectOnNetworkDestructionSetting,
    FactionsEnum,
    UserListDisplayModeEnum,
)
from pysaic.ui.avatar_options import AvatarOptions
from pysaic.ui.colors import ColorsOptions
from pysaic.ui.constants import WM_DELETE_WINDOW
from pysaic.ui.font import FontOptions
from pysaic.ui.theme_options import ThemeOptions
from pysaic.ui.utils import add_separator, apply_style_to_tkinter, update_style
from pysaic.use_cases.nick import sanitize_nick

logger = logging.getLogger(__name__)

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class Options:
    def __init__(self, config: Config, main_window):
        self.config = config
        self.main_window = main_window
        self._avatar_options: None | AvatarOptions = None
        self._colors_options: None | ColorsOptions = None
        self._font_options: None | FontOptions = None
        self._theme_options: None | ThemeOptions = None
        self.this_window = Toplevel(self.main_window)
        self.this_window.protocol(WM_DELETE_WINDOW, self._destroy_this_window)
        self.this_window.title("Options")
        self.this_window.configure(bg=self.main_window.cget("bg"))
        height = 580
        width = 450
        self.this_window.minsize(width, height)
        self.this_window.iconbitmap(PATH / "pysaic_icon.ico")
        self.main_window.options_button.config(state=DISABLED)

        self.background_color = self.main_window.cget("bg")
        self.text_color = self.config.colors.content.text
        self.font_normal_size = Font(
            family=self.config.font.name, size=self.config.font.size - 1
        )
        self.default_style_kwargs = {
            "background": self.background_color,
            "foreground": self.text_color,
            "activebackground": self.background_color,
            "activeforeground": self.text_color,
            "selectcolor": self.background_color,
            "font": self.font_normal_size,
        }

    def main(self):
        self.this_window.grid_columnconfigure(0, weight=1)
        self.this_window.grid_rowconfigure(0, weight=1)

        self._configure_style()

        main_frame = Frame(self.this_window, background=self.background_color)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        main_frame.grid_columnconfigure(0, weight=1)

        row_index = 0
        add_separator(
            main_frame,
            self.background_color,
            self.text_color,
            row_index,
            "Faction Settings",
            font=self.font_normal_size,
        )
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_faction_settings(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        add_separator(
            main_frame,
            self.background_color,
            self.text_color,
            row_index,
            "Account Details",
            font=self.font_normal_size,
        )
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_account_details(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        add_separator(
            main_frame,
            self.background_color,
            self.text_color,
            row_index,
            "Client Configuration",
            pad_y_top=5,
            font=self.font_normal_size,
        )
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_client_config(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        add_separator(
            main_frame,
            self.background_color,
            self.text_color,
            row_index,
            "Display Options",
            pad_y_top=5,
            font=self.font_normal_size,
        )
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_display_options(main_frame, row_index)
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        add_separator(
            main_frame, self.background_color, self.text_color, row_index
        )
        main_frame.grid_rowconfigure(row_index, weight=1)
        row_index += 1
        self._create_buttons(main_frame, row_index)
        apply_style_to_tkinter(self.this_window, self.config)

    def _configure_style(self):
        update_style(self.this_window, self.config)

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
            font=self.font_normal_size,
        )
        self.faction_options_menu["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        self.faction_options_menu.grid(
            row=0, column=1, sticky="e", padx=(5, 0)
        )

        self._update_faction_ui()

    def _update_faction_ui(self):
        selection = self.faction_var.get()
        logger.debug("Setting faction to %r", selection)
        if selection == FactionSetting.GameSynced.value:
            self.faction_options_menu["state"] = DISABLED
        else:
            self.faction_options_menu["state"] = NORMAL

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
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w")
        self.name_entry = Entry(
            frame,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
            insertbackground=self.config.colors.content.text,
        )
        self.name_entry.insert(0, self.config.nick)
        self.name_entry.grid(row=0, column=1, sticky="we", padx=5)

        Label(
            frame,
            text="Password:",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=2, sticky="w", padx=(10, 0))
        self.password_entry = Entry(
            frame,
            background=self.background_color,
            foreground=self.text_color,
            show="*",
            font=self.font_normal_size,
            insertbackground=self.config.colors.content.text,
        )
        self.password_entry.insert(0, self.config.password)
        self.password_entry.grid(row=0, column=3, sticky="we", padx=5)

    def _create_client_config(self, master, row):
        frame = Frame(master, background=self.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(0, weight=1)

        disconnect_tuple = (
            DisconnectOnNetworkDestructionSetting.Never,
            DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
            DisconnectOnNetworkDestructionSetting.Always,
            DisconnectOnNetworkDestructionSetting.Random,
        )
        disconnect_config_values = [
            record.value for record in disconnect_tuple
        ]
        Label(
            frame,
            text="Disconnect when emission",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w", pady=3)
        self._disconnect_when_emission_var = StringVar(
            value=self.config.disconnect_when_emission
        )
        disconnect_when_network = OptionMenu(
            frame,
            self._disconnect_when_emission_var,
            *disconnect_config_values,
        )
        disconnect_when_network.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=22,
            font=self.font_normal_size,
        )
        disconnect_when_network.grid(row=0, column=1, sticky="e", pady=2)
        disconnect_when_network["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )

        Label(
            frame,
            text="Disconnect when underground",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=1, column=0, sticky="w", pady=2)
        self._disconnect_when_underground_var = StringVar(
            value=self.config.disconnect_when_underground
        )
        disconnect_when_underground = OptionMenu(
            frame,
            self._disconnect_when_underground_var,
            *[record.value for record in disconnect_tuple],
        )
        disconnect_when_underground.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=22,
            font=self.font_normal_size,
        )
        disconnect_when_underground.grid(row=1, column=1, sticky="e", pady=2)
        disconnect_when_underground["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )

        self.block_money_transfer_var = BooleanVar(
            value=self.config.block_money_transfer
        )
        Checkbutton(
            frame,
            text="Block money transfer",
            variable=self.block_money_transfer_var,
            **self.default_style_kwargs,
        ).grid(row=2, column=0, sticky="w")

        self.sound_notification_var = BooleanVar(value=self.config.news_sound)
        Checkbutton(
            frame,
            text="Sound notification",
            variable=self.sound_notification_var,
            **self.default_style_kwargs,
        ).grid(row=3, column=0, sticky="w")

        news_duration_frame = Frame(frame, background=self.background_color)
        news_duration_frame.grid(row=4, column=0, sticky="w")

        Label(
            news_duration_frame,
            text="Notification duration (in milliseconds):",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w")
        self.news_duration_spinbox = Spinbox(
            news_duration_frame,
            from_=1000,
            to=20000,
            increment=25,
            width=10,
            font=self.font_normal_size,
        )
        self.news_duration_spinbox.delete(0, "end")
        self.news_duration_spinbox.insert(0, str(self.config.news_duration))
        self.news_duration_spinbox.grid(row=0, column=1, sticky="w")

        Label(
            frame,
            text="Theme Colors",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=5, column=0, sticky="w", pady=(5, 0))

        theme_frame = Frame(frame, background=self.background_color)
        theme_frame.grid(row=5, column=1, sticky="e", pady=(5, 0))

        self._theme_button = Button(
            theme_frame,
            text="Themes",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
            command=self._spawn_theme_options,
        )
        self._theme_button.grid(row=0, column=0, padx=(0, 5))

        self._colors_button = Button(
            theme_frame,
            text="Colors Config",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
            command=self._spawn_colors_options,
        )
        self._colors_button.grid(row=0, column=1)

        Label(
            frame,
            text="Text Styling",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=6, column=0, sticky="w", pady=(5, 0))
        self._font_button = Button(
            frame,
            text="Font Config",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
            command=self._spawn_font_options,
        )

        self._font_button.grid(row=6, column=1, sticky="e", pady=(5, 0))

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
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w", pady=2)
        self.user_list_display_var = StringVar(
            frame, value=self.config.user_list_display
        )
        user_list_display_option = OptionMenu(
            frame,
            self.user_list_display_var,
            *(x.value for x in DISPLAY_MODES_MAP.keys()),
        )
        user_list_display_option.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=32,
            font=self.font_normal_size,
        )
        user_list_display_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        user_list_display_option.grid(
            row=0, column=1, sticky="e", pady=2, padx=(5, 0), columnspan=2
        )

        # In-game list display
        Label(
            frame,
            text="In-game list display type",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=1, column=0, sticky="w", pady=2)
        self._faction_colored_nicks = BooleanVar(
            value=self.config.faction_colored_nicks
        )
        Checkbutton(
            frame,
            text="Faction colored nicks",
            variable=self._faction_colored_nicks,
            **self.default_style_kwargs,
        ).grid(row=1, column=1, sticky="w", pady=2)
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
            font=self.font_normal_size,
        )
        in_game_display_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        in_game_display_option.grid(
            row=1, column=2, sticky="e", pady=2, padx=(5, 0)
        )

        # In-game users display order
        Label(
            frame,
            text="In-game list display order",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=2, column=0, sticky="w", pady=2)
        self.in_game_display_order_var = StringVar(
            frame, value=self.config.in_game_users_display_order
        )
        in_game_display_order_option = OptionMenu(
            frame,
            self.in_game_display_order_var,
            *[
                InGameUserDisplayOrderEnum.Nick.value,
                InGameUserDisplayOrderEnum.Faction.value,
                InGameUserDisplayOrderEnum.Faction_Counter.value,
                InGameUserDisplayOrderEnum.OnlineStatus.value,
            ],
        )
        in_game_display_order_option.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=15,
            font=self.font_normal_size,
        )
        in_game_display_order_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        in_game_display_order_option.grid(
            row=2, column=2, sticky="e", pady=2, padx=(5, 0)
        )

        # Death report
        Label(
            frame,
            text="Death report",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=3, column=0, sticky="w", pady=2)

        self.report_death_var = BooleanVar(value=self.config.death_reports)
        Checkbutton(
            frame,
            text="Report death?",
            variable=self.report_death_var,
            command=self._toggle_death_report_type,
            **self.default_style_kwargs,
        ).grid(row=3, column=1, sticky="w", pady=2)

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
            font=self.font_normal_size,
        )
        self.death_report_type_option["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        self.death_report_type_option.grid(row=3, column=2, sticky="e", pady=2)

        self._toggle_death_report_type()

        # Notification options
        Label(
            frame,
            text="Popup settings",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=4, column=0, sticky="w", pady=2)
        self.notification_on_ping_var = BooleanVar(
            value=self.config.pop_up_on_ping
        )
        logger.debug("Pop up on ping: %r", self.config.pop_up_on_ping)
        Checkbutton(
            frame,
            text="Show popup on ping",
            variable=self.notification_on_ping_var,
            **self.default_style_kwargs,
        ).grid(row=4, column=1, sticky="w", pady=2)
        self.notification_popop_sound_var = BooleanVar(
            value=self.config.pop_up_sound
        )
        logger.debug("Play sound on ping: %r", self.config.pop_up_sound)
        Checkbutton(
            frame,
            text="Play sound on ping",
            variable=self.notification_popop_sound_var,
            **self.default_style_kwargs,
        ).grid(row=4, column=2, sticky="e", pady=2)

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
            command=lambda: os.system("start https://discord.gg/wqETk83bvh"),
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w")

        self._avatar_button = Button(
            frame,
            text="Avatar Creator",
            command=self._spawn_avatar_options,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        )
        self._avatar_button.grid(row=0, column=1, sticky="n", padx=5)

        Button(
            frame,
            text="Save",
            command=self.save_options,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=2, sticky="e", padx=5)

        Button(
            frame,
            text="Cancel",
            command=self._destroy_this_window,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
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
            "disconnect_when_emission: %r",
            self._disconnect_when_emission_var.get(),
        )
        self.config.disconnect_when_emission = (
            DisconnectOnNetworkDestructionSetting(
                self._disconnect_when_emission_var.get()
            )
        )
        logger.debug(
            "disconnect_when_underground: %r",
            self._disconnect_when_underground_var.get(),
        )
        self.config.disconnect_when_underground = (
            DisconnectOnNetworkDestructionSetting(
                self._disconnect_when_underground_var.get()
            )
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
        self.config.user_list_display = UserListDisplayModeEnum(
            self.user_list_display_var.get()
        )

        logger.debug(
            "in_game_users_display: %r", self.in_game_display_var.get()
        )
        self.config.in_game_users_display = InGameUserDisplayEnum(
            self.in_game_display_var.get()
        )
        logger.debug(
            "faction_colored_nicks: %r", self._faction_colored_nicks.get()
        )
        self.config.faction_colored_nicks = self._faction_colored_nicks.get()

        logger.debug(
            "in_game_users_display_order: %r",
            self.in_game_display_order_var.get(),
        )
        self.config.in_game_users_display_order = InGameUserDisplayOrderEnum(
            self.in_game_display_order_var.get()
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
        for sub in (
            self._avatar_options,
            self._colors_options,
            self._font_options,
            self._theme_options,
        ):
            if sub:
                sub._destroy_this_window()
        self.this_window.destroy()
        self.main_window.options_button.config(state=NORMAL)
        self.main_window.focus()

    def _spawn_avatar_options(self):
        self._avatar_button.config(state=DISABLED)
        self._avatar_options = AvatarOptions(self.config, self)
        self._avatar_options.main()

    def _spawn_colors_options(self):
        self._colors_button.config(state=DISABLED)
        self._colors_options = ColorsOptions(self, self.config)

    def _spawn_font_options(self):
        self._font_button.config(state=DISABLED)
        self._font_options = FontOptions(self, self.config)

    def _spawn_theme_options(self):
        self._theme_button.config(state=DISABLED)
        self._theme_options = ThemeOptions(self, self.config)

    def update_colors(self):
        for sub in (
            self._avatar_options,
            # self._colors_options,
            self._font_options,
            self._theme_options,
        ):
            if sub:
                apply_style_to_tkinter(sub.this_window, self.config)

    def clear(self, name):
        match name:
            case "colors":
                self._colors_options = None
                self._colors_button.config(state=NORMAL)
            case "font":
                self._font_options = None
                self._font_button.config(state=NORMAL)
            case "avatar":
                self._avatar_options = None
                self._avatar_button.config(state=NORMAL)
            case "theme":
                self._theme_options = None
                self._theme_button.config(state=NORMAL)
            case _:
                logger.error("%r unexpected name to clear", name)
