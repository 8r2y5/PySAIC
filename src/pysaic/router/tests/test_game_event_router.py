import asyncio
import contextlib
from datetime import UTC
from unittest.mock import Mock, call, patch

import pytest

from pysaic.entities import IncomingEvent, IrcUser
from pysaic.enums import (
    AppEventEnum,
    LocationEnum,
    RankEnum,
    ReputationEnum,
    SAICCTCPEnum,
)
from pysaic.events.enum import GameEvents
from pysaic.script_reader.entities import Achievement, Handshake
from pysaic.settings import LOCATIONS_FOR_ENUM_PATH


@contextlib.contextmanager
def threadsafe_coroutine():
    with patch("asyncio.run_coroutine_threadsafe") as mock_threadsafe:

        def side_effect(coro, loop):
            return asyncio.create_task(coro)

        mock_threadsafe.side_effect = side_effect
        yield


@contextlib.contextmanager
def patch_saicsync(game_event_router):
    with patch.object(
        game_event_router, "_send_saicsync_message"
    ) as mock_full_sync:
        yield mock_full_sync


@pytest.fixture
def mock_ui():
    return Mock()


@pytest.fixture
def game_event_router(mock_state, mock_config, mock_ui):
    from pysaic.router.game_event_router import GameEventRouter

    return GameEventRouter(mock_state, mock_config, mock_ui, Mock())


@pytest.mark.parametrize("money_value", ("37", 37.0, 37))
def test__handle_money_change(
    mock_state, mock_config, game_event_router, money_value
):
    # given
    mock_state.player.money = 1300
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.MONEY_CHANGE, money_value
    )

    # when
    game_event_router._handle_money_change()

    # then
    assert mock_state.player.money == 37


@patch("pysaic.router.game_event_router.SUPPORTED_SCRIPT_VERSION", ("6", 7))
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.GameEventRouter._add_error_text")
def test__handle_game_handshake_not_supported_version(
    mock__add_error_text, mock_logger, game_event_router
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.HANDSHAKE, Handshake("not existing version", "test value")
    )

    # when
    game_event_router._handle_game_handshake()

    # then
    mock_logger.error.assert_called_once_with(
        "Unsupported handshake version: %r", "not existing version"
    )
    mock__add_error_text.assert_called_once_with(
        "[PySAIC] Please update your game script. "
        "Use one provided in the 7zip package. "
        "Current version: not existing version. "
        "Required versions: 6 or 7"
    )


@patch(
    "pysaic.router.game_event_router.SUPPORTED_SCRIPT_VERSION",
    ("5", "test value"),
)
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.GameEventRouter._add_error_text")
def test__handle_game_handshake_happy_path(
    mock__add_error_text, mock_logger, game_event_router
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.HANDSHAKE, Handshake("test value", "test value")
    )

    # when
    game_event_router._handle_game_handshake()

    # then
    mock_logger.error.assert_not_called()
    mock__add_error_text.assert_not_called()


@patch("pysaic.router.game_event_router.OutgoingCTCP")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_location(
    mock_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
):
    # given
    mock_config.server.previous_channel = "test channel"
    mock_state.player.location = LocationEnum.k02_trucks_cemetery
    mock_OutgoingCTCP.return_value = "test outgoing ctcp"

    # when
    game_event_router._send_saic_location()

    # then
    mock_logger.info.assert_called_once_with(
        'Sending "%s" message', SAICCTCPEnum.SAICLOC
    )
    mock_OutgoingCTCP.assert_called_once_with(
        target=mock_config.server.previous_channel,
        content=f"SAICLOC 1/{LocationEnum.k02_trucks_cemetery.name}",
    )
    mock_ui.outgoing_queue.put_nowait.assert_called_once_with(
        "test outgoing ctcp"
    )


