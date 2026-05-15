import logging
from dataclasses import dataclass
from itertools import chain
from typing import Callable, Union

from pysaic.config import Config
from pysaic.controllers.game import add_channel_message_to_game
from pysaic.entities import (
    AppEvent,
    ChatUser,
    GameEvent,
    IncomingEvent,
    IncomingMessage,
    InformationEvent,
    IrcEvent,
    OutgoingCTCP,
)
from pysaic.enums import (
    AppEventEnum,
    FactionsEnum,
    HistoryMessageEnum,
    LocationEnum,
    SAICStateEnum,
    RankEnum,
    ReputationEnum,
    SAICCTCPEnum,
)
from pysaic.router.app_event_router import AppEventRouter
from pysaic.router.game_event_router import GameEventRouter
from pysaic.router.irc_event_router import IrcEventRouter
from pysaic.router.router import Router
from pysaic.settings import (
    APP_IDENTITY,
    START_OF_ACTOR_CHARACTER,
)
from pysaic.state import State
from pysaic.ui.app import App
from pysaic.use_cases.command import CommandUseCase
from pysaic.use_cases.irc_mode_to_user_type import parsed_mode_to_name
from pysaic.use_cases.money_transfer import IncomingMoneyTransferUseCase
from pysaic.use_cases.text import make_content_malformed
from pysaic.use_cases.ui.add_dm_message import AddDmMessage
from pysaic.use_cases.ui.add_message import AddMessageUseCase
from pysaic.use_cases.ui.utils import (
    get_faction_actor,
    normalize_content,
)

logger = logging.getLogger(__name__)


class _InvalidValue:
    pass


INVALID_VALUE = _InvalidValue()


@dataclass
class SaicSyncEntity:
    location: None | str = None
    avatar: None | str = None
    rank: None | str = None
    reputation: None | str = None
    afk: None | str = None
    state: None | str = None
    rest: None | str = None


def parse_saic_sync_v1(line) -> SaicSyncEntity:
    location, avatar, rank, reputation, afk = line.split("/", 4)
    return SaicSyncEntity(
        location=location,
        avatar=avatar,
        rank=rank,
        reputation=reputation,
        afk=afk,
    )


def parse_saic_sync_v2(line) -> SaicSyncEntity:
    location, avatar, rank, reputation, afk, state = line.split("/", 5)
    return SaicSyncEntity(
        location=location,
        avatar=avatar,
        rank=rank,
        reputation=reputation,
        afk=afk,
        state=state,
    )


def parse_saic_sync_v3(line) -> SaicSyncEntity:
    location, avatar, rank, reputation, afk, state, _ = line.split("/", 6)
    return SaicSyncEntity(
        location=location,
        avatar=avatar,
        rank=rank,
        reputation=reputation,
        afk=afk,
        state=state,
    )


