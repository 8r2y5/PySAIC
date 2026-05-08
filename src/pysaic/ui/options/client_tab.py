import logging
from tkinter import (
    Frame,
    StringVar,
    BooleanVar,
    Label,
    Button,
    Checkbutton,
)
from tkinter.ttk import Spinbox

from pysaic.config import Config
from pysaic.enums import DisconnectOnNetworkDestructionSetting
from pysaic.ui.utils import add_separator

logger = logging.getLogger(__name__)


class ClientTab(Frame):
    def __init__(self, master, options):
        super().__init__(
            master, background=options.background_color, padx=5, pady=5
        )
        self.options = options
        self.config: Config = options.config
        self.grid_columnconfigure(0, weight=1)

        self._setup_ui()

    def _setup_ui(self):
        row_index = 0
        add_separator(
            self,
            self.options.background_color,
            self.options.text_color,
            row_index,
            "Client Configuration",
            pad_y_top=5,
            font=self.options.font_normal_size,
        )
        row_index += 1
        self._create_client_config(row_index)

    def _create_client_config(self, row):
        frame = Frame(self, background=self.options.background_color)
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
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=0, column=0, sticky="w", pady=3)
        self._disconnect_when_emission_var = StringVar(
            value=self.config.disconnect_when_emission
        )

        Label(
            frame,
            text="Disconnect when underground",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=1, column=0, sticky="w", pady=2)
        self._disconnect_when_underground_var = StringVar(
            value=self.config.disconnect_when_underground
        )

        @self.options.add_save_callback
        def save_emission_settings():
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

        disconnect_when_network = self.options._create_option_menu(
            frame,
            self._disconnect_when_emission_var,
            disconnect_config_values,
            22,
        )
        disconnect_when_network.grid(row=0, column=1, sticky="e", pady=2)

        disconnect_when_underground = self.options._create_option_menu(
            frame,
            self._disconnect_when_underground_var,
            [record.value for record in disconnect_tuple],
            22,
        )
        disconnect_when_underground.grid(row=1, column=1, sticky="e", pady=2)

        self.block_money_transfer_var = BooleanVar(
            value=self.config.block_money_transfer
        )

        @self.options.add_save_callback
        def save_money_transfer():
            logger.debug(
                "block_money_transfer: %r", self.block_money_transfer_var.get()
            )
            self.config.block_money_transfer = (
                self.block_money_transfer_var.get()
            )

        Checkbutton(
            frame,
            text="Block money transfer",
            variable=self.block_money_transfer_var,
            **self.options.default_style_kwargs,
        ).grid(row=2, column=0, sticky="w")

        self.sound_notification_var = BooleanVar(value=self.config.news_sound)

        Checkbutton(
            frame,
            text="Sound notification",
            variable=self.sound_notification_var,
            **self.options.default_style_kwargs,
        ).grid(row=3, column=0, sticky="w")

        news_duration_frame = Frame(
            frame, background=self.options.background_color
        )
        news_duration_frame.grid(row=4, column=0, sticky="w")

        Label(
            news_duration_frame,
            text="Notification duration (in milliseconds):",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=0, column=0, sticky="w")
        self.news_duration_spinbox = Spinbox(
            news_duration_frame,
            from_=1000,
            to=20000,
            increment=25,
            width=10,
            font=self.options.font_normal_size,
        )
        self.news_duration_spinbox.delete(0, "end")
        self.news_duration_spinbox.insert(0, str(self.config.news_duration))
        self.news_duration_spinbox.grid(row=0, column=1, sticky="w")

        @self.options.add_save_callback
        def save_notification_settings():
            logger.debug(
                "sound_notification: %r", self.sound_notification_var.get()
            )
            self.config.news_sound = self.sound_notification_var.get()

            try:
                self.config.news_duration = int(
                    self.news_duration_spinbox.get()
                )
            except ValueError:
                # Handle the case where the input is not a valid integer.
                # You might want to log an error or reset to a default value.
                logger.error("Invalid notification duration format.")
                self.news_duration_spinbox.delete(0, "end")
                self.news_duration_spinbox.insert(
                    0, str(self.config.news_duration)
                )

        Label(
            frame,
            text="Theme Colors",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=5, column=0, sticky="w", pady=(5, 0))

        theme_frame = Frame(frame, background=self.options.background_color)
        theme_frame.grid(row=5, column=1, sticky="e", pady=(5, 0))

        self.options._theme_button = Button(
            theme_frame,
            text="Themes",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
            command=self.options._spawn_theme_options,
        )
        self.options._theme_button.grid(row=0, column=0, padx=(0, 5))

        self.options._colors_button = Button(
            theme_frame,
            text="Colors Config",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
            command=self.options._spawn_colors_options,
        )
        self.options._colors_button.grid(row=0, column=1)

        Label(
            frame,
            text="Text Styling",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
        ).grid(row=6, column=0, sticky="nw", pady=(7, 0))

        self.turn_off_bold_font_chat_var = BooleanVar(
            value=self.config.font.turn_off_bold_font_username_in_chat
        )

        @self.options.add_save_callback
        def save_bold_font_chat_settings():
            logger.debug(
                "turn_off_bold_font_chat_var: %r",
                self.turn_off_bold_font_chat_var.get(),
            )
            self.config.font.turn_off_bold_font_username_in_chat = (
                self.turn_off_bold_font_chat_var.get()
            )

        font_frame = Frame(frame, background=self.options.background_color)
        Checkbutton(
            font_frame,
            text="Turn off bold font in chat",
            variable=self.turn_off_bold_font_chat_var,
            **self.options.default_style_kwargs,
        ).grid(row=0, column=1, sticky="w", pady=(5, 0))

        self.turn_off_bold_font_user_var = BooleanVar(
            value=self.config.font.turn_off_bold_font_username_in_list
        )

        @self.options.add_save_callback
        def save_bold_font_user_settings():
            logger.debug(
                "turn_off_bold_font_user_var: %r",
                self.turn_off_bold_font_user_var.get(),
            )
            self.config.font.turn_off_bold_font_username_in_list = (
                self.turn_off_bold_font_user_var.get()
            )

        Checkbutton(
            font_frame,
            text="Turn off bold font in user list",
            variable=self.turn_off_bold_font_user_var,
            **self.options.default_style_kwargs,
        ).grid(row=1, column=1, sticky="w", pady=(5, 0))

        self.use_static_nick_color_var = BooleanVar(
            value=self.config.use_static_nick_color
        )

        @self.options.add_save_callback
        def save_use_static_nick_color():
            logger.debug(
                "static nick: %r",
                self.use_static_nick_color_var.get(),
            )
            self.config.use_static_nick_color = (
                self.use_static_nick_color_var.get()
            )

        Checkbutton(
            font_frame,
            text="User static nick color",
            variable=self.use_static_nick_color_var,
            **self.options.default_style_kwargs,
        ).grid(row=2, column=1, sticky="w", pady=(5, 0))

        self.options._font_button = Button(
            font_frame,
            text="Font Config",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
            command=self.options._spawn_font_options,
        )
        self.options._font_button.grid(
            row=0, column=2, sticky="e", pady=(5, 0)
        )
        font_frame.grid(row=6, column=1, sticky="e", pady=(5, 0))
