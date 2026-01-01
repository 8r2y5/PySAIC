import logging
from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Optional, Union

import yaml

from pysaic.controllers.ui.user_list import GroupByFactionWithCounter
from pysaic.enums import (
    AvatarEnum,
    DeathReportTypeEnum,
    FactionsEnum,
    DisconnectOnNetworkDestructionSetting,
)
from pysaic.use_cases.avatar import (
    calculate_icon_based_on_faction_and_name,
    is_icon_valid,
)
from pysaic.crc_strings.use_case import random_name

logger = logging.getLogger(__name__)

DEFAULT_STATIC_AVATAR = f"crc_icon_{FactionsEnum.Loner.value}_1"


class InGameUserDisplayEnum(StrEnum):
    CRCR = "CRCR"
    PySAIC_Compact = "PySAIC Compact"
    PySAIC_Card = "PySAIC Card"


class FactionSetting(StrEnum):
    GameSynced = "GameSynced"
    Static = "Static"


class InGameUserDisplayOrderEnum(StrEnum):
    Faction = "Faction"
    Faction_Counter = "Faction Counter"
    Nick = "Nick"
    OnlineStatus = "Online Status"


@dataclass
class Channel:
    name: str = "#crcr_english"
    description: str = "CRCR English Moderated"


@dataclass
class Server:
    host: str = "irc.slashnet.org"
    port: int = 6667
    channels: list[Channel] = field(default_factory=lambda: [Channel()])
    previous_channel: str = Channel.name
    password: str = ""
    commands: list[str] = field(default_factory=lambda: ["MODE +x {nick}"])

    @classmethod
    def create_default(cls):
        return asdict(cls())

    @classmethod
    def load_config(cls):
        should_save = False
        try:
            with open("server.yml") as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading config file")
            config = cls.create_default()
            should_save = True
        else:
            if not config:
                config = cls.create_default()
                should_save = True

        instance = cls._create_instance_from_config(config)
        if should_save is True:
            instance.save_config()
        return instance

    def save_config(self):
        with open("server.yml", "w") as f:
            yaml.dump(asdict(self), f)

    @classmethod
    def _create_instance_from_config(cls, config: dict):
        return cls(
            host=config["host"],
            port=config["port"],
            channels=[
                Channel(
                    name=channel["name"], description=channel["description"]
                )
                for channel in config["channels"]
            ],
            previous_channel=config["previous_channel"],
            password=config.get("password", ""),
            commands=config.get("commands", []),
        )


@dataclass
class FontConfig:
    name: str = "Segoe UI"
    size: int = 11

    @classmethod
    def load_from_config(cls, config):
        try:
            return cls(
                config.get("name") or cls.name, config.get("size") or cls.size
            )
        except Exception:
            logger.exception("Could not read font config, creating default")
            return cls()


