import logging
from tkinter import Frame, Text, Menu
from tkinter.ttk import Notebook, Scrollbar

from pysaic.ui.hyper_links import HyperlinkManager
from pysaic.ui.utils import apply_color_tags_to_text

logger = logging.getLogger(__name__)


class ChatTab(Frame):
    def __init__(self, master, config, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config = config
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=16)
        self.rowconfigure(0, weight=1)

        self.chat_scroll = Scrollbar(self)
        self.messages_list = Text(
            self,
            yscrollcommand=self.chat_scroll.set,
            background=self.config.colors.background.content,
            wrap="word",
        )
        self.messages_list.grid(row=0, column=0, sticky="nsew")
        self.chat_scroll.config(command=self.messages_list.yview)
        self.chat_scroll.grid(row=0, column=1, sticky="ns")
        self.messages_list.list_scroll = self.chat_scroll
        self.hyperlinks = HyperlinkManager(self.messages_list)

        self.apply_styles()

    def apply_styles(self):
        self.messages_list.configure(
            background=self.config.colors.background.content,
            font=(self.config.font.name, self.config.font.size),
        )
        apply_color_tags_to_text(self.messages_list, self.config)


class TabbedChat(Frame):
    def __init__(self, master, config, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config = config
        self.notebook = Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.tabs = {}
        self.add_tab("main", "Main")

        self.notebook.bind("<Button-3>", self.show_context_menu)
        self.context_menu = Menu(
            self,
            tearoff=0,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
        )
        self.context_menu.add_command(
            label="Close Tab", command=self.close_current_tab
        )

    def add_tab(self, tab_id, title):
        if tab_id in self.tabs:
            return self.tabs[tab_id]

        tab = ChatTab(self.notebook, self.config)
        self.notebook.add(tab, text=title)
        self.tabs[tab_id] = tab
        return tab

    def get_tab(self, tab_id):
        return self.tabs.get(tab_id)

    def get_current_tab_id(self):
        current_tab_widget = self.notebook.nametowidget(self.notebook.select())
        for tab_id, tab in self.tabs.items():
            if tab == current_tab_widget:
                return tab_id
        return "main"

    def close_tab(self, tab_id):
        if tab_id == "main":
            return  # Cannot close main tab

        if tab_id in self.tabs:
            self.notebook.forget(self.tabs[tab_id])
            del self.tabs[tab_id]

    def show_context_menu(self, event):
        try:
            index = self.notebook.index(f"@{event.x},{event.y}")
            self.notebook.select(index)
            tab_id = self.get_current_tab_id()
            if tab_id != "main":
                self.context_menu.post(event.x_root, event.y_root)
        except Exception:
            pass

    def close_current_tab(self):
        tab_id = self.get_current_tab_id()
        self.close_tab(tab_id)

    def update_styles(self):
        for tab in self.tabs.values():
            tab.apply_styles()
