import logging
import os
import re
from asyncio import Queue
from functools import partial
from pathlib import Path
from tkinter import (
    INSERT,
    Button,
    Entry,
    Frame,
    OptionMenu,
    StringVar,
    Text,
    Tk,
    Toplevel,
)
from tkinter.font import Font
from tkinter.ttk import Scrollbar, Style

from winotify import Notification, audio

from pysaic.config import Config
from pysaic.entities import AppEvent, IncomingEvent
from pysaic.enums import AppEventEnum, FactionsEnum
from pysaic.settings import APP_IDENTITY, DEBUG
from pysaic.state import State
from pysaic.ui.hyper_links import HyperlinkManager
from pysaic.ui.options import Options

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 550

MIN_WIDTH = 400
MIN_HEIGHT = 300

TK_BREAK = "break"

PATH = Path(os.path.abspath(os.path.dirname(__file__)))
AUTO_COMPLETE_REGEXP = re.compile(r"[@]?\w+$")


class AltFontSize:
    def __init__(self, widget, delta):
        self.widget = widget
        self.delta = delta

    def config(self, **kwargs):
        if "font" in kwargs:
            font = kwargs["font"]
            if isinstance(font, (list, tuple)) and len(font) > 1:
                font = (font[0], max(font[1] + self.delta, 1))
                kwargs["font"] = font

        self.widget.config(**kwargs)


