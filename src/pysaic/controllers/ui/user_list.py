import logging
from collections import Counter
from tkinter import END

from pysaic.entities import ChatUser
from pysaic.enums import FactionsEnum, SAICStateEnum, UserListDisplayModeEnum

ONLINE_ICON = "●"
OFFLINE_ICON = "○"
AFK_ICON = "●"
SURGE_ICON = "⚡"
UNDERGROUND_ICON = "⊝"

logger = logging.getLogger(__name__)


def get_faction_tag(faction):
    return faction.name if faction else FactionsEnum.Anonymous.name


class SortedMixin:
    def __init__(self, config, users_list, users):
        self.config = config
        self.users_list = users_list
        self.users = users
        self.new_line = ""

    def _add_user(self, chat_user):
        tag, icon = (
            ("online", ONLINE_ICON)
            if chat_user.in_game
            else ("offline", OFFLINE_ICON)
        )
        if chat_user.afk:
            tag = "afk"
            icon = AFK_ICON
        if chat_user.state != SAICStateEnum.ok and chat_user.in_game:
            # tag = chat_user.state.name
            icon = (
                SURGE_ICON
                if chat_user.state == SAICStateEnum.emission
                else UNDERGROUND_ICON
            )
        # logger.debug("Adding user: %r (%r)", chat_user, tag)
        faction_tag = get_faction_tag(chat_user.faction)
        self.users_list.insert(END, f"{self.new_line} {icon} ", tag)
        prefix = (
            chat_user.irc_mode if self.config.enable_irc_user_display else ""
        )
        self.users_list.insert(
            END,
            f"{prefix}{chat_user.name}",
            faction_tag,
        )
        self.new_line = "\n"


class NamesInAlphabeticalOrder(SortedMixin):
    @property
    def sorted_users(self):
        return sorted(
            self.users.values(), key=lambda chat_user: chat_user.name.lower()
        )

    def write(self):
        for chat_user in self.sorted_users:
            self._add_user(chat_user)


class OnlineFirstInAlphabeticalOrder(NamesInAlphabeticalOrder):
    @property
    def sorted_users(self):
        return sorted(
            self.users.values(),
            key=lambda chat_user: (
                not chat_user.in_game,
                chat_user.name.lower(),
            ),
        )


class NamesInReverseAlphabeticalOrder(NamesInAlphabeticalOrder):
    @property
    def sorted_users(self):
        return sorted(
            self.users.values(),
            key=lambda chat_user: chat_user.name.lower(),
            reverse=True,
        )


class GroupByFactionAndName(SortedMixin):
    def sort_by(self, chat_user: ChatUser):
        faction = get_faction_tag(chat_user.faction)
        return (
            get_faction_tag(chat_user.faction),
            1 if faction == FactionsEnum.Anonymous.name else 0,
            chat_user.name.lower(),
        )

    def write(self):
        for chat_user in sorted(self.users.values(), key=self.sort_by):
            self._add_user(chat_user)


class GroupByFactionWithCounter(SortedMixin):
    def __init__(self, config, users_list, users):
        super().__init__(config, users_list, users)
        self.counter = Counter(
            [chat_user.faction for chat_user in self.users.values()]
        )
        # we need to override _add_user section will be first item
        self.new_line = "\n"

    def sort_by(self, chat_user: ChatUser):
        faction = get_faction_tag(chat_user.faction)
        return (
            -(self.counter[chat_user.faction] if chat_user.faction else 0),
            1 if faction == FactionsEnum.Anonymous.name else 0,
            faction,
            -int(chat_user.in_game),
            chat_user.name.lower(),
        )

    def write(self):
        last_group = None
        section_new_line = ""
        users_sorted = sorted(
            self.users.values(), key=self.sort_by, reverse=False
        )
        for chat_user in users_sorted:
            faction_tag = get_faction_tag(chat_user.faction)
            if last_group != faction_tag:
                display_tag = faction_tag.replace("_", " ")
                self.users_list.insert(
                    END, f"{section_new_line}{display_tag}", faction_tag
                )
                self.users_list.insert(
                    END, f" ({self.counter[chat_user.faction]})", "Text"
                )
                last_group = faction_tag
                section_new_line = "\n"

            self._add_user(chat_user)


DISPLAY_MODES_MAP = {
    UserListDisplayModeEnum.NamesInAlphabeticalOrder: NamesInAlphabeticalOrder,
    UserListDisplayModeEnum.NamesInReverseAlphabeticalOrder: (
        NamesInReverseAlphabeticalOrder
    ),
    UserListDisplayModeEnum.OnlineFirstInAlphabeticalOrder: (
        OnlineFirstInAlphabeticalOrder
    ),
    UserListDisplayModeEnum.GroupByFactionAndName: GroupByFactionAndName,
    UserListDisplayModeEnum.GroupByFactionWithCounter: (
        GroupByFactionWithCounter
    ),
}
