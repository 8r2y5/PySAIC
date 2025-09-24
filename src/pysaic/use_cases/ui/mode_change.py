import logging
import re
from collections import defaultdict

from pysaic.controllers.game import add_users_list_to_game
from pysaic.entities import IncomingEvent
from pysaic.state import State
from pysaic.use_cases.ui.update_users import UpdateUsersUseCase

mode_regex = re.compile(r"([+-]\w+)")
logger = logging.getLogger(__name__)

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


SET = object()


def get_rank(modes):
    try:
        return max(
            MODE_RANKS.get(MODE_TRANSLATOR.get(mode, ""), 0) for mode in modes
        )
    except ValueError:
        return 0


class ModeChangeUseCase:
    def __init__(self, state: State, ui, chat_users, event: IncomingEvent):
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

        highest_mode, type_of_mode = self._get_highest_mode_and_type(
            current_rank, highest_rank_remove, highest_rank_add, nick
        )

        if type_of_mode is SET:
            self.chat_users[nick].irc_mode = highest_mode
        else:
            self.chat_users[nick].irc_mode = ""

        if nick == self.state.nick:
            self.state.player.irc_mode = self.chat_users[nick].irc_mode

        logger.info(
            'User "%s" mode changed to %s',
            nick,
            self.chat_users[nick].irc_mode,
        )
        UpdateUsersUseCase(self.state, self.ui).execute()
        add_users_list_to_game(self.state.chat_users.values())

    def _get_highest_mode_and_type(
        self, current_rank, highest_rank_remove, highest_rank_add, nick
    ):
        type_of_mode = SET
        if current_rank == highest_rank_remove:
            highest_mode = RANK_TO_MODE[highest_rank_add]

        elif current_rank > highest_rank_remove:
            highest_mode = self.chat_users[nick].irc_mode

        elif highest_rank_add > highest_rank_remove:
            highest_mode = RANK_TO_MODE[highest_rank_add]

        else:
            highest_mode = None
            type_of_mode = None

        return highest_mode, type_of_mode
