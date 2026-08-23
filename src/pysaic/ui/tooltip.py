import re
from abc import ABCMeta, abstractmethod
from tkinter import TclError, Toplevel
from tkinter.ttk import Label

from pysaic.config import Config
from pysaic.entities import ChatUser
from pysaic.state import State
from pysaic.use_cases.irc_mode_to_rank import parse_and_get_highest_rank
from pysaic.use_cases.irc_mode_to_user_type import (
    USER_TYPE_MAP,
    parse_mode_to_user_friendly_name,
)

IRC_MODES_PATTERN = re.compile(
    "[" + re.escape("".join(USER_TYPE_MAP.keys())) + "]"
)


class ToolTip(metaclass=ABCMeta):
    def __init__(self, widget, state: State, pysaic_config: Config):
        self.widget = widget
        self.state = state
        self.pysaic_config = pysaic_config
        self.tip_window = None
        self.id = None
        self.text = ""

    def showtip(self, event):
        self.text = self._get_tooltip_text(event)
        if not self.text:
            self.hidetip()
            return

        if self.tip_window:
            x = event.x_root + 20
            y = event.y_root + 20
            self.tip_window.wm_geometry(f"+{x}+{y}")
            for child in self.tip_window.winfo_children():
                if isinstance(child, Label):
                    child.config(text=self.text)
                    break
            return

        x = event.x_root + 20
        y = event.y_root + 20

        self.tip_window = tw = Toplevel(self.widget)
        tw.wm_overrideredirect(True)
        tw.wm_geometry(f"+{x}+{y}")

        label = Label(
            tw,
            text=self.text,
            background=self.pysaic_config.colors.background.app,
            foreground=self.pysaic_config.colors.content.text,
            relief="solid",
            borderwidth=1,
            font=(
                self.pysaic_config.font.name,
                self.pysaic_config.font.size - 2,
            ),
        )
        label.pack(ipadx=1)

    def hidetip(self):
        tw = self.tip_window
        self.tip_window = None
        if tw:
            tw.destroy()

    @abstractmethod
    def _get_tooltip_text(self, event):
        pass


class UserListToolTip(ToolTip):
    def _get_tooltip_text(self, event):
        try:
            index = self.widget.index(f"@{event.x},{event.y}")
            line_start = self.widget.index(f"{index} linestart")
            line_end = self.widget.index(f"{index} lineend")
            line_content = self.widget.get(line_start, line_end).strip()

            username_with_modes = line_content.split(" ")[1]
            username = IRC_MODES_PATTERN.sub("", username_with_modes)

            user_info: ChatUser | None = self.state.chat_users.get(username)
            if user_info:
                tooltip_lines = [f"Nick: {username}"]
                if irc_user := user_info.irc_user:
                    if parse_and_get_highest_rank(user_info.irc_mode) >= 1:
                        tooltip_lines.insert(
                            0,
                            parse_mode_to_user_friendly_name(
                                user_info.irc_mode
                            ),
                        )
                    tooltip_lines.append(f"User: {irc_user.user}")
                    tooltip_lines.append(f"Host: {irc_user.host}")
                tooltip_lines.append(f"Location: {user_info.location.value}")
                tooltip_lines.append(f"Rank: {user_info.rank.title()}")
                tooltip_lines.append(
                    f"Reputation: {user_info.reputation.title()}"
                )
                return "\n".join(tooltip_lines)
        except TclError:
            pass
        return ""
