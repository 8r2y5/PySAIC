import logging
from dataclasses import field
from datetime import datetime
from functools import partial, wraps
from typing import List, Optional, NamedTuple, Self

from pysaic.enums import FactionsEnum, NetworkDestroyReasonEnum, LocationEnum

main_logger = logging.getLogger(__name__)


def provide_logger(func=None, *, name=None):
    if func is None:
        return partial(provide_logger, name=name)

    this_logger = main_logger.getChild(name)

    @wraps(func)
    def _wrapper(*args, **kwargs):
        return func(*args, **kwargs, logger=this_logger)

    return _wrapper


class Actor(NamedTuple):
    type: type[FactionsEnum]
    name: str
    in_game: bool = None


class ActorTimestamped(Actor):
    last_update: datetime = field(default_factory=datetime.utcnow)


class DirectMessage(NamedTuple):
    sender: Actor
    receiver: str
    message: str
    in_file_id = "Query"

    @classmethod
    def from_line(cls, line):
        faction_str, author_name, receiver, message = line.split("/", 3)
        return cls(
            sender=Actor(
                type=FactionsEnum(faction_str),  # noqa
                name=author_name,
            ),
            receiver=receiver,
            message=message,
        )


class ChannelMessage(NamedTuple):
    sender: Actor
    message: str
    in_file_id = "Message"

    @classmethod
    @provide_logger(name="channel_message")
    def from_line(cls, nick, line, logger: logging.Logger):
        try:
            faction_str, message = line.split("/", 1)
        except ValueError:
            logger.exception("%r", line)
            raise
        return cls(
            sender=Actor(
                type=FactionsEnum(faction_str),  # noqa
                name=nick,
                in_game=True,
            ),
            message=message,
        )


class ConnectedUser(NamedTuple):
    name: str
    in_game: bool


class ConnectedUsers(NamedTuple):
    users: List[ConnectedUser]
    in_file_id = "Users"

    @classmethod
    @provide_logger(name="connected_users")
    def from_line(cls, line, logger: logging.Logger):
        users = []
        for user in line.split("/"):
            try:
                name, is_in_game = user.replace(" ", "").split("=")
            except Exception:
                logger.exception("%r", user)
                continue
            users.append(
                ConnectedUser(name=name, in_game=is_in_game == "True")
            )
        return cls(users=users)


class Information(NamedTuple):
    message: str
    in_file_id = "Information"

    @classmethod
    def from_line(cls, line):
        return cls(message=line)


class Handshake(NamedTuple):
    version: int
    handshake_id: str
    in_file_id = "Handshake"

    @classmethod
    def from_line(cls, value):
        try:
            version, handshake_id = value.split("/", 2)
        except ValueError:
            version = value
            handshake_id = "None"
        return cls(
            version=int(version),
            handshake_id=handshake_id,
        )


class Money(NamedTuple):
    amount: int
    in_file_id = "Money"

    @classmethod
    def from_line(cls, value):
        return cls(amount=int(value))


class Death(NamedTuple):
    user_actor: str
    location: str
    death_by: str
    meta: str
    in_file_id = "Death"

    @classmethod
    def from_line(cls, line):
        user_actor, location, death_by, meta = line.split("/", 3)
        return cls(
            user_actor=user_actor,
            location=location,
            death_by=death_by,
            meta=meta,
        )


class ConnectionLost(NamedTuple):
    lost: bool
    reason: Optional[str]
    in_file_id = "ConnLost"

    @classmethod
    def from_line(cls, value):
        lost, reason = value.split("/", 1)
        return cls(
            lost=lost.lower() == "true",
            reason=NetworkDestroyReasonEnum(reason.lower()),
        )


class ActorStatus(NamedTuple):
    value: str
    in_file_id = "ActorStatus"

    @classmethod
    def from_line(cls, value):
        return cls(value=value)


class ChannelChange(NamedTuple):
    channel_description: str
    in_file_id = "ChannelChange"

    @classmethod
    def from_line(cls, value):
        return cls(channel_description=value)


class Location(NamedTuple):
    name: str
    in_file_id = "Location"

    @classmethod
    def from_line(cls, line):
        return cls(name=line)


class Achievement(NamedTuple):
    name: str
    game_enum: str
    in_file_id = "Achievement"

    @classmethod
    def from_line(cls, line):
        name, game_enum = line.split("/", 1)
        return cls(name=name.replace("_", " ").title(), game_enum=game_enum)


class Reputation(NamedTuple):
    value: str
    in_file_id = "Reputation"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)


class Rank(NamedTuple):
    value: str
    in_file_id = "Rank"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)


class AFK(NamedTuple):
    value: str
    in_file_id = "AFK"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)


class Item(NamedTuple):
    game_id: str
    location: LocationEnum
    item_name: str
    in_file_id = "Item"

    @classmethod
    def from_line(cls, line: str) -> Self:
        game_id, map_id, item_name = line.split("/", 2)
        return cls(
            game_id=game_id, location=LocationEnum[map_id], item_name=item_name
        )
