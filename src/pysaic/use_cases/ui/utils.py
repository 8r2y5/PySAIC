import logging
import re
from contextlib import contextmanager
from tkinter import DISABLED, END, NORMAL, Text
from unicodedata import normalize

from pysaic.ui.hyper_links import HyperlinkManager

color_regex = re.compile(r"(%c\[[\w,]+\])")
logger = logging.getLogger(__name__)


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


def add_content_of_message_to_messages_list(
    messages_list: Text,
    hyperlinks: HyperlinkManager,
    content: str,
    tags: list[str],
):
    content = content.rstrip("\n").split(" ")
    segments = len(content) - 1

    for index, value in enumerate(content):
        if value.startswith("http"):
            logger.debug("Adding hyperlink: %s", value)
            messages_list.insert(
                END, value, tags + hyperlinks.prepare_tags(value)
            )
        else:
            messages_list.insert(END, value, tags)

        if index < segments:
            messages_list.insert(END, " ", tags)

    messages_list.insert(END, "\n", tags)
