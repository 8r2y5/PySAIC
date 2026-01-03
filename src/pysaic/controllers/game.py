import logging
from typing import Iterable, Optional

import inject

from pysaic.entities import ChatUser, IncomingEvent, IncomingQueue
from pysaic.enums import FactionsEnum
from pysaic.state import State
from pysaic.use_cases.irc_mode_to_user_type import parsed_mode_to_name

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
    faction_actor: str,
    author: str,
    icon_id: str,
    reputation_author: str,
    rank_author: str,
    highlight: str,
    user_type: str,
    content: str,
):
    add_to_crc_input_file(
        "/".join(
            (
                "Message",
                faction_actor,
                author,
                icon_id,
                reputation_author,
                rank_author,
                highlight,
                user_type,
                content,
            )
        )
    )


@ensure_game_is_running
def add_dm_message_to_game(
    author_faction_actor: str,
    user_type: str,
    author: str,
    icon_id: str,
    reputation_author: str,
    rank_author: str,
    receiver: str,
    content: str,
):
    add_to_crc_input_file(
        "/".join(
            (
                "Query",
                author_faction_actor,
                user_type,
                author,
                icon_id,
                reputation_author,
                rank_author,
                receiver,
                content,
            )
        )
    )


def ask_for_actor_status():
    add_setting_to_game("ActorStatus", "Query")


def ask_for_handshake(state_id):
    add_setting_to_game("Handshake", state_id)


def set_ingame_display_setting(value: str):
    add_setting_to_game("UserDisplayStyle", value)


def set_ingame_display_setting_order_setting(value: str):
    add_setting_to_game("InGameUserDisplayOrder", value)


@ensure_game_is_running
def add_information_message_to_game(content: str):
    add_to_crc_input_file(f"Information/{content}")


@ensure_game_is_running
def add_error_message_to_game(content: str):
    add_to_crc_input_file(f"Error/{content}")


@ensure_game_is_running
def add_signal_state(content: str):
    logger.debug("Adding signal state: %s", content)
    add_to_crc_input_file(f"SignalState/{content}")


@ensure_game_is_running
def add_faction_colored_nicks(enabled: bool):
    add_setting_to_game("FactionColoredNicks", str(enabled))


def _get_clear_nick(user: ChatUser):
    return user.name.lstrip("@%+")


def _get_message_metadata(message_type: str, me: ChatUser):
    if message_type == "dm":
        return f"dm,{_get_clear_nick(me)}"
    else:
        return "channel,"


@ensure_game_is_running
def add_message_history(history: list[tuple[str, ChatUser, ChatUser, str]]):
    for message_type, source, me, message_content in history:
        add_to_crc_input_file(
            "/".join(
                (
                    "History",
                    str(_get_chat_user_faction(source.faction)),
                    _get_clear_nick(source),
                    str(source.avatar),
                    source.reputation.value.title(),
                    str(source.rank),
                    str(me.name in message_content),
                    parsed_mode_to_name(source.irc_mode),
                    _get_message_metadata(message_type, me),
                    message_content,
                )
            )
        )


def _get_chat_user_faction(faction: Optional[FactionsEnum]):
    return faction or FactionsEnum.Anonymous


def _get_chat_user_data(chat_user: ChatUser):
    return ",".join(
        (
            _get_clear_nick(chat_user),
            str(_get_chat_user_faction(chat_user.faction)),
            str(chat_user.rank),
            chat_user.reputation.value.title(),
            str(int(chat_user.afk)),
            str(chat_user.avatar),
            parsed_mode_to_name(chat_user.irc_mode),
        )
    )


def serialize_chat_user(chat_user: ChatUser):
    return (
        f"{_get_chat_user_data(chat_user)} = "
        f"{chat_user.location.name if chat_user.in_game else chat_user.in_game}"
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
def add_money_to_user(author: str, reputation: str, rank: str, amount: str):
    add_to_crc_input_file(f"MoneyRecv/{author}/{reputation}/{rank}/{amount}")


@ensure_game_is_running
def remove_money_from_player(player: ChatUser, receiver: str, amount: str):
    add_to_crc_input_file(
        f"Money/{player.name}/{player.reputation}/{player.rank}/{receiver}/{amount}"
    )


@ensure_game_is_running
def add_setting_to_game(setting: str, value: str):
    add_to_crc_input_file(f"Setting/{setting}/{value}")


@inject.autoparams()
def add_to_crc_input_file(
    content: str, state: State, incoming_queue: IncomingQueue
):
    content = (
        content.encode("utf-8", errors="replace")
        .decode("utf-8")
        .replace("\n", "")
        .replace("\r", "")
    )
    logger.debug("Adding to %s: %r", state.crc_input_path, content)
    try:
        with open(state.crc_input_path, "a") as f:
            f.write(content + "\n")
    except FileNotFoundError:
        logger.exception(
            "Game location %s does not exist, cannot write to crc_input.txt",
            state.game_location,
        )
        incoming_queue.put_nowait(
            IncomingEvent.create_error_event(
                f"File {state.crc_input_path} does not exist"
            )
        )
        raise
    except OSError as e:
        logger.exception(
            "Failed to write to crc_input.txt: %s. Game location: %s",
            e,
            state.game_location,
        )
        incoming_queue.put_nowait(
            IncomingEvent.create_error_event(
                f"Cannot write into {state.crc_input_path}. "
                f"Please check permissions or disk space."
            )
        )
        raise
