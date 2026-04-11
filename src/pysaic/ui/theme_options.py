import logging
import os
from dataclasses import asdict
from pathlib import Path
from tkinter import (
    Button,
    Entry,
    Frame,
    Label,
    OptionMenu,
    StringVar,
    Toplevel,
    messagebox,
)
from tkinter.font import Font

import inject
import yaml

from pysaic.config import Config, ColorsConfig
from pysaic.entities import IncomingEvent, IncomingQueue
from pysaic.enums import AppEventEnum
from pysaic.settings import THEMES_PATH
from pysaic.ui.constants import WM_DELETE_WINDOW
from pysaic.ui.utils import apply_style_to_tkinter

PATH = Path(os.path.abspath(os.path.dirname(__file__)))
logger = logging.getLogger(__name__)


class ThemeOptions:
    def __init__(self, parent, config: Config):
        self.parent = parent
        self.config = config
        self.this_window = Toplevel(self.parent.this_window)
        self.this_window.protocol(WM_DELETE_WINDOW, self.destroy_this_window)
        self.this_window.title("Theme Management")
        self.this_window.iconbitmap(parent.icon_path)

        self.background_color = self.config.colors.background.app
        self.text_color = self.config.colors.content.text
        self.font_normal_size = Font(
            family=self.config.font.name, size=self.config.font.size - 1
        )

        self.this_window.configure(bg=self.background_color)
        height = 200
        width = 350
        self.this_window.minsize(width, height)

        self.themes = []
        self.selected_theme = StringVar(value=self.config.theme_name)

        self.main()
        apply_style_to_tkinter(self.this_window, self.config)

    def main(self):
        for widget in self.this_window.winfo_children():
            if not isinstance(widget, Toplevel):
                widget.destroy()

        self.this_window.grid_columnconfigure(0, weight=1)

        main_frame = Frame(self.this_window, background=self.background_color)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        main_frame.grid_columnconfigure(1, weight=1)

        # Theme selection
        Label(
            main_frame,
            text="Select Theme:",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=0, sticky="w", pady=5)
        self.theme_menu = OptionMenu(main_frame, self.selected_theme, "")
        self.theme_menu.grid(row=0, column=1, sticky="ew", padx=5, pady=5)

        self._load_themes()
        self.selected_theme.trace_add("write", self._select_theme_from_var)

        self.theme_menu.config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
            width=15,
            font=self.font_normal_size,
        )
        self.theme_menu["menu"].config(
            bg=self.background_color,
            fg=self.text_color,
            activebackground=self.config.colors.background.active_background,
            activeforeground=self.config.colors.background.active_foreground,
        )

        # Create/Rename theme
        Label(
            main_frame,
            text="Theme Name:",
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=1, column=0, sticky="w", pady=5)
        self.theme_name_entry = Entry(
            main_frame,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
            insertbackground=self.text_color,
        )
        self.theme_name_entry.grid(
            row=1, column=1, sticky="ew", padx=5, pady=5
        )
        self.theme_name_entry.insert(0, self.config.theme_name)

        # Buttons
        button_frame = Frame(main_frame, background=self.background_color)
        button_frame.grid(row=2, column=0, columnspan=2, sticky="ew", pady=10)
        button_frame.grid_columnconfigure([0, 1, 2], weight=1)

        Button(
            button_frame,
            text="Save/Create",
            command=self._save_theme,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=0, padx=2)
        Button(
            button_frame,
            text="Delete",
            command=self._delete_theme,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=1, padx=2)
        Button(
            button_frame,
            text="Close",
            command=self.destroy_this_window,
            background=self.background_color,
            foreground=self.text_color,
            font=self.font_normal_size,
        ).grid(row=0, column=2, padx=2)

    def _load_themes(self):
        self.themes = sorted([p.stem for p in THEMES_PATH.glob("*.yml")])
        menu = self.theme_menu["menu"]
        menu.delete(0, "end")
        for theme in self.themes:
            menu.add_command(
                label=theme,
                command=lambda value=theme: self.selected_theme.set(value),
            )

    def _select_theme_from_var(self, *args):
        theme_name = self.selected_theme.get()
        self.theme_name_entry.delete(0, "end")
        self.theme_name_entry.insert(0, theme_name)
        self._select_theme(theme_name)

    @inject.autoparams()
    def _select_theme(self, theme_name: str, incoming_queue: IncomingQueue):
        if self.config.theme_name == theme_name:
            return

        logger.debug(f"Switching theme to {theme_name}")

        theme_path = THEMES_PATH / f"{theme_name}.yml"
        if theme_path.exists():
            try:
                with open(theme_path) as f:
                    theme_data = yaml.safe_load(f)
                if theme_data:
                    self.config.theme_name = theme_name
                    self.config.colors = ColorsConfig.load_from_config(
                        theme_data
                    )
                    # self.config.save_config() # Do not save automatically
                    incoming_queue.put_nowait(
                        IncomingEvent.create_app_event(
                            AppEventEnum.OPTIONS_UPDATED,
                        )
                    )
                    self.update_colors()
                    self.parent.update_colors()
            except Exception as e:
                logger.exception(f"Error loading theme {theme_name}: {e}")
                messagebox.showerror(
                    "Theme Error", f"Could not load theme '{theme_name}'."
                )
        else:
            logger.warning(f"Theme file not found for {theme_name}")

    def _save_theme(self):
        new_name = self.theme_name_entry.get().strip()
        if not new_name or not new_name.replace("_", "").isalnum():
            messagebox.showerror(
                "Invalid Name",
                "Theme name can only contain letters, numbers, and underscores.",
            )
            return

        new_theme_path = THEMES_PATH / f"{new_name}.yml"

        if new_theme_path.exists():
            if not messagebox.askyesno(
                "Overwrite Theme",
                f"Theme '{new_name}' already exists. Do you want to overwrite it with the current colors?",
            ):
                return

        try:
            with open(new_theme_path, "w") as f:
                yaml.dump(asdict(self.config.colors), f)
            messagebox.showinfo(
                "Theme Saved", f"Theme '{new_name}' saved successfully."
            )
        except Exception as e:
            logger.exception(f"Error saving theme {new_name}: {e}")
            messagebox.showerror(
                "Save Error", f"Could not save theme '{new_name}'."
            )
            return

        self._load_themes()
        self.selected_theme.set(new_name)

    def _delete_theme(self):
        theme_to_delete = self.selected_theme.get()
        if theme_to_delete == "pysaic":
            messagebox.showwarning(
                "Delete Error", "Cannot delete the default 'pysaic' theme."
            )
            return

        if not messagebox.askyesno(
            "Delete Theme",
            f"Are you sure you want to delete the theme '{theme_to_delete}'?",
        ):
            return

        theme_path = THEMES_PATH / f"{theme_to_delete}.yml"
        if theme_path.exists():
            try:
                theme_path.unlink()
                messagebox.showinfo(
                    "Theme Deleted",
                    f"Theme '{theme_to_delete}' has been deleted.",
                )
            except Exception as e:
                logger.exception(
                    f"Error deleting theme {theme_to_delete}: {e}"
                )
                messagebox.showerror(
                    "Delete Error",
                    f"Could not delete theme '{theme_to_delete}'.",
                )
                return

        self._load_themes()
        self.selected_theme.set("pysaic")

    def destroy_this_window(self):
        self.parent.clear("theme")
        self.this_window.destroy()
        self.parent.this_window.focus()

    def update_colors(self):
        self.background_color = self.config.colors.background.app
        self.text_color = self.config.colors.content.text
        self.this_window.configure(bg=self.background_color)
        self.main()  # Re-draw widgets with new colors
        apply_style_to_tkinter(self.this_window, self.config)
