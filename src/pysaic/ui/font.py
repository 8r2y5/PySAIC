import os
from pathlib import Path
from tkinter import (
    Toplevel,
    Frame,
    Text,
    Listbox,
    END,
    font,
    Tk,
    SINGLE,
    Button,
)
from tkinter.font import Font

import inject

from pysaic.config import Config
from pysaic.entities import IncomingQueue, IncomingEvent
from pysaic.enums import AppEventEnum

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class FontOptions:
    def __init__(self, parent, config):
        self.parent = parent
        self.config = config

        self._setup_window()
        self._create_widgets()

    def _setup_window(self):
        self.this_window = Toplevel(
            self.parent.this_window,
            background=self.config.colors.background.app,
        )
        self.this_window.protocol(
            "WM_DELETE_WINDOW", self._destroy_this_window
        )
        self.this_window.title("Font Options")
        self.this_window.geometry("450x610")
        self.this_window.resizable(False, False)

        font_name = self.config.font.name
        font_size = self.config.font.size
        self.font = Font(family=font_name, size=font_size)
        self.font_small = Font(family=font_name, size=font_size - 2)

    def _destroy_this_window(self):
        self.this_window.destroy()
        self.parent.this_window.focus()
        self.parent.clear("font")

    def _create_widgets(self):
        self.main_frame = Frame(
            self.this_window,
            padx=10,
            background=self.config.colors.background.app,
        )
        self.main_frame.pack(fill="both", expand=True, pady=(10, 5))

        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(0, weight=2)
        self.main_frame.rowconfigure(1, weight=1)

        self._create_top_frame()
        self._create_bottom_frame()

    def _create_top_frame(self):
        self.top_frame = Frame(
            self.main_frame,
            background=self.config.colors.background.app,
            height=410,
            width=430,
        )
        self.top_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        self.top_frame.pack_propagate(False)
        self.top_frame.grid_propagate(False)

        self.text = Text(
            self.top_frame,
            background=self.config.colors.background.content,
            foreground=self.config.colors.content.text,
            font=self.font,
            wrap="word",
            borderwidth=1,
        )
        self.text.insert(
            END,
            "Lorem ipsum dolor sit amet, consectetur adipiscing elit. Test your font here.",
        )

        self.text.pack(fill="both", expand=True)

    def _create_bottom_frame(self):
        self.bottom_frame = Frame(
            self.main_frame, background=self.config.colors.background.app
        )
        self.bottom_frame.grid(row=1, column=0, sticky="nsew")

        self.bottom_frame.columnconfigure(0, weight=3)
        self.bottom_frame.columnconfigure(1, weight=1)
        self.bottom_frame.rowconfigure(0, weight=1)
        self.bottom_frame.rowconfigure(1, weight=1)

        self.font_family_box = Listbox(
            self.bottom_frame,
            background=self.config.colors.background.content,
            foreground=self.config.colors.content.text,
            selectbackground=self.config.colors.content.highlight,
            font=("Arial", 10),
            selectmode=SINGLE,
        )
        self.font_family_box.grid(row=0, column=0, sticky="nsew", padx=(0, 5))
        self.font_family_box.bind(
            "<<ListboxSelect>>", self._update_font_family
        )

        self.font_family_size = Listbox(
            self.bottom_frame,
            background=self.config.colors.background.content,
            foreground=self.config.colors.content.text,
            selectbackground=self.config.colors.content.highlight,
            font=("Arial", 10),
            selectmode=SINGLE,
        )
        self.font_family_size.grid(row=0, column=1, sticky="nsew")
        self.font_family_size.bind("<<ListboxSelect>>", self._update_font_size)
        button_frame = Frame(
            self.bottom_frame, background=self.config.colors.background.app
        )
        button_frame.grid(row=1, column=0, columnspan=2, sticky="sew")

        self.cancel_button = Button(
            button_frame,
            text="Cancel",
            command=self.this_window.destroy,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
            font=self.font,
        )
        self.cancel_button.pack(side="left", pady=(5, 0))
        self.save_btn = Button(
            button_frame,
            text="Save",
            command=self._save_config,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
            font=self.font,
        )
        self.save_btn.pack(side="right", pady=(5, 0))

        self._fill_data()

    def _fill_data(self):
        for i, f in enumerate(sorted(font.families())):
            self.font_family_box.insert(END, f)
            if self.font.actual("family") == f:
                self.font_family_box.selection_set(i)
                self.font_family_box.see(i)

        sizes = (9, 10, 11, 12, 14, 16, 18, 20)
        for i, x in enumerate(sizes):
            self.font_family_size.insert(END, x)
            if x == self.config.font.size:
                self.font_family_size.selection_set(i)
                self.font_family_size.see(i)

    def _update_font_family(self, _):
        selection = self.font_family_box.curselection()
        if selection:
            self.font.config(family=self.font_family_box.get(selection[0]))
            self.font_small.config(
                family=self.font_family_box.get(selection[0])
            )

    def _update_font_size(self, _):
        selection = self.font_family_size.curselection()
        if selection:
            self.font.config(size=self.font_family_size.get(selection[0]))
            self.font_small.config(
                size=self.font_family_size.get(selection[0] - 2)
            )

    @inject.autoparams()
    def _save_config(self, incoming_queue: IncomingQueue):
        self.config.font.name = self.font.actual("family")
        self.config.font.size = self.font.actual("size")
        incoming_queue.put_nowait(
            IncomingEvent.create_app_event(
                what=AppEventEnum.OPTIONS_UPDATED, payload="settings"
            )
        )
        self.this_window.destroy()


if __name__ == "__main__":
    root = Tk()
    config = Config._create_instance_from_config({})
    c_o = FontOptions(root, config)
    root.mainloop()
