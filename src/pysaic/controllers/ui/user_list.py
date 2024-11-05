from collections import Counter
from tkinter import END

from pysaic.entities import ChatUser
from pysaic.enums import FactionsEnum

ONLINE_ICON = "⦿"
OFFLINE_ICON = "⦾"


def get_faction_tag(faction):
    return faction.name if faction else FactionsEnum.Anonymous.name


class SortedMixin:
    def _add_user(self, chat_user):
        icon = ONLINE_ICON if chat_user.in_game else OFFLINE_ICON
        tag = "online" if chat_user.in_game else "offline"
        faction_tag = get_faction_tag(chat_user.faction)
        self.users_list.insert(END, f" {icon} ", tag)
        self.users_list.insert(
            END, f"{chat_user.irc_mode}{chat_user.name}\n", faction_tag
        )


class NamesInAlphabeticalOrder(SortedMixin):
    name = "Names in alphabetical order"

    @property
    def sorted_users(self):
        return sorted(
            self.users.values(), key=lambda chat_user: chat_user.name
        )

    def __init__(self, users_list, users):
        self.users_list = users_list
        self.users = users

    def write(self):
        for chat_user in self.sorted_users:
            self._add_user(chat_user)


class OnlineFirstInAlphabeticalOrder(NamesInAlphabeticalOrder):
    name = "Online first in alphabetical order"

    @property
    def sorted_users(self):
        return sorted(
            self.users.values(),
            key=lambda chat_user: (not chat_user.in_game, chat_user.name),
        )


class NamesInReverseAlphabeticalOrder(NamesInAlphabeticalOrder):
    name = "Names in reverse alphabetical order"

    @property
    def sorted_users(self):
        return sorted(
            self.users.values(),
            key=lambda chat_user: chat_user.name,
            reverse=True,
        )


class GroupByFactionAndName(SortedMixin):
    name = "Group by faction and name"

    def __init__(self, users_list, users):
        self.users_list = users_list
        self.users = users

    def sort_by(self, chat_user: ChatUser):
        return get_faction_tag(chat_user.faction), chat_user.name

    def write(self):
        for chat_user in sorted(self.users.values(), key=self.sort_by):
            self._add_user(chat_user)


class GroupByFactionWithCounter(SortedMixin):
    name = "Group by faction with counter"

    def __init__(self, users_list, users):
        self.users_list = users_list
        self.users = users
        self.counter = Counter(
            [chat_user.faction for chat_user in self.users.values()]
        )

    def sort_by(self, chat_user: ChatUser):
        return (
            self.counter[chat_user.faction] if chat_user.faction else 0,
            get_faction_tag(chat_user.faction),
            int(chat_user.in_game),
            chat_user.name,
        )

    def write(self):
        last_group = None
        users_sorted = sorted(
            self.users.values(), key=self.sort_by, reverse=True
        )
        for chat_user in users_sorted:
            faction_tag = get_faction_tag(chat_user.faction)
            # logger.info("Adding user: %r (%r)", chat_user, faction_tag)
            if last_group != faction_tag:
                self.users_list.insert(END, f"{faction_tag}", faction_tag)
                self.users_list.insert(
                    END, f" ({self.counter[chat_user.faction]})\n"
                )
                last_group = faction_tag

            self._add_user(chat_user)


DISPLAY_MODES_MAP = {
    NamesInAlphabeticalOrder.name: NamesInAlphabeticalOrder,
    NamesInReverseAlphabeticalOrder.name: NamesInReverseAlphabeticalOrder,
    OnlineFirstInAlphabeticalOrder.name: OnlineFirstInAlphabeticalOrder,
    GroupByFactionAndName.name: GroupByFactionAndName,
    GroupByFactionWithCounter.name: GroupByFactionWithCounter,
}
