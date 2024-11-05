from enum import Enum, auto


class GameEvents(Enum):
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
