MODE_TRANSLATOR = {
    "o": "@",  # Channel Operator, higher than admin
    "h": "%",  # Half-Operator
    "v": "+",  # Voiced
    "a": "&",  # Admin
    "q": "*",  # Channel Owner/Founder
    "r": "",
}
TRANSLATOR_TO_MODE = {v: k for k, v in MODE_TRANSLATOR.items()}
MODE_RANKS = {
    "": 0,
    "@": 4,
    "%": 2,
    "+": 1,
    "&": 3,
    "*": 5,
}
RANK_TO_MODE = {rank: mode for mode, rank in MODE_RANKS.items()}


def get_rank(modes):
    try:
        return max(
            MODE_RANKS.get(MODE_TRANSLATOR.get(mode, ""), 0) for mode in modes
        )
    except ValueError:
        return 0


def parse_and_get_highest_rank(modes: str) -> int:
    return get_rank(TRANSLATOR_TO_MODE.get(modes, 0))