@patch("pysaic.router.game_event_router.add_user_update_to_game")
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.GameEventRouter._add_error_text")
@patch("pysaic.router.game_event_router.GameEventRouter._send_saic_location")
def test__handle_player_location_unknown_or_invalid_location(
    mock__send_saic_location,
    mock__add_error_text,
    mock_logger,
    mock_add_user_update_to_game,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.PLAYER_LOCATION, "test location"
    )
    previous_state_location = mock_state.player.location
    previous_user_location = chat_users["test nick"].location

    # when
    game_event_router._handle_player_location()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling PLAYER_LOCATION event"),
        call.debug(
            "Invalid %r value: %r", "location", "test location", exc_info=True
        ),
        call.exception("Unknown location: %r", "test location"),
    ]
    mock__send_saic_location.assert_not_called()
    mock_add_user_update_to_game.assert_not_called()
    mock__add_error_text.assert_called_once_with(
        "Unknown location: test location. "
        f"Please add it to {LOCATIONS_FOR_ENUM_PATH} and restart the app."
    )
    assert mock_state.player.location == previous_state_location
    assert chat_users["test nick"].location == previous_user_location


@pytest.mark.asyncio
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
@patch("pysaic.router.game_event_router.GameEventRouter._add_error_text")
async def test__handle_player_location_happy_path_with_callback(
    mock__add_error_text,
    mock_add_user_update_to_game,
    mock_logger,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.PLAYER_LOCATION, "k02_trucks_cemetery"
    )
    previous_state_location = mock_state.player.location
    previous_user_location = chat_users["test nick"].location

    # when
    with (
        threadsafe_coroutine(),
        patch_saicsync(game_event_router) as mock_saic_sync,
        patch.object(
            game_event_router, "_send_saic_location"
        ) as mock__send_saic_location,
    ):
        game_event_router._handle_player_location()
        task = mock_state.player_update_task
        assert task is not None
        await task

    # then
    mock_saic_sync.assert_not_called()
    mock__send_saic_location.assert_called_once_with()
    assert mock_logger.mock_calls == [
        call.debug("Handling PLAYER_LOCATION event"),
        call.debug(
            "Syncing changes: %s",
            {"location": LocationEnum.k02_trucks_cemetery},
        ),
    ]
    mock_add_user_update_to_game.assert_called_once()
    mock__add_error_text.assert_not_called()
    assert previous_state_location != LocationEnum.k02_trucks_cemetery
    assert previous_user_location != LocationEnum.k02_trucks_cemetery
    assert mock_state.player.location == LocationEnum.k02_trucks_cemetery
    assert chat_users["test nick"].location == LocationEnum.k02_trucks_cemetery


@patch("pysaic.router.game_event_router.GameEventRouter._send_saic_location")
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
@patch("pysaic.router.game_event_router.GameEventRouter._add_error_text")
def test__handle_player_location_happy_path_without_callback(
    mock__add_error_text,
    mock_add_user_update_to_game,
    mock_logger,
    mock__send_saic_location,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    mock_state.player.location = LocationEnum.k02_trucks_cemetery
    chat_users["test nick"].location = LocationEnum.k02_trucks_cemetery
    previous_state_location = mock_state.player.location
    previous_user_location = chat_users["test nick"].location
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.PLAYER_LOCATION, "k02_trucks_cemetery"
    )

    # when
    game_event_router._handle_player_location()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling PLAYER_LOCATION event"),
        call.debug(
            "Value for field %r is the same, skipping update", "location"
        ),
    ]
    mock__send_saic_location.assert_not_called()
    mock_add_user_update_to_game.assert_not_called()
    mock__add_error_text.assert_not_called()
    assert previous_state_location == LocationEnum.k02_trucks_cemetery
    assert previous_user_location == LocationEnum.k02_trucks_cemetery
    assert mock_state.player.location == LocationEnum.k02_trucks_cemetery
    assert chat_users["test nick"].location == LocationEnum.k02_trucks_cemetery


@patch("pysaic.router.game_event_router.IncomingMessage")
@patch("pysaic.router.game_event_router.OutgoingMessage")
@pytest.mark.asyncio
async def test__handle_new_achievement(
    mock_OutgoingMessage,
    mock_IncomingMessage,
    mock_ui,
    mock_state,
    mock_config,
    game_event_router,
):
    # given
    loop = asyncio.get_running_loop()
    mock_state.is_in_channel = asyncio.Event()
    mock_state.is_in_channel.set()
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.ACHIEVEMENT,
        Achievement("test achievement", "test game_enum"),
    )
    mock_OutgoingMessage.return_value = "test outgoing message"
    mock_IncomingMessage.return_value = "test incoming message"
    expected_message = 'Just unlocked achievement "test achievement".'

    # when
    game_event_router._handle_new_achievement(loop)
    tasks = [
        t for t in asyncio.all_tasks(loop) if t != asyncio.current_task(loop)
    ]
    if tasks:
        await asyncio.gather(*tasks)

    # then
    mock_OutgoingMessage.assert_called_once_with(
        target=mock_config.server.previous_channel,
        content=expected_message,
    )
    mock_ui.outgoing_queue.put_nowait.assert_called_once_with(
        "test outgoing message"
    )
    mock_IncomingMessage.assert_called_once_with(
        author=IrcUser("test nick", None, None),
        target=mock_config.server.previous_channel,
        content=expected_message,
    )
    mock_ui.incoming_queue.put_nowait.assert_called_once_with(
        "test incoming message"
    )


