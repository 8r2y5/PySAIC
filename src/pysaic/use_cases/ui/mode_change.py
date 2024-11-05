import logging
import re
from collections import defaultdict

from pysaic.entities import IncomingEvent
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase

mode_regex = re.compile(r"([+-]\w+)")
logger = logging.getLogger(__name__)

MODE_TRANSLATOR = {"o": "@", "h": "%", "v": "+", "a": "&", "q": "*", "r": ""}
TRANSLATOR_TO_MODE = {v: k for k, v in MODE_TRANSLATOR.items()}
MODE_RANKS = {
    "": 0,
    "@": 3,
    "%": 2,
    "+": 1,
    "&": 4,
    "*": 5,
}
RANK_TO_MODE = {rank: mode for mode, rank in MODE_RANKS.items()}


SET = object()


def get_rank(modes):
    try:
        return max(
            MODE_RANKS.get(MODE_TRANSLATOR.get(mode, ""), 0) for mode in modes
        )
    except ValueError:
        return 0


class ModeChangeUseCase:
    def __init__(self, state, ui, chat_users, event: IncomingEvent):
        self.state = state
        self.ui = ui
        self.chat_users = chat_users
        self.event = event

    @classmethod
    def handle(cls, state, ui, chat_users, event):
        instance = cls(state, ui, chat_users, event)
        instance.execute()

    def execute(self):
        mode_information = mode_regex.findall(self.event.event.payload["mode"])
        nick = self.event.event.payload["nick"]
        modes = defaultdict(list)

        for mode in mode_information:
            modes_list = mode[1:]
            for single_mode in modes_list:
                if single_mode not in MODE_TRANSLATOR:
                    logger.critical("Unknown mode: %s", single_mode)
                    return

            modes[mode[0]].extend(modes_list)

        highest_rank_add = get_rank(modes.get("+", []))
        highest_rank_remove = get_rank(modes.get("-", []))
        current_rank = get_rank(
            [TRANSLATOR_TO_MODE.get(self.chat_users[nick].irc_mode)]
        )

        if current_rank == highest_rank_remove:
            highest_mode = RANK_TO_MODE[highest_rank_add]
            type_of_mode = SET

        elif current_rank > highest_rank_remove:
            highest_mode = self.chat_users[nick].irc_mode
            type_of_mode = SET

        elif highest_rank_add > highest_rank_remove:
            highest_mode = RANK_TO_MODE[highest_rank_add]
            type_of_mode = SET

        else:
            highest_mode = None
            type_of_mode = None

        if type_of_mode is SET:
            self.chat_users[nick].irc_mode = highest_mode
        else:
            self.chat_users[nick].irc_mode = ""

        UpdateUsersUseCase(self.state, self.ui).execute()
