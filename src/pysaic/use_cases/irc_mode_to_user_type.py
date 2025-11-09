USER_TYPE_MAP = {
    "q": "admin",
    "a": "admin",
    "o": "admin",
    "h": "halfop",
    "v": "voice",
    "": "normal",
}


def get(mode: str) -> str:
    return USER_TYPE_MAP.get(mode, "normal")
