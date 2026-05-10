import logging
from tkinter import Frame, Menu
from tkinter.ttk import Notebook, Scrollbar

from pysaic.ui.hyper_links import HyperlinkManager
from pysaic.ui.utils import apply_color_tags_to_text, MessagesListText

logger = logging.getLogger(__name__)


class ChatTab(Frame):
    def __init__(self, master, config, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config = config
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=0, minsize=16)
        self.rowconfigure(0, weight=1)

        self.chat_scroll = Scrollbar(self)
        self.messages_list = MessagesListText(
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
        apply_color_tags_to_text(
            self.messages_list,
            self.config.colors,
            bold_font=not self.config.font.turn_off_bold_font_username_in_chat,
            own_above_faction=self.config.use_static_nick_color,
        )


class TabbedChat(Frame):
    def __init__(self, master, config, *args, **kwargs):
        super().__init__(master, *args, **kwargs)
        self.config = config
        self.notebook = Notebook(self)
        self.notebook.pack(fill="both", expand=True)

        self.tabs = {}
        self.add_tab("main", "Main")

        self.notebook.bind("<Button-3>", self.show_context_menu)
        self.notebook.bind("<<NotebookTabChanged>>", self._on_tab_changed)
        self.context_menu = Menu(
            self,
            tearoff=0,
            background=self.config.colors.background.app,
            foreground=self.config.colors.content.text,
        )
        self.context_menu.add_command(
            label="Close Tab", command=self.close_current_tab
        )

    def add_tab(self, tab_id, title, is_app_tab=False):
        if tab_id in self.tabs:
            return self.tabs[tab_id]["widget"]

        tab = ChatTab(self.notebook, self.config)
        self.notebook.add(tab, text=title)
        self.tabs[tab_id] = {
            "widget": tab,
            "is_app_tab": is_app_tab,
            "original_title": title,
            "has_unread_messages": False,
        }
        self._update_tab_style(tab_id)
        return tab

    def get_tab(self, tab_id):
        tab_info = self.tabs.get(tab_id)
        return tab_info["widget"] if tab_info else None

    def get_current_tab_id(self):
        current_tab_widget = self.notebook.nametowidget(self.notebook.select())
        for tab_id, tab_info in self.tabs.items():
            if tab_info["widget"] == current_tab_widget:
                return tab_id
        return "main"

    def close_tab(self, tab_id):
        if tab_id == "main":
            return  # Cannot close main tab

        if tab_id in self.tabs:
            self.notebook.forget(self.tabs[tab_id]["widget"])
            del self.tabs[tab_id]
            self._on_tab_changed()

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

    def notify_new_message(self, tab_id):
        if tab_id not in self.tabs:
            return

        current_selected_tab_widget = self.notebook.nametowidget(
            self.notebook.select()
        )
        tab_info = self.tabs[tab_id]

        if tab_info["widget"] != current_selected_tab_widget:
            tab_info["has_unread_messages"] = True
            self._update_tab_style(tab_id)

    def _on_tab_changed(self, event=None):
        selected_tab_id = self.get_current_tab_id()
        if selected_tab_id in self.tabs:
            self.tabs[selected_tab_id]["has_unread_messages"] = False

        for tab_id in self.tabs:
            self._update_tab_style(tab_id)

    def _update_tab_style(self, tab_id):
        tab_info = self.tabs.get(tab_id)
        if not tab_info:
            return

        tab_widget = tab_info["widget"]
        original_title = tab_info["original_title"]
        has_unread_messages = tab_info["has_unread_messages"]
        is_app_tab = tab_info["is_app_tab"]
        current_selected_tab_widget = self.notebook.nametowidget(
            self.notebook.select()
        )

        if (
            is_app_tab
            and has_unread_messages
            and tab_widget != current_selected_tab_widget
        ):
            self.notebook.tab(tab_widget, text=f"🔴 {original_title}")
        else:
            self.notebook.tab(tab_widget, text=original_title)

    def update_styles(self):
        for tab_info in self.tabs.values():
            tab_info["widget"].apply_styles()
        self._on_tab_changed()
