import logging
from asyncio import Queue
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterable, Optional, Union

from irclib.parser import Prefix

from pysaic.enums import (
    AppEventEnum,
    FactionsEnum,
    IrcEvents,
    LocationEnum,
    SAICStateEnum,
    RankEnum,
    ReputationEnum,
)
from pysaic.events.enum import GameEvents

logger = logging.getLogger(__name__)


class OutgoingQueue(Queue):
    pass


@dataclass
class OutgoingMessage:
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class OutgoingCTCP:
    target: str
    content: str
    created_at: datetime = field(default_factory=datetime.now)
    send_as: IrcEvents = IrcEvents.NOTICE

    def __post_init__(self):
        self.content = f"\x01{self.content}\x01".replace("\n", "")


@dataclass
class OutgoingQuery:
    target: str
    content: str
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
class OutgoingCommand:
    command: IrcEvents
    args: Iterable[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create_nick_command(cls, nick: str):
        return cls(command=IrcEvents.NICK, args=[nick])

    def __str__(self):
        args_str = " ".join(self.args)
        return f"{self.command} {args_str}" if args_str else self.command


@dataclass
class IrcUser:
    nick: str
    user: Optional[str] = None
    host: Optional[str] = None

    @classmethod
    def from_prefix(cls, prefix: Prefix):
        return cls(nick=prefix.nick, user=prefix.user, host=prefix.host)

    @property
    def mask(self):
        return f"{self.nick}!{self.user}@{self.host}"


@dataclass
class IncomingMessage:
    author: IrcUser
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
class EventRegister:
    name: str
    handler: callable
    on: Any


@dataclass
class IncomingAppEvent:
    author: str
    target: str
    event: Union[
        AppEventEnum, GameEvents, IrcEvent, InformationEvent, ErrorEvent
    ]
    payload: Optional[Any] = None
    created_at: datetime = field(default_factory=datetime.now)


@dataclass
class IncomingEvent:
    author: Union[str, IrcUser]
    target: str
    event: Union[
        IrcEvent,
        InformationEvent,
        AppEvent,
        ErrorEvent,
        GameEvent,
        EventRegister,
    ]
    created_at: datetime = field(default_factory=datetime.now)

    @classmethod
    def create_information_event(cls, content: str, target: str = ""):
        return cls(
            author="",
            target=target,
            event=InformationEvent(content),
        )

    @classmethod
    def create_irc_event(cls, what, payload):
        return cls(
            author="",
            target="",
            event=IrcEvent(what, payload),
        )

    @classmethod
    def create_error_event(cls, param):
        return cls(
            author="",
            target="",
            event=ErrorEvent(param),
        )

    @classmethod
    def create_app_event(cls, what, payload=None):
        return cls(
            author="",
            target="",
            event=AppEvent(what, payload),
        )

    @classmethod
    def create_game_event(cls, what, payload):
        return cls(
            author="",
            target="",
            event=GameEvent(what, payload),
        )


class IncomingQueue(Queue):
    def create_information_event(self, content: str, target: str = ""):
        self.put_nowait(
            IncomingEvent.create_information_event(content, target)
        )

    def create_error_event(self, content):
        self.put_nowait(IncomingEvent.create_error_event(content))


@dataclass
class ChatUser:
    name: str
    in_game: bool = False
    location: LocationEnum = field(default=LocationEnum.unknown)
    faction: FactionsEnum = field(default=FactionsEnum.Anonymous)
    rank: RankEnum = field(default=RankEnum.unknown)
    reputation: ReputationEnum = field(default=ReputationEnum.unknown)
    afk: bool = False
    last_ask_update: Optional[datetime] = None
    irc_mode: str = ""
    avatar: str = "random"
    irc_user: Optional[IrcUser] = None
    state: SAICStateEnum = SAICStateEnum.ok

    def copy(self):
        return self.__class__(
            **{
                field_name: getattr(self, field_name)
                for field_name in self.__dataclass_fields__.keys()
            }
        )


@dataclass
class DeathTimestamped:
    user_faction: str
    location: str
    death_by: str
    meta: str
    created_at: datetime = field(default_factory=datetime.now)


class ChatUsers(dict):
    def __init__(self, data):
        super().__init__(data)
        self.needs_update = False
        self.logger = logger.getChild("chat_users")

    def _update_user_field_if_different(self, user_id, field, value):
        self.logger.debug(
            'Updating user "%s" %s to "%s"', user_id, value, field
        )
        user = self[user_id]
        if getattr(user, field) == value:
            return
        setattr(user, field, value)
        self[user_id] = user
        self.needs_update = True

    def update_user_faction(self, user_id, faction):
        self._update_user_field_if_different(user_id, "faction", faction)

    def update_user_location(self, user_id, location):
        self._update_user_field_if_different(user_id, "location", location)

    def update_user_name(self, old_name, name):
        self.logger.debug('Renaming user "%s" to "%s"', old_name, name)
        user = self.pop(old_name)
        user.name = name
        self[name] = user
        self.needs_update = True

    def remove_user(self, user_id):
        self.logger.debug('Removing user "%s"', user_id)
        self.pop(user_id, None)
        self.needs_update = True

    def add_user(self, user_id, user: ChatUser):
        self.logger.debug('Adding user "%s"', user_id)
        self[user_id] = user
        self.needs_update = True

    def get_user(self, user_id):
        self.logger.debug('Getting user "%s"', user_id)
        return self.get(user_id)

    def update_or_create(self, name, actor) -> ChatUser:
        if self.get(name):
            self.logger.debug('User "%s" already exists', name)
            self.update_user_faction(name, FactionsEnum(actor))
            # self.update_user_ingame(name, True)
        else:
            self.logger.debug('User "%s" does not exist', name)
            self.add_user(
                name,
                ChatUser(name=name, faction=FactionsEnum(actor)),
            )

        self.needs_update = True
        return self[name]

    def update_user_ingame(self, name, in_game):
        self.logger.debug('Updating user "%s" in_game to "%s"', name, in_game)
        user = self[name]
        if user.in_game == in_game:
            return
        user.in_game = in_game
        self.needs_update = True

    def set_user(self, author, user):
        self.logger.debug('Setting user "%s"', author)
        self[author] = user
        self.needs_update = True

    def __getitem__(self, item):
        self.logger.debug('Getting key "%s"', item)
        return super().__getitem__(item)

    def __setitem__(self, key, value):
        self.logger.debug('Setting key "%s" with value "%s"', key, value)
        super().__setitem__(key, value)
        self.needs_update = True

    def __delitem__(self, key):
        self.logger.debug('Deleting key "%s"', key)
        super().__delitem__(key)
        self.needs_update = True
