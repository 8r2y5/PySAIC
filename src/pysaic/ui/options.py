import logging
import os
from pathlib import Path
from tkinter import (
    BooleanVar,
    Button,
    Checkbutton,
    Entry,
    Frame,
    Label,
    OptionMenu,
    Radiobutton,
    StringVar,
    Toplevel,
    Spinbox,
)
from tkinter.ttk import Separator, Style

import inject

from pysaic.config import Config, FactionSetting
from pysaic.controllers.ui.user_list import (
    DISPLAY_MODES_MAP,
)
from pysaic.entities import IncomingQueue, IncomingEvent, AppEvent
from pysaic.enums import FactionsEnum, AppEventEnum

logger = logging.getLogger(__name__)

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class Options:
    def __init__(self, config: Config, main_window):
        self.config = config
        self.main_window = main_window
        self.options_window = Toplevel(self.main_window)
        self.options_window.title("Options")
        self.options_window.configure(bg=self.main_window.cget("bg"))
        self.options_window.geometry("400x335")
        self.options_window.resizable(False, False)
        self.options_window.iconbitmap(PATH / "crcr_icon_new.ico")

    def main(self):
        style = Style()
        style.configure("white.TSeparator", background="white")
        background_color = self.main_window.cget("bg")
        text_color = "ghost white"
        default_style_kwargs = {
            "background": background_color,
            "foreground": text_color,
            "activebackground": background_color,
            "activeforeground": text_color,
            "selectcolor": background_color,
        }

        def set_faction(selection=None):
            if selection is None:
                selection = self.faction_var.get()

            logger.debug("Setting faction to %r", selection)
            if selection == FactionSetting.GameSynced.value:
                sync_faction_radio_button.select()
                static_faction_radio_button.deselect()
                faction_options_menu["state"] = "disabled"

            elif selection == "Static":
                static_faction_radio_button.select()
                sync_faction_radio_button.deselect()
                faction_options_menu["state"] = "normal"

        self.faction_var = StringVar(
            self.main_window, value=self.config.faction_setting
        )
        faction_settings = Frame(
            self.options_window, background=background_color
        )
        sync_faction_radio_button = Radiobutton(
            faction_settings,
            text="Sync game faction",
            value=FactionSetting.GameSynced,
            command=set_faction,
            variable=self.faction_var,
            **default_style_kwargs,
        )
        sync_faction_radio_button.pack(anchor="w")
        static_faction = Frame(faction_settings, background=background_color)
        static_faction_radio_button = Radiobutton(
            static_faction,
            text="Static faction",
            value="Static",
            variable=self.faction_var,
            command=set_faction,
            **default_style_kwargs,
        )
        static_faction_radio_button.pack(side="left")

        self.static_faction_var = StringVar(
            self.main_window,
        )
        self.static_faction_var.set(
            self.config.current_faction.name.replace("_", " ")
        )
        options = list(
            sorted(
                [faction.name.replace("_", " ") for faction in FactionsEnum]
            )
        )
        faction_options_menu = OptionMenu(
            static_faction,
            self.static_faction_var,
            *options,
        )
        faction_options_menu.config(
            bg=background_color,
            fg=text_color,
            activebackground=background_color,
            activeforeground=text_color,
        )
        faction_options_menu["menu"].config(
            bg=background_color,
            fg=text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        faction_options_menu.pack(side="left")
        static_faction.pack(anchor="w")
        faction_settings.pack(anchor="w", padx=50, pady=5)
        set_faction()

        self._add_separator()

        account_details_frame = Frame(self.options_window)
        name_label = Label(
            account_details_frame,
            text="Name:",
            background=background_color,
            foreground=text_color,
        )
        name_label.pack(side="left")
        self.name_entry = Entry(
            account_details_frame,
            background=background_color,
            foreground=text_color,
        )
        self.name_entry.pack(side="left")
        self.name_entry.insert(0, self.config.nick)

        password_label = Label(
            account_details_frame,
            text="Password:",
            background=background_color,
            foreground=text_color,
        )
        password_label.pack(side="left")
        self.password_entry = Entry(
            account_details_frame,
            background=background_color,
            foreground=text_color,
            show="*",
        )
        self.password_entry.pack(side="left")
        self.password_entry.insert(0, self.config.password)
        account_details_frame.pack()

        self._add_separator()

        client_config_frame = Frame(
            self.options_window, background=background_color
        )
        self.disconnect_during_emission_or_when_underground_var = BooleanVar()
        self.disconnect_during_emission_or_when_underground_var.set(
            value=self.config.disconnect_when_blowout_or_underground
        )
        disconnect_during_emission_or_when_underground = Checkbutton(
            client_config_frame,
            text="Disconnect during emission or when underground",
            onvalue=True,
            offvalue=False,
            variable=self.disconnect_during_emission_or_when_underground_var,
            **default_style_kwargs,
        )
        disconnect_during_emission_or_when_underground.pack(anchor="w")

        self.block_money_transfer_var = BooleanVar()
        self.block_money_transfer_var.set(
            value=self.config.block_money_transfer
        )
        block_money_transfer = Checkbutton(
            client_config_frame,
            text="Block money transfer",
            onvalue=True,
            offvalue=False,
            variable=self.block_money_transfer_var,
            **default_style_kwargs,
        )
        block_money_transfer.pack(anchor="w")

        self.sound_notification_var = BooleanVar()
        self.sound_notification_var.set(value=self.config.news_sound)
        sound_notification = Checkbutton(
            client_config_frame,
            text="Sound notification",
            onvalue=True,
            offvalue=False,
            variable=self.sound_notification_var,
            **default_style_kwargs,
        )
        sound_notification.pack(anchor="w")

        news_frame = Frame(client_config_frame)
        news_duration_label = Label(
            client_config_frame,
            text="Notification duration (in milliseconds):",
            background=background_color,
            foreground=text_color,
        )
        news_duration_label.pack(side="left")
        self.news_duration_spinbox = Spinbox(
            news_frame,
            from_=1000,
            to=20000,
            increment=25,
            width=10,
            background=background_color,
            foreground=text_color,
        )
        self.news_duration_spinbox.delete(0, "end")
        self.news_duration_spinbox.insert(0, str(self.config.news_duration))
        self.news_duration_spinbox.pack(side="left")

        news_frame.pack(side="left")
        client_config_frame.pack()
        self._add_separator()

        user_display_frame = Frame(
            self.options_window, background=background_color
        )
        user_list_display_label = Label(
            user_display_frame,
            text="User list display:",
            background=background_color,
            foreground=text_color,
        )
        user_list_display_label.pack(side="left")

        self.user_list_display_var = StringVar(
            self.main_window, value=self.config.user_list_display
        )
        user_list_display_options = DISPLAY_MODES_MAP.keys()
        user_list_display_option = OptionMenu(
            user_display_frame,
            self.user_list_display_var,
            *user_list_display_options,
        )
        user_list_display_option.config(
            bg=background_color,
            fg=text_color,
            activebackground=background_color,
            activeforeground=text_color,
        )
        user_list_display_option["menu"].config(
            bg=background_color,
            fg=text_color,
            activebackground="dim gray",
            activeforeground="black",
        )
        user_list_display_option.pack(side="left")
        user_display_frame.pack()
        self._add_separator()

        buttons_frame = Frame(
            self.options_window,
            background=background_color,
        )
        buttons_frame.columnconfigure(0, minsize=258, weight=1)
        buttons_frame.columnconfigure(1, weight=1)
        join_discord = Button(
            buttons_frame,
            text="Join Discord",
            command=lambda: os.system("start https://discord.gg/KjNHXCkHr9"),
            background=background_color,
            foreground=text_color,
        )
        join_discord.grid(row=0, column=0, sticky="w")
        decision_frame = Frame(buttons_frame, background=background_color)
        save_button = Button(
            decision_frame,
            text="Save",
            command=self.save_options,
            background=background_color,
            foreground=text_color,
        )
        save_button.pack(side="left", padx=10)

        cancel_button = Button(
            decision_frame,
            text="Cancel",
            command=self.options_window.destroy,
            background=background_color,
            foreground=text_color,
        )
        cancel_button.pack(side="left")

        decision_frame.grid(row=0, column=1, sticky="e")
        buttons_frame.pack()
        set_faction(selection=self.config.faction_setting)

    @inject.autoparams()
    def save_options(self, incoming_queue: IncomingQueue):
        logger.debug("Saving options")
        logger.debug("Faction setting: %r", self.faction_var.get())
        self.config.faction_setting = FactionSetting[self.faction_var.get()]
        if self.config.faction_setting == FactionSetting.Static:
            logger.debug("Current faction: %r", self.static_faction_var.get())
            self.config.current_faction = FactionsEnum[
                self.static_faction_var.get().replace(" ", "_")
            ]

        logger.debug("Name: %r", self.name_entry.get())
        self.config.nick = self.name_entry.get()

        logger.debug("Password: %r", self.password_entry.get())
        self.config.password = self.password_entry.get()

        logger.debug(
            "disconnect_during_emission_or_when_underground: %r",
            self.disconnect_during_emission_or_when_underground_var.get(),
        )
        self.config.disconnect_when_blowout_or_underground = (
            self.disconnect_during_emission_or_when_underground_var.get()
        )

        logger.debug(
            "block_money_transfer: %r", self.block_money_transfer_var.get()
        )
        self.config.block_money_transfer = self.block_money_transfer_var.get()

        logger.debug(
            "sound_notification: %r", self.sound_notification_var.get()
        )
        self.config.news_sound = self.sound_notification_var.get()

        logger.debug("user_list_display: %r", self.user_list_display_var.get())
        self.config.user_list_display = self.user_list_display_var.get()

        logger.debug("Saving config")
        self.config.save_config()
        incoming_queue.put_nowait(
            IncomingEvent(
                author="",
                target="",
                event=AppEvent(what=AppEventEnum.OPTIONS_UPDATED),
            )
        )
        self.options_window.destroy()

    def _add_separator(self):
        Separator(
            self.options_window, orient="horizontal", style="white.TSeparator"
        ).pack(fill="x", pady=10, padx=20)
