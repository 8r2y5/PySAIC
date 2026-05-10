import asyncio
import logging
import threading
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from random import choice
from typing import Optional, Self

from pysaic.config import Config
from pysaic.entities import ChatUser, ChatUsers
from pysaic.enums import (
    AvatarEnum,
    DisconnectOnNetworkDestructionSetting,
    HistoryMessageEnum,
    LocationEnum,
    SAICStateEnum,
    RankEnum,
    ReputationEnum,
    NetworkDestroyReasonEnum,
)
from pysaic.use_cases.avatar import calculate_icon_based_on_faction_and_name

logger = logging.getLogger(__name__)


@dataclass()
class Player(ChatUser):
    money: int = 0
    config: Optional[Config] = None
    logger: logging.Logger = logger.getChild("player")

    def reset(self):
        self.location = LocationEnum.unknown
        self.in_game = False
        self.rank = RankEnum.unknown
        self.reputation = ReputationEnum.unknown
        self.money = 0
        self.last_ask_update = None
        self.afk = False
        self.state = SAICStateEnum.ok

    def create_chat_user(self) -> ChatUser:
        return ChatUser(
            name=self.name,
            faction=self.faction,
            location=self.location,
            in_game=self.in_game,
            rank=self.rank,
            reputation=self.reputation,
            irc_mode=self.irc_mode,
            avatar=self.get_avatar(myself=True),
            state=self.state,
        )

    def get_avatar(self, myself: bool = False) -> str:
        if myself is True:
            return self.config.current_avatar

        return (
            calculate_icon_based_on_faction_and_name(
                self.faction.name, self.name
            )
            if self.config.avatar == AvatarEnum.player
            else self.config.current_avatar
        )

    @classmethod
    def create_from_config(cls, config: Config) -> Self:
        return cls(
            name=config.nick,
            faction=config.current_faction,
            avatar=config.current_avatar,
            config=config,
        )


class NetworkDestructionStrategy(ABC):
    @abstractmethod
    def should_disconnect(self) -> bool: ...

    @abstractmethod
    def should_malform(self) -> bool: ...


class NeverNetworkDestructionStrategy(NetworkDestructionStrategy):
    def should_disconnect(self) -> bool:
        return False

    def should_malform(self) -> bool:
        return False


class AlwaysNetworkDestructionStrategy(NetworkDestructionStrategy):
    def should_disconnect(self) -> bool:
        return True

    def should_malform(self) -> bool:
        return False


class MalformOnlyNetworkDestructionStrategy(NetworkDestructionStrategy):
    def should_malform(self) -> bool:
        return True

    def should_disconnect(self) -> bool:
        return False


class RandomNetworkDestructionStrategy(NetworkDestructionStrategy):
    def __init__(self):
        super().__init__()
        random_cls = choice(
            (
                NeverNetworkDestructionStrategy,
                AlwaysNetworkDestructionStrategy,
                MalformOnlyNetworkDestructionStrategy,
            )
        )
        self.setting_instance = random_cls()

    def should_disconnect(self) -> bool:
        return self.setting_instance.should_disconnect()

    def should_malform(self) -> bool:
        return self.setting_instance.should_malform()


NETWORK_DESTRUCTION_MAP = {
    DisconnectOnNetworkDestructionSetting.Always: AlwaysNetworkDestructionStrategy,
    DisconnectOnNetworkDestructionSetting.Never: NetworkDestructionStrategy,
    DisconnectOnNetworkDestructionSetting.MalformSignalOnly: MalformOnlyNetworkDestructionStrategy,
    DisconnectOnNetworkDestructionSetting.Random: RandomNetworkDestructionStrategy,
}


