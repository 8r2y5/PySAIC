# Death/actor_killer/l04_darkvalley/ARMY/sim_default_military_1
# Death/actor_bandit/l07_military/S_ACTOR/actor # this crashes death messages
import logging
import os
import re
import xml.etree.ElementTree as ET
from copy import deepcopy
from pathlib import Path
from random import choice, randint
from typing import Union

import inject

from pysaic.entities import DeathTimestamped
from pysaic.enums import FactionsEnum
from pysaic.script_reader.entities import Death
from pysaic.settings import END_OF_ACTOR_CHARACTER, START_OF_ACTOR_CHARACTER
from pysaic.state import State

tags_regexp = re.compile(r"(\w+)")

PATH = Path(os.path.abspath(os.path.dirname(__file__)))


logger = logging.getLogger(__name__)

SENTINEL = object()


def _load_random_name_from_file(filename):
    return choice(choice(tuple(XMLFileController(filename).load()))).text


def random_name():
    return (
        f'{_load_random_name_from_file("fnames.xml")} '
        f'{_load_random_name_from_file("snames.xml")}'
    )


class XMLFileController:
    def __init__(self, file_path):
        try:
            state = inject.instance(State)
        except inject.InjectorException:
            self.file_path = PATH / file_path
        else:
            if state.is_game_running:
                self.file_path = state.game_location / "res" / file_path
            else:
                self.file_path = PATH / file_path

    def load(self):
        tree = ET.parse(self.file_path)
        root = tree.getroot()
        nodes_map = {node.tag: node for node in root.find("eng")}

        for node in nodes_map.values():
            if key := node.get("clone"):
                copy_node = deepcopy(nodes_map[key])
                copy_node.tag = node.tag
                node_to_return = copy_node
            else:
                node_to_return = node

            yield node_to_return


class DeathMessageUseCase:
    def __init__(self, nick, death: Union[Death, DeathTimestamped]):
        self.nick = nick
        self.death = death
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
            logger.error("Could not generate message: %r", death)
            raise ValueError(death)

        message = f"{message}."
        message = message[0].upper() + message[1:]
        if randint(0, 9) == 0:
            message = f"{message} {self._load_random_comment()}."

        reporter_actor = choice(
            [
                record
                for record in FactionsEnum
                if record.name != FactionsEnum.Zombie.name
            ]
        ).value
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
            for record in XMLFileController("death_formats.xml").load()
        ]

    def _load_random_saw(self):
        return choice(self._load_saw())

    def _load_levels(self):
        try:
            return self._load_by_key("death_levels.xml", self.death.location)
        except StopIteration:
            logger.warning('Could not load levels for "%r"', self.death)
            return [f"somewhere in the Zone ({self.death.location})"]

    def _load_saw(self):
        return self._load_simple("death_observances.xml")

    def _load_random_when(self):
        return choice(self._load_when())

    def _load_when(self):
        return self._load_simple("death_times.xml")

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
        return self._load_by_key("death_classes.xml", self.death.death_by)

    def _load_random_comment(self):
        return choice(self._load_simple("death_remarks.xml"))

    def _load_generic_death(self):
        return self._load_simple("death_generic.xml")

    @staticmethod
    def _load_simple(filename):
        return [record.text for record in XMLFileController(filename).load()]

    @staticmethod
    def _load_by_key(filename, key):
        logger.debug("Loading %r by key %r", filename, key)
        return [
            record.text
            for record in next(
                record
                for record in XMLFileController(filename).load()
                if record.tag == key
            )
        ]

    def _load_random_reporter(self):
        return random_name()

    def _get_crcr_actor(self, reporter_actor):
        return (
            f"{START_OF_ACTOR_CHARACTER}"
            f"{reporter_actor}"
            f"{END_OF_ACTOR_CHARACTER}"
        )


if __name__ == "__main__":
    # death = Death(
    #     user_actor="actor_killer",
    #     location="l04_darkvalley",
    #     death_by="ARMY",
    #     meta="sim_default_military_1",
    # )
    death = Death(
        user_actor="actor_bandit",
        location="l07_military",
        death_by="S_ACTOR",
        meta="actor",
    )
    print(death)
    use_case = DeathMessageUseCase("Balon", death)
    print(use_case.execute())
