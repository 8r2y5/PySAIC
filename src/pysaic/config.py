import logging
from dataclasses import asdict, dataclass, field, MISSING
from enum import StrEnum
from typing import Optional, Callable, Any, Self

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


def config_field(
    *,
    default: Any = MISSING,
    default_factory: Any = MISSING,
    init=True,
    repr=True,
    hash=None,
    compare=True,
    kw_only=MISSING,
    loading: None | Callable = None,
    dumping: None | Callable = None,
    own_save: bool = False,
):
    return field(
        default=default,
        default_factory=default_factory,
        init=init,
        repr=repr,
        hash=hash,
        compare=compare,
        metadata={
            "loading": loading,
            "dumping": dumping,
            "own_save": own_save,
        },
        kw_only=kw_only,
    )


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
    renegade: str = "green yellow"
    zombie: str = "black"
    anonymous: str = "black"
    unisg: str = "salmon"
    sin: str = "maroon4"
    direct_message: str = "hot pink"
    online: str = "green"
    offline: str = "red"
    afk: str = "yellow"
    background: str = "gray30"

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
    name: str = "Segoe UI"
    size: int = 11

    @classmethod
    def load_from_config(cls, config: None | dict[str, int | str] = None):
        try:
            return cls(
                config.get("name") or cls.name, config.get("size") or cls.size
            )
        except Exception:
            logger.exception("Could not read font config, creating default")
            return cls()


def to_enum(enum_class, value, default):
    try:
        return enum_class[value]
    except (KeyError, TypeError):
        return default


def _to_bool(param: str | bool, default: bool = True) -> bool:
    if isinstance(param, bool):
        return param
    try:
        return param.lower() == "true"
    except AttributeError:
        return default


def config_bool_field(field_name, default):
    return config_field(
        default=default, loading=lambda x: _to_bool(x.get(field_name), default)
    )


def config_enum_field(field_name, default):
    return config_field(
        default=default,
        loading=lambda x: to_enum(
            default.__class__,
            x.get(field_name),
            default=default,
        ),
        dumping=lambda x: getattr(x, field_name).name,
    )


def load_and_sanitize_nick(config):
    from pysaic.use_cases.nick import sanitize_nick

    return sanitize_nick(config.get("nick") or random_name().replace(" ", "_"))


@dataclass
class Config:
    nick: str = config_field(
        default=lambda x: random_name().replace(" ", "_"),
        loading=load_and_sanitize_nick,
    )
    password: str = ""
    server: Server = config_field(
        loading=lambda x: Server.load_config(),
        dumping=lambda x: getattr(x, "server").save_config(),
        own_save=True,
        default_factory=Server,
    )
    faction_setting: FactionSetting = config_enum_field(
        field_name="faction_setting", default=FactionSetting.GameSynced
    )
    current_faction: FactionsEnum = config_enum_field(
        field_name="current_faction", default=FactionsEnum.Loner
    )
    news_duration: int = config_field(
        default=3250, loading=lambda x: int(x.get("news_duration") or 3250)
    )
    chat_key: str = "DIK_RETURN"
    nick_auto_complete_key: str = "DIK_TAB"
    news_sound: bool = config_bool_field("news_sound", True)
    close_chat: bool = config_bool_field("close_chat", True)
    disconnect_when_emission: DisconnectOnNetworkDestructionSetting = (
        config_enum_field(
            field_name="disconnect_when_emission",
            default=DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
        )
    )
    disconnect_when_underground: DisconnectOnNetworkDestructionSetting = (
        config_enum_field(
            field_name="disconnect_when_underground",
            default=DisconnectOnNetworkDestructionSetting.MalformSignalOnly,
        )
    )
    block_money_transfer: bool = config_bool_field(
        "block_money_transfer", True
    )
    user_list_display: str = GroupByFactionWithCounter.name
    accept_dms_from_not_in_the_channel: bool = config_bool_field(
        "accept_dms_from_not_in_the_channel", False
    )
    avatar: str = AvatarEnum.faction_and_name_based.value
    current_avatar: str = f"{FactionsEnum.Loner.value}_1"
    blocked_users: dict[str, set[str]] = field(default_factory=dict)
    blocked_words: list[str] = field(default_factory=list)
    in_game_users_display: InGameUserDisplayEnum = config_enum_field(
        field_name="in_game_users_display",
        default=InGameUserDisplayEnum.PySAIC_Card,
    )
    in_game_users_display_order: InGameUserDisplayOrderEnum = (
        config_enum_field(
            field_name="in_game_users_display_order",
            default=InGameUserDisplayOrderEnum.Faction,
        )
    )
    faction_colored_nicks: bool = config_bool_field(
        "faction_colored_nicks", True
    )
    death_report_type: DeathReportTypeEnum = config_enum_field(
        field_name="death_report_type",
        default=DeathReportTypeEnum.OnlineFactions,
    )
    death_reports: bool = config_bool_field("death_reports", True)
    pop_up_on_ping: bool = config_bool_field("pop_up_on_ping", False)
    pop_up_sound: bool = config_bool_field("pop_up_sound", True)
    font: FontConfig = config_field(
        default_factory=FontConfig,
        loading=lambda x: FontConfig.load_from_config(x.get("font")),
        dumping=lambda x: asdict(x.font),
    )
    colors: ColorsConfig = config_field(
        default_factory=ColorsConfig,
        loading=lambda x: ColorsConfig.load_from_config(x.get("colors")),
        dumping=lambda x: asdict(x.colors),
    )

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
        separate_save = []
        for field_name, field_value in self.__dataclass_fields__.items():
            if (
                field_value.metadata
                and field_value.metadata.get("own_save") is True
            ):
                separate_save.append(field_value.metadata["dumping"])
                continue

            if dump_function := (
                field_value.metadata and field_value.metadata.get("dumping")
            ):
                value = dump_function(self)
            else:
                value = getattr(self, field_name)

            data[field_name] = value

        with open("config.yml", "w") as f:
            yaml.dump(data, f)
            for callable in separate_save:
                callable(self)

    @classmethod
    def _default_config(cls) -> dict:
        return {}

    @classmethod
    def _create_instance_from_config(cls, config: dict) -> Self:
        data = {}
        for field_name, field_value in cls.__dataclass_fields__.items():
            if load_func := (
                field_value.metadata and field_value.metadata.get("loading")
            ):
                value = load_func(config)
            else:
                value = config.get(field_name)

            data[field_name] = value

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


if __name__ == "__main__":
    config = Config.load_config()
    print(config)
    config.save_config()