@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
def test__handle_rank_invalid_rank(
    mock_add_user_update_to_game,
    mock_logger,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.RANK, "test rank"
    )
    previous_state_rank = mock_state.player.rank
    previous_user_rank = chat_users["test nick"].rank

    # when
    game_event_router._handle_rank()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling GAME_RANK event"),
        call.debug("Invalid %r value: %r", "rank", "test rank", exc_info=True),
    ]

    mock_add_user_update_to_game.assert_not_called()
    assert mock_state.player.rank == previous_state_rank
    assert chat_users["test nick"].rank == previous_user_rank


@pytest.mark.asyncio
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
async def test__handle_rank_happy_path(
    mock_add_user_update_to_game,
    mock_logger,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.RANK, RankEnum.professional.value
    )
    previous_state_rank = mock_state.player.rank
    previous_user_rank = chat_users["test nick"].rank

    # when
    with (
        threadsafe_coroutine(),
        patch_saicsync(game_event_router) as mock_full_sync,
        patch.object(
            game_event_router, "_send_saic_rank"
        ) as mock__send_saic_rank,
    ):
        game_event_router._handle_rank()
        task = mock_state.player_update_task
        assert task is not None
        await task

    # then
    mock__send_saic_rank.assert_called_once_with()
    mock_full_sync.assert_not_called()
    assert mock_logger.mock_calls == [
        call.debug("Handling GAME_RANK event"),
        call.debug("Syncing changes: %s", {"rank": RankEnum.professional}),
    ]

    mock_add_user_update_to_game.assert_called_once()
    assert mock_state.player.rank == RankEnum.professional
    assert chat_users["test nick"].rank == RankEnum.professional
    assert mock_state.player.rank != previous_state_rank
    assert chat_users["test nick"].rank != previous_user_rank


@patch("pysaic.router.game_event_router.GameEventRouter._send_saic_reputation")
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
def test__handle_reputation_invalid_value(
    mock_add_user_update_to_game,
    mock_logger,
    mock__send_saic_reputation,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.REPUTATION, "test reputation"
    )
    previous_state_reputation = mock_state.player.reputation
    previous_user_reputation = chat_users["test nick"].reputation

    # when
    game_event_router._handle_reputation()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling GAME_REPUTATION event"),
        call.debug(
            "Invalid %r value: %r",
            "reputation",
            "test reputation",
            exc_info=True,
        ),
    ]

    mock__send_saic_reputation.assert_not_called()
    mock_add_user_update_to_game.assert_not_called()
    assert mock_state.player.reputation == previous_state_reputation
    assert chat_users["test nick"].reputation == previous_user_reputation


