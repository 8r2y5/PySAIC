from enum import StrEnum


class ModeNames(StrEnum):
    ADMIN = "op"
    HALFOP = "halfop"
    VOICE = "voice"
    NORMAL = "normal"


class UserFriendlyModeNames(StrEnum):
    ADMIN = "Operator"
    HALFOP = "Half Operator"
    VOICE = "Moderator"
    NORMAL = "User"


USER_FRIENDLY_MAP = {
    "*": UserFriendlyModeNames.ADMIN,
    "&": UserFriendlyModeNames.ADMIN,
    "@": UserFriendlyModeNames.ADMIN,
    "%": UserFriendlyModeNames.HALFOP,
    "+": UserFriendlyModeNames.VOICE,
    "": UserFriendlyModeNames.NORMAL,
}

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


def parse_mode_to_user_friendly_name(mode: str) -> str:
    return USER_FRIENDLY_MAP.get(mode, UserFriendlyModeNames.NORMAL)
