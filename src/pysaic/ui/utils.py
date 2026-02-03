import tkinter
from tkinter import Frame
from tkinter.font import Font
from tkinter.ttk import Separator, Style, Label

from pysaic.config import ColorsConfig, Config
from pysaic.enums import FactionsEnum


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


class ContentFrame(tkinter.Frame):
    pass


class BoldLabel(tkinter.Label):
    pass


def apply_color_tags_to_text(widget: tkinter.Text, colors: ColorsConfig):
    bold_font = Font(widget, widget.cget("font"))
    bold_font.configure(weight="bold")
    widget.tag_config("Time", foreground=colors.content.time)
    widget.tag_config("Text", foreground=colors.content.text)
    widget.tag_config(
        "Highlight",
        background=colors.content.highlight,
    )
    widget.tag_config(
        "hyper",
        foreground=colors.content.hyper_link,
        underline=True,
    )
    widget.tag_raise("sel", aboveThis="Highlight")
    widget.tag_config(
        "Information",
        foreground=colors.content.information,
    )
    widget.tag_config("Error", foreground=colors.content.error)
    widget.tag_config(
        FactionsEnum.Clear_Sky.name,
        foreground=colors.factions.clear_sky,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Loner.name,
        foreground=colors.factions.loner,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Ecologist.name,
        foreground=colors.factions.ecologist,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Bandit.name,
        foreground=colors.factions.bandit,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Monolith.name,
        foreground=colors.factions.monolith,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Duty.name,
        foreground=colors.factions.duty,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Freedom.name,
        foreground=colors.factions.freedom,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Mercenary.name,
        foreground=colors.factions.mercenary,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Military.name,
        foreground=colors.factions.military,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Renegade.name,
        foreground=colors.factions.renegade,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Zombie.name,
        foreground=colors.factions.zombie,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.Anonymous.name,
        foreground=colors.factions.anonymous,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.UNISG.name,
        foreground=colors.factions.unisg,
        font=bold_font,
    )
    widget.tag_config(
        FactionsEnum.SIN.name,
        foreground=colors.factions.sin,
        font=bold_font,
    )
    widget.tag_config(
        "DM",
        foreground=colors.content.direct_message,
        font=bold_font,
    )
    widget.tag_config(
        "online",
        foreground=colors.content.online,
        font=bold_font,
    )
    widget.tag_config(
        "offline",
        foreground=colors.content.offline,
        font=bold_font,
    )
    widget.tag_config(
        "afk",
        foreground=colors.content.afk,
        font=bold_font,
    )
    widget.tag_config(
        "emission",
        foreground=colors.content.surge,
        font=bold_font,
    )
    widget.tag_config(
        "underground",
        foreground=colors.content.underground,
        font=bold_font,
    )


def apply_style_to_tkinter(container, config: Config):
    for widget in container.winfo_children():
        if isinstance(widget, tkinter.Button):
            widget.configure(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                font=(config.font.name, config.font.size - 2),
            )
        elif isinstance(widget, tkinter.Entry):
            widget.configure(
                background=config.colors.background.content,
                foreground=config.colors.content.text,
                font=(config.font.name, config.font.size - 1),
            )
        elif isinstance(widget, tkinter.OptionMenu):
            widget.configure(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                activebackground=config.colors.background.app,
                activeforeground=config.colors.content.text,
                highlightbackground=config.colors.background.app,
                highlightcolor=config.colors.background.app,
                highlightthickness=0,
                font=(config.font.name, config.font.size - 2),
            )
            widget["menu"].config(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                activebackground=config.colors.background.active_background,
                activeforeground=config.colors.background.active_foreground,
                selectcolor=config.colors.background.app,
                relief="flat",
                borderwidth=1,
                activeborderwidth=1,
                font=(config.font.name, config.font.size - 2),
            )
        elif isinstance(widget, tkinter.Label):
            font = (config.font.name, config.font.size - 1)
            widget.configure(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                font=(
                    font + ("bold",) if isinstance(widget, BoldLabel) else font
                ),
            )
        elif isinstance(widget, tkinter.Radiobutton):
            widget.configure(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                font=(config.font.name, config.font.size - 1),
            )
        elif isinstance(widget, tkinter.Checkbutton):
            widget.configure(
                background=config.colors.background.app,
                foreground=config.colors.content.text,
                font=(config.font.name, config.font.size - 1),
            )
        elif isinstance(widget, ContentFrame):
            widget.configure(background=config.colors.background.content)
        elif isinstance(widget, tkinter.Frame):
            widget.configure(
                background=config.colors.background.app,
            )
        elif isinstance(widget, tkinter.Text):
            widget.configure(
                background=config.colors.background.content,
            )
            apply_color_tags_to_text(widget, config.colors)

        if widget.winfo_children():
            apply_style_to_tkinter(widget, config)


def update_style(container, config: Config):
    style = Style()
    style.theme_use("clam")
    style.configure(
        "TScrollbar",
        gripcount=0,
        background=config.colors.background.content,  # The thumb color
        troughcolor=config.colors.background.app,  # The track color
        bordercolor=config.colors.background.app,
        darkcolor=config.colors.background.app,
        lightcolor=config.colors.background.in_between,
        arrowcolor=config.colors.slider_arrow,
        arrowsize=15,
    )
    style.map(
        "TScrollbar",
        background=[
            ("disabled", config.colors.background.content),
            ("pressed", config.colors.pressed),
            (
                "active",
                config.colors.background.active_background,
            ),
        ],
        troughcolor=[("disabled", config.colors.background.content)],
        arrowcolor=[("disabled", config.colors.slider_arrow_disabled)],
    )
    style.configure("white.TSeparator", background=config.colors.content.text)
    style.configure(
        "TSpinbox",
        fieldbackground=config.colors.background.app,
        background=config.colors.background.app,
        foreground=config.colors.content.text,
        arrowcolor=config.colors.content.text,
    )
    apply_style_to_tkinter(container, config)
