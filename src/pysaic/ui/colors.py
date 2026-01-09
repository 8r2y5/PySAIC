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
        self._create_window()

    def _create_window(self):
        self.this_window = Toplevel(self.parent)
        self.this_window.title("Color Options")
        self.font = Font(
            family=self.config.font.name, size=self.config.font.size
        )
        self.font_bold = Font(
            family=self.config.font.name,
            size=self.config.font.size,
            weight=BOLD,
        )
        height = 610
        width = 450
        # self.this_window.geometry(f"{width}x{height}+100+100")
        self.this_window.minsize(width, height)
        self.this_window.iconbitmap(PATH / "crcr_icon_new.ico")

        self._create_window_content()

        self.update_colors()

    def update_colors(self):
        style = Style()
        style.theme_use("clam")
        style.configure(
            "TScrollbar",
            gripcount=0,
            background=self.config.colors.background,  # The thumb color
            troughcolor=self.config.colors.background_light,  # The track color
            bordercolor=self.config.colors.background,
            darkcolor=self.config.colors.background,
            lightcolor=self.config.colors.background_in_between,
            arrowcolor=self.config.colors.slider_arrow,
            arrowsize=15,
        )
        self.this_window.configure(bg=self.config.colors.background)
        self.faction_frame.configure(
            background=self.config.colors.background_light
        )
        for name, (label, entry, button) in self.elements.items():
            color = getattr(self.config.colors, name.lower())
            label.configure(
                fg=color,
                bg=self.config.colors.background_light,
            )
            entry.delete(0, END)
            entry.insert(0, color)
            button.configure(
                fg=self.config.colors.text, bg=self.config.colors.background
            )

    def _create_window_content(self):
        self.this_window.grid_rowconfigure(0, weight=1)
        self.this_window.grid_rowconfigure(1, weight=1)
        self.this_window.grid_rowconfigure(2, weight=1)
        self.this_window.grid_columnconfigure(0, weight=1)
        self.this_window.grid_columnconfigure(1, weight=1)

        self._make_left()

        # right
        self._make_right()

        self.add_separator(self.this_window, row=1, section_name="")

        self._create_buttons()

    def _faction_color_picker(self, name):
        rgb, hex = colorchooser.askcolor(
            color=getattr(self.config.colors, name.lower()),
            title=f"Choose color for {name.replace('_', ' ')}",
        )
        # self.elements[name].configure(fg=hex)
        setattr(self.config.colors, name.lower(), hex)
        label, entry, _ = self.elements[name]
        entry.delete(0, END)
        entry.insert(0, hex)
        label.configure(fg=hex)

    def add_separator(self, frame, row, section_name, pad_y_top=5, column=0):
        add_separator(
            frame,
            self.config.colors.background,
            self.config.colors.text,
            row,
            section_name,
            pad_y_top,
            font=self.font,
            column=column,
        )

    def _factions_preview(self, master_row):
        self.faction_frame = Frame(
            self.left_frame, background=self.config.colors.background_light
        )
        self.faction_frame.grid_columnconfigure(0, weight=1)
        self.faction_frame.grid_columnconfigure(1, weight=0)
        self.faction_frame.grid_columnconfigure(2, weight=0)
        self.faction_frame.grid(
            row=master_row, column=0, columnspan=3, sticky="new"
        )
        row = 0

        for enum in sorted(FactionsEnum, key=lambda x: x.name):
            color = getattr(self.config.colors, enum.name.lower())
            faction_label = Label(
                self.faction_frame,
                text=enum.name.replace("_", " "),
                font=self.font_bold,
                bg=self.config.colors.background_light,
                fg=color,
                justify="center",
            )
            faction_entry = Entry(
                self.faction_frame,
                background=self.config.colors.background_light,
                foreground=self.config.colors.text,
                disabledbackground=self.config.colors.background,
                font=self.font,
                width=12,
                insertbackground=self.config.colors.text,
            )
            faction_entry.insert(0, color)
            faction_button = Button(
                self.faction_frame,
                font=self.font,
                text="...",
                command=partial(self._faction_color_picker, name=enum.name),
                background=self.config.colors.background,
                foreground=self.config.colors.text,
            )
            self.elements[enum.name] = (
                faction_label,
                faction_entry,
                faction_button,
            )
            faction_label.grid(
                row=row, column=0, padx=(10, 5), pady=2, sticky="w"
            )
            faction_entry.grid(row=row, column=1, padx=2, pady=2, sticky="e")
            faction_button.grid(
                row=row, column=2, padx=(10, 0), pady=2, sticky="e"
            )
            row += 1

    def _text_preview(self, master_row):
        self._text_preview_frame = Frame(
            self.right_frame, background=self.config.colors.background_light
        )
        self._text_preview_frame.grid(row=master_row, sticky="new")
        self._text_preview_frame.grid_columnconfigure(0, weight=1)
        self._text_preview_frame.grid_columnconfigure(1, weight=1)
        self._text_preview_frame.grid_rowconfigure(0, weight=1)

        label_highlight = Label(
            self._text_preview_frame,
            text="highlight",
            bg=self.config.colors.highlight,
            fg=self.config.colors.text,
            font=self.font,
        )
        label_highlight.grid(row=0, column=0, pady=2)
        label_highlight_color = Button(
            self._text_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        label_highlight_color.grid(row=0, column=1, pady=2)
        self._text_preview_frame.grid_rowconfigure(0, weight=1)

        label_info = Label(
            self._text_preview_frame,
            text="Information",
            bg=self.config.colors.background_light,
            fg=self.config.colors.information,
            font=self.font,
        )
        label_info.grid(row=1, column=0, pady=2)
        label_info_color = Button(
            self._text_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        label_info_color.grid(row=1, column=1, pady=2)
        self._text_preview_frame.grid_rowconfigure(1, weight=1)

        label_error = Label(
            self._text_preview_frame,
            text="Error Information",
            bg=self.config.colors.background_light,
            fg=self.config.colors.error,
            font=self.font,
        )
        label_error.grid(row=2, column=0, pady=2)
        label_error_color = Button(
            self._text_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        label_error_color.grid(row=2, column=1, pady=2)
        self._text_preview_frame.grid_rowconfigure(2, weight=1)

        label_text = Label(
            self._text_preview_frame,
            text="Example text",
            bg=self.config.colors.background_light,
            fg=self.config.colors.text,
            font=self.font,
        )
        label_text.grid(row=3, column=0, pady=2)
        label_text_color = Button(
            self._text_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        label_text_color.grid(row=3, column=1, pady=2)
        self._text_preview_frame.grid_rowconfigure(3, weight=1)

        label_link = Label(
            self._text_preview_frame,
            text="Example text",
            bg=self.config.colors.background_light,
            fg=self.config.colors.hyper_link,
            font=self.font,
        )
        label_link.grid(row=4, column=0, pady=2)
        label_link_color = Button(
            self._text_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background_light,
            foreground=self.config.colors.text,
        )
        label_link_color.grid(row=4, column=1, pady=2)
        self._text_preview_frame.grid_rowconfigure(4, weight=1)

    def _pysaic_preview(self, master_row):
        self._pysaic_preview_frame = Frame(
            self.right_frame, background=self.config.colors.background
        )
        self._pysaic_preview_frame.grid_columnconfigure(0, weight=1)
        self._pysaic_preview_frame.grid_columnconfigure(1, weight=1)
        self._pysaic_preview_frame.grid(row=master_row, sticky="new")
        self.example_button = Button(
            self._pysaic_preview_frame,
            text="Example",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        self.example_button.grid(row=0, column=0, pady=2)
        self.example_button_color = Button(
            self._pysaic_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        self.example_button_color.grid(row=0, column=1, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(0, weight=1)

        self.example_disable_button = Button(
            self._pysaic_preview_frame,
            text="Example Disable",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
            state="disabled",
        )
        self.example_disable_button.grid(row=1, column=0, pady=2)
        self.example_disable_button_color = Button(
            self._pysaic_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        self.example_disable_button_color.grid(row=1, column=1, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(1, weight=1)

        # 1. Active Scrollbar Example
        active_label = Label(
            self._pysaic_preview_frame,
            text="Active",
            bg=self.config.colors.background,
            fg=self.config.colors.text,
            font=self.font,
        )
        active_label.grid(row=2, column=0, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(2, weight=1)

        self.sb_active = Scrollbar(
            self._pysaic_preview_frame, orient="vertical"
        )
        self.sb_active.set(0.2, 0.5)  # Set thumb position for preview
        self.sb_active.grid(row=3, column=0, pady=5)
        self.active_label_color = Button(
            self._pysaic_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        self.active_label_color.grid(row=3, column=1, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(3, weight=1)

        # 2. Disabled Scrollbar Example
        disabled_label = Label(
            self._pysaic_preview_frame,
            text="Disabled",
            bg=self.config.colors.background,
            fg=self.config.colors.text,
            font=self.font,
        )
        disabled_label.grid(row=4, column=0, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(4, weight=1)

        self.sb_disabled = Scrollbar(
            self._pysaic_preview_frame, orient="vertical"
        )
        self.sb_disabled.set(0, 0)
        self.sb_disabled.grid(row=5, column=0, pady=5)
        self.sb_disabled_color = Button(
            self._pysaic_preview_frame,
            text="...",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        self.sb_disabled_color.grid(row=5, column=1, pady=2)
        self._pysaic_preview_frame.grid_rowconfigure(5, weight=1)

    def _create_buttons(self):
        self.button_frame = Frame(
            self.this_window, bg=self.config.colors.background
        )
        self.button_frame.grid(
            row=2, column=0, columnspan=2, padx=10, pady=10, sticky="new"
        )
        self.button_frame.grid_rowconfigure(0, weight=1)
        self.button_frame.grid_columnconfigure((0, 1), weight=1)
        cancel = Button(
            self.button_frame,
            text="Cancel",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        cancel.grid(row=0, column=0, sticky="nw")

        save = Button(
            self.button_frame,
            text="Save",
            font=self.font,
            background=self.config.colors.background,
            foreground=self.config.colors.text,
        )
        save.grid(row=0, column=1, sticky="ne")

    def _make_left(self):
        self.left_frame = Frame(
            self.this_window, background=self.config.colors.background
        )
        self.left_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        self.left_frame.grid_rowconfigure(0, weight=1)
        self.left_frame.grid_columnconfigure(0, weight=1)

        row = 0
        self.add_separator(
            self.left_frame, row=row, section_name="Factions", pad_y_top=0
        )
        row += 1
        self.left_frame.grid_rowconfigure(1, weight=1)

        self._factions_preview(row)

    def _make_right(self):
        row = 0
        self.right_frame = Frame(
            self.this_window, background=self.config.colors.background
        )
        self.right_frame.grid_rowconfigure(row, weight=1)
        self.right_frame.grid_columnconfigure(0, weight=1)
        self.right_frame.grid(row=row, column=1, padx=10, pady=0, sticky="new")

        self.add_separator(self.right_frame, row=row, section_name="Text")
        row += 1
        self.right_frame.grid_rowconfigure(row, weight=1)

        self._text_preview(row)
        row += 1
        self.right_frame.grid_rowconfigure(row, weight=1)
        self.add_separator(
            self.right_frame, row=row, section_name="PySAIC", pad_y_top=0
        )
        row += 1
        self.right_frame.grid_rowconfigure(row, weight=1)
        self._pysaic_preview(row)
        row += 1
        self.right_frame.grid_rowconfigure(row, weight=1)

        # row += 1
        # self.right_frame.grid_rowconfigure(row, weight=1)


if __name__ == "__main__":
    root = Tk()
    config = Config._create_instance_from_config({})
    c_o = ColorsOptions(root, config)
    root.mainloop()
