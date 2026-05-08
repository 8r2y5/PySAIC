import os
from functools import partial
from pathlib import Path
from tkinter import (
    END,
    Button,
    Entry,
    Frame,
    Label,
    Tk,
    Toplevel,
    colorchooser,
    Misc,
)
from tkinter.font import BOLD, Font
from tkinter.ttk import Scrollbar
from typing import NamedTuple

import inject

from pysaic.config import (
    Config,
    ColorsConfig,
    FactionColors,
    ContentColors,
    BackgroundColors,
)
from pysaic.controllers.ui.user_list import (
    ONLINE_ICON,
    OFFLINE_ICON,
    AFK_ICON,
    UNDERGROUND_ICON,
    SURGE_ICON,
)
from pysaic.entities import IncomingQueue, IncomingEvent
from pysaic.enums import FactionsEnum, AppEventEnum
from pysaic.ui.constants import WM_DELETE_WINDOW
from pysaic.ui.utils import (
    add_separator,
    ContentFrame,
    BoldLabel,
)

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


def invert(value):
    return 255 - value


def _invert_color(window, color):
    r, g, b = window.winfo_rgb(color)
    r = r // 256
    g = g // 256
    b = b // 256
    return f"#{invert(r):02x}{invert(g):02x}{invert(b):02x}"


class ElementColorData(NamedTuple):
    name: str
    label: Label
    entry: Entry
    button: Button
    colors: ColorsConfig | FactionColors | ContentColors | BackgroundColors
    invert_colors: bool
    window: Misc

    def reapply(self, colors: ColorsConfig):
        color = getattr(self.colors, self.name.lower())
        if not self.invert_colors:
            fg = color
            bg = colors.background.content
        else:
            fg = _invert_color(self.window, color)
            bg = color
        self.label.configure(fg=fg, bg=bg)
        self.entry.delete(0, END)
        self.entry.insert(0, color)
        self.button.configure(fg=colors.content.text, bg=colors.background.app)


