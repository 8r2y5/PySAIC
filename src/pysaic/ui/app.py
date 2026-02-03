import ctypes
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
from tkinter.ttk import Scrollbar

from pysaic.ui.constants import WM_DELETE_WINDOW
from pysaic.ui.utils import update_style, apply_color_tags_to_text
from winotify import Notification, audio

from pysaic.config import Config
from pysaic.entities import AppEvent, IncomingEvent
from pysaic.enums import AppEventEnum
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
AUTO_COMPLETE_REGEXP = re.compile(r"(@)?([\w]+)$")
DELETION_STOP_CHARS = {" ", ",", ".", ":", ";", "@", "!", "(", ")"}


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
        ctypes.windll.gdi32.AddFontResourceExW(
            str(PATH / "JetBrainsMono-Regular.ttf"), 0x10, 0
        )
        super().__init__()
        self.pysaic_config = config
        self.pysaic_state = state
        self.title(APP_IDENTITY)
        self.minsize(MIN_WIDTH + 210, MIN_HEIGHT + 32)
        # self.resizable(False, False)
        self.protocol(WM_DELETE_WINDOW, self.on_close)
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.hyperlinks = None
        print(self.pysaic_config)
        self.create_widgets()
        update_style(self, config)
        # self.after(250, self.process_incoming_events)
        self.iconbitmap(PATH / "pysaic_icon.ico")
        self.disable_input()
        self._options_window: None | Options = None

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
        self.configure(background=self.pysaic_config.colors.background.app)
        self.main_frame = Frame(
            self, background=self.pysaic_config.colors.background.app
        )
        self.main_frame.pack(expand=True, fill="both", pady=(1, 0))

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
            background=self.pysaic_config.colors.background.app,
        )
        left_frame.grid(
            row=0,
            column=0,
            sticky="nsew",
            padx=(4, 1),
            pady=3,
        )
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=0, minsize=16)
        left_frame.rowconfigure(0, weight=1)

        chat_scroll = Scrollbar(left_frame)
        self.messages_list = Text(
            left_frame,
            yscrollcommand=chat_scroll.set,
            background=self.pysaic_config.colors.background.content,
            wrap="word",
        )
        self.messages_list.grid(row=0, column=0, sticky="nsew")
        chat_scroll.config(command=self.messages_list.yview)
        chat_scroll.grid(row=0, column=1, sticky="ns")
        self.messages_list.list_scroll = chat_scroll
        self.hyperlinks = HyperlinkManager(self.messages_list)

    def _prepare_right_frame(self):
        right_frame = Frame(
            self.main_frame,
            background=self.pysaic_config.colors.background.app,
        )
        right_frame.grid(
            row=0,
            column=1,
            sticky="nsew",
            padx=(0, 3),
            pady=3,
        )
        right_top_frame = Frame(
            right_frame, background=self.pysaic_config.colors.background.app
        )
        right_top_frame.pack(fill="x")
        right_bottom_frame = Frame(
            right_frame, background=self.pysaic_config.colors.background.app
        )
        right_bottom_frame.pack(fill="both", expand=True)

        channels_and_option_section = Frame(
            right_top_frame,
            background=self.pysaic_config.colors.background.app,
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
            bg=self.pysaic_config.colors.background.app,
            fg=self.pysaic_config.colors.content.text,
            activebackground=self.pysaic_config.colors.background.app,
            activeforeground=self.pysaic_config.colors.content.text,
            highlightbackground=self.pysaic_config.colors.background.app,
            highlightcolor=self.pysaic_config.colors.background.app,
            highlightthickness=0,
            width=22,
        )
        self.channels_dropbox["menu"].config(
            bg=self.pysaic_config.colors.background.app,
            fg=self.pysaic_config.colors.content.text,
            activebackground=self.pysaic_config.colors.background.active_background,
            activeforeground=self.pysaic_config.colors.background.active_foreground,
            relief="flat",
            borderwidth=1,
            activeborderwidth=1,
            selectcolor=self.pysaic_config.colors.background.app,
        )
        self.channels_dropbox.grid(row=0, column=0, sticky="ew")

        self.options_button = Button(
            channels_and_option_section,
            text="Options",
            command=self._spawn_options,
            background=self.pysaic_config.colors.background.app,
            foreground=self.pysaic_config.colors.content.text,
            width=10,
        )
        self.options_button.grid(row=0, column=1, sticky="ew", padx=(5, 0))

        channels_and_option_section.pack(side="left", fill="x")

        self.users_list_scroll = Scrollbar(
            right_bottom_frame,
        )
        self.users_list = Text(
            right_bottom_frame,
            yscrollcommand=self.users_list_scroll.set,
            width=22,
            background=self.pysaic_config.colors.background.content,
        )
        self.users_list.pack(side="left", expand=True, fill="both")
        self.users_list_scroll.config(command=self.users_list.yview)
        self.users_list_scroll.pack(side="left", fill="y")

    def _prepare_bottom_frame(self):
        self.bottom_frame = Frame(
            self.main_frame,
            background=self.pysaic_config.colors.background.app,
        )
        self.bottom_frame.grid(
            row=1, column=0, columnspan=2, sticky="nsew", pady=(2, 1)
        )
        self.input_message = Entry(
            self.bottom_frame,
            background=self.pysaic_config.colors.background.content,
            foreground=self.pysaic_config.colors.content.text,
            disabledbackground=self.pysaic_config.colors.background.app,
            insertbackground=self.pysaic_config.colors.content.text,
        )
        self.input_message.pack(
            expand=True, fill="both", side="left", padx=3, pady=(0, 3)
        )
        input_function = partial(
            self._send_message, input_entry=self.input_message
        )
        self.input_message.bind("<Return>", input_function)
        self.send_button = Button(
            self.bottom_frame,
            text="Send",
            command=input_function,
            foreground=self.pysaic_config.colors.content.text,
            background=self.pysaic_config.colors.background.app,
        )
        self.input_message.bind("<Tab>", self._nick_auto_complete)
        self.input_message.bind(
            "<Control-Key-A>",
            lambda _: self.input_message.select_range(0, "end"),
        )
        self.input_message.bind(
            "<Control-BackSpace>", self._delete_till_previous_word
        )

        self.send_button.pack(side="left", padx=3, pady=(0, 3), fill="both")

    def show_popup(self, title: str, message: str):
        logger.info("Showing popup: %r: %r", title, message)
        toast = Notification(
            app_id="PySAIC",
            title=title,
            msg=message,
            duration="long",
            icon=str(PATH / "pysaic_icon.ico"),
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
        text_before_cursor = self.input_message.get()[:cursor_position]

        match = AUTO_COMPLETE_REGEXP.search(text_before_cursor)
        if not match:
            return TK_BREAK

        prefix, partial_nick = match.groups()
        start_pos = match.start()

        if len(partial_nick) < 2:
            return TK_BREAK

        users = sorted(self.pysaic_state.chat_users.keys())

        if partial_nick in users:
            found_user = self._cycle_through_users(users, partial_nick)
        else:
            found_user = next(
                (
                    user
                    for user in users
                    if user.lower().startswith(partial_nick.lower())
                ),
                None,
            )

        if found_user:
            completion = f"@{found_user}" if prefix else found_user

            self.input_message.delete(start_pos, cursor_position)
            self.input_message.insert(start_pos, completion)

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

    def _cycle_through_users(self, users, current_nick) -> str:
        try:
            current_index = users.index(current_nick)
            next_index = (current_index + 1) % len(users)
            return users[next_index]
        except ValueError:
            return next(iter(users), "")

    def _delete_till_previous_word(self, _):
        cursor_position = self.input_message.index("insert")
        text = self.input_message.get()
        if cursor_position == 0:
            return TK_BREAK

        # if the character before the cursor is a stop char just delete it
        if text[cursor_position - 1] in DELETION_STOP_CHARS:
            self.input_message.delete(cursor_position - 1, cursor_position)
            return TK_BREAK

        substring = text[:cursor_position]

        last_stop_index = -1
        for char in DELETION_STOP_CHARS:
            index = substring.rfind(char)
            if index > last_stop_index:
                last_stop_index = index

        delete_start = last_stop_index + 1

        self.input_message.delete(delete_start, cursor_position)
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
        self.irc_window.protocol(WM_DELETE_WINDOW, self.on_close)
        self.irc_window.iconbitmap(PATH / "pysaic_icon.ico")
        self.irc_window.configure(
            background=self.pysaic_config.colors.background.app
        )
        self.irc_messages_list = Text(
            self.irc_window,
            background=self.pysaic_config.colors.background.content,
            wrap="word",
        )
        self.irc_messages_list.pack(expand=True, fill="both", padx=3, pady=3)
        self.irc_messages_list.tag_config(
            "Text", foreground=self.pysaic_config.colors.content.text
        )
        self.irc_messages_list.config(
            font=(self.pysaic_config.font.name, self.pysaic_config.font.size)
        )
        self.irc_messages_list.config(state="disabled")

    def _update_fonts_on_widgets(self):
        for widget in (
            self.users_list,
            self.messages_list,
            AltFontSize(self.input_message, -1),
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

    def set_color_tags(self):
        apply_color_tags_to_text(self.messages_list, self.pysaic_config.colors)
        apply_color_tags_to_text(self.users_list, self.pysaic_config.colors)

    def update_colors(self):
        update_style(self, self.pysaic_config)
        if self._options_window:
            self._options_window.update_colors()

    def _spawn_options(self):
        self._options_window = Options(self.pysaic_config, self)
        self._options_window.main()
