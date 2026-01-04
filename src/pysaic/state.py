import asyncio
import logging
from asyncio import Task
from collections import deque
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional

from pysaic.config import Config
from pysaic.entities import ChatUser, ChatUsers
from pysaic.enums import (
    DisconnectOnNetworkDestructionSetting,
    LocationEnum,
    RankEnum,
    ReputationEnum,
    AvatarEnum,
)

logger = logging.getLogger(__name__)


@dataclass()
class Player(ChatUser):
    money: int = 0
    config: Optional[Config] = None
    logger = logger.getChild("player")

    def reset(self):
        self.location = LocationEnum.unknown
        self.in_game = False
        self.rank = RankEnum.unknown
        self.reputation = ReputationEnum.unknown
        self.money = 0
        self.last_ask_update = None
        self.afk = False

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
        )

    def get_avatar(self, myself: bool = False) -> str:
        if myself is True:
            return self.config.current_avatar

        return (
            "random"
            if self.config.avatar == AvatarEnum.player
            else self.config.current_avatar
        )

    @classmethod
    def create_from_config(cls, config):
        return cls(
            name=config.nick,
            faction=config.current_faction,
            avatar=config.current_avatar,
            config=config,
        )


class State:
    @property
    def nick(self):
        return self.player.name

    @nick.setter
    def nick(self, value):
        self.logger.debug(
            'Changing nick from "%s" to "%s"', self.player.name, value
        )
        self.player.name = value

    @property
    def is_game_running(self):
        return self._is_game_running

    @is_game_running.setter
    def is_game_running(self, value):
        self.player.in_game = self._is_game_running = value

    @property
    def game_location(self) -> Optional[Path]:
        return self._game_location

    @game_location.setter
    def game_location(self, value):
        if isinstance(value, Path):
            self.crc_input_path = (
                value / "gamedata" / "configs" / "crc_input.txt"
            ).resolve()
        else:
            self.crc_input_path = None
        self._game_location = value

    def __init__(self, config: Config):
        self.id = str(id(self))
        self.got_first_handshake = asyncio.Event()
        self.logger = logger.getChild("instance").getChild(self.id)
        self.config = config
        self.got_welcome_message = asyncio.Event()
        self._game_location: Optional[Path] = None
        self.crc_input_path: Optional[Path] = None
        self._is_game_running: bool = False
        self.is_author_authorized = asyncio.Event()
        self.is_in_channel = asyncio.Event()
        self.chat_users: ChatUsers = ChatUsers({})
        self.game_related_tasks: list[Task] = []
        self.player = Player.create_from_config(config)
        self.last_death: Optional[datetime] = None
        self.last_messages = deque(maxlen=20)
        self.player_update_task = None
        self.player_changed_values_queue = asyncio.Queue()
        self.is_currently_under_network_destruction: str | None = None
        self.last_private_message_from: str | None = None

    def money_enough(self, amount) -> bool:
        return self.player.money >= amount

    def add_message(self, message_type: str, user: ChatUser, message: str):
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
        if not self.is_currently_under_network_destruction:
            return False
        if (
            self.is_currently_under_network_destruction == "Surge"
            and self.config.disconnect_when_emission
            in (
                DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
                DisconnectOnNetworkDestructionSetting.Always,
            )
        ):
            return True
        return (
            self.is_currently_under_network_destruction == "Underground"
            and self.config.disconnect_when_underground
            in (
                DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
                DisconnectOnNetworkDestructionSetting.Always,
            )
        )

    @property
    def fake_disconnect(self) -> bool:
        if not self.is_currently_under_network_destruction:
            return False
        if (
            self.is_currently_under_network_destruction == "Surge"
            and self.config.disconnect_when_emission
            in (DisconnectOnNetworkDestructionSetting.Always,)
        ):
            return True
        return (
            self.is_currently_under_network_destruction == "Underground"
            and self.config.disconnect_when_underground
            in (DisconnectOnNetworkDestructionSetting.Always,)
        )
