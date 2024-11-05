import logging
from typing import Iterable, Optional

import inject

from pysaic.entities import ChatUser
from pysaic.enums import FactionsEnum
from pysaic.state import State

logger = logging.getLogger(__name__)


def ensure_game_is_running(func):
    @inject.autoparams()
    def wrapper(*args, state: State, **kwargs):
        if state.game_location is None:
            logger.debug('Game is not running, skipping "%s"', func.__name__)
            return

        return func(*args, **kwargs)

    return wrapper


@ensure_game_is_running
def add_channel_message_to_game(
    faction_actor: str, author: str, highlight: str, content: str
):
    add_to_crc_input_file(
        f"Message/{faction_actor}/{author}/{highlight}/{content}"
    )


@ensure_game_is_running
def add_dm_message_to_game(
    author_faction_actor: str, author: str, receiver: str, content: str
):
    add_to_crc_input_file(
        f"Query/{author_faction_actor}/{author}/{receiver}/{content}"
    )


@ensure_game_is_running
def ask_for_actor_status():
    add_to_crc_input_file("Setting/ActorStatus")


@ensure_game_is_running
def add_information_message_to_game(content: str):
    add_to_crc_input_file(f"Information/{content}")


@ensure_game_is_running
def add_error_message_to_game(content: str):
    add_to_crc_input_file(f"Error/{content}")


@ensure_game_is_running
def _get_chat_user_faction(faction: Optional[FactionsEnum]):
    return faction or FactionsEnum.Anonymous


def serialize_chat_user(chat_user: ChatUser):
    return (
        f"{chat_user.name.lstrip('@%+')},"
        f"{_get_chat_user_faction(chat_user.faction)} = "
        f"{chat_user.in_game}"
    )


@ensure_game_is_running
def add_users_list_to_game(users: Iterable[ChatUser]):
    if not users:
        logger.warning("No users to update")
        return

    add_to_crc_input_file(
        f"Users/{'/'.join(serialize_chat_user(user) for user in users)}"
    )


@ensure_game_is_running
def add_money_to_user(author: str, amount: str):
    add_to_crc_input_file(f"MoneyRecv/{author}/{amount}")


@ensure_game_is_running
def remove_money_from_player(author: str, receiver: str, amount: str):
    add_to_crc_input_file(f"Money/{author}/{receiver}/{amount}")


@ensure_game_is_running
def add_setting_to_game(setting: str, value: str):
    add_to_crc_input_file(f"Setting/{setting}/{value}")


@inject.autoparams()
def add_to_crc_input_file(content: str, state: State):
    logger.debug("Adding to crc_input.txt: %r", content)
    with open(
        state.game_location / "gamedata" / "configs" / "crc_input.txt", "a"
    ) as f:
        f.write(content + "\n")