class ColorsOptions:
    def __init__(self, parent, config: Config):
        self.parent = parent
        self.config = config
        self.elements: dict[
            str,
            ElementColorData,
        ] = {}

        self._setup_window()
        self._create_widgets()
        self.update_colors()
        self.this_window.iconbitmap(parent.icon_path)

    def _setup_window(self):
        self.this_window = Toplevel(self.parent.this_window)
        self.this_window.protocol(WM_DELETE_WINDOW, self.destroy_this_window)
        self.this_window.title("Color Options")
        self.this_window.minsize(450, 610)

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
        self,
        master,
        row,
        label_text,
        colors,
        config_key,
        is_bold=False,
        invert_background_color=False,
    ):
        """Helper to create a standard label, entry, and picker button row."""
        color = getattr(colors, config_key.lower())
        if invert_background_color:
            label_background = _invert_color(self.this_window, color)
        else:
            label_background = self.config.colors.background.content
        lbl = BoldLabel(
            master,
            text=label_text,
            font=self.font_bold if is_bold else self.font,
            foreground=color,
            background=label_background,
        )
        ent = Entry(
            master,
            font=self.font,
            width=12,
            background=self.config.colors.background.content,
            foreground=self.config.colors.content.text,
        )
        btn = Button(
            master,
            text="...",
            command=partial(self._open_picker, colors, config_key),
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
        )

        lbl.grid(row=row, column=0, padx=5, pady=2, sticky="w")
        ent.grid(row=row, column=1, padx=2, pady=2, sticky="e")
        btn.grid(row=row, column=2, padx=5, pady=2, sticky="e")

        self.elements[config_key] = ElementColorData(
            config_key,
            lbl,
            ent,
            btn,
            colors,
            invert_background_color,
            self.this_window,
        )
        return row + 1

    def _build_factions_section(self):
        add_separator(
            self.left_frame,
            self.config.colors.background.app,
            self.config.colors.content.text,
            0,
            "Factions",
            font=self.font,
        )

        container = ContentFrame(
            self.left_frame, background=self.config.colors.background.content
        )
        container.grid(row=1, column=0, sticky="nsew")
        container.columnconfigure(0, weight=1)

        factions = sorted(FactionsEnum, key=lambda x: x.name)
        for i, enum in enumerate(factions):
            self._create_color_row(
                container,
                i,
                enum.name.replace("_", " "),
                self.config.colors.factions,
                enum.name,
                is_bold=True,
            )

    def _build_previews_section(self):
        # 1. Text Section
        add_separator(
            self.right_frame,
            self.config.colors.background.app,
            self.config.colors.content.text,
            0,
            "Text",
            font=self.font,
        )
        text_cont = ContentFrame(
            self.right_frame, background=self.config.colors.background.content
        )
        text_cont.grid(row=1, column=0, sticky="ew")
        text_cont.grid_columnconfigure((0, 1, 2), weight=1)

        text_items = [
            ("Highlight", "highlight"),
            ("Information", "information"),
            ("Error", "error"),
            ("Standard Text", "text"),
            ("Hyperlink", "hyper_link"),
            (f"{AFK_ICON} AFK", "afk"),
            ("-> DM", "direct_message"),
            (f"{OFFLINE_ICON} Offline", "offline"),
            (f"{ONLINE_ICON} Online", "online"),
            (f"{SURGE_ICON} Surge", "surge"),
            (f"{UNDERGROUND_ICON} Underground", "underground"),
            ("[13:37] time", "time"),
            ("Own Nick", "static_nick"),
        ]
        for i, (label, key) in enumerate(text_items):
            self._create_color_row(
                text_cont, i, label, self.config.colors.content, key
            )

        # 2. PySAIC UI Section
        add_separator(
            self.right_frame,
            self.config.colors.background.app,
            self.config.colors.content.text,
            2,
            "PySAIC",
            font=self.font,
            pad_y_top=5,
        )
        ui_cont = ContentFrame(
            self.right_frame, background=self.config.colors.background.content
        )
        ui_cont.grid(row=3, column=0, sticky="ew")

        # Scrollbar Previews (Manual setup as they are unique widgets)
        Label(
            ui_cont,
            text="Scrollbars",
            font=self.font,
            background=self.config.colors.background.content,
            foreground=self.config.colors.content.text,
        ).grid(row=0, column=0, pady=(5, 0))
        sb = Scrollbar(ui_cont, orient="horizontal")
        sb.set(0.0, 0.9)
        sb.grid(row=1, column=0, columnspan=3, padx=5, pady=2, sticky="ew")
        initial_row = 1
        scroll_items = (
            ("Arrow color", "slider_arrow"),
            ("Pressed", "pressed"),
            ("Disabled", "slider_arrow_disabled"),
        )
        for i, (label, key) in enumerate(scroll_items, start=initial_row + 1):
            self._create_color_row(
                ui_cont,
                i,
                label,
                self.config.colors,
                key,
                invert_background_color=True,
            )

        initial_row += i
        # Generic background/button color pickers could be added here similarly
        text_items = [
            ("App", "app"),
            ("In Between", "in_between"),
            ("Content", "content"),
            ("Active background", "active_background"),
            ("Active foreground", "active_foreground"),
        ]
        for i, (label, key) in enumerate(text_items, start=initial_row + 1):
            self._create_color_row(
                ui_cont,
                i,
                label,
                self.config.colors.background,
                key,
                invert_background_color=True,
            )

    def _open_picker(self, colors, key):
        current_color = getattr(colors, key.lower())
        rgb, hex_code = colorchooser.askcolor(
            color=current_color, title=f"Choose color for {key}"
        )

        if hex_code:
            setattr(colors, key.lower(), hex_code)
            self.update_colors()

    def update_colors(self):
        """Refreshes all widget styles based on current config."""
        bg_app = self.config.colors.background.app

        # incoming_queue.put_nowait(
        #     IncomingEvent.create_app_event(
        #         what=AppEventEnum.COLORS_UPDATED, payload=None
        #     )
        # )

        self.this_window.configure(bg=bg_app)
        self.left_frame.configure(bg=bg_app)
        self.right_frame.configure(bg=bg_app)

        # Update dynamic elements
        for element_color in self.elements.values():
            element_color.reapply(self.config.colors)

    def _create_action_buttons(self):
        btn_frame = Frame(
            self.this_window, bg=self.config.colors.background.app
        )
        btn_frame.grid(
            row=1, column=0, columnspan=2, padx=10, pady=10, sticky="ew"
        )
        btn_frame.columnconfigure((0, 1), weight=1)

        Button(
            btn_frame,
            text="Cancel",
            command=self.destroy_this_window,
            font=self.font,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
        ).grid(row=0, column=0, sticky="w")
        Button(
            btn_frame,
            text="Save",
            command=self._save_config,
            font=self.font,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
        ).grid(row=0, column=1, sticky="e")

    @inject.autoparams()
    def _save_config(self, incoming_queue: IncomingQueue):
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.OPTIONS_UPDATED, payload=self.config.colors
            )
        )
        self.destroy_this_window()

    def destroy_this_window(self):
        self.this_window.destroy()
        self.parent.this_window.focus()
        self.parent.clear("colors")


if __name__ == "__main__":
    root = Tk()
    config = Config.create_instance_from_config({})
    c_o = ColorsOptions(root, config)
    root.mainloop()
