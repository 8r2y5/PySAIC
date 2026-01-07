from tkinter import Frame, Label
from tkinter.ttk import Separator


def create_separator(frame):
    return Separator(frame, orient="horizontal", style="white.TSeparator")


def add_separator(
    master,
    background_color,
    text_color,
    row,
    section_name="",
    pad_y_top: int = 0,
    font=None,
    column: int = 0,
):
    frame = Frame(master, background=background_color)
    frame.grid(
        row=row, column=column, columnspan=2, sticky="ew", pady=(pad_y_top, 5)
    )
    frame.grid_columnconfigure(0, weight=1)
    frame.grid_columnconfigure(1, weight=0)
    frame.grid_columnconfigure(2, weight=1)

    if section_name:
        create_separator(frame).grid(row=0, column=0, sticky="ew")

        Label(
            frame,
            text=section_name,
            background=background_color,
            foreground=text_color,
            font=font,
        ).grid(row=0, column=1, padx=10, sticky="n")

        create_separator(frame).grid(row=0, column=2, sticky="ew")
    else:
        create_separator(frame).grid(
            row=0, column=0, sticky="ew", columnspan=3
        )