class App(Tk):
    @property
    def is_focused(self) -> bool:
        return bool(self.focus_get())

    @property
    def should_show_popups(self) -> bool:
        return (
            self.pysaic_config.pop_up_on_ping
            and not self.is_focused
            and self.pysaic_state.is_game_running is not True
        )

    def __init__(
        self,
        state: State,
        config: Config,
        incoming_queue: Queue,
        outgoing_queue: Queue,
    ):
        super().__init__()
        self.pysaic_config = config
        self.pysaic_state = state
        style = Style()
        style.theme_use("clam")
        style.configure(
            "TScrollbar",
            gripcount=0,
            background=self.pysaic_config.colors.background,  # The thumb color
            troughcolor=self.pysaic_config.colors.background_light,  # The track color
            bordercolor=self.pysaic_config.colors.background,
            darkcolor=self.pysaic_config.colors.background,
            lightcolor=self.pysaic_config.colors.background_in_between,
            arrowcolor=self.pysaic_config.colors.slider_arrow,
            arrowsize=15,
        )
        style.map(
            "TScrollbar",
            background=[
                ("disabled", self.pysaic_config.colors.background_light),
                ("pressed", self.pysaic_config.colors.pressed),
                ("active", self.pysaic_config.colors.active_background),
            ],
            troughcolor=[
                ("disabled", self.pysaic_config.colors.background_light)
            ],
            arrowcolor=[
                ("disabled", self.pysaic_config.colors.slider_arrow_disabled)
            ],
        )
        self.title(APP_IDENTITY)
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.minsize(MIN_WIDTH + 210, MIN_HEIGHT + 32)
        # self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.hyperlinks = None
        self.create_widgets()
        # self.after(250, self.process_incoming_events)
        self.iconbitmap(PATH / "crcr_icon_new.ico")
        self.disable_input()

    def on_close(self):
        self.destroy()
        self.outgoing_queue.put_nowait(None)
        self.incoming_queue.put_nowait(None)

    def lift_and_focus(self):
        # makes app light up on the taskbar
        self.lift()

        # bring window to the front, this actually lifts it above all other windows
        self.attributes("-topmost", True)

        # disable topmost so other windows can be focused later
        self.after_idle(self.attributes, "-topmost", False)

        # focus on input bar, making it ready for typing
        self.focus_force()

    def create_widgets(self):
        self.configure(background=self.pysaic_config.colors.background)
        self.main_frame = Frame(
            self, background=self.pysaic_config.colors.background
        )
        self.main_frame.pack(expand=True, fill="both")

        self._configure_grid()
        self._prepare_left_frame()
        self._prepare_right_frame()
        self._prepare_bottom_frame()

        self._update_fonts_on_widgets()
        self.set_color_tags()
        if DEBUG:
            self._create_irc_window()

    def disable_input(self):
        self._set_input_state("disabled")

    def enable_input(self):
        self._set_input_state("normal")

    def _prepare_left_frame(self):
        left_frame = Frame(
            self.main_frame,
            padx=3,
            pady=3,
            background=self.pysaic_config.colors.background,
        )
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=0, minsize=16)
        left_frame.rowconfigure(0, weight=1)

        chat_scroll = Scrollbar(left_frame)
        self.messages_list = Text(
            left_frame,
            yscrollcommand=chat_scroll.set,
            background=self.pysaic_config.colors.background_light,
            wrap="word",
        )
        self.messages_list.grid(row=0, column=0, sticky="nsew")
        chat_scroll.config(command=self.messages_list.yview)
        chat_scroll.grid(row=0, column=1, sticky="ns")
        self.hyperlinks = HyperlinkManager(self.messages_list)

    def _prepare_right_frame(self):
        right_frame = Frame(
            self.main_frame,
            padx=3,
            pady=3,
            background=self.pysaic_config.colors.background,
        )
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_top_frame = Frame(
            right_frame, background=self.pysaic_config.colors.background
        )
        right_top_frame.pack(fill="x")
        right_bottom_frame = Frame(
            right_frame, background=self.pysaic_config.colors.background
        )
        right_bottom_frame.pack(fill="both", expand=True)

        channels_and_option_section = Frame(
            right_top_frame, background=self.pysaic_config.colors.background
        )
        channels_and_option_section.columnconfigure(0, weight=1)
        channels_and_option_section.columnconfigure(1, weight=1, minsize=10)
        irc_channels_to_name_map = {
            channel.name: channel.description
            for channel in self.pysaic_config.server.channels
        }
        name_to_irc_channels_map = {
            channel.description: channel.name
            for channel in self.pysaic_config.server.channels
        }
        selected_channel = StringVar(
            value=irc_channels_to_name_map[
                self.pysaic_config.server.previous_channel
            ],
        )
        self.channels_dropbox = OptionMenu(
            channels_and_option_section,
            selected_channel,
            *[
                channel.description
                for channel in self.pysaic_config.server.channels
            ],
            command=lambda _: self.incoming_queue.put_nowait(
                IncomingEvent(
                    author="",
                    target="",
                    event=AppEvent(
                        what=AppEventEnum.CHANGE_CHANNEL,
                        payload=name_to_irc_channels_map[
                            selected_channel.get()
                        ],
                    ),
                )
            ),
        )
        selected_channel.set(
            irc_channels_to_name_map[
                self.pysaic_config.server.previous_channel
            ]
        )
        self.channels_dropbox.config(
            bg=self.pysaic_config.colors.background,
            fg=self.pysaic_config.colors.text,
            activebackground=self.pysaic_config.colors.background,
            activeforeground=self.pysaic_config.colors.text,
        )
        self.channels_dropbox["menu"].config(
            bg=self.pysaic_config.colors.background,
            fg=self.pysaic_config.colors.text,
            activebackground=self.pysaic_config.colors.active_background,
            activeforeground=self.pysaic_config.colors.active_foreground,
        )
        self.channels_dropbox.grid(row=0, column=0, sticky="ew")

        self.options_button = Button(
            channels_and_option_section,
            text="Options",
            command=lambda: Options(self.pysaic_config, self).main(),
            background=self.pysaic_config.colors.background,
            foreground=self.pysaic_config.colors.text,
            width=10,
        )
        self.options_button.grid(row=0, column=1, sticky="ew")

        channels_and_option_section.pack(side="left", fill="x")

        self.users_list_scroll = Scrollbar(
            right_bottom_frame,
        )
        self.users_list = Text(
            right_bottom_frame,
            yscrollcommand=self.users_list_scroll.set,
            width=22,
            background=self.pysaic_config.colors.background_light,
        )
        self.users_list.pack(side="left", expand=True, fill="both")
        self.users_list_scroll.config(command=self.users_list.yview)
        self.users_list_scroll.pack(side="left", fill="y")

    def _prepare_bottom_frame(self):
        self.bottom_frame = Frame(
            self.main_frame, background=self.pysaic_config.colors.background
        )
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.input_message = Entry(
            self.bottom_frame,
            background=self.pysaic_config.colors.background_light,
            foreground=self.pysaic_config.colors.text,
            disabledbackground=self.pysaic_config.colors.background,
        )
        self.input_message.pack(
            expand=True, fill="both", side="left", padx=3, pady=3
        )
        input_function = partial(
            self._send_message, input_entry=self.input_message
        )
        self.input_message.bind("<Return>", input_function)
        self.send_button = Button(
            self.bottom_frame,
            text="Send",
            command=input_function,
            foreground=self.pysaic_config.colors.text,
            background=self.pysaic_config.colors.background,
        )
        self.input_message.bind("<Tab>", self._nick_auto_complete)
        self.input_message.bind(
            "<Control-Key-A>",
            lambda _: self.input_message.select_range(0, "end"),
        )
        self.input_message.bind(
            "<Control-BackSpace>", self._delete_till_previous_word
        )

        self.send_button.pack(side="left", padx=3, pady=3)

    def show_popup(self, title: str, message: str):
        logger.info("Showing popup: %r: %r", title, message)
        toast = Notification(
            app_id="PySAIC",
            title=title,
            msg=message,
            duration="long",
            icon=str(PATH / "crcr_icon_new.ico"),
            launch="pysaic://open",
        )
        logger.debug(
            "Popup sound is set to %r", self.pysaic_config.pop_up_sound
        )
        if self.pysaic_config.pop_up_sound:
            logger.debug("Playing popup sound")
            toast.set_audio(audio.Default, loop=False)
        else:
            logger.debug("Silent popup")
            toast.set_audio(audio.Silent, loop=False)
        toast.show()

    def _nick_auto_complete(self, _event):
        self.input_message.focus_set()
        cursor_position = self.input_message.index(INSERT)
        text = self.input_message.get()
        result = AUTO_COMPLETE_REGEXP.search(text[:cursor_position])
        start = 0 if not result else result.start()

        if start == -1:
            start = 0

        characters = text[start:cursor_position]
        if characters.startswith(" "):
            original_len = len(characters)
            word = characters.lstrip()
            start += original_len - len(word)

        was_at_there = False
        if characters.startswith("@"):
            characters = characters[1:]
            was_at_there = True

        if len(characters) < 2:
            return TK_BREAK

        users = sorted(self.pysaic_state.chat_users.keys())
        if characters in users:
            found_user = self._cycle_through_users(users, characters)
        else:
            characters = characters.lower()
            found_user = next(
                (
                    user
                    for user in users
                    if user.lower().startswith(characters)
                ),
                [],
            )

        if found_user:
            self.input_message.delete(start, cursor_position)
            if was_at_there:
                found_user = f"@{found_user}"
            self.input_message.insert(start, found_user)

        return TK_BREAK

    def _configure_grid(self):
        self.main_frame.rowconfigure(0, minsize=MIN_HEIGHT, weight=1)
        self.main_frame.rowconfigure(1, minsize=18, weight=0)
        # self.rowconfigure(2, minsize=18, weight=1)

        self.main_frame.columnconfigure(0, minsize=MIN_WIDTH, weight=8)
        self.main_frame.columnconfigure(1, minsize=210, weight=1)
        # self.columnconfigure(1, minsize=10, weight=0)

    def _send_message(self, *_args, input_entry):
        content = input_entry.get().replace("\n", "").strip(" ")
        if not content:
            return

        if content.startswith("/"):
            app_event = AppEvent(
                what=AppEventEnum.COMMAND, payload=content[1:]
            )
        else:
            app_event = AppEvent(
                what=AppEventEnum.OUR_MESSAGE, payload=content
            )
        self.incoming_queue.put_nowait(
            IncomingEvent(
                author="",
                target="",
                event=app_event,
            )
        )

        input_entry.delete(0, "end")

    def set_color_tags(self):
        # TODO: Load values from config
        for widget in (self.messages_list, self.users_list):
            bold_font = Font(widget, widget.cget("font"))
            bold_font.configure(weight="bold")
            widget.tag_config(
                "Time", foreground=self.pysaic_config.colors.time
            )
            widget.tag_config(
                "Text", foreground=self.pysaic_config.colors.text
            )
            widget.tag_config(
                "Highlight", background=self.pysaic_config.colors.highlight
            )
            widget.tag_config(
                "hyper",
                foreground=self.pysaic_config.colors.hyper_link,
                underline=True,
            )
            widget.tag_raise("sel", aboveThis="Highlight")
            widget.tag_config(
                "Information", foreground=self.pysaic_config.colors.information
            )
            widget.tag_config(
                "Error", foreground=self.pysaic_config.colors.error
            )
            widget.tag_config(
                FactionsEnum.Clear_Sky.name,
                foreground=self.pysaic_config.colors.clear_sky,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Loner.name,
                foreground=self.pysaic_config.colors.loner,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Ecologist.name,
                foreground=self.pysaic_config.colors.ecologist,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Bandit.name,
                foreground=self.pysaic_config.colors.bandit,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Monolith.name,
                foreground=self.pysaic_config.colors.monolith,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Duty.name,
                foreground=self.pysaic_config.colors.duty,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Freedom.name,
                foreground=self.pysaic_config.colors.freedom,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Mercenary.name,
                foreground=self.pysaic_config.colors.mercenary,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Military.name,
                foreground=self.pysaic_config.colors.military,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Renegade.name,
                foreground=self.pysaic_config.colors.renegade,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Zombie.name,
                foreground=self.pysaic_config.colors.zombie,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Anonymous.name,
                foreground=self.pysaic_config.colors.anonymous,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.UNISG.name,
                foreground=self.pysaic_config.colors.unisg,
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.SIN.name,
                foreground=self.pysaic_config.colors.sin,
                font=bold_font,
            )
            widget.tag_config(
                "DM",
                foreground=self.pysaic_config.colors.direct_message,
                font=bold_font,
            )
            widget.tag_config(
                "online",
                foreground=self.pysaic_config.colors.online,
                font=bold_font,
            )
            widget.tag_config(
                "offline",
                foreground=self.pysaic_config.colors.offline,
                font=bold_font,
            )
            widget.tag_config(
                "afk", foreground=self.pysaic_config.colors.afk, font=bold_font
            )

    def _cycle_through_users(self, users, characters) -> str:
        users_gen = iter(users)
        user = next(users_gen)
        while user != characters:
            user = next(users_gen)
        user = next(users_gen, None)
        if not user:
            user = next(iter(users), "")
        return user

    def _delete_till_previous_word(self, _):
        cursor_position = self.input_message.index("insert")
        text = self.input_message.get()
        if cursor_position == 0:
            return TK_BREAK

        if text[cursor_position - 1] == " ":
            self.input_message.delete(cursor_position - 1, cursor_position)
            return TK_BREAK

        while cursor_position > 0 and text[cursor_position - 1] != " ":
            cursor_position -= 1

        self.input_message.delete(cursor_position, "insert")
        return TK_BREAK

    # noinspection PyTypeChecker
    def _set_input_state(self, value: str):
        self.channels_dropbox.config(state=value)
        self.input_message.config(state=value)
        self.send_button.config(state=value)

    def _create_irc_window(self):
        self.irc_window = Toplevel(self)
        self.irc_window.title("IRC Window")
        self.irc_window.geometry(f"{WIDTH}x{HEIGHT}")
        self.irc_window.minsize(MIN_WIDTH, MIN_HEIGHT)
        self.irc_window.protocol("WM_DELETE_WINDOW", self.on_close)
        self.irc_window.iconbitmap(PATH / "crcr_icon_new.ico")
        self.irc_window.configure(
            background=self.pysaic_config.colors.background
        )
        self.irc_messages_list = Text(
            self.irc_window,
            background=self.pysaic_config.colors.background_light,
            wrap="word",
        )
        self.irc_messages_list.pack(expand=True, fill="both", padx=3, pady=3)
        self.irc_messages_list.tag_config(
            "Text", foreground=self.pysaic_config.colors.text
        )
        self.irc_messages_list.config(
            font=(self.pysaic_config.font.name, self.pysaic_config.font.size)
        )
        self.irc_messages_list.config(state="disabled")

    def _update_fonts_on_widgets(self):
        for widget in (
            AltFontSize(self.users_list, 1),
            AltFontSize(self.messages_list, 1),
            self.input_message,
            AltFontSize(self.send_button, -1),
            AltFontSize(self.channels_dropbox, -2),
            AltFontSize(self.options_button, -2),
        ):
            widget.config(
                font=(
                    self.pysaic_config.font.name,
                    self.pysaic_config.font.size,
                )
            )
