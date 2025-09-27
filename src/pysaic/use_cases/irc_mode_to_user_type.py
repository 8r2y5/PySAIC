from enum import StrEnum


class ModeNames(StrEnum):
    ADMIN = "op"
    HALFOP = "halfop"
    VOICE = "voice"
    NORMAL = "normal"


USER_TYPE_MAP = {
    "*": ModeNames.ADMIN,
    "&": ModeNames.ADMIN,
    "@": ModeNames.ADMIN,
    "%": ModeNames.HALFOP,
    "+": ModeNames.VOICE,
    "": ModeNames.NORMAL,
}


def parsed_mode_to_name(mode: str) -> str:
    return USER_TYPE_MAP.get(mode, ModeNames.NORMAL)
