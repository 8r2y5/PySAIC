import logging
from tkinter import Frame, StringVar, BooleanVar, Label, Button, Checkbutton, NORMAL, DISABLED
from tkinter.ttk import Spinbox

from pysaic.enums import DisconnectOnNetworkDestructionSetting
from pysaic.ui.utils import add_separator

logger = logging.getLogger(__name__)

class ClientTab(Frame):
    def __init__(self, master, options):
        super().__init__(master, background=options.background_color, padx=5, pady=5)
        self.options = options
        self.config = options.config
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
        disconnect_when_network = self.options._create_option_menu(
            frame,
            self._disconnect_when_emission_var,
            disconnect_config_values,
            22,
        )
        disconnect_when_network.grid(row=0, column=1, sticky="e", pady=2)

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

        news_duration_frame = Frame(frame, background=self.options.background_color)
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
        ).grid(row=6, column=0, sticky="w", pady=(5, 0))
        self.options._font_button = Button(
            frame,
            text="Font Config",
            background=self.options.background_color,
            foreground=self.options.text_color,
            font=self.options.font_normal_size,
            command=self.options._spawn_font_options,
        )

        self.options._font_button.grid(row=6, column=1, sticky="e", pady=(5, 0))

    def update_config(self):
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
