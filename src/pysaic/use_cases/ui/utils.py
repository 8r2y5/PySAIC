import re
from contextlib import contextmanager
from tkinter import DISABLED, END, NORMAL
from unicodedata import normalize


color_regex = re.compile(r"(%c\[[\w,]+\])")


@contextmanager
def enable_disable(widget, *, tail=True):
    widget.config(state=NORMAL)
    yield
    if tail is True:
        widget.see(END)
    widget.config(state=DISABLED)


def get_faction_actor(author_chat_user):
    return author_chat_user.faction.value


def prepare_date(event):
    return event.created_at.strftime("%H:%M:%S")


def normalize_content(content):
    return color_regex.sub(
        "",
        normalize("NFKD", content).encode("ascii", "replace").decode("ascii"),
    )