@dataclass
class Config:
    nick: str
    server: Server
    password: str
    faction_setting: FactionSetting = FactionSetting.GameSynced
    current_faction: FactionsEnum = FactionsEnum.Loner
    news_duration: int = 3250
    chat_key: str = "DIK_RETURN"
    nick_auto_complete_key: str = "DIK_TAB"
    news_sound: bool = True
    close_chat: bool = True
    disconnect_when_emission: DisconnectOnNetworkDestructionSetting = (
        DisconnectOnNetworkDestructionSetting.MalformSignalOnly
    )
    disconnect_when_underground: DisconnectOnNetworkDestructionSetting = (
        DisconnectOnNetworkDestructionSetting.MalformSignalOnly
    )
    block_money_transfer: bool = True
    user_list_display: str = GroupByFactionWithCounter.name
    accept_dms_from_not_in_the_channel: bool = False
    avatar: str = AvatarEnum.faction_and_name_based.value
    current_avatar: str = f"{FactionsEnum.Loner.value}_1"
    blocked_users: dict[str, set[str]] = field(default_factory=dict)
    blocked_words: list[str] = field(default_factory=list)
    in_game_users_display: InGameUserDisplayEnum = (
        InGameUserDisplayEnum.PySAIC_Card
    )
    in_game_users_display_order: InGameUserDisplayOrderEnum = (
        InGameUserDisplayOrderEnum.Faction
    )
    faction_colored_nicks: bool = True
    death_report_type: DeathReportTypeEnum = DeathReportTypeEnum.OnlineFactions
    death_reports: bool = True
    pop_up_on_ping: bool = False
    pop_up_sound: bool = True
    font: FontConfig = field(default_factory=FontConfig)

    @classmethod
    def load_config(cls):
        should_save = False
        try:
            with open("config.yml") as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading config file")
            config = cls._default_config()
            should_save = True
        else:
            if not config:
                config = cls._default_config()
                should_save = True

        instance = cls._create_instance_from_config(config)
        changed_avatar = instance.recalculate_avatar()
        if any((should_save, changed_avatar)):
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
                    "disconnect_when_emission": self.disconnect_when_emission.name,
                    "disconnect_when_underground": self.disconnect_when_underground.name,
                    "block_money_transfer": self.block_money_transfer,
                    "user_list_display": self.user_list_display,
                    "avatar": self.avatar,
                    "current_avatar": self.current_avatar,
                    "accept_dms_from_not_in_the_channel": self.accept_dms_from_not_in_the_channel,
                    "blocked_users": self.blocked_users,
                    "blocked_words": self.blocked_words,
                    "in_game_users_display": self.in_game_users_display.name,
                    "in_game_users_display_order": self.in_game_users_display_order.name,
                    "faction_colored_nicks": self.faction_colored_nicks,
                    "death_report_type": self.death_report_type.name,
                    "death_reports": self.death_reports,
                    "pop_up_on_ping": self.pop_up_on_ping,
                    "pop_up_sound": self.pop_up_sound,
                    "font": asdict(self.font),
                },
                f,
            )
            self.server.save_config()

    @staticmethod
    def _parse_to_yaml_faction(faction: Union[FactionsEnum, str]) -> str:
        try:
            return faction.name
        except AttributeError:
            return faction

    @classmethod
    def _default_config(cls) -> dict:
        return {
            "nick": random_name().replace(" ", "_"),
            "password": "",
            "faction_setting": cls.faction_setting.value,
            "current_faction": cls.current_faction.name,
            "news_duration": cls.news_duration,
            "chat_key": cls.chat_key,
            "nick_auto_complete_key": cls.nick_auto_complete_key,
            "news_sound": cls.news_sound,
            "close_chat": cls.close_chat,
            "disconnect_when_emission": cls.disconnect_when_emission,
            "disconnect_when_underground": cls.disconnect_when_underground,
            "block_money_transfer": cls.block_money_transfer,
            "user_list_display": cls.user_list_display,
            "avatar": cls.avatar,
            "current_avatar": cls.current_avatar,
            "accept_dms_from_not_in_the_channel": cls.accept_dms_from_not_in_the_channel,
            "blocked_users": {},
            "blocked_words": [],
            "in_game_users_display": cls.in_game_users_display.name,
            "in_game_users_display_order": cls.in_game_users_display_order.name,
            "faction_colored_nicks": cls.faction_colored_nicks,
            "death_report_type": cls.death_report_type.name,
            "death_reports": cls.death_reports,
            "pop_up_on_ping": cls.pop_up_on_ping,
            "pop_up_sound": cls.pop_up_sound,
            "font": cls.font,
        }

    @classmethod
    def _to_bool(cls, param: str | bool, default: bool = True) -> bool:
        if isinstance(param, bool):
            return param
        try:
            return param.lower() == "true"
        except AttributeError:
            return default

    @classmethod
    def _create_instance_from_config(cls, config: dict):
        current_faction = FactionsEnum[
            config.get("current_faction") or FactionsEnum.Loner.name
        ]
        from pysaic.use_cases.nick import sanitize_nick

        return cls(
            nick=sanitize_nick(config["nick"]),
            server=Server.load_config(),
            password=config["password"],
            faction_setting=FactionSetting(config["faction_setting"]),
            current_faction=current_faction,
            news_duration=int(config["news_duration"]),
            chat_key=config["chat_key"],
            nick_auto_complete_key=config["nick_auto_complete_key"],
            news_sound=cls._to_bool(
                config["news_sound"], default=cls.news_sound
            ),
            close_chat=cls._to_bool(
                config["close_chat"], default=cls.close_chat
            ),
            disconnect_when_emission=cls._to_enum(
                DisconnectOnNetworkDestructionSetting,
                config.get("disconnect_when_emission"),
                default=cls.disconnect_when_emission,
            ),
            disconnect_when_underground=cls._to_enum(
                DisconnectOnNetworkDestructionSetting,
                config.get("disconnect_when_underground"),
                default=cls.disconnect_when_underground,
            ),
            block_money_transfer=cls._to_bool(
                config["block_money_transfer"],
                default=cls.block_money_transfer,
            ),
            user_list_display=config.get("user_list_display")
            or cls.user_list_display,
            accept_dms_from_not_in_the_channel=cls._to_bool(
                config.get("accept_dms_from_not_in_the_channel"),
                default=cls.accept_dms_from_not_in_the_channel,
            ),
            avatar=cls._parse_avatar(config.get("avatar") or cls.avatar),
            current_avatar=cls._parse_static_avatar(
                config.get("current_avatar") or cls.current_avatar,
            ),
            blocked_users=config.get("blocked_users") or {},
            blocked_words=config.get("blocked_words") or {},
            in_game_users_display=InGameUserDisplayEnum[
                config.get("in_game_users_display")
                or cls.in_game_users_display.value
            ],
            in_game_users_display_order=cls._to_enum(
                InGameUserDisplayOrderEnum,
                config.get("in_game_users_display_order"),
                default=cls.in_game_users_display_order.name,
            ),
            faction_colored_nicks=cls._to_bool(
                config.get("faction_colored_nicks"),
                default=cls.faction_colored_nicks,
            ),
            death_report_type=DeathReportTypeEnum[
                config.get("death_report_type") or cls.death_report_type.name
            ],
            death_reports=cls._to_bool(
                config.get("death_reports"), default=cls.death_reports
            ),
            pop_up_on_ping=cls._to_bool(
                config.get("pop_up_on_ping"), default=cls.pop_up_on_ping
            ),
            pop_up_sound=cls._to_bool(
                config.get("pop_up_sound"), default=cls.pop_up_sound
            ),
            font=FontConfig.load_from_config(config),
        )

    @classmethod
    def _parse_static_avatar(cls, value: Optional[str]) -> str:
        if not value:
            return cls.current_avatar

        if is_icon_valid(value):
            logger.debug("Using provided static avatar: %s", value)
            return value
        else:
            logger.warning(
                "Invalid static avatar: %s, defaulting to default",
                value,
            )
            return cls.current_avatar

    @classmethod
    def _parse_avatar(cls, value: Optional[str]) -> str:
        if not value:
            return AvatarEnum.faction_and_name_based.value

        try:
            return AvatarEnum(value).value
        except ValueError:
            logger.warning(
                "Invalid avatar type: %s, defaulting to faction_and_name_based",
                value,
            )
            return AvatarEnum.faction_and_name_based.value

    def recalculate_avatar(self) -> bool:
        if self.avatar == AvatarEnum.static.value:
            logger.debug(
                "Validating static_avatar value: %r",
                self.current_avatar,
            )
            if not is_icon_valid(self.current_avatar):
                logger.warning(
                    "Invalid static avatar: %s, defaulting to faction_and_name_based",
                    self.current_avatar,
                )
                self.current_avatar = calculate_icon_based_on_faction_and_name(
                    self.current_faction.value, self.nick
                )
                return True
            logger.debug("Static avatar is valid: %s", self.current_avatar)
            return False
        elif self.avatar == AvatarEnum.faction_and_name_based.value:
            logger.debug(
                "Recalculating faction and name based avatar for faction: %s",
                self.current_faction,
            )
            value = calculate_icon_based_on_faction_and_name(
                self.current_faction.value, self.nick
            )
            if value != self.current_avatar:
                logger.debug(
                    "Avatar changed from %s to %s",
                    self.current_avatar,
                    value,
                )
                self.current_avatar = value
                self.save_config()
                return True
            return False
        elif self.avatar == AvatarEnum.player.value:
            logger.debug("Setting static_avatar to player avatar")
            if self.current_avatar != "pysaic_icon_player":
                self.current_avatar = "pysaic_icon_player"
                return True
            return False
        else:
            logger.warning(
                "Unknown avatar type: %s, defaulting to faction_and_name_based",
                self.avatar,
            )
            self.avatar = AvatarEnum.faction_and_name_based.value
            self.current_avatar = f"crc_icon_{self.current_faction.value}_1"
            return True

    @classmethod
    def _to_enum(cls, enum_class, value, default):
        try:
            return enum_class[value]
        except (KeyError, TypeError):
            return default


if __name__ == "__main__":
    config = Config.load_config()
    print(config)
