import logging
from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum, auto
from typing import Any, Callable, Optional, Self, Type

import yaml

from pysaic.crc_strings.use_case import random_name
from pysaic.enums import (
    AvatarEnum,
    DeathReportTypeEnum,
    DisconnectOnNetworkDestructionSetting,
    FactionsEnum,
    UserListDisplayModeEnum,
)
from pysaic.use_cases.avatar import (
    calculate_icon_based_on_faction_and_name,
    is_icon_valid,
)
from pysaic.settings import THEMES_PATH, PROJECT_PATH, WORKDIR
from pysaic.use_cases.themes import create_default_themes

CONFIG_FILE = PROJECT_PATH / "config.yml"
PRIO_CONFIG_FILE = WORKDIR / "config.yml"

SERVER_FILE = PROJECT_PATH / "server.yml"
PRIO_SERVER_FILE = WORKDIR / "server.yml"

logger = logging.getLogger(__name__)

NOT_SET = object()


class ConfigFileNames(Enum):
    config = auto()
    server = auto()


def get_config_location(name: ConfigFileNames):
    if name == ConfigFileNames.config:
        return PRIO_CONFIG_FILE if PRIO_CONFIG_FILE.exists() else CONFIG_FILE
    elif name == ConfigFileNames.server:
        return PRIO_SERVER_FILE if PRIO_SERVER_FILE.exists() else SERVER_FILE


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
    version: int = 1
    name: str = "#crcr_english"
    description: str = "English Moderated"
    password: str = ""


def _create_default_channels() -> list[Channel]:
    return [
        Channel(name="#crcr_english", description="English Moderated"),
        Channel(name="#crcr_english_rp", description="English Roleplay"),
        Channel(
            name="#crcr_english_shitposting", description="English Unmoderated"
        ),
    ]


@dataclass
class Server:
    version: int = 1
    host: str = "irc.slashnet.org"
    port: int = 6667
    channels: list[Channel] = field(default_factory=_create_default_channels)
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
            with open(get_config_location(ConfigFileNames.server)) as f:
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
        with open(get_config_location(ConfigFileNames.server), "w") as f:
            yaml.dump(asdict(self), f)

    @classmethod
    def _create_instance_from_config(cls, config: dict):
        return cls(
            host=config["host"],
            port=config["port"],
            channels=[
                Channel(
                    name=channel["name"],
                    description=channel["description"],
                    password=channel.get("password") or "",
                )
                for channel in config["channels"]
            ],
            previous_channel=config["previous_channel"],
            password=config.get("password", ""),
            commands=config.get("commands", []),
        )


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

        return instance.__dict__.get(self.name)

    def __set__(self, instance, value):
        instance.__dict__[self.name] = value

    def load_value(self, config: dict) -> Any:
        value = config.get(self.name, NOT_SET)
        if value is NOT_SET:
            if self.default_factory:
                value = self.default_factory()
            else:
                value = self.default
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

    def load_value(self, config: dict) -> Any | None:
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
        except (ValueError, KeyError, TypeError):
            return self.default

    def dump_value(self, instance) -> Enum | str:
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
class FontConfig:
    version: int = 1
    name: str = "JetBrains Mono"
    size: int = 10
    turn_off_bold_font_username_in_list: bool = False
    turn_off_bold_font_username_in_chat: bool = False

    @classmethod
    def load_from_config(cls, config: None | dict[str, int | str] = None):
        try:
            return cls(
                version=config.get("version") or cls.version,
                name=config.get("name") or cls.name,
                size=config.get("size") or cls.size,
                turn_off_bold_font_username_in_list=config.get(
                    "turn_off_bold_font_username_in_list"
                )
                or cls.turn_off_bold_font_username_in_list,
                turn_off_bold_font_username_in_chat=config.get(
                    "turn_off_bold_font_username_in_chat"
                )
                or cls.turn_off_bold_font_username_in_chat,
            )
        except Exception:
            logger.exception("Could not read font config, creating default")
            return cls()


class Colors:
    @classmethod
    def load_from_config(cls, config: None | dict[str, str] = None):
        try:
            return cls(
                **{
                    field: cls._load_field(field, value, config)
                    for field, value in cls.__dataclass_fields__.items()
                }
            )
        except Exception:
            logger.exception("Cannot load config for colors, creating default")
            return cls.load_from_config({})

    @classmethod
    def _load_field(cls, field, value, config):
        field_value = cls.__dict__[field]
        if isinstance(field_value, NestedObjectFiled):
            return field_value.load_value(config)
        return config.get(field) or value.default


