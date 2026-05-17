# Death/actor_killer/l04_darkvalley/ARMY/sim_default_military_1
# Death/actor_bandit/l07_military/S_ACTOR/actor # this crashes death messages
import logging
import os
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from datetime import date
from pathlib import Path
from random import choice, randint
from typing import Union

import inject

from pysaic.entities import DeathTimestamped
from pysaic.enums import DeathReportTypeEnum, FactionsEnum, LocationEnum
from pysaic.script_reader.entities import Death
from pysaic.settings import (
    END_OF_ACTOR_CHARACTER,
    START_OF_ACTOR_CHARACTER,
    RES_PATH,
)

tags_regexp = re.compile(r"(\w+)")

PATH = Path(os.path.abspath(os.path.dirname(__file__)))

logger = logging.getLogger(__name__)

SENTINEL = object()


def _load_random_name_from_file(filename):
    return choice(
        [
            x.text
            for x in XMLFileController(filename, flat=True).load()
            if x.text and not x.text.isspace()
        ]
    )


def random_name():
    return (
        f'{_load_random_name_from_file("fnames.xml")} '
        f'{_load_random_name_from_file("snames.xml")}'
    )


class XMLFileController:
    def __init__(self, file_path, flat=False):
        self.flat = flat
        from pysaic.state import State

        try:
            state = inject.instance(State)
        except inject.InjectorException:
            self.file_path = PATH / file_path
        else:
            if state.is_game_running:
                self.file_path = RES_PATH / file_path
            else:
                self.file_path = PATH / file_path

    def load(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        eng_node = root.find("eng")
        if self.flat:
            for node in eng_node.iter():
                if node.tag != "eng":
                    yield node
            return StopIteration

        nodes_map = {
            node.tag: node for node in eng_node.iter() if node.tag != "eng"
        }

        for node in nodes_map.values():
            if key := node.get("clone"):
                copy_node = deepcopy(nodes_map[key])
                copy_node.tag = node.tag
                node_to_return = copy_node
            else:
                node_to_return = node

            yield node_to_return


def _load_faction_name(filename, faction):
    if faction in [FactionsEnum.Anonymous.value, FactionsEnum.Zombie.value]:
        logger.warning("Using default faction name for %r", faction)
        faction = FactionsEnum.Loner.value
    data = {
        node.tag: node
        for node in XMLFileController(filename).load()
        if node.tag not in ["eng", "string"]
    }
    if faction not in data:
        logger.warning(
            "Faction %r not found in faction file %r, using random faction name",
            faction,
            filename,
        )
        faction_node = choice(tuple(data.values()))
    else:
        logger.debug("Loading faction name for %s", faction)
        faction_node = data[faction]

    return choice(faction_node).text


def random_name_based_on_faction(faction):
    logger.debug("Loading faction name for %s", faction)
    return (
        f'{_load_faction_name("fnames.xml", faction)} '
        f'{_load_faction_name("snames.xml", faction)}'
    )


def load_simple(filename):
    return [
        record.text for record in XMLFileController(filename, flat=True).load()
    ]


def load_by_key(filename, key):
    logger.debug("Loading %r by key %r", filename, key)
    return [
        record.text
        for record in next(
            record
            for record in XMLFileController(filename).load()
            if record.tag == key
        )
    ]


class StringsController:
    def _load_levels(self):
        try:
            return load_by_key("death_levels.xml", self.death.location)
        except StopIteration:
            logger.warning('Could not load levels for "%r"', self.death)
            return [f"somewhere in the Zone ({self.death.location})"]

    def _load_random_reporter(self):
        if self.config.death_report_type == DeathReportTypeEnum.Faction:
            return random_name_based_on_faction(self.config.current_faction)
        elif (
            self.config.death_report_type == DeathReportTypeEnum.OnlineFactions
        ):
            return random_name_based_on_faction(
                choice(
                    [user.faction for user in self.state.chat_users.values()]
                ).value
            )
        else:
            return random_name()

    def _get_crcr_actor(self, reporter_actor):
        return (
            f"{START_OF_ACTOR_CHARACTER}"
            f"{reporter_actor}"
            f"{END_OF_ACTOR_CHARACTER}"
        )

    def _get_reporter_actor(self):
        if self.config.death_report_type == DeathReportTypeEnum.Faction:
            return self.config.current_faction.value
        elif (
            self.config.death_report_type == DeathReportTypeEnum.OnlineFactions
        ):
            return choice(
                [
                    user.faction
                    for user in self.state.chat_users.values()
                    if user.faction
                    not in (FactionsEnum.Zombie, FactionsEnum.Anonymous)
                ]
                or [FactionsEnum.Loner.value]
            ).value
        else:
            return choice(
                [
                    record
                    for record in FactionsEnum
                    if record.name
                    not in (
                        FactionsEnum.Zombie.name,
                        FactionsEnum.Anonymous.name,
                    )
                ]
            ).value


class DeathMessageUseCase(StringsController):
    def __init__(
        self, state, config, nick, death: Union[Death, DeathTimestamped]
    ):
        self.state = state
        self.nick = nick
        self.death = death
        self.config = config
        self._tags_handlers = {
            "name": lambda: nick,
            "level": self._load_random_level,
            "saw": self._load_random_saw,
            "when": self._load_random_when,
            "death": self._load_random_death,
        }

    def execute(self):
        message = " ".join(
            [
                self._tags_handlers.get(tag, SENTINEL)()
                for tag in choice(self._load_formats())
            ]
        )
        if message is SENTINEL or not message:
            logger.error(
                "Could not generate message: %r, message %r", death, message
            )
            raise ValueError(death)

        message = f"{message}."
        message = message[0].upper() + message[1:]
        if randint(0, 8) == 0:
            message = f"{message} {self._load_random_comment()}"
        if "{{day}}" in message:
            message = message.replace("{{day}}", date.today().strftime("%A"))

        reporter_actor = self._get_reporter_actor()
        return (
            f"{self._load_random_reporter()}"
            f"{self._get_crcr_actor(reporter_actor)}"
            f"{message}"
        )

    def _load_random_level(self):
        return choice(self._load_levels())

    @staticmethod
    def _parse_format(record):
        return tags_regexp.findall(record.text)

    @classmethod
    def _load_formats(cls):
        return [
            cls._parse_format(record)
            for record in XMLFileController(
                "death_formats.xml", flat=True
            ).load()
        ]

    def _load_random_saw(self):
        return choice(self._load_saw())

    def _load_saw(self):
        return load_simple("death_observances.xml")

    def _load_random_when(self):
        return choice(self._load_when())

    def _load_when(self):
        return load_simple("death_times.xml")

    def _load_random_death(self):
        if randint(0, 10) == 0:
            return choice(self._load_generic_death())
        try:
            return choice(self._load_death())
        except RuntimeError:
            logger.warning(
                "Could not load specific death, fallback to generic"
            )
            return choice(self._load_generic_death())

    def _load_death(self):
        return load_by_key("death_classes.xml", self.death.death_by)

    def _load_random_comment(self):
        return choice(load_simple("death_remarks.xml"))

    def _load_generic_death(self):
        return load_simple("death_generic.xml")


class TravelMessageUseCase(StringsController):
    def __init__(self, state, config, nick, location):
        self.state = state
        self.nick = nick
        try:
            self.location = LocationEnum[location]
        except ValueError:
            logger.warning(
                "Could not translate location %r, using default %s",
                location,
                LocationEnum.unknown.value,
            )
            self.location = LocationEnum.unknown
        self.config = config

    def execute(self) -> Union[str, None]:
        if self.location == LocationEnum.unknown:
            logger.warning(
                "Could not translate location %r, using default message",
                self.location,
            )
            return None

        i_saw = self._load_i_saw()
        location_translated = self._load_location()
        random_time = self._load_random_time()
        message = f"{i_saw} {self.nick} {random_time} {location_translated}."
        if randint(0, 8) == 0:
            message += f" {self._load_random_comment()}"

        reporter_actor = self._get_reporter_actor()
        return (
            f"{self._load_random_reporter()}"
            f"{self._get_crcr_actor(reporter_actor)}"
            f"{message}"
        )

    # def _get_crcr_actor(self, reporter_actor):
    #     return (
    #         f"{START_OF_ACTOR_CHARACTER}"
    #         f"info {reporter_actor}"
    #         f"{END_OF_ACTOR_CHARACTER}"
    #     )

    @staticmethod
    def _load_random_comment() -> str:
        return choice(
            [
                record.text
                for record in XMLFileController("travel_remarks.xml").load()
            ]
        )

    def _load_location(self) -> str:
        try:
            return choice(load_by_key("death_levels.xml", self.location.name))
        except StopIteration:
            logger.warning('Could not load levels for "%r"', self.location)
            return f"somewhere in the Zone ({self.location.value})"

    def _load_i_saw(self) -> str:
        return choice(
            [
                record.text
                for record in XMLFileController("location_remarks.xml").load()
            ]
        )

    def _load_random_time(self):
        return choice(
            (
                "is now",
                "has arrived",
                "is here",
                "has come",
                "is present",
                "is located",
                "is",
                "is situated",
                "can be found",
                "is currently",
                "is currently located",
                "is currently situated",
                "is currently found",
                "is currently present",
            )
        )


if __name__ == "__main__":
    # death = Death(
    #     user_actor="actor_killer",
    #     location="l04_darkvalley",
    #     death_by="ARMY",
    #     meta="sim_default_military_1",
    # )
    # print(random_name_based_on_faction("actor_bandit"))
    # death = Death(
    #     user_actor="actor_bandit",
    #     location="l07_military",
    #     death_by="S_ACTOR",
    #     meta="actor",
    # )
    death = Death(
        user_actor="actor_bandit",
        location="l10_limansk",
        death_by="MONOLITH",
        meta="sim_default_monolith_1",
    )
    print(death)
    config = type("Config", (), {})()
    config.death_report_type = DeathReportTypeEnum.OnlineFactions
    state = type("State", (), {})()
    state.chat_users = {
        "user2": type("User", (), {"faction": FactionsEnum.Mercenary}),
    }
    use_case = DeathMessageUseCase(state, config, "Balon", death)
    print(use_case.execute())

    travel_use_case = TravelMessageUseCase(
        state, config, "Balon", "l10_limansk"
    )
    print(travel_use_case.execute())
