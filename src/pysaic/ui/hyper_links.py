"""
based on https://github.com/kaixxx/noScribe/blob/main/tkHyperlinkManager.py
"""

import logging
import webbrowser
from functools import partial
from tkinter import CURRENT, Text

logger = logging.getLogger(__name__)


class HyperlinkManager:
    def __init__(self, text: Text):
        self.text = text
        self.links = {}
        self.text.tag_bind("hyper", "<Enter>", self._enter)
        self.text.tag_bind("hyper", "<Leave>", self._leave)
        self.text.tag_bind("hyper", "<Double-Button-1>", self._click)

    def prepare_tags(self, url: str) -> list[str]:
        tag = f"hyper-{len(self.links)}"
        logger.debug("Creating hyperlink tag: %s for URL: %s", tag, url)
        self.links[tag] = partial(webbrowser.open, url)
        return ["hyper", tag]

    def _enter(self, _event):
        self.text.config(cursor="hand2")

    def _leave(self, _event):
        self.text.config(cursor="")

    def _click(self, _event):
        for tag in self.text.tag_names(CURRENT):
            if tag[:6] == "hyper-":
                logger.debug("Opening link: %s, %s", tag, self.links[tag])
                self.links[tag]()
                return
