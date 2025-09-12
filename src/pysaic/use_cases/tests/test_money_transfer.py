from unittest.mock import call, patch

from pysaic.enums import FactionsEnum
from pysaic.settings import END_OF_ACTOR_CHARACTER
from pysaic.use_cases.money_transfer import send_money_use_case


@patch("pysaic.use_cases.money_transfer.OutgoingMessage")
@patch("pysaic.use_cases.money_transfer.logger")
@patch("pysaic.use_cases.money_transfer.IncomingEvent")
@patch("pysaic.use_cases.money_transfer.remove_money_from_player")
def test_player_is_not_in_game(
    mock_remove_money_from_player,
    mock_IncomingEvent,
    mock_logger,
    mock_OutgoingMessage,
    mock_incoming_queue,
    mock_outgoing_queue,
    mock_state,
):
    # given
    mock_state.is_game_running = False
    mock_IncomingEvent.create_information_event.return_value = "test event"

    # when
    assert send_money_use_case("someone", 100) is False

    # then
    assert mock_logger.mock_calls == [
        call.debug("Game is not running in order to send money.")
    ]
    assert mock_outgoing_queue.mock_calls == []
    assert mock_incoming_queue.mock_calls == [call.put_nowait("test event")]
    mock_IncomingEvent.create_information_event.assert_called_once_with(
        "You need to be in game to send money."
    )
    mock_remove_money_from_player.assert_not_called()
    mock_OutgoingMessage.assert_not_called()


@patch("pysaic.use_cases.money_transfer.OutgoingMessage")
@patch("pysaic.use_cases.money_transfer.logger")
@patch("pysaic.use_cases.money_transfer.IncomingEvent")
@patch("pysaic.use_cases.money_transfer.remove_money_from_player")
def test_player_in_game_but_transfer_blocked_in_config(
    mock_remove_money_from_player,
    mock_IncomingEvent,
    mock_logger,
    mock_OutgoingMessage,
    mock_incoming_queue,
    mock_outgoing_queue,
    mock_state,
    mock_config,
):
    # given
    mock_state.is_game_running = True
    mock_IncomingEvent.create_information_event.return_value = "test event"
    mock_config.block_money_transfer = True

    # when
    assert send_money_use_case("someone", 100) is False

    # then
    assert mock_logger.mock_calls == [call.debug("Money transfer is blocked.")]
    assert mock_outgoing_queue.mock_calls == []
    assert mock_incoming_queue.mock_calls == [call.put_nowait("test event")]
    mock_IncomingEvent.create_information_event.assert_called_once_with(
        "Money transfer is blocked. Change it in the settings."
    )
    mock_remove_money_from_player.assert_not_called()
    mock_OutgoingMessage.assert_not_called()


@patch("pysaic.use_cases.money_transfer.OutgoingMessage")
@patch("pysaic.use_cases.money_transfer.logger")
@patch("pysaic.use_cases.money_transfer.IncomingEvent")
@patch("pysaic.use_cases.money_transfer.remove_money_from_player")
def test_player_does_not_have_enough_money(
    mock_remove_money_from_player,
    mock_IncomingEvent,
    mock_logger,
    mock_OutgoingMessage,
    mock_incoming_queue,
    mock_outgoing_queue,
    mock_state,
    mock_config,
):
    # given
    mock_state.is_game_running = True
    mock_state.money_enough.return_value = False
    mock_IncomingEvent.create_information_event.return_value = "test event"
    mock_config.block_money_transfer = False

    # when
    assert send_money_use_case("someone", 100) is False

    # then
    assert mock_logger.mock_calls == [call.debug("Not enough money to send.")]
    assert mock_outgoing_queue.mock_calls == []
    assert mock_incoming_queue.mock_calls == [call.put_nowait("test event")]
    mock_IncomingEvent.create_information_event.assert_called_once_with(
        "You don't have enough money to send."
    )
    mock_state.money_enough.assert_called_once_with(100)
    mock_remove_money_from_player.assert_not_called()
    mock_OutgoingMessage.assert_not_called()


@patch("pysaic.use_cases.money_transfer.OutgoingMessage")
@patch("pysaic.use_cases.money_transfer.logger")
@patch("pysaic.use_cases.money_transfer.IncomingEvent")
@patch("pysaic.use_cases.money_transfer.remove_money_from_player")
def test_money_transfer_happy_path(
    mock_remove_money_from_player,
    mock_IncomingEvent,
    mock_logger,
    mock_OutgoingMessage,
    mock_incoming_queue,
    mock_outgoing_queue,
    mock_state,
    mock_config,
):
    # given
    mock_state.is_game_running = True
    mock_state.money_enough.return_value = True
    mock_IncomingEvent.create_information_event.return_value = "test event"
    mock_OutgoingMessage.return_value = "test outgoing message"
    mock_config.block_money_transfer = False
    mock_config.current_faction = FactionsEnum.Loner

    # when
    assert send_money_use_case("someone", 100) is True

    # then
    assert mock_logger.mock_calls == [
        call.debug("Sending money %r to %r", 100, "someone")
    ]
    assert mock_outgoing_queue.mock_calls == [
        call.put_nowait("test outgoing message")
    ]
    assert mock_incoming_queue.mock_calls == []
    mock_IncomingEvent.create_information_event.assert_not_called()
    mock_state.money_enough.assert_called_once_with(100)
    mock_remove_money_from_player.assert_called_once_with(
        mock_state.player, "someone", 100
    )
    mock_OutgoingMessage.assert_called_once_with(
        target="someone",
        content=f"{FactionsEnum.Loner.value} pay {END_OF_ACTOR_CHARACTER} 100",
    )