class IncomingRouter(Router):
    def __init__(
        self,
        state: State,
        config: Config,
        ui: App,
        event,
    ):
        super().__init__(state, config, ui, event)
        self.handlers = {
            IncomingMessage: self._add_message,
            IncomingEvent: self._add_event,
        }

    @classmethod
    def handle_event(cls, state, config: Config, ui: App, event):
        cls(state, config, ui, event=event)()

    def __call__(self):
        if not (
            isinstance(self.event, IncomingEvent)
            and isinstance(self.event.event, AppEvent)
            and self.event.event.what == AppEventEnum.RAW_IRC_MESSAGE
        ):
            logger.debug("Handling event: %r", self.event)
        handler = self.handlers.get(type(self.event), self._not_found_handler)
        try:
            handler(self.event)
        except Exception:
            logger.critical(
                "Error handling event: %r", self.event, exc_info=True
            )
            self._add_error_text(
                "Error occurred, please provide error logs to creator."
            )

    def _add_message(self, event: IncomingMessage):
        logger.debug("Handling message: %r", event)
        if event.author.nick in self.config.blocked_users:
            self._handle_blocked_user(event)
            return

        for word in self.config.blocked_words:
            if word in event.content:
                logger.debug(
                    'Blocked message from "%s" due to word "%s"',
                    event.author,
                    word,
                )
                return

        if event.author.host in chain(*self.config.blocked_users.values()):
            logger.info(
                'Blocked user based on address "%s" message', event.author
            )
            return

        if event.content.startswith("/"):
            command, *params = event.content[1:].split(" ")
            logger.debug("Handling command: %r, args: %r", command, params)
            CommandUseCase.handle(
                self.state,
                self.config,
                self.ui,
                command,
                " ".join(params),
            )
            return

        if event.content.startswith("\x01") and event.content.endswith("\x01"):
            self._handle_ctcp(event)
            return

        elif event.target[0] == "#":
            self._handle_channel_message(event)

        else:
            self._handle_private_message(event)

    def __str__(self):
        return f"IncomingNewEvent: {self.event}"

    def _add_channel_message(self, event: IncomingMessage):
        logger.debug("Adding channel message: %r", event)
        AddMessageUseCase(self.state, self.config, self.ui, event).execute()

    def _add_event(self, event):
        # TODO: replace with dict mapping or or add them dynamically
        if isinstance(event.event, IrcEvent):
            IrcEventRouter.handle(
                self.state,
                self.config,
                self.ui,
                event,
            )
        elif isinstance(event.event, InformationEvent):
            self._add_information_event(event)
        elif isinstance(event.event, AppEvent):
            AppEventRouter.handle(
                self.state,
                self.config,
                self.ui,
                event,
            )
        elif isinstance(event.event, GameEvent):
            GameEventRouter.handle(
                self.state,
                self.config,
                self.ui,
                event,
            )
        else:
            logger.warning("Unknown event: %r", event)

    def _not_found_handler(self, event):
        logger.warning("Handler not found for event: %r", event)

    def _handle_ctcp(self, event: IncomingMessage):
        message = event.content[1:-1]
        logger.debug("Handling CTCP: %r", message)
        match ctcp := message.split(" ")[0]:
            case SAICCTCPEnum.VERSION | SAICCTCPEnum.CLIENTINFO:
                self._send_ctcp_version(event)
            case SAICCTCPEnum.PING:
                self._send_ctcp_ping(event)
            case SAICCTCPEnum.USERDATA:
                self._send_user_data()
            case SAICCTCPEnum.AMOGUS:
                self._parse_amogus(event.author.nick, message)
            case SAICCTCPEnum.SAICSYNC:
                self._parse_saicsync(event.author.nick, message)
            case SAICCTCPEnum.SAICREP:
                self._parse_saicrep(event.author.nick, message)
            case SAICCTCPEnum.SAICRANK:
                self._parse_saicrank(event.author.nick, message)
            case SAICCTCPEnum.SAICLOC:
                self._parse_saicloc(event.author.nick, message)
            case SAICCTCPEnum.SAICAFK:
                self._parse_saicafk(event.author.nick, message)
            case SAICCTCPEnum.SAICAVATAR:
                self._parse_saicavatar(event.author.nick, message)
            case SAICCTCPEnum.SAICSTATE:
                self._parse_saicstate(event.author.nick, message)
            case _:
                logger.warning("Unknown CTCP: %r", ctcp)

    def _send_ctcp_version(self, event):
        logger.debug("Sending CTCP VERSION")
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=event.author.nick,
                content=f"VERSION {APP_IDENTITY}",
            )
        )

    def _send_ctcp_ping(self, event):
        logger.debug("Sending CTCP PING")
        self.outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=event.author.nick,
                content=f"PING {event.created_at.timestamp()}",
            )
        )

    def _send_user_data(self):
        logger.debug("Sending USERDATA")
        self._send_amogus_message()
        self._send_saicsync_message()

    def _parse_amogus(self, author, content):
        _, data = content.split(" ", 1)
        logger.debug("Parsing AMOGUS: %r", data)
        _, faction, in_game = data.split("/")
        should_update = False

        user = self.chat_users.get(author)
        if user is None:
            should_update = True
            user = ChatUser(name=author)

        try:
            faction = FactionsEnum(faction)
        except Exception:
            logger.exception("Error parsing faction - %r", faction)
            return
        else:
            if user.faction != faction:
                should_update = True
                user.faction = faction

        in_game = in_game.lower() == "true"
        if user.in_game != in_game:
            should_update = True
            user.in_game = in_game

        if not should_update:
            return

        self.chat_users.set_user(author, user)
        self._update_crc_users_data()
        self._update_ui_user_list()

    def _add_channel_message_to_game(self, event: IncomingMessage):
        if START_OF_ACTOR_CHARACTER in event.content:
            author, faction_actor, content = (
                self._get_death_message_author_and_content(event)
            )
        else:
            author, content = event.author.nick, normalize_content(
                event.content
            )
            try:
                faction_actor = get_faction_actor(self.chat_users[author])
            except KeyError:
                self._readd_user_to_chat_users()
                try:
                    faction_actor = get_faction_actor(self.chat_users[author])
                except KeyError:
                    # happens in edge cases when user was deleted from
                    # the list before message was processed
                    faction_actor = FactionsEnum.Anonymous.value

        user = self.chat_users.get(author, ChatUser(name=author))
        self.state.add_message(HistoryMessageEnum.channel, user, content)

        add_channel_message_to_game(
            faction_actor=faction_actor,
            author=author,
            icon_id=user.avatar,
            reputation_author=user.reputation,
            rank_author=user.rank,
            highlight=str(self.nick in event.content),
            user_type=parsed_mode_to_name(user.irc_mode),
            content=content,
        )

    def _parse_saicsync(self, author, content):
        # SAIC: 1/location/avatar/rank/reputation/afk
        logger.debug("Parsing SAICSYNC: %r", content)
        try:
            sync_msg = content.split(" ", 1)[1]
            version, params = sync_msg.split("/", 1)
        except Exception:
            logger.exception("Error parsing SAICSYNC message: %r", content)
            return
        try:
            if version == "1":
                saic_sync = parse_saic_sync_v1(params)
            elif version == "2":
                saic_sync = parse_saic_sync_v2(params)
            elif version == "3":
                saic_sync = parse_saic_sync_v3(params)
            else:
                logger.error("Unsupported SAICSYNC version: %r", version)
                return
        except Exception:
            logger.exception("Error parsing SAICSYNC params: %r", params)
            return

        should_update = False

        location = self._parse_location(saic_sync.location)
        rank = self._parse_rank(saic_sync.rank)
        reputation = self._parse_reputation(saic_sync.reputation)
        afk = self._parse_afk(saic_sync.afk)

        if saic_sync.state is not None:
            state = self._parse_state(saic_sync.state)
        else:
            state = None

        if any(
            (
                location is INVALID_VALUE,
                rank is INVALID_VALUE,
                reputation is INVALID_VALUE,
                afk is INVALID_VALUE,
                state is INVALID_VALUE,
            )
        ):
            logger.error(
                "Error parsing location %r, rank %r, reputation %r, afk %r",
                location,
                rank,
                reputation,
                afk,
            )
            return

        user = self.chat_users.get(author, ChatUser(name=author))
        # Rely on ChatUser.avatar property for validation and calculation
        avatar = saic_sync.avatar

        if user.location != location:
            should_update = True
            user.location = location

        if rank != user.rank:
            should_update = True
            user.rank = rank

        if reputation != user.reputation:
            should_update = True
            user.reputation = reputation

        if user.afk != afk:
            should_update = True
            user.afk = afk

        if user.avatar != avatar:
            should_update = True
            user.avatar = avatar

        if user.state != state:
            should_update = True
            user.state = state

        if not should_update:
            return

        self.chat_users.set_user(author, user)
        self._update_crc_users_data()
        self._update_ui_user_list()

    def _parse_saicrep(self, author, message):
        _, reputation = message.split(" ", 1)[1].split("/")
        logger.debug("Parsing SAICREP: %r", reputation)
        self._parse_saic_generic_update(
            author, self._parse_reputation, "reputation", reputation
        )

    def _parse_saic_generic_update(
        self, author: str, parse_function: Callable, field: str, value: str
    ):
        logger.debug(
            "Parsing SAIC generic for %r, field: %r, value: %r",
            author,
            field,
            value,
        )

        value = parse_function(value)
        if value is INVALID_VALUE:
            logger.error("Invalid value for field %r: %r", field, value)
            return

        user = self.chat_users.get(author)
        if user is None:
            logger.debug(
                "Creating new user %r field %r: %r", author, field, value
            )
            user = ChatUser(name=author, in_game=True, **{field: value})

        elif getattr(user, field) != value:
            logger.debug("Updating user %r field %r: %r", author, field, value)
            setattr(user, field, value)

        else:
            logger.debug(
                "User %r field %r is already up to date: %r",
                author,
                field,
                getattr(user, field),
            )
            return

        self.chat_users.set_user(author, user)
        self._update_crc_users_data()
        self._update_ui_user_list()

    def _parse_saicrank(self, author, message):
        _, rank = message.split(" ", 1)
        logger.debug("Parsing SAICRANK: %r", rank)
        if rank.startswith("1"):
            rank = rank[2:]
        else:
            logger.warning("Unexpected rank version value: %r", rank)
            return

        self._parse_saic_generic_update(author, self._parse_rank, "rank", rank)

    def _parse_saicloc(self, author, message):
        _, location = message.split("/", 1)
        logger.debug("Parsing SAICLOC: %r", location)
        self._parse_saic_generic_update(
            author, self._parse_location, "location", location
        )

    def _handle_blocked_user(self, event):
        logger.info('Blocked user "%s" message', event.author)
        if (
            event.author.host
            not in self.config.blocked_users[event.author.nick]
        ):
            self.config.blocked_users[event.author.nick].add(event.author.host)
            self.config.save_config()

    def _handle_private_message(self, event):
        if event.content.startswith("actor_"):
            IncomingMoneyTransferUseCase(
                self.state, self.config, self.ui, event
            ).execute()
            return

        AddDmMessage(self.state, self.config, self.ui, event).execute()

    def _handle_channel_message(self, event):
        if self.state.should_malform_messages is True:
            event.content = make_content_malformed(event.content)
        self._add_channel_message(event)

    def _parse_saicafk(self, nick, message):
        logger.debug("Parsing %s: %r %r", SAICCTCPEnum.SAICAFK, nick, message)
        _, afk = message.split(" ", 1)[1].split("/")

        if not afk.isdigit():
            logger.error('Invalid AFK value: "%s"', afk)
            return

        self._parse_saic_generic_update(nick, self._parse_afk, "afk", afk)

    @staticmethod
    def _parse_reputation(
        reputation: str,
    ) -> Union[ReputationEnum, INVALID_VALUE]:
        try:
            return ReputationEnum(reputation)
        except Exception:
            logger.warning("Could not parse reputation - %r", reputation)
            return INVALID_VALUE

    @staticmethod
    def _parse_rank(rank: str) -> Union[RankEnum, INVALID_VALUE]:
        try:
            return RankEnum[rank]
        except Exception:
            logger.warning("Error parsing rank - %r", rank)
            return INVALID_VALUE

    @staticmethod
    def _parse_location(location: str) -> Union[LocationEnum, INVALID_VALUE]:
        try:
            return LocationEnum[location]
        except Exception:
            logger.exception("Error parsing location - %r", location)
            return INVALID_VALUE

    def _parse_afk(self, afk: str) -> Union[bool, INVALID_VALUE]:
        try:
            return bool(int(afk))
        except ValueError:
            logger.exception("Error parsing AFK state - %r", afk)
            return INVALID_VALUE

    def _parse_saicavatar(self, nick, message):
        logger.debug("Parsing SAICAVATAR: %r %r", nick, message)
        _, avatar_data = message.split(" ", 1)
        version, avatar = avatar_data.split("/", 1)
        if version != "1":
            logger.error(
                "Unsupported SAICAVATAR version: %r, sent by %r", version, nick
            )
            return

        user = self.chat_users.get(nick)
        if user is None:
            logger.debug("Creating new user %r with avatar %r", nick, avatar)
            user = ChatUser(name=nick, in_game=True, avatar=avatar)
        elif user.avatar != avatar:
            logger.debug("Updating user %r avatar to %r", nick, avatar)
            user.avatar = avatar
        else:
            logger.debug(
                "User %r avatar is already up to date: %r", nick, user.avatar
            )
            return

        self.chat_users.set_user(nick, user)
        self._update_crc_users_data()
        self._update_ui_user_list()

    def _parse_state(self, state: str) -> SAICStateEnum | _InvalidValue:
        try:
            return SAICStateEnum(state)
        except Exception:
            logger.warning("Could not parse state %r", state)
            return INVALID_VALUE

    def _parse_saicstate(self, nick, message):
        _, state = message.split("/")
        self._parse_saic_generic_update(
            nick, self._parse_state, "state", state
        )
