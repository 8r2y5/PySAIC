import logging
from enum import Enum, StrEnum, auto

import yaml

from pysaic.settings import LOCATIONS_FOR_ENUM_PATH

logger = logging.getLogger(__name__)


class StateEnum(Enum):
    DISCONNECTED = auto()
    NICK_WAS_FREE = auto()
    RECOVERED_NICK = auto()
    RELEASING_NICK = auto()
    IDENTIFIED = auto()
    IDENTIFYING = auto()
    RECOVERING_NICK = auto()
    INITIALIZING = auto()
    NICK_IN_USE = auto()


class IrcEvents(StrEnum):
    ERR_CHANOPRIVSNEEDED = "482"
    ERR_NOTONCHANNEL = "442"
    # I love democracy
    RPL_WHOISHOST = "378"  # Unreal
    RPL_BANEXPIRED = "378"  # aircd
    RPL_MOTD = "378"  # AustHex
    # different codes for different servers engines

    RPL_USERIP = "307"
    RPL_ENDOFBANLIST = "368"
    RPL_BANLIST = "367"
    ERR_BADCHANMASK = "476"
    ERR_UMODEUNKNOWNFLAG = "501"
    RPL_CREATIONTIME = "329"
    RPL_UMODEIS = "221"
    RPL_ENDOFMODE = "324"
    ERR_WASNOSUCHNICK = "406"
    RPL_WHOREPLY = "352"
    RPL_ENDOFWHO = "315"
    RPL_ENDOFWHOWAS = "369"
    RPL_WHOWASUSER = "314"
    WHOWAS = "WHOWAS"
    WHO = "WHO"
    ERR_NOSUCHNICK = "401"
    WHOIS = "WHOIS"
    USER = "USER"
    TOPIC = "TOPIC"
    KICK = "KICK"
    NICK = "NICK"
    PART = "PART"
    QUIT = "QUIT"
    JOIN = "JOIN"
    PRIVMSG = "PRIVMSG"
    MODE = "MODE"
    NOTICE = "NOTICE"
    END_OF_NAMES = "366"
    NAMES = "353"
    PONG = "PONG"
    PING = "PING"
    Message_of_the_Day_Start = "375"
    Message_of_the_Day_Content = "372"
    Message_of_the_Day_End = "376"
    WELCOME = "001"
    ERROR_NICKNAME_IN_USE = "433"
    RPL_WHOISUSER = "311"
    RPL_WHOISSERVER = "312"
    RPL_WHOISOPERATOR = "313"
    RPL_WHOISIDLE = "317"
    RPL_ENDOFWHOIS = "318"
    RPL_WHOISCHANNELS = "319"
    RPL_LISTSTART = "321"
    CHANNEL_TOPIC = "332"
    NO_SUCH_USER = "401"
    BANNED_FROM_CHANNEL = "474"
    NOT_IN_THE_CHANNEL = "404"
    ERROR_IN_NICKNAME = "432"
    ERROR_NICK_CHANGE_TOO_FAST = "438"


class RankEnum(StrEnum):
    unknown = "unknown"
    novice = "novice"
    trainee = "trainee"
    experienced = "experienced"
    professional = "professional"
    veteran = "veteran"
    expert = "expert"
    master = "master"
    legend = "legend"


class ReputationEnum(StrEnum):
    unknown = "Unknown"
    st_reputation_terrible = "Terrible"
    st_reputation_really_bad = "Dreary"
    st_reputation_very_bad = "Awful"
    st_reputation_bad = "Bad"
    st_reputation_neutral = "Neutral"
    st_reputation_good = "Good"
    st_reputation_very_good = "Great"
    st_reputation_really_good = "Brilliant"
    st_reputation_excellent = "Excellent"


class FactionsEnum(Enum):
    Clear_Sky = "actor_csky"
    Loner = "actor_stalker"
    Ecologist = "actor_ecolog"
    Bandit = "actor_bandit"
    Monolith = "actor_monolith"
    Duty = "actor_dolg"
    Freedom = "actor_freedom"
    Mercenary = "actor_killer"
    Military = "actor_army"
    Renegade = "actor_renegade"
    Zombie = "actor_zombied"
    Anonymous = "actor_anonymous"  # appears in yellow color in-game
    UNISG = "actor_isg"
    SIN = "actor_greh"

    def __str__(self):
        return self.value