class State:
    @property
    def nick(self) -> str:
        return self.player.name

    @nick.setter
    def nick(self, value: str):
        self.logger.debug(
            'Changing nick from "%s" to "%s"', self.player.name, value
        )
        self.player.name = value

    @property
    def is_game_running(self) -> bool:
        return self._is_game_running

    @is_game_running.setter
    def is_game_running(self, value: bool):
        self.player.in_game = self._is_game_running = value
        if not value:
            self.is_currently_under_network_destruction = None
            self.network_destruction_handler = None

    @property
    def game_location(self) -> Optional[Path]:
        return self._game_location

    @game_location.setter
    def game_location(self, value: Optional[Path]):
        if isinstance(value, Path):
            self.crc_input_path = (
                value / "gamedata" / "configs" / "crc_input.txt"
            ).resolve()
        else:
            self.crc_input_path = None
        self._game_location = value

    @property
    def is_currently_under_network_destruction(
        self,
    ) -> NetworkDestroyReasonEnum:
        return self._is_currently_under_network_destruction

    @is_currently_under_network_destruction.setter
    def is_currently_under_network_destruction(
        self, value: NetworkDestroyReasonEnum
    ):
        self._is_currently_under_network_destruction = value
        if value == NetworkDestroyReasonEnum.surge:
            config_value = self.config.disconnect_when_emission
        elif value == NetworkDestroyReasonEnum.underground:
            config_value = self.config.disconnect_when_underground
        else:
            self.network_destruction_handler = None
            return

        self.network_destruction_handler = NETWORK_DESTRUCTION_MAP[
            config_value
        ]()

    def __init__(self, config: Config):
        self.state_lock = threading.Lock()
        self.pending_updates: dict[str, int | str] = {}
        self.id: str = str(id(self))
        self.got_first_handshake: asyncio.Event = asyncio.Event()
        self.logger: logging.Logger = logger.getChild("instance").getChild(
            self.id
        )
        self.config: Config = config
        self.got_welcome_message: asyncio.Event = asyncio.Event()
        self._game_location: Optional[Path] = None
        self.crc_input_path: Optional[Path] = None
        self._is_game_running: bool = False
        self.is_author_authorized: asyncio.Event = asyncio.Event()
        self.is_in_channel: asyncio.Event = asyncio.Event()
        self.chat_users: ChatUsers = ChatUsers({})
        self.player: Player = Player.create_from_config(config)
        self.last_death: Optional[datetime] = None
        self.last_messages: deque[
            tuple[HistoryMessageEnum, ChatUser, ChatUser, str]
        ] = deque(maxlen=100)
        self.player_update_task: Optional[asyncio.Future] = None
        self.player_changed_values_queue: asyncio.Queue = asyncio.Queue()
        self._is_currently_under_network_destruction: (
            NetworkDestroyReasonEnum
        ) = NetworkDestroyReasonEnum.none
        self.network_destruction_handler: Optional[
            NetworkDestructionStrategy
        ] = None
        self.last_private_message_from: Optional[str] = None
        self.game_transport: Optional[asyncio.Transport] = None
        self.sent_achievements: set[str] = set()

    def money_enough(self, amount) -> bool:
        return self.player.money >= amount

    def add_message(
        self, message_type: HistoryMessageEnum, user: ChatUser, message: str
    ):
        self.last_messages.append(
            (
                message_type,
                user.copy(),
                self.player.create_chat_user(),
                message,
            )
        )

    def set_not_in_channel(self):
        self.logger.info("Setting not in channel")
        self.is_in_channel.clear()
        self.chat_users.clear()

    def set_in_channel(self):
        self.logger.info("Setting in channel")
        self.chat_users.update_or_create(
            self.nick, self.config.current_faction
        )
        self.player.faction = self.config.current_faction
        self.chat_users.update_user_location(self.nick, self.player.location)
        self.is_in_channel.set()

    @property
    def should_malform_messages(self) -> bool:
        if not self.network_destruction_handler:
            return False
        return self.network_destruction_handler.should_malform()

    @property
    def fake_disconnect(self) -> bool:
        if not self.network_destruction_handler:
            return False
        return self.network_destruction_handler.should_disconnect()

    def get_player_state(self):
        match self.is_currently_under_network_destruction:
            case NetworkDestroyReasonEnum.surge:
                return SAICStateEnum.emission
            case NetworkDestroyReasonEnum.underground:
                return SAICStateEnum.underground
            case _:
                return SAICStateEnum.ok
