import logging
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
from typing import Any, Callable, Optional, Self, Type

import yaml

from pysaic.controllers.ui.user_list import GroupByFactionWithCounter
from pysaic.crc_strings.use_case import random_name
from pysaic.enums import (
    AvatarEnum,
    DeathReportTypeEnum,
    DisconnectOnNetworkDestructionSetting,
    FactionsEnum,
)
from pysaic.use_cases.avatar import (
    calculate_icon_based_on_faction_and_name,
    is_icon_valid,
)

logger = logging.getLogger(__name__)


class InGameUserDisplayEnum(StrEnum):
    CRCR = "CRCR"
    PySAIC_Compact = "PySAIC Compact"
    PySAIC_Card = "PySAIC Card"


class FactionSetting(StrEnum):
    GameSynced = "Game Synced"
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
class ColorsConfig:
    time: str = "floral white"
    text: str = "ghost white"
    highlight: str = "gray50"
    hyper_link: str = "#3B8ED0"
    information: str = "lightblue"
    error: str = "red3"
    clear_sky: str = "deep sky blue"
    loner: str = "light goldenrod"
    ecologist: str = "darkorange"
    bandit: str = "sienna3"
    monolith: str = "DarkOrchid3"
    duty: str = "firebrick1"
    freedom: str = "spring green"
    mercenary: str = "dodgerblue"
    military: str = "PaleGreen3"
    renegade: str = "green yellow"
    zombie: str = "#573613"
    anonymous: str = "#573613"
    unisg: str = "salmon"
    sin: str = "maroon4"
    direct_message: str = "hot pink"
    online: str = "green"
    offline: str = "red"
    afk: str = "yellow"
    background: str = "#212121"
    background_in_between: str = "#282a2c"
    background_light: str = "#131313"
    pressed: str = "gray45"
    slider_arrow: str = "floral white"
    slider_arrow_disabled: str = "dim gray"
    active_background: str = "dim gray"
    active_foreground: str = "black"

    @classmethod
    def load_from_config(cls, config: None | dict[str, str] = None):
        try:
            return cls(
                **{
                    field: config.get(field) or value.default
                    for field, value in cls.__dataclass_fields__.items()
                }
            )
        except Exception:
            logger.exception("Cannot load config for colors, creating default")
            return cls()


@dataclass
class FontConfig:
    name: str = "Jetbrains Mono"
    size: int = 10

    @classmethod
    def load_from_config(cls, config: None | dict[str, int | str] = None):
        try:
            return cls(
                config.get("name") or cls.name, config.get("size") or cls.size
            )
        except Exception:
            logger.exception("Could not read font config, creating default")
            return cls()


def load_and_sanitize_nick(nick):
    from pysaic.use_cases.nick import sanitize_nick

    return sanitize_nick(nick or random_name().replace(" ", "_"))


class ConfigField:
    def __init__(
        self,
        default: Any = None,
        default_factory: Optional[Callable] = None,
        loading: Optional[Callable] = None,
        dumping: Optional[Callable] = None,
    ):
        self.default = default
        self.default_factory = default_factory
        self.loading = loading
        self.dumping = dumping
        self.name: Optional[str] = None

    def __set_name__(self, owner, name):
        self.name = name

    def __get__(self, instance, owner):
        if instance is None:
            return self

        return instance.__dict__.get(
            self.name,
            self.default or self.default_factory and self.default_factory(),
        )

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def load_value(self, config: dict) -> Any:
        value = config.get(self.name, self.default)
        if self.loading and value is not None:
            return self.loading(value)
        return value

    def dump_value(self, instance) -> Any:
        return getattr(instance, self.name)


class BoolField(ConfigField):
    def load_value(self, config: dict) -> bool:
        value = config.get(self.name, self.default)
        if isinstance(value, bool):
            return value
        try:
            return value.lower() == "true"
        except AttributeError:
            return self.default


class EnumField(ConfigField):
    def __init__(self, default: Enum, reverse=False):
        super().__init__(default=default)
        self.enum_cls = default.__class__
        self.reverse = reverse

    def load_value(self, config: dict) -> Enum:
        name = config.get(self.name)
        try:
            return (
                (
                    self.enum_cls(name)
                    if not self.reverse
                    else self.enum_cls[name]
                )
                if name
                else self.default
            )
        except KeyError:
            return self.default

    def dump_value(self, instance) -> str:
        value = getattr(instance, self.name)
        return (
            (value.value if not self.reverse else value.name)
            if isinstance(value, Enum)
            else str(value)
        )


