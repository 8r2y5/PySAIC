from enum import Enum, auto


class IrcEvents(Enum):
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
    GAME_CHANNEL_CHANGE = auto()
    CHANGE_CHANNEL = auto()
    NEW_VERSION = auto()
    EXIT = auto()
    RECONNECTING_TO_SERVER = auto()
    NICKNAME_CHANGED = auto()
    OUR_MESSAGE = auto()
    COMMAND = auto()
    OPTIONS_UPDATED = auto()
    UPDATE_UI_USERS_LIST = auto()
    DISCONNECTED_FROM_PDA_NETWORK = auto()
    CONNECTED = auto()
    ACTOR_UPDATE = auto()
    IN_GAME = auto()
    UPDATE_USERS = auto()
