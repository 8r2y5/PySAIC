import logging
import os
from pathlib import Path
from tkinter import (
    Button,
    Frame,
    OptionMenu,
    Toplevel,
    DISABLED,
    NORMAL,
)
from tkinter.font import Font
from tkinter.ttk import Notebook

import inject

from pysaic.config import Config
from pysaic.entities import AppEvent, IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum
from pysaic.ui.avatar_options import AvatarOptions
from pysaic.ui.colors import ColorsOptions
from pysaic.ui.constants import WM_DELETE_WINDOW
from pysaic.ui.font import FontOptions
from pysaic.ui.theme_options import ThemeOptions
from pysaic.ui.utils import apply_style_to_tkinter, update_style
from pysaic.ui.options.general_tab import GeneralTab
from pysaic.ui.options.client_tab import ClientTab
from pysaic.ui.options.display_tab import DisplayTab

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
        self.this_window.protocol(WM_DELETE_WINDOW, self.destroy_this_window)
        self.this_window.title("Options")

        self.background_color = self.config.colors.background.app
        self.text_color = self.config.colors.content.text

        self.this_window.configure(bg=self.background_color)
        height = 580
        width = 450
        self.this_window.minsize(width, height)
        self.icon_path = main_window.icon_path
        self.this_window.iconbitmap(self.icon_path)
        self.main_window.options_button.config(state=DISABLED)

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
        for widget in self.this_window.winfo_children():
            if not isinstance(widget, Toplevel):
                widget.destroy()

        self.this_window.grid_columnconfigure(0, weight=1)
        self.this_window.grid_rowconfigure(0, weight=1)

        self._configure_style()

        main_frame = Frame(self.this_window, background=self.background_color)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)

        main_frame.grid_columnconfigure(0, weight=1)
        main_frame.grid_rowconfigure(0, weight=1)  # For notebook

        notebook = Notebook(main_frame)
        notebook.grid(row=0, column=0, sticky="nsew")

        # General Tab
        self.general_tab = GeneralTab(notebook, self)
        notebook.add(self.general_tab, text="General")

        # Client Tab
        self.client_tab = ClientTab(notebook, self)
        notebook.add(self.client_tab, text="Client")

        # Display Tab
        self.display_tab = DisplayTab(notebook, self)
        notebook.add(self.display_tab, text="Display")

        # Buttons
        self._create_buttons(main_frame, 1)

        apply_style_to_tkinter(self.this_window, self.config)

    def _configure_style(self):
        update_style(self.this_window, self.config)

    def _create_option_menu(self, master, var, options, width):
        option_menu = OptionMenu(master, var, *options)
        option_menu.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.background_color,
            activeforeground=self.text_color,
            width=width,
            font=self.font_normal_size,
        )
        option_menu["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )
        return option_menu

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
            command=lambda: os.system("start https://discord.gg/9ef8NKjEjg"),
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
            command=lambda: self.save_options(),
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=2, sticky="e", padx=5)

        Button(
            frame,
            text="Cancel",
            command=self.destroy_this_window,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=3, sticky="e", padx=(5, 0))

    @inject.autoparams()
    def save_options(self, incoming_queue: IncomingQueue):
        logger.debug("Saving options")
        self.general_tab.update_config()
        self.client_tab.update_config()
        self.display_tab.update_config()

        logger.debug("Saving config")
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent(
                author="",
                target="",
                event=AppEvent(what=AppEventEnum.OPTIONS_UPDATED),
            )
        )
        self.destroy_this_window()

    def destroy_this_window(self):
        logger.debug("Destroying options window")
        for sub in (
            self._avatar_options,
            self._colors_options,
            self._font_options,
            self._theme_options,
        ):
            if sub:
                sub.destroy_this_window()
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
        self.background_color = self.config.colors.background.app
        self.text_color = self.config.colors.content.text
        self.this_window.configure(bg=self.background_color)

        self.default_style_kwargs = {
            "background": self.background_color,
            "foreground": self.text_color,
            "activebackground": self.background_color,
            "activeforeground": self.text_color,
            "selectcolor": self.background_color,
            "font": self.font_normal_size,
        }

        self.main()  # Recreate UI

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
