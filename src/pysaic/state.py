import asyncio
import logging
from asyncio import Task
from datetime import datetime
from pathlib import Path
from typing import Optional

from pysaic.entities import ChatUser
from pysaic.enums import FactionsEnum


logger = logging.getLogger(__name__)


class ChatUsers(dict):
    def __init__(self, data):
        super().__init__(data)
        self.needs_update = False
        self.logger = logger.getChild("chat_users")

    def update_user_faction(self, user_id, faction):
        self.logger.info(
            'Updating user "%s" faction to "%s"', user_id, faction
        )
        user = self[user_id]
        if user.faction == faction:
            return
        user.faction = faction
        self[user_id] = user
        self.needs_update = True

    def update_user_name(self, old_name, name):
        self.logger.info('Renaming user "%s" to "%s"', old_name, name)
        user = self.pop(old_name)
        user.name = name
        self[name] = user
        self.needs_update = True

    def remove_user(self, user_id):
        self.logger.info('Removing user "%s"', user_id)
        self.pop(user_id, None)
        self.needs_update = True

    def add_user(self, user_id, user: ChatUser):
        self.logger.info('Adding user "%s"', user_id)
        self[user_id] = user
        self.needs_update = True

    def get_user(self, user_id):
        return self.get(user_id)

    def update_or_create(self, name, actor) -> ChatUser:
        if self.get(name):
            self.logger.info('User "%s" already exists', name)
            self.update_user_faction(name, FactionsEnum(actor))
            # self.update_user_ingame(name, True)
        else:
            self.logger.info('User "%s" does not exist', name)
            self.add_user(
                name,
                ChatUser(name=name, faction=FactionsEnum(actor)),
            )

        self.needs_update = True
        return self[name]

    def update_user_ingame(self, name, in_game):
        self.logger.info('Updating user "%s" in_game to "%s"', name, in_game)
        user = self[name]
        if user.in_game == in_game:
            return
        user.in_game = in_game
        self.needs_update = True

    def set_user(self, author, user):
        self.logger.info('Setting user "%s"', author)
        self[author] = user
        self.needs_update = True


class State:
    def __init__(self, config):
        self.logger = logger.getChild("state")
        self.config = config
        self.got_welcome_message = asyncio.Event()
        self.fake_disconnect: bool = False
        self.game_location: Optional[Path] = None
        self.is_game_running: bool = False
        self.is_author_authorized = asyncio.Event()
        self.is_in_channel = asyncio.Event()
        self.chat_users: ChatUsers[str, ChatUser] = ChatUsers({})
        self.player_money: int = 0
        self.game_related_tasks: list[Task] = []
        self.nick: str = config.nick
        self.last_death: Optional[datetime] = None

    def money_enough(self, amount) -> bool:
        return self.player_money >= amount

    def set_not_in_channel(self):
        self.logger.info("Setting not in channel")
        self.is_in_channel.clear()
        self.chat_users.clear()

    def set_in_channel(self):
        self.logger.info("Setting in channel")
        self.chat_users.update_or_create(
            self.config.nick, self.config.current_faction
        )
        self.is_in_channel.set()