@dataclass
class BackgroundColors(Colors):
    version: int = 1
    app: str = "#212121"
    in_between: str = "#282a2c"
    content: str = "#131313"
    active_background: str = "#696969"
    active_foreground: str = "#000000"


@dataclass()
class ContentColors(Colors):
    version: int = 1
    time: str = "#fffaf0"
    text: str = "#f8f8ff"
    highlight: str = "#7f7f7f"
    hyper_link: str = "#3b8ed0"
    information: str = "#add8e6"
    error: str = "#cd0000"
    direct_message: str = "#ff69b4"
    online: str = "#008000"
    offline: str = "#ff0000"
    surge: str = "#5b5bff"
    underground: str = "#5b5bff"
    afk: str = "#ffff00"
    static_nick: str = "#808080"


@dataclass
class FactionColors(Colors):
    version: int = 1
    clear_sky: str = "#00bfff"
    loner: str = "#eedd82"
    ecologist: str = "#ff8c00"
    bandit: str = "#cd6839"
    monolith: str = "#9a32cd"
    duty: str = "#ff3030"
    freedom: str = "#00ff7f"
    mercenary: str = "#1e90ff"
    military: str = "#7ccd7c"
    renegade: str = "#adff2f"
    zombie: str = "#573613"
    anonymous: str = "#573613"
    unisg: str = "#fa8072"
    sin: str = "#8b1c62"


@dataclass
class ColorsConfig(Colors):
    version: int = 1
    content: ContentColors = NestedObjectFiled(ContentColors)
    factions: FactionColors = NestedObjectFiled(FactionColors)
    background: BackgroundColors = NestedObjectFiled(BackgroundColors)
    pressed: str = "#737373"
    slider_arrow: str = "#fffaf0"
    slider_arrow_disabled: str = "#696969"


@dataclass
class Config:
    version: int = ConfigField(default=1)
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
            default=DisconnectOnNetworkDestructionSetting.Random,
        )
    )
    disconnect_when_underground: DisconnectOnNetworkDestructionSetting = (
        EnumField(
            default=DisconnectOnNetworkDestructionSetting.Random,
        )
    )
    block_money_transfer: bool = BoolField(default=True)
    user_list_display: str = EnumField(
        UserListDisplayModeEnum.GroupByFactionWithCounter
    )
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
    theme_name: str = ConfigField(default="pysaic")
    colors: ColorsConfig = NestedObjectFiled(ColorsConfig)
    enable_irc_user_display: bool = BoolField(default=True)
    show_less_information: bool = BoolField(default=False)
    use_static_nick_color: bool = BoolField(default=False)

    @classmethod
    def load_config(cls):
        should_save = False
        try:
            with open(get_config_location(ConfigFileNames.config)) as f:
                config = yaml.safe_load(f)
        except Exception:
            logger.exception("Error loading config file")
            config = cls.default_config()
            should_save = True
        else:
            if not config:
                config = cls.default_config()
                should_save = True

        # Load theme
        theme_name = config.get("theme_name", "pysaic")
        theme_path = THEMES_PATH / f"{theme_name}.yml"
        should_create_theme = False
        if theme_path.exists():
            try:
                with open(theme_path) as f:
                    theme_data = yaml.safe_load(f)
                    if theme_data:
                        config["colors"] = theme_data
            except Exception:
                logger.exception(f"Error loading theme {theme_name}")
                should_create_theme = True
        else:
            should_create_theme = True

        if should_create_theme:
            create_default_themes(config)

        instance = cls.create_instance_from_config(config)
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

            if name == "colors":
                continue

            value = attr.dump_value(self)
            if value is not None:
                data[name] = value

        with open(get_config_location(ConfigFileNames.config), "w") as f:
            yaml.dump(data, f)
            for attr in separate_save:
                attr.save_value(self)

        theme_path = THEMES_PATH / f"{self.theme_name}.yml"
        with open(theme_path, "w") as f:
            yaml.dump(asdict(self.colors), f)

    @classmethod
    def default_config(cls) -> dict:
        # TODO:
        #  try to pull data from CRCR first
        return {}

    @classmethod
    def create_instance_from_config(cls, config: dict) -> Self:
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
    logging.basicConfig(level=logging.DEBUG)
    config = Config.load_config()
    print(config)
    config.save_config()
