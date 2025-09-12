import logging
import math
import random
import re
from typing import Optional

from pysaic.constants import crcr_factions, pysaic_factions
from pysaic.enums import FactionsEnum

logger = logging.getLogger(__name__)
ICON_REGEXP = re.compile(
    r"^(?P<icon_type>crc_icon|pysaic_icon)_"
    r"(?P<actor>actor_\w+)_"
    r"(?P<icon_id>\d+)$"
)


def calculate_icon_based_on_faction_and_name(faction, nick):
    old_random = random.random()
    seed = sum([ord(char) for char in nick])
    seed /= len(nick)
    seed = math.floor(seed - math.floor(seed))
    random.seed(seed)
    count = crcr_factions.get(faction)
    if count:
        index = random.randint(
            1, crcr_factions[faction] + pysaic_factions[faction] + 1
        )
        if index <= crcr_factions[faction]:
            avatar_id = f"crc_icon_{faction}_{index}"
        else:
            index -= crcr_factions[faction]
            avatar_id = f"pysaic_icon_{faction}_{index}"
    else:
        logger.warning(
            "Faction %r is not defined in crcr_factions, using default avatar.",
            faction,
        )
        avatar_id = "crc_icon_unknown"
    random.seed(old_random)

    return avatar_id


def parse_icon_id(
    avatar_id: str,
) -> tuple[Optional[str], Optional[str], Optional[int], bool]:
    icon_match = ICON_REGEXP.match(avatar_id)
    if not icon_match:
        logger.warning(
            "Current avatar %r does not match expected format.",
            avatar_id,
        )
        return None, None, None, False
    icon_type = icon_match.group("icon_type")
    static_faction_value = icon_match.group("actor")
    icon_id = int(icon_match.group("icon_id"))
    avatar_number = (
        icon_id + crcr_factions[static_faction_value]
        if icon_type == "pysaic_icon"
        else icon_id
    )
    logger.debug(
        "Parsed icon_id %r: type=%r, faction=%r, number=%d",
        avatar_id,
        icon_type,
        static_faction_value,
        avatar_number,
    )
    if avatar_number < 1:
        if icon_type == "crc_icon" and avatar_number > (
            crcr_factions.get(static_faction_value) or 0
        ):
            logger.warning(
                "Current crc avatar %r is out of range for faction %r, using default values",
                avatar_id,
                static_faction_value,
            )
            return icon_type, static_faction_value, avatar_number, False
        if icon_type == "pysaic_icon" and avatar_number > (
            pysaic_factions.get(static_faction_value) or 0
        ):
            logger.warning(
                "Current pysaic avatar %r is out of range for faction %r, using default values",
                avatar_id,
                static_faction_value,
            )
            icon_type = "crc_icon"
            static_faction_value = FactionsEnum.Loner.value
            avatar_number = 1
            return icon_type, static_faction_value, avatar_number, False
    return icon_type, static_faction_value, avatar_number, True


def is_icon_valid(avatar_id: str) -> bool:
    icon_type, static_faction_value, avatar_number, valid = parse_icon_id(
        avatar_id
    )
    if not valid:
        logger.warning(
            "Current avatar %r is invalid or out of range for faction %r.",
            avatar_id,
            static_faction_value,
        )
    return valid


def get_valid_icon_from_icon_id(avatar_id: str) -> tuple[str, str, int]:
    icon_type, static_faction_value, avatar_number, valid = parse_icon_id(
        avatar_id
    )
    if not valid:
        logger.warning(
            "Current avatar %r is out of range for faction %r, using default values",
            avatar_id,
            static_faction_value,
        )
        icon_type = "crc_icon"
        static_faction_value = FactionsEnum.Loner.value
        avatar_number = 1
    return icon_type, static_faction_value, avatar_number
