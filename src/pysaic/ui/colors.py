import os
from functools import partial
from pathlib import Path
from tkinter import (
    Toplevel,
    Frame,
    Label,
    Button,
    Tk,
    colorchooser,
    Entry,
    END,
)
from tkinter.font import Font, BOLD
from tkinter.ttk import Scrollbar, Style

from pysaic.config import Config
from pysaic.enums import FactionsEnum
from pysaic.ui.utils import add_separator

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class ColorsOptions:
    def __init__(self, parent, config: Config):
        self.parent = parent
        self.config = config
        self.elements: dict[str, tuple[Label, Entry, Button]] = {}

        self._setup_window()
        self._create_widgets()
        self.update_colors()

    def _setup_window(self):
        self.this_window = Toplevel(self.parent)
        self.this_window.title("Color Options")
        self.this_window.minsize(450, 610)
        self.this_window.iconbitmap(PATH / "crcr_icon_new.ico")

        # Initialize Fonts
        font_name = self.config.font.name
        font_size = self.config.font.size
        self.font = Font(family=font_name, size=font_size)
        self.font_bold = Font(family=font_name, size=font_size, weight=BOLD)

    def _create_widgets(self):
        """Main layout container."""
        self.this_window.grid_columnconfigure((0, 1), weight=1)
        self.this_window.grid_rowconfigure(0, weight=1)

        # Left Column: Factions
        self.left_frame = Frame(self.this_window)
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self._build_factions_section()

        # Right Column: Text & PySAIC
        self.right_frame = Frame(self.this_window)
        self.right_frame.grid(row=0, column=1, padx=10, pady=10, sticky="nsew")
        self._build_previews_section()

        # Bottom: Action Buttons
        self._create_action_buttons()

    def _create_color_row(
        self, master, row, label_text, config_key, is_bold=False
    ):
        """Helper to create a standard label, entry, and picker button row."""
        color = getattr(self.config.colors, config_key.lower())
        lbl = Label(
            master,
            text=label_text,
            font=self.font_bold if is_bold else self.font,
            foreground=color,
            background=self.config.colors.duty,
        )
        ent = Entry(
            master,
            font=self.font,
            width=12,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        btn = Button(
            master,
            text="...",
            command=partial(self._open_picker, config_key),
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )

        lbl.grid(row=row, column=0, padx=5, pady=2, sticky="w")
        ent.grid(row=row, column=1, padx=2, pady=2, sticky="e")
        btn.grid(row=row, column=2, padx=5, pady=2, sticky="e")

        self.elements[config_key] = (lbl, ent, btn)
        return row + 1

    def _build_factions_section(self):
        add_separator(
            self.left_frame,
            self.config.colors.background,
            self.config.colors.text,
            0,
            "Factions",
            font=self.font,
        )

        container = Frame(
            self.left_frame, background=self.config.colors.background_light
        )
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        factions = sorted(FactionsEnum, key=lambda x: x.name)
        for i, enum in enumerate(factions):
            self._create_color_row(
                container,
                i,
                enum.name.replace("_", " "),
                enum.name,
                is_bold=True,
            )

    def _build_previews_section(self):
        # 1. Text Section
        add_separator(
            self.right_frame,
            self.config.colors.background,
            self.config.colors.text,
            0,
            "Text",
            font=self.font,
        )
        text_cont = Frame(
            self.right_frame, background=self.config.colors.background_light
        )
        text_cont.grid(row=1, column=0, sticky="ew")

        text_items = [
            ("Highlight", "highlight"),
            ("Information", "information"),
            ("Error", "error"),
            ("Standard Text", "text"),
            ("Hyperlink", "hyper_link"),
        ]
        for i, (label, key) in enumerate(text_items):
            self._create_color_row(text_cont, i, label, key)

        # 2. PySAIC UI Section
        add_separator(
            self.right_frame,
            self.config.colors.background,
            self.config.colors.text,
            2,
            "PySAIC",
            font=self.font,
        )
        ui_cont = Frame(
            self.right_frame, background=self.config.colors.background_light
        )
        ui_cont.grid(row=3, column=0, sticky="ew")

        # Scrollbar Previews (Manual setup as they are unique widgets)
        Label(
            ui_cont,
            text="Scrollbars",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        ).grid(row=0, column=0, pady=(5, 0))
        sb = Scrollbar(ui_cont, orient="vertical")
        sb.set(0.2, 0.5)
        sb.grid(row=1, column=0, pady=5)

        # Generic background/button color pickers could be added here similarly

    def _open_picker(self, key):
        current_color = getattr(self.config.colors, key.lower())
        rgb, hex_code = colorchooser.askcolor(
            color=current_color, title=f"Choose color for {key}"
        )

        if hex_code:
            setattr(self.config.colors, key.lower(), hex_code)
            self.update_colors()

    def update_colors(self):
        """Refreshes all widget styles based on current config."""
        bg = self.config.colors.background
        bg_light = self.config.colors.background_light
        text_color = self.config.colors.text

        # Update Scrollbar Styles
        style = Style()
        style.theme_use("clam")
        style.configure(
            "TScrollbar",
            background=bg,
            troughcolor=bg_light,
            bordercolor=bg,
            arrowcolor=self.config.colors.slider_arrow,
        )

        self.this_window.configure(bg=bg)
        self.left_frame.configure(bg=bg)
        self.right_frame.configure(bg=bg)

        # Update dynamic elements
        for name, (label, entry, button) in self.elements.items():
            color = getattr(self.config.colors, name.lower())
            label.configure(fg=color, bg=bg_light)
            entry.delete(0, END)
            entry.insert(0, color)
            button.configure(fg=text_color, bg=bg)

    def _create_action_buttons(self):
        btn_frame = Frame(self.this_window, bg=self.config.colors.background)
        btn_frame.grid(
            row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew"
        )
        btn_frame.columnconfigure((0, 1), weight=1)

        Button(
            btn_frame,
            text="Cancel",
            command=self.this_window.destroy,
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        ).grid(row=0, column=0, sticky="w")
        Button(
            btn_frame,
            text="Save",
            command=self._save_config,
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        ).grid(row=0, column=1, sticky="e")

    def _save_config(self):
        # Logic to save self.config to disk
        print("Configuration Saved")
        self.this_window.destroy()


if __name__ == "__main__":
    root = Tk()
    config = Config._create_instance_from_config({})
    c_o = ColorsOptions(root, config)
    root.mainloop()
