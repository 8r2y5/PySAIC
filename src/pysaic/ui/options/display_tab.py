import logging
from tkinter import (
    Frame,
    StringVar,
    BooleanVar,
    Label,
    Checkbutton,
    NORMAL,
    DISABLED,
)

from pysaic.config import InGameUserDisplayEnum, InGameUserDisplayOrderEnum
from pysaic.controllers.ui.user_list import DISPLAY_MODES_MAP
from pysaic.enums import UserListDisplayModeEnum, DeathReportTypeEnum
from pysaic.ui.options.utils import RowCounter
from pysaic.ui.utils import add_separator

logger = logging.getLogger(__name__)


class DisplayTab(Frame):
    def __init__(self, master, options):
        super().__init__(
            master, background=options.background_color, padx=5, pady=5
        )
        self.options = options
        self.config = options.config
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()
        self.options.add_save_callback(self.update_config)

    def _setup_ui(self):
        row_index = 0
        add_separator(
            self,
            self.options.background_color,
            self.options.text_color,
            row_index,
            "Display Options",
            pad_y_top=5,
            font=self.options.font_normal_size,
        )
        row_index += 1
        self._create_display_options(row_index)

    def _create_display_options(self, row):
        frame = Frame(self, background=self.options.background_color)
        frame.grid(row=row, column=0, columnspan=2, sticky="we")

        frame.grid_columnconfigure(0, weight=0)  # labels do not stretch
        frame.grid_columnconfigure(
            1, weight=1
        )  # checkboxes and option menus can stretch
        frame.grid_columnconfigure(
            2, weight=1
        )  # last column should also be stretchable

        row_counter = RowCounter()
        # Chat App list display
        with row_counter as row:
            Label(
                frame,
                text="Chat App list display",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)
            self.user_list_display_var = StringVar(
                frame, value=self.config.user_list_display
            )
            user_list_display_option = self.options._create_option_menu(
                frame,
                self.user_list_display_var,
                [x.value for x in DISPLAY_MODES_MAP.keys()],
                32,
            )
            user_list_display_option.grid(
                row=row,
                column=1,
                sticky="e",
                pady=2,
                padx=(5, 0),
                columnspan=2,
            )

        with row_counter as row:
            self.enable_irc_user_display_var = BooleanVar(
                frame, value=self.config.enable_irc_user_display
            )
            Checkbutton(
                frame,
                text="Enable IRC user information",
                variable=self.enable_irc_user_display_var,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=0, sticky="w", pady=2)

            self.show_less_information_var = BooleanVar(
                frame, value=self.config.show_less_information
            )
            Checkbutton(
                frame,
                text="Show less information messages",
                variable=self.show_less_information_var,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=1, sticky="w", pady=2)

        # In-game list display
        with row_counter as row:
            Label(
                frame,
                text="In-game list display type",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)
            self._faction_colored_nicks = BooleanVar(
                value=self.config.faction_colored_nicks
            )
            Checkbutton(
                frame,
                text="Faction colored nicks",
                variable=self._faction_colored_nicks,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=1, sticky="w", pady=2)
            self.in_game_display_var = StringVar(
                frame, value=self.config.in_game_users_display
            )
            in_game_options = [enum.value for enum in InGameUserDisplayEnum]
            in_game_display_option = self.options._create_option_menu(
                frame, self.in_game_display_var, in_game_options, 15
            )
            in_game_display_option.grid(
                row=row, column=2, sticky="e", pady=2, padx=(5, 0)
            )

        # In-game users display order
        with row_counter as row:
            Label(
                frame,
                text="In-game list display order",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)
            self.in_game_display_order_var = StringVar(
                frame, value=self.config.in_game_users_display_order
            )
            in_game_display_order_option = self.options._create_option_menu(
                frame,
                self.in_game_display_order_var,
                [
                    InGameUserDisplayOrderEnum.Nick.value,
                    InGameUserDisplayOrderEnum.Faction.value,
                    InGameUserDisplayOrderEnum.Faction_Counter.value,
                    InGameUserDisplayOrderEnum.OnlineStatus.value,
                ],
                15,
            )
            in_game_display_order_option.grid(
                row=row, column=2, sticky="e", pady=2, padx=(5, 0)
            )

        # Death report
        with row_counter as row:
            Label(
                frame,
                text="Death report",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)

            self.report_death_var = BooleanVar(value=self.config.death_reports)
            Checkbutton(
                frame,
                text="Report death?",
                variable=self.report_death_var,
                command=self._toggle_death_report_type,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=1, sticky="w", pady=2)

            self.death_report_type_var = StringVar(
                frame, value=self.config.death_report_type
            )
            death_report_options = [enum.value for enum in DeathReportTypeEnum]
            self.death_report_type_option = self.options._create_option_menu(
                frame, self.death_report_type_var, death_report_options, 15
            )
            self.death_report_type_option.grid(
                row=row, column=2, sticky="e", pady=2
            )

        self._toggle_death_report_type()

        # Notification options
        with row_counter as row:
            Label(
                frame,
                text="Popup settings",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)
            self.notification_on_ping_var = BooleanVar(
                value=self.config.pop_up_on_ping
            )
            logger.debug("Pop up on ping: %r", self.config.pop_up_on_ping)
            Checkbutton(
                frame,
                text="Show popup on ping",
                variable=self.notification_on_ping_var,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=1, sticky="w", pady=2)
            self.notification_popop_sound_var = BooleanVar(
                value=self.config.pop_up_sound
            )
            logger.debug("Play sound on ping: %r", self.config.pop_up_sound)
            Checkbutton(
                frame,
                text="Play sound on ping",
                variable=self.notification_popop_sound_var,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=2, sticky="e", pady=2)

        with row_counter as row:
            Label(
                frame,
                text="PySAIC in PDA",
                background=self.options.background_color,
                foreground=self.options.text_color,
                font=self.options.font_normal_size,
            ).grid(row=row, column=0, sticky="w", pady=2)
            self.in_game_pda_instead_of_window_var = BooleanVar(
                value=self.config.in_game_pda_instead_of_window
            )
            logger.debug(
                "Pop up on ping: %r", self.config.in_game_pda_instead_of_window
            )
            Checkbutton(
                frame,
                text="Yes",
                variable=self.in_game_pda_instead_of_window_var,
                **self.options.default_style_kwargs,
            ).grid(row=row, column=1, sticky="w", pady=2)

    def _toggle_death_report_type(self):
        self.death_report_type_option.config(
            state=(NORMAL if self.report_death_var.get() else DISABLED)
        )

    def update_config(self):
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
            "enable_irc_user_display: %r",
            self.enable_irc_user_display_var.get(),
        )
        self.config.enable_irc_user_display = (
            self.enable_irc_user_display_var.get()
        )
        logger.debug(
            "show_less_information: %r", self.show_less_information_var.get()
        )
        self.config.show_less_information = (
            self.show_less_information_var.get()
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

        logger.debug(
            "in_game_pda_instead_of_window_var: %r",
            self.in_game_pda_instead_of_window_var.get(),
        )
        self.config.in_game_pda_instead_of_window = (
            self.in_game_pda_instead_of_window_var.get()
        )
