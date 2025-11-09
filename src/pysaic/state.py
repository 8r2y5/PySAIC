import asyncio
import logging
from asyncio import Task
from collections import deque
from datetime import datetime
from pathlib import Path
from typing import Optional

from pysaic.entities import ChatUser, ChatUsers, Player
from pysaic.enums import DisconnectOnNetworkDestructionSetting

logger = logging.getLogger(__name__)


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

    def __init__(self, config):
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
        self.chat_users: ChatUsers[str, ChatUser] = ChatUsers({})
        self.game_related_tasks: list[Task] = []
        self.player = Player.create_from_config(config)
        self.last_death: Optional[datetime] = None
        self.last_messages = deque(maxlen=20)
        self.player_update_task = None
        self.player_changed_values_queue = asyncio.Queue()
        self.is_currently_under_network_destruction: bool | None = None

    def money_enough(self, amount) -> bool:
        return self.player.money >= amount

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
        return (
            self.is_currently_under_network_destruction
            and self.config.disconnect_when_blowout_or_underground
            in (
                DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
                DisconnectOnNetworkDestructionSetting.Always,
            )
        )

    @property
    def fake_disconnect(self) -> bool:
        return (
            self.is_currently_under_network_destruction
            and self.config.disconnect_when_blowout_or_underground
            in (DisconnectOnNetworkDestructionSetting.Always,)
        )