@pytest.mark.asyncio
@patch("pysaic.router.game_event_router.logger")
@patch("pysaic.router.game_event_router.add_user_update_to_game")
async def test__handle_reputation_happy_path(
    mock_add_user_update_to_game,
    mock_logger,
    game_event_router,
    mock_state,
    chat_users,
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        GameEvents.REPUTATION, ReputationEnum.st_reputation_bad.name
    )
    previous_state_reputation = mock_state.player.reputation
    previous_user_reputation = chat_users["test nick"].reputation

    # when
    with (
        threadsafe_coroutine(),
        patch_saicsync(game_event_router) as mock_full_sync,
        patch.object(
            game_event_router, "_send_saic_reputation"
        ) as mock__send_saic_reputation,
    ):
        game_event_router._handle_reputation()
        task = mock_state.player_update_task
        assert task is not None
        await task

    # then
    mock__send_saic_reputation.assert_called_once_with()
    mock_full_sync.assert_not_called()
    assert mock_logger.mock_calls == [
        call.debug("Handling GAME_REPUTATION event"),
        call.debug(
            "Syncing changes: %s",
            {"reputation": ReputationEnum.st_reputation_bad},
        ),
    ]

    mock_add_user_update_to_game.assert_called_once()
    assert mock_state.player.reputation == ReputationEnum.st_reputation_bad
    assert (
        chat_users["test nick"].reputation == ReputationEnum.st_reputation_bad
    )
    assert mock_state.player.reputation != previous_state_reputation
    assert chat_users["test nick"].reputation != previous_user_reputation


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_reputation_but_not_connected_to_channel(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
):
    # given
    mock_state.is_in_channel.is_set.return_value = False

    # when
    game_event_router._send_saic_reputation()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_not_called()
    mock_OutgoingCTCP.assert_not_called()
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == []


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_reputation_happy_path(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
    user,
):
    # given
    mock_state.nick = "test nick"
    mock_state.is_in_channel.is_set.return_value = True
    mock_OutgoingCTCP.return_value = "test outgoing ctcp"

    # when
    game_event_router._send_saic_reputation()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_called_once_with(
        "test outgoing ctcp"
    )
    mock_OutgoingCTCP.assert_called_once_with(
        target=mock_config.server.previous_channel,
        content=f"SAICREP 1/{user.reputation.value}",
    )
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == [
        call.debug('Sending "%s" message', "SAICREP"),
    ]


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_reputation_no_user_in_users(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
    chat_users,
):
    # given
    mock_state.is_in_channel.is_set.return_value = True
    mock_OutgoingCTCP.return_value = "test outgoing ctcp"
    del chat_users["test nick"]

    # when
    game_event_router._send_saic_reputation()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_not_called()
    mock_OutgoingCTCP.assert_not_called()
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == [
        call.debug('Sending "%s" message', "SAICREP"),
        call.exception("User was missing in chat_users."),
    ]


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_rank_but_not_connected_to_channel(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
):
    # given
    mock_state.is_in_channel.is_set.return_value = False

    # when
    game_event_router._send_saic_rank()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_not_called()
    mock_OutgoingCTCP.assert_not_called()
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == []


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_rank_happy_path(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
    user,
):
    # given
    mock_state.nick = "test nick"
    mock_state.is_in_channel.is_set.return_value = True
    mock_OutgoingCTCP.return_value = "test outgoing ctcp"

    # when
    game_event_router._send_saic_rank()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_called_once_with(
        "test outgoing ctcp"
    )
    mock_OutgoingCTCP.assert_called_once_with(
        target=mock_config.server.previous_channel,
        content=f"SAICRANK 1/{user.rank}",
    )
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == [
        call.debug('Sending "%s" message', "SAICRANK")
    ]


@patch("pysaic.router.utils.OutgoingCTCP")
@patch("pysaic.router.utils.logger")
@patch("pysaic.router.game_event_router.logger")
def test__send_saic_rank_no_user_in_users(
    mock_game_router_logger,
    mock_utils_logger,
    mock_OutgoingCTCP,
    mock_state,
    mock_config,
    mock_ui,
    game_event_router,
    chat_users,
):
    # given
    mock_state.is_in_channel.is_set.return_value = True
    del chat_users["test nick"]

    # when
    game_event_router._send_saic_rank()

    # then
    mock_ui.outgoing_queue.put_nowait.assert_not_called()
    mock_OutgoingCTCP.assert_not_called()
    assert mock_game_router_logger.mock_calls == []
    assert mock_utils_logger.mock_calls == [
        call.debug('Sending "%s" message', "SAICRANK"),
        call.exception("User was missing in chat_users."),
    ]


