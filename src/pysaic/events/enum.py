from enum import Enum, auto


class GameEvents(Enum):
    NEW_ITEM = auto()
    AFK = auto()
    RANK = auto()
    REPUTATION = auto()
    ACHIEVEMENT = auto()
    PLAYER_LOCATION = auto()
    MONEY_CHANGE = auto()
    DEATH = auto()
    HANDSHAKE = auto()
    CHAT_MESSAGE = auto()
    MESSAGE = auto()
    CONNECTED_TO_PDA_NETWORK = auto()
    ACTOR_UPDATE = auto()
    IN_GAME = auto()
    UPDATE_USERS = auto()
    DISCONNECTED_FROM_PDA_NETWORK = auto()


class UIEvents(Enum):
    NEW_CHANNEL_MESSAGE = auto()
    NEW_DIRECT_MESSAGE = auto()

    USER_LEFT = auto()
    USER_JOINED = auto()
    USER_UPDATE = auto()
    USER_BANNED = auto()
    USER_KICKED = auto()

    CHANNEL_TOPIC = auto()
    CHANNEL_UPDATE = auto()
    CHANNEL_JOIN = auto()
    CHANNEL_PART = auto()


class MessageEvents(Enum):
    ERROR = auto()
    INFORMATION = auto()
    MESSAGE = auto()
    QUERY = auto()
    PAY = auto()


class AppEventEnum(Enum):
    GAME_TRANSPORT_DELETED = auto()
    GAME_TRANSPORT_CREATED = auto()
    COLORS_UPDATED = auto()
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
