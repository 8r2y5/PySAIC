import logging
import re
from contextlib import contextmanager
from tkinter import DISABLED, END, NORMAL, Text
from unicodedata import normalize

from pysaic.ui.hyper_links import HyperlinkManager

color_regex = re.compile(r"(%c\[[\w,]+\])")
URL_REGEXP = re.compile(
    "(?:https?://)[-a-zA-Z0-9@:%._\\+~#=]{1,256}\\.[a-zA-Z0-9()]{1,6}\\b(?:[-a-zA-Z0-9()@:%_\\+.~#?&\\/=]*)"
)
logger = logging.getLogger(__name__)


@contextmanager
def enable_disable(widget, *, tail=True):
    widget.config(state=NORMAL)
    if widget.get("1.0", "end-1c") != "":
        widget.insert(END, "\n")
    widget.tag_remove("Highlight", "end-1c", "end")
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
    ).lstrip("\n")


def add_content_of_message_to_messages_list(
    messages_list: Text,
    hyperlinks: HyperlinkManager,
    content: str,
    tags: list[str],
):
    content = content.lstrip("\n")
    split_content = content.split(" ")
    count = len(split_content)
    for index, part in enumerate(split_content, start=1):
        url = URL_REGEXP.search(part)
        if url:
            before, after = URL_REGEXP.split(part, maxsplit=1)
            messages_list.insert(END, f"{before}", tags)
            messages_list.insert(
                END, url[0], tags + hyperlinks.prepare_tags(url[0])
            )
            messages_list.insert(END, f"{after}", tags)
        else:
            messages_list.insert(END, part, tags)

        if index < count:
            messages_list.insert(END, " ", tags)