class NestedFileField(ConfigField):
    def __init__(self, klass: Type):
        super().__init__(default_factory=klass)
        self.klass = klass

    def load_value(self, raw_data: dict) -> Any:
        return self.klass.load_config()

    def save_value(self, instance) -> None:
        obj = getattr(instance, self.name)
        obj.save_config()


class NestedObjectFiled(ConfigField):
    def __init__(self, klass: Type):
        super().__init__(default_factory=klass)
        self.klass = klass

    def load_value(self, raw_data: dict) -> Any:
        return self.klass.load_from_config(raw_data.get(self.name))

    def dump_value(self, instance) -> dict:
        return asdict(getattr(instance, self.name))


@dataclass
class Config:
    nick: str = ConfigField(
        default_factory=lambda: random_name().replace(" ", "_"),
        loading=load_and_sanitize_nick,
    )
    password: str = ConfigField(default="")
    server: Server = NestedFileField(Server)
    faction_setting: FactionSetting = EnumField(
        default=FactionSetting.GameSynced
    )
    current_faction: FactionsEnum = EnumField(
        default=FactionsEnum.Loner, reverse=True
    )
    news_duration: int = ConfigField(default=3250)
    chat_key: str = ConfigField(default="DIK_RETURN")
    nick_auto_complete_key: str = ConfigField(default="DIK_TAB")
    news_sound: bool = BoolField(default=True)
    close_chat: bool = BoolField(default=True)
    disconnect_when_emission: DisconnectOnNetworkDestructionSetting = (
        EnumField(
            default=DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
        )
    )
    disconnect_when_underground: DisconnectOnNetworkDestructionSetting = (
        EnumField(
            default=DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
        )
    )
    block_money_transfer: bool = BoolField(default=True)
    user_list_display: str = ConfigField(GroupByFactionWithCounter.name)
    accept_dms_from_not_in_the_channel: bool = BoolField(default=False)
    avatar: str = EnumField(AvatarEnum.faction_and_name_based)
    current_avatar: str = ConfigField(f"crc_icon_{FactionsEnum.Loner.value}_1")
    blocked_users: dict[str, set[str]] = ConfigField(default_factory=dict)
    blocked_words: list[str] = ConfigField(default_factory=list)
    in_game_users_display: InGameUserDisplayEnum = EnumField(
        default=InGameUserDisplayEnum.PySAIC_Card,
    )
    in_game_users_display_order: InGameUserDisplayOrderEnum = EnumField(
        default=InGameUserDisplayOrderEnum.Faction
    )
    faction_colored_nicks: bool = BoolField(default=True)
    death_report_type: DeathReportTypeEnum = EnumField(
        default=DeathReportTypeEnum.OnlineFactions,
    )
    death_reports: bool = BoolField(default=True)
    pop_up_on_ping: bool = BoolField(default=False)
    pop_up_sound: bool = BoolField(default=True)
    font: FontConfig = NestedObjectFiled(FontConfig)
    colors: ColorsConfig = NestedObjectFiled(ColorsConfig)

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
        data = {}
        separate_save: list[NestedFileField] = []
        for name, attr in self.__class__.__dict__.items():
            if not isinstance(attr, ConfigField):
                continue

            if isinstance(attr, NestedFileField):
                separate_save.append(attr)
                continue

            value = attr.dump_value(self)
            if value is not None:
                data[name] = value

        with open("config.yml", "w") as f:
            yaml.dump(data, f)
            for attr in separate_save:
                attr.save_value(self)

    @classmethod
    def _default_config(cls) -> dict:
        return {}

    @classmethod
    def _create_instance_from_config(cls, config: dict) -> Self:
        data = {}
        for name, attr in cls.__dict__.items():
            if isinstance(attr, ConfigField):
                data[name] = attr.load_value(config)

        return cls(**data)

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
        if self.avatar == AvatarEnum.static:
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
        elif self.avatar == AvatarEnum.faction_and_name_based:
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
        elif self.avatar == AvatarEnum.player:
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


if __name__ == "__main__":
    config = Config.load_config()
    print(config)
    config.save_config()
