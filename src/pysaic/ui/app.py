import logging
import os
import re
from pathlib import Path
from asyncio import Queue
from functools import partial
from tkinter import Button, Entry, Frame, OptionMenu, StringVar, Text, Tk
from tkinter.font import Font
from tkinter.ttk import Scrollbar, Style

from pysaic.entities import IncomingEvent, AppEvent
from pysaic.enums import FactionsEnum, AppEventEnum
from pysaic.settings import APP_IDENTITY
from pysaic.ui.options import Options

logger = logging.getLogger(__name__)

WIDTH = 1080
HEIGHT = 550

MIN_WIDTH = 400
MIN_HEIGHT = 300

BACKGROUND_COLOR = "gray30"
TK_BREAK = "break"

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


class App(Tk):
    def __init__(
        self,
        state,
        config,
        incoming_queue: Queue,
        outgoing_queue: Queue,
    ):
        super().__init__()
        style = Style()
        style.theme_use("clam")
        style.configure(
            "TScrollbar",
            gripcount=0,
            background=BACKGROUND_COLOR,
            darkcolor="gray20",
            lightcolor="gray40",
            troughcolor="dim gray",
            bordercolor=BACKGROUND_COLOR,
            arrowcolor="floral white",
            foreground="red",
            arrowsize=15,
            disabledcolor=BACKGROUND_COLOR,
            activebackground="red",
            relief="flat",
            deactivebackground="red",
        )
        style.configure(
            "TScrollbar.slider.lightcolor",
            background="deep sky blue",
            bordercolor="red",
            troughcolor="green",
            lightcolor="blue",
            darkcolor="red",
            arrowcolor="red",
            arrowsize="red",
            gripcount=5,
        )
        style.configure(
            "TScrollbar.thumb.arrowcolor",
            background="deep sky blue",
            # 'sliderlength'
        )
        self.pysaic_config = config
        self.pysaic_state = state
        self.title(APP_IDENTITY)
        self.geometry(f"{WIDTH}x{HEIGHT}")
        self.minsize(MIN_WIDTH + 210, MIN_HEIGHT + 32)
        # self.resizable(False, False)
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        self.incoming_queue = incoming_queue
        self.outgoing_queue = outgoing_queue
        self.create_widgets()
        # self.after(250, self.process_incoming_events)
        self.iconbitmap(PATH / "crcr_icon_new.ico")
        self.disable_input()

    def on_close(self):
        self.destroy()
        self.outgoing_queue.put_nowait(None)
        self.incoming_queue.put_nowait(None)

    def create_widgets(self):
        self.configure(background=BACKGROUND_COLOR)
        self.main_frame = Frame(self, background=BACKGROUND_COLOR)
        self.main_frame.pack(expand=True, fill="both")

        self._configure_grid()
        self._prepare_left_frame()
        self._prepare_right_frame()
        self._prepare_bottom_frame()

        self.users_list.config(font=("Microsoft Sans Serif", 11))
        self.messages_list.config(font=("Microsoft Sans Serif", 11))
        self.set_color_tags()

    def disable_input(self):
        self.channels_dropbox.config(state="disabled")
        self.input_message.config(state="disabled")
        self.send_button.config(state="disabled")

    def enable_input(self):
        self.channels_dropbox.config(state="normal")
        self.input_message.config(state="normal")
        self.send_button.config(state="normal")

    def _prepare_left_frame(self):
        left_frame = Frame(
            self.main_frame, padx=3, pady=3, background=BACKGROUND_COLOR
        )
        left_frame.grid(row=0, column=0, sticky="nsew")
        left_frame.columnconfigure(0, weight=1)
        left_frame.columnconfigure(1, weight=0, minsize=16)
        left_frame.rowconfigure(0, weight=1)

        chat_scroll = Scrollbar(left_frame)
        self.messages_list = Text(
            left_frame, yscrollcommand=chat_scroll.set, background="gray40"
        )
        self.messages_list.grid(row=0, column=0, sticky="nsew")
        chat_scroll.config(command=self.messages_list.yview)
        chat_scroll.grid(row=0, column=1, sticky="ns")

    def _prepare_right_frame(self):
        right_frame = Frame(
            self.main_frame, padx=3, pady=3, background=BACKGROUND_COLOR
        )
        right_frame.grid(row=0, column=1, sticky="nsew")
        right_top_frame = Frame(right_frame, background=BACKGROUND_COLOR)
        right_top_frame.pack(fill="x")
        right_bottom_frame = Frame(right_frame, background=BACKGROUND_COLOR)
        right_bottom_frame.pack(fill="both", expand=True)

        channels_and_option_section = Frame(
            right_top_frame, background=BACKGROUND_COLOR
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
            bg=BACKGROUND_COLOR,
            fg="ghost white",
            activebackground=BACKGROUND_COLOR,
            activeforeground="ghost white",
        )
        self.channels_dropbox["menu"].config(
            bg=BACKGROUND_COLOR,
            fg="ghost white",
            activebackground="dim gray",
            activeforeground="black",
        )
        self.channels_dropbox.grid(row=0, column=0, sticky="ew")

        options_button = Button(
            channels_and_option_section,
            text="Options",
            command=lambda: Options(self.pysaic_config, self).main(),
            background=BACKGROUND_COLOR,
            foreground="ghost white",
            width=10,
        )
        options_button.grid(row=0, column=1, sticky="ew")

        channels_and_option_section.pack(side="left", fill="x")

        self.users_list_scroll = Scrollbar(
            right_bottom_frame,
        )
        self.users_list = Text(
            right_bottom_frame,
            yscrollcommand=self.users_list_scroll.set,
            width=22,
            background="gray40",
        )
        self.users_list.pack(side="left", expand=True, fill="both")
        self.users_list_scroll.config(command=self.users_list.yview)
        self.users_list_scroll.pack(side="left", fill="y")

    def _prepare_bottom_frame(self):
        self.bottom_frame = Frame(self.main_frame, background=BACKGROUND_COLOR)
        self.bottom_frame.grid(row=1, column=0, columnspan=2, sticky="nsew")
        self.input_message = Entry(
            self.bottom_frame,
            background="gray40",
            foreground="ghost white",
            disabledbackground="gray30",
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
            foreground="ghost white",
            background=BACKGROUND_COLOR,
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

    def _nick_auto_complete(self, _event):
        self.input_message.focus_set()
        cursor_position = self.input_message.index("insert")
        text = self.input_message.get()
        result = re.search("[@]\w+", text[:cursor_position])
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

        users = self.pysaic_state.chat_users.keys()
        if characters in users:
            found_user = self._cycle_through_users(users, characters)
        else:
            found_user = next(
                (user for user in users if user.startswith(characters)), []
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
        content = input_entry.get()
        if not content:
            return

        if content.startswith("/"):
            self.incoming_queue.put_nowait(
                IncomingEvent(
                    author="",
                    target="",
                    event=AppEvent(
                        what=AppEventEnum.COMMAND, payload=content[1:]
                    ),
                )
            )
        else:
            self.incoming_queue.put_nowait(
                IncomingEvent(
                    author="",
                    target="",
                    event=AppEvent(
                        what=AppEventEnum.OUR_MESSAGE, payload=content
                    ),
                )
            )

        input_entry.delete(0, "end")

    def update(self):
        # UpdateUsersUseCase(self).execute()
        return super().update()

    def set_color_tags(self):
        # TODO: Load values from config
        for widget in (self.messages_list, self.users_list):
            bold_font = Font(widget, widget.cget("font"))
            bold_font.configure(weight="bold")
            widget.tag_config("Time", foreground="floral white")
            widget.tag_config("Text", foreground="ghost white")
            widget.tag_config("Highlight", background="gray50")
            widget.tag_config("Information", foreground="lightblue")
            widget.tag_config("Error", foreground="red3")
            widget.tag_config(
                FactionsEnum.Clear_Sky.name,
                foreground="deep sky blue",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Loner.name,
                foreground="light goldenrod",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Ecologist.name,
                foreground="darkorange",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Bandit.name, foreground="sienna3", font=bold_font
            )
            widget.tag_config(
                FactionsEnum.Monolith.name,
                foreground="DarkOrchid3",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Duty.name, foreground="firebrick1", font=bold_font
            )
            widget.tag_config(
                FactionsEnum.Freedom.name,
                foreground="spring green",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Mercenary.name,
                foreground="dodgerblue",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Military.name,
                foreground="PaleGreen3",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Renegade.name,
                foreground="green yellow",
                font=bold_font,
            )
            widget.tag_config(
                FactionsEnum.Zombie.name, foreground="black", font=bold_font
            )
            widget.tag_config(
                FactionsEnum.Anonymous.name, foreground="black", font=bold_font
            )
            widget.tag_config(
                FactionsEnum.UNISG.name, foreground="salmon", font=bold_font
            )
            widget.tag_config(
                FactionsEnum.SIN.name, foreground="maroon4", font=bold_font
            )
            widget.tag_config("DM", foreground="hot pink", font=bold_font)
            widget.tag_config("online", foreground="green", font=bold_font)
            widget.tag_config("offline", foreground="red", font=bold_font)

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