@patch("pysaic.router.game_event_router.GameEventRouter._update_ui_user_list")
@patch("pysaic.router.game_event_router.GameEventRouter._add_information_text")
@patch("pysaic.router.game_event_router.datetime")
@patch("pysaic.router.game_event_router.logger")
def test__handle_not_afk_player_not_afk(
    mock_logger,
    mock_datetime,
    mock__add_information_text,
    mock__update_ui_user_list,
    game_event_router,
    mock_state,
    mock_outgoing_queue,
):
    # given
    mock_state.player.afk = False
    mock_state.player.last_ask_update = None
    mock_datetime.now.return_value = "test datetime"

    # when
    game_event_router._handle_not_afk()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling NOT_AFK event"),
    ]
    assert mock_state.player.last_ask_update == "test datetime"
    assert mock_state.player.afk is False
    mock_datetime.now.assert_called_once_with(UTC)
    mock__add_information_text.assert_not_called()
    mock_outgoing_queue.put.assert_not_called()
    mock__update_ui_user_list.assert_not_called()


@patch("pysaic.router.game_event_router.IncomingEvent")
@patch("pysaic.router.game_event_router.datetime")
@patch("pysaic.router.game_event_router.logger")
def test__handle_not_afk_player_is_afk(
    mock_logger,
    mock_datetime,
    mock_IncomingEvent,
    game_event_router,
    mock_state,
    user,
    mock_ui,
):
    # given
    mock_state.player.afk = True
    mock_state.player.last_ask_update = None
    mock_datetime.now.return_value = "test datetime"
    mock_IncomingEvent.create_app_event.return_value = "test incoming_event"

    # when
    game_event_router._handle_not_afk()

    # then
    assert mock_logger.mock_calls == [
        call.debug("Handling NOT_AFK event"),
    ]
    assert mock_state.player.last_ask_update == "test datetime"
    assert mock_state.player.afk is True
    mock_datetime.now.assert_called_once_with(UTC)
    mock_ui.incoming_queue.put_nowait.assert_called_once_with(
        "test incoming_event"
    )
    mock_IncomingEvent.create_app_event(AppEventEnum.SET_NOT_AFK, None)


@pytest.mark.parametrize(
    "event_type, expected_method",
    [
        (GameEvents.ACTOR_UPDATE, "_handle_actor_update"),
        (GameEvents.MONEY_CHANGE, "_handle_money_change"),
        (GameEvents.HANDSHAKE, "_handle_game_handshake"),
        (GameEvents.PLAYER_LOCATION, "_handle_player_location"),
        (GameEvents.ACHIEVEMENT, "_handle_new_achievement"),
        (GameEvents.RANK, "_handle_rank"),
        (GameEvents.REPUTATION, "_handle_reputation"),
        (GameEvents.AFK, None),
    ],
)
@patch("pysaic.router.game_event_router.GameEventRouter._handle_not_afk")
def test_route(
    mock__handle_not_afk, game_event_router, event_type, expected_method
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        event_type, "test payload"
    )

    # when
    if expected_method is None:
        game_event_router.route()
    else:
        with patch(
            f"pysaic.router.game_event_router.GameEventRouter.{expected_method}"
        ) as mock_method:
            game_event_router.route()
        # then really
        mock_method.assert_called_once_with()

    # this should be always called
    mock__handle_not_afk.assert_called_once()


@patch("pysaic.router.game_event_router.GameEventRouter._handle_not_afk")
@patch("pysaic.router.game_event_router.logger")
def test_route_invalid_event_type(
    mock_logger, mock__handle_not_afk, game_event_router
):
    # given
    game_event_router.event = IncomingEvent.create_game_event(
        "INVALID_EVENT_TYPE", "test payload"
    )

    # when
    game_event_router.route()

    # then
    mock_logger.warning.assert_called_once_with(
        "Unknown game event: %r", game_event_router.event
    )
    mock__handle_not_afk.assert_called_once()


@pytest.mark.asyncio
async def test_sync_batching_and_locking_logic(
    game_event_router, mock_state, chat_users
):
    # given
    game_event_router.state = mock_state

    # when
    with (
        threadsafe_coroutine(),
        patch_saicsync(game_event_router) as mock_full_sync,
    ):
        game_event_router.event = IncomingEvent.create_game_event(
            GameEvents.RANK, RankEnum.professional.value
        )
        game_event_router._handle_rank()

        task = mock_state.player_update_task
        assert task is not None

        game_event_router.event = IncomingEvent.create_game_event(
            GameEvents.REPUTATION, ReputationEnum.st_reputation_bad.name
        )
        game_event_router._handle_reputation()
        await task

    mock_full_sync.assert_called_once_with()
    assert mock_state.pending_updates == {}
    assert mock_state.player_update_task is None
