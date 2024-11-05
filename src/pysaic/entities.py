from asyncio import Queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Union

from pysaic.enums import AppEventEnum, FactionsEnum, IrcEvents
from pysaic.events.enum import GameEvents


class IncomingQueue(Queue):
    pass


class OutgoingQueue(Queue):
    pass


@dataclass
class OutgoingMessage:
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingQuery:
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingNotice:
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingNick:
    nick: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingJoin:
    channel: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingPart:
    channel: str
    content: str = ""
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IncomingMessage:
    author: str
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    service: bool = False


@dataclass
class IrcEvent:
    type: IrcEvents
    payload: Optional[dict[str, any]] = None


@dataclass
class InformationEvent:
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class ErrorEvent(InformationEvent):
    pass


@dataclass
class AppEvent:
    what: AppEventEnum
    payload: Optional[Any] = None


@dataclass
class GameEvent:
    what: GameEvents
    payload: Optional[Any] = None


@dataclass
class IncomingAppEvent:
    author: str
    target: str
    event: [AppEventEnum, GameEvents, IrcEvent, InformationEvent, ErrorEvent]
    payload: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IncomingEvent:
    author: str
    target: str
    event: Union[IrcEvent, InformationEvent, AppEvent, ErrorEvent, GameEvent]
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create_information_event(cls, content: str):
        return cls(
            author="",
            target="",
            event=InformationEvent(content),
        )

    @classmethod
    def create_irc_event(cls, NICK, param):
        return cls(
            author="",
            target="",
            event=IrcEvent(NICK, {"nick": param}),
        )

    @classmethod
    def create_error_event(cls, param):
        return cls(
            author="",
            target="",
            event=ErrorEvent(param),
        )

    @classmethod
    def create_app_event(cls, what, payload):
        return cls(
            author="",
            target="",
            event=AppEvent(what, payload),
        )

    @classmethod
    def create_game_event(cls, param):
        return cls(
            author="",
            target="",
            event=GameEvent(param),
        )


@dataclass
class ChatUser:
    name: str
    in_game: bool = False
    faction: FactionsEnum = field(default=FactionsEnum.Anonymous)
    irc_mode: str = ""


# Unknown type: Death/actor_killer/l04_darkvalley/ARMY/sim_default_military_1


@dataclass
class DeathTimestamped:
    user_faction: str
    location: str
    death_by: str
    meta: str
    created_at: datetime = field(default_factory=datetime.now)