class AppEventEnum(Enum):
    FOCUS = auto()
    RAW_IRC_MESSAGE = auto()
    SET_NOT_AFK = auto()
    SET_AFK = auto()
    TOGGLE_AFK = auto()
    CHECK_AFK = auto()
    GAME_CHANNEL_CHANGE = auto()
    CHANGE_CHANNEL = auto()
    NEW_VERSION = auto()
    EXIT = auto()
    CONNECTION_TO_SERVER_ISSUE = auto()
    NICKNAME_CHANGED = auto()
    OUR_MESSAGE = auto()
    COMMAND = auto()
    OPTIONS_UPDATED = auto()
    UPDATE_UI_USERS_LIST = auto()
    DISCONNECTED_FROM_PDA_NETWORK = auto()
    ACTOR_UPDATE = auto()
    IN_GAME = auto()
    UPDATE_USERS = auto()


class AvatarEnum(StrEnum):
    faction_and_name_based = "faction_and_name_based"
    static = "static"
    player = "player"


class DeathReportTypeEnum(StrEnum):
    Faction = "Player Faction"
    Random = "Random"
    OnlineFactions = "Online Factions"


class DisconnectOnNetworkDestructionSetting(StrEnum):
    Never = "Never"
    Always = "Always"
    MalformSignalOnly = "Malform Signal Only"


def _recreate_locations_yaml(locations_data):
    locations_data.update(
        {
            "grimwood": "Grimwood",
            "jupiter": "Jupiter",
            "jupiter_underground": "Jupiter Underground",
            "k00_marsh": "Great Swamp",
            "k01_darkscape": "Darkscape",
            "k02_trucks_cemetery": "Truck Cemetery",
            "l01_escape": "Cordon",
            "l02_garbage": "Garbage",
            "l03_agroprom": "Agroprom",
            "l03u_agr_underground": "Agroprom Underground",
            "l04_darkvalley": "Dark Valley",
            "l04u_labx18": "Lab X-18",
            "l05_bar": "Rostok",
            "l06_rostok": "Wild Territory",
            "l07_military": "Army Warehouses",
            "l08_yantar": "Yantar",
            "l08u_brainlab": "Lab X-16",
            "l09_deadcity": "Dead City",
            "l10_limansk": "Limansk",
            "l10_radar": "Radar",
            "l10_red_forest": "Red Forest",
            "l10u_bunker": "Brain Scorcher",
            "l11_hospital": "Deserted Hospital",
            "l11_pripyat": "Outskirts",
            "l12_stancia": "South of the CNPP",
            "l12_stancia_2": "North of the CNPP",
            "l12u_control_monolith": "Mono Control Center",
            "l12u_sarcofag": "CNPP",
            "l13_generators": "Generators",
            "l13u_warlab": "Warlab",
            "labx8": "Lab X-8",
            "poselok_ug": "Town Yuzhniy",
            "pripyat": "Pripyat",
            "promzona": "Promzone",
            "unknown": "Unknown",
            "y04_pole": "Meadow",
            "zaton": "Zaton",
        }
    )
    try:
        with open(LOCATIONS_FOR_ENUM_PATH, "w", encoding="utf-8") as file:
            yaml.safe_dump(locations_data, file)
    except FileNotFoundError:
        logger.error("Welp, i guess no locations will be set.")


try:
    with open(LOCATIONS_FOR_ENUM_PATH, "r", encoding="utf-8") as file:
        locations_data = yaml.safe_load(file)
except FileNotFoundError:
    locations_data = {}
    _recreate_locations_yaml(locations_data)

if not locations_data or not isinstance(locations_data, dict):
    locations_data = {}
    _recreate_locations_yaml(locations_data)
# Ensure 'unknown' is always present as a default value
locations_data["unknown"] = "Unknown"
LocationEnum = Enum(
    "LocationEnum",
    locations_data.items(),
)
logger.debug("Loaded locations: %s", list(LocationEnum.__members__.keys()))
