import logging
from dataclasses import dataclass, field
from datetime import datetime
from functools import partial, wraps
from typing import List, Optional

from pysaic.enums import FactionsEnum, NetworkDestroyReasonEnum

main_logger = logging.getLogger(__name__)


timezone = datetime


def provide_logger(func=None, *, name=None):
    if func is None:
        return partial(provide_logger, name=name)

    this_logger = main_logger.getChild(name)

    @wraps(func)
    def _wrapper(*args, **kwargs):
        return func(*args, **kwargs, logger=this_logger)

    return _wrapper


@dataclass
class Actor:
    type: FactionsEnum
    name: str
    in_game: bool = None


@dataclass
class ActorTimestamped(Actor):
    last_update: datetime = field(default_factory=timezone.utcnow)


@dataclass
class DirectMessage:
    sender: Actor
    receiver: str
    message: str
    in_file_id = "Query"

    @classmethod
    def from_line(cls, line):
        faction_str, author_name, receiver, message = line.split("/", 3)
        return cls(
            sender=Actor(
                type=FactionsEnum(faction_str),
                name=author_name,
            ),
            receiver=receiver,
            message=message,
        )


@dataclass
class ChannelMessage:
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
                type=FactionsEnum(faction_str),
                name=nick,
                in_game=True,
            ),
            message=message,
        )


@dataclass
class ConnectedUser:
    name: str
    in_game: bool


@dataclass
class ConnectedUsers:
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


@dataclass
class Information:
    message: str
    in_file_id = "Information"

    @classmethod
    def from_line(cls, line):
        return cls(message=line)


@dataclass
class Handshake:
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


@dataclass
class Money:
    amount: int
    in_file_id = "Money"

    @classmethod
    def from_line(cls, value):
        return cls(amount=int(value))


@dataclass
class Death:
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


@dataclass
class ConnectionLost:
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


@dataclass
class ActorStatus:
    value: str
    in_file_id = "ActorStatus"

    @classmethod
    def from_line(cls, value):
        return cls(value=value)


@dataclass
class ChannelChange:
    channel_description: str
    in_file_id = "ChannelChange"

    @classmethod
    def from_line(cls, value):
        return cls(channel_description=value)


@dataclass()
class Location:
    name: str
    in_file_id = "Location"

    @classmethod
    def from_line(cls, line):
        return cls(name=line)


@dataclass()
class Achievement:
    name: str
    game_enum: str
    in_file_id = "Achievement"

    @classmethod
    def from_line(cls, line):
        # Achievement/mechanized_warfare/st_achievement_7_unlock
        # Achievement/rag_and_bone/st_achievement_9_unlock
        name, game_enum = line.split("/", 1)
        return cls(name=name.replace("_", " ").title(), game_enum=game_enum)


@dataclass()
class Reputation:
    value: str
    in_file_id = "Reputation"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)


@dataclass()
class Rank:
    value: str
    in_file_id = "Rank"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)


@dataclass
class AFK:
    value: str
    in_file_id = "AFK"

    @classmethod
    def from_line(cls, line):
        return cls(value=line)
