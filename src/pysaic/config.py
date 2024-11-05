import logging
from dataclasses import dataclass, asdict
from enum import StrEnum
from typing import Union

import yaml

from pysaic.controllers.ui.user_list import NamesInAlphabeticalOrder
from pysaic.crc_strings.use_case import random_name
from pysaic.enums import FactionsEnum

logger = logging.getLogger(__name__)


class FactionSetting(StrEnum):
    GameSynced = "GameSynced"
    Static = "Static"


@dataclass
class Channel:
    name: str
    description: str


@dataclass
class Server:
    host: str
    port: int
    channels: list[Channel]
    previous_channel: str

    @classmethod
    def create_default(cls):
        return {
            "host": "irc.slashnet.org",
            "port": 6667,
            "channels": [
                {
                    "name": "#crcr_english",
                    "description": "CRCR English Moderated",
                },
            ],
            "previous_channel": "#crcr_english",
        }

    @classmethod
    def load_config(cls):
        exception = False
        try:
            with open("server.yml") as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading config file")
            config = cls.create_default()
            exception = True
        else:
            if not config:
                config = cls.create_default()
                exception = True

        instance = cls(
            host=config["host"],
            port=config["port"],
            channels=[
                Channel(
                    name=channel["name"], description=channel["description"]
                )
                for channel in config["channels"]
            ],
            previous_channel=config["previous_channel"],
        )
        if exception:
            instance.save_config()
        return instance

    def save_config(self):
        with open("server.yml", "w") as f:
            yaml.dump(asdict(self), f)


@dataclass
class Config:
    nick: str
    server: Server
    password: str
    faction_setting: Union[FactionSetting]
    current_faction: FactionsEnum
    news_duration: int = 3250
    chat_key: str = "DIK_RETURN"
    nick_auto_complete_key: str = "DIK_TAB"
    news_sound: bool = True
    close_chat: bool = False
    disconnect_when_blowout_or_underground: bool = False
    block_money_transfer: bool = True
    user_list_display: str = NamesInAlphabeticalOrder.name

    @classmethod
    def load_config(cls):
        exception = False
        try:
            with open("config.yml") as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading config file")
            config = cls._default_config()
            exception = True
        else:
            if not config:
                config = cls._default_config()
                exception = True
        server = Server.load_config()

        instance = cls(
            nick=config["nick"],
            server=server,
            password=config["password"],
            faction_setting=FactionSetting(config["faction_setting"]),
            current_faction=FactionsEnum[
                (config.get("current_faction") or FactionsEnum.Loner.name)
            ],
            news_duration=int(config["news_duration"]),
            chat_key=config["chat_key"],
            nick_auto_complete_key=config["nick_auto_complete_key"],
            news_sound=cls._to_bool(config["news_sound"]),
            close_chat=cls._to_bool(config["close_chat"]),
            disconnect_when_blowout_or_underground=cls._to_bool(
                config["disconnect_when_blowout_or_underground"]
            ),
            block_money_transfer=cls._to_bool(config["block_money_transfer"]),
            user_list_display=config.get("user_list_display")
            or NamesInAlphabeticalOrder.name,
        )
        if exception:
            instance.save_config()
        return instance

    def save_config(self):
        with open("config.yml", "w") as f:
            yaml.dump(
                {
                    "nick": self.nick,
                    "password": self.password,
                    "faction_setting": self.faction_setting.value,
                    "current_faction": self._parse_to_yaml_faction(
                        self.current_faction or FactionsEnum.Loner
                    ),
                    "news_duration": self.news_duration,
                    "chat_key": self.chat_key,
                    "nick_auto_complete_key": self.nick_auto_complete_key,
                    "news_sound": self.news_sound,
                    "close_chat": self.close_chat,
                    "disconnect_when_blowout_or_underground": self.disconnect_when_blowout_or_underground,
                    "block_money_transfer": self.block_money_transfer,
                    "user_list_display": self.user_list_display,
                },
                f,
            )

    @staticmethod
    def _parse_to_yaml_faction(faction):
        try:
            return faction.name
        except AttributeError:
            return faction

    @classmethod
    def _default_config(cls) -> dict:
        return {
            "nick": random_name().replace(" ", "_"),
            "password": "",
            "faction_setting": FactionSetting.GameSynced,
            "current_faction": "Loner",
            "news_duration": 3250,
            "chat_key": "DIK_RETURN",
            "nick_auto_complete_key": "DIK_TAB",
            "news_sound": True,
            "close_chat": False,
            "disconnect_when_blowout_or_underground": True,
            "block_money_transfer": True,
            "user_list_display": NamesInAlphabeticalOrder.name,
        }

    @classmethod
    def _to_bool(cls, param):
        try:
            return param.lower() == "true"
        except AttributeError:
            return param


if __name__ == "__main__":
    config = Config.load_config()
    print(config)
