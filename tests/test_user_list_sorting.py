import unittest
from unittest.mock import Mock

# Assuming pysaic.entities and pysaic.enums are accessible
from pysaic.entities import ChatUser
from pysaic.enums import FactionsEnum, SAICStateEnum
from pysaic.controllers.ui.user_list import (
    GroupByFactionWithCounter,
)


class TestGroupByFactionWithCounterSorting(unittest.TestCase):
    maxDiff = None

    def test_sort_by_online_status_within_faction(self):
        # Mock ChatUser objects
        online_user_a = ChatUser(
            name="Alice",
            faction=FactionsEnum.Loner,
            in_game=True,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        offline_user_b = ChatUser(
            name="Bob",
            faction=FactionsEnum.Loner,
            in_game=False,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        online_user_c = ChatUser(
            name="Charlie",
            faction=FactionsEnum.Loner,
            in_game=True,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        offline_user_d = ChatUser(
            name="David",
            faction=FactionsEnum.Loner,
            in_game=False,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )

        # Users dictionary for GroupByFactionWithCounter
        users = {
            "Alice": online_user_a,
            "Bob": offline_user_b,
            "Charlie": online_user_c,
            "David": offline_user_d,
        }

        # Mock config and users_list (not directly used by sort_by, but needed for constructor)
        mock_config = Mock()
        mock_users_list = Mock()

        sorter = GroupByFactionWithCounter(mock_config, mock_users_list, users)

        # Create a list of users to be sorted
        unsorted_users = [
            offline_user_b,
            online_user_a,
            offline_user_d,
            online_user_c,
        ]

        # Sort the users using the sort_by method
        # The key function returns a tuple, and Python sorts tuples lexicographically
        sorted_users = sorted(unsorted_users, key=sorter.sort_by)

        # Expected order: Online users first, then alphabetical by name
        # Within Loner: Alice (online), Charlie (online), Bob (offline), David (offline)
        expected_order = [
            online_user_a,
            online_user_c,
            offline_user_b,
            offline_user_d,
        ]

        self.assertEqual(sorted_users, expected_order)

    def test_sort_by_faction_size_and_anonymous(self):
        # Mock ChatUser objects for different factions and states
        Alice_user = ChatUser(
            name="Alice",
            faction=FactionsEnum.Loner,
            in_game=True,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        Bob_user = ChatUser(
            name="Bob",
            faction=FactionsEnum.Renegade,
            in_game=False,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        Charlie_user = ChatUser(
            name="Charlie",
            faction=FactionsEnum.Loner,
            in_game=False,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        Zoe_user = ChatUser(
            name="Zoe",
            faction=FactionsEnum.Anonymous,
            in_game=True,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        David_user = ChatUser(
            name="David",
            faction=FactionsEnum.Renegade,
            in_game=True,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )
        Yara_user = ChatUser(
            name="Yara",
            faction=FactionsEnum.Anonymous,
            in_game=False,
            afk=False,
            state=SAICStateEnum.ok,
            irc_mode="",
        )

        users = {
            "Alice": Alice_user,
            "Bob": Bob_user,
            "Charlie": Charlie_user,
            "Zoe": Zoe_user,
            "David": David_user,
            "Yara": Yara_user,
        }

        # Mock config and users_list
        mock_config = Mock()
        mock_users_list = Mock()

        sorter = GroupByFactionWithCounter(mock_config, mock_users_list, users)

        unsorted_users = [
            Alice_user,
            Bob_user,
            Charlie_user,
            Zoe_user,
            David_user,
            Yara_user,
        ]

        sorted_users = sorted(unsorted_users, key=sorter.sort_by)

        # All factions have size 2 in this test, so faction size is not a differentiator.
        # Sorting order:
        # 1. Anonymous last
        # 2. Online first
        # 3. Faction name (alphabetical by value: 'actor_renegade' < 'actor_stalker')
        # 4. Nickname alphabetical

        expected_order = [
            Alice_user,
            David_user,
            Charlie_user,
            Bob_user,
            Zoe_user,
            Yara_user,
        ]

        self.assertEqual(sorted_users, expected_order)


if __name__ == "__main__":
    unittest.main()
