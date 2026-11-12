import asyncio
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

import pytest

from pysaic.enums import NetworkDestroyReasonEnum
from pysaic.use_cases.hazard import handle_synced_hazards


@pytest.fixture
def mock_loop():
    return MagicMock(spec=asyncio.AbstractEventLoop)


def test_returns_early_when_sync_hazards_disabled(
    mock_config, mock_state, mock_incoming_queue, mock_loop
):
    mock_config.sync_hazards = False

    handle_synced_hazards(
        raw_reason="surge",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()
    mock_loop.create_task.assert_not_called()


@pytest.mark.parametrize("invalid_reason", [None, "", "   "])
def test_returns_early_when_raw_reason_is_empty_or_none(
    invalid_reason, mock_config, mock_state, mock_incoming_queue, mock_loop
):
    handle_synced_hazards(
        raw_reason=invalid_reason,
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


def test_returns_early_when_user_exists_and_not_in_game(
    mock_config, mock_state, mock_incoming_queue, mock_loop
):
    user_mock = Mock()
    user_mock.in_game = False
    mock_state.chat_users = {"TestUser": user_mock}

    handle_synced_hazards(
        raw_reason="surge",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


def test_returns_early_when_player_not_in_game(
    mock_config, mock_state, mock_incoming_queue, mock_loop
):
    mock_state.player.in_game = False

    handle_synced_hazards(
        raw_reason="surge",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


def test_returns_early_when_player_is_afk(
    mock_config, mock_state, mock_incoming_queue, mock_loop
):
    mock_state.player.afk = True

    handle_synced_hazards(
        raw_reason="surge",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


def test_returns_early_when_reason_is_unhandled(
    mock_config, mock_state, mock_incoming_queue, mock_loop
):
    handle_synced_hazards(
        raw_reason="unknown_hazard",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


@patch("pysaic.use_cases.hazard.datetime")
def test_returns_early_when_cooldown_is_active(
    mock_datetime, mock_config, mock_state, mock_incoming_queue, mock_loop
):
    now = datetime.now()
    mock_state.last_synced_hazard = now - timedelta(minutes=2)
    mock_datetime.now.return_value = now

    handle_synced_hazards(
        raw_reason="surge",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    mock_incoming_queue.create_information_event.assert_not_called()


@pytest.mark.parametrize(
    "raw_reason, expected_name",
    [
        ("emission", "Blowout"),
        ("psy_storm", "Psy Storm"),
    ],
)
@patch("pysaic.use_cases.hazard.datetime")
def test_processes_hazards_successfully(
    mock_datetime,
    raw_reason,
    expected_name,
    mock_config,
    mock_state,
    mock_incoming_queue,
    mock_loop,
):
    now = datetime.now()
    mock_datetime.now.return_value = now
    mock_state.is_currently_under_network_destruction = (
        NetworkDestroyReasonEnum.none
    )

    handle_synced_hazards(
        raw_reason=raw_reason,
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    assert mock_state.last_synced_hazard == now

    expected_msg = (
        f"{expected_name} is coming from TestUser, "
        "it will arrive in approximately 10 sec"
    )
    mock_incoming_queue.create_information_event.assert_called_once_with(
        expected_msg
    )

    mock_loop.create_task.assert_called_once()
    _, kwargs = mock_loop.create_task.call_args
    assert kwargs.get("name") == "trigger_hazard_in_game"


@pytest.mark.asyncio
@patch("pysaic.use_cases.hazard.trigger_hazard_in_game")
@patch("pysaic.use_cases.hazard.asyncio.sleep")
@patch("pysaic.use_cases.hazard.randint", return_value=8)
async def test_async_task_execution(
    mock_randint,
    mock_sleep,
    mock_trigger,
    mock_config,
    mock_state,
    mock_incoming_queue,
    mock_loop,
):
    mock_state.is_currently_under_network_destruction = (
        NetworkDestroyReasonEnum.none
    )
    mock_config.sync_hazards = True

    handle_synced_hazards(
        raw_reason="emission",
        nick="TestUser",
        loop=mock_loop,
        config=mock_config,
        state=mock_state,
        incoming_queue=mock_incoming_queue,
    )

    task_coro = mock_loop.create_task.call_args[0][0]
    await task_coro

    mock_randint.assert_called_once_with(6, 14)
    mock_sleep.assert_called_once_with(8)
    mock_trigger.assert_called_once_with("Surge")
