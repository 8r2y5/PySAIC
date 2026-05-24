from unittest.mock import ANY, call, patch

import pytest

from pysaic.entities import IncomingEvent, IrcEvent
from pysaic.enums import IrcEvents
from pysaic.use_cases.ui.mode_change import ModeChangeUseCase


@pytest.fixture()
def payload():
    return {"mode": "", "nick": "test nick"}


@pytest.fixture
def event(payload):
    return IncomingEvent(
        author="author",
        target="target",
        event=IrcEvent(type=IrcEvents.MODE, payload=payload),
    )


@patch("pysaic.use_cases.ui.mode_change.add_user_update_to_game")
@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_adding_highest_rank_mode(
    mock_UpdateUsersUseCase,
    mock_add_user_update_to_game,
    event,
    payload,
    chat_users,
    user,
    mock_ui,
    mock_state,
):
    # given
    payload["mode"] = "+oa"

    # when
    ModeChangeUseCase.handle(mock_state, mock_ui, chat_users, event)

    # then
    assert user.irc_mode == "@"
    assert mock_UpdateUsersUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]
    mock_add_user_update_to_game.assert_called_once_with(ANY)


@patch("pysaic.use_cases.ui.mode_change.add_user_update_to_game")
@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_removing_highest_rank_mode(
    mock_UpdateUsersUseCase,
    mock_add_user_update_to_game,
    event,
    payload,
    chat_users,
    user,
    mock_ui,
    mock_state,
):
    # given
    payload["mode"] = "-oa"
    user.irc_mode = "&"

    # when
    ModeChangeUseCase.handle(mock_state, mock_ui, chat_users, event)

    # then
    assert user.irc_mode == ""
    assert mock_UpdateUsersUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]
    mock_add_user_update_to_game.assert_called_once_with(ANY)


@patch("pysaic.use_cases.ui.mode_change.add_user_update_to_game")
@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_lowering_rank_from_owner_to_op(
    mock_UpdateUserListUseCase,
    mock_add_user_update_to_game,
    event,
    payload,
    chat_users,
    user,
    mock_ui,
    mock_state,
):
    # given
    payload["mode"] = "+o-a"
    user.irc_mode = "&"

    # when
    ModeChangeUseCase.handle(mock_state, mock_ui, chat_users, event)

    # then
    assert user.irc_mode == "@"
    assert mock_UpdateUserListUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]
    mock_add_user_update_to_game.assert_called_once_with(ANY)


@patch("pysaic.use_cases.ui.mode_change.add_user_update_to_game")
@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_lowering_current_rank_from_owner_to_op(
    mock_UpdateUserListUseCase,
    mock_add_user_update_to_game,
    event,
    payload,
    chat_users,
    user,
    mock_ui,
    mock_state,
):
    # given
    payload["mode"] = "-a"
    user.irc_mode = "&"

    # when
    ModeChangeUseCase.handle(mock_state, mock_ui, chat_users, event)

    # then
    assert user.irc_mode == ""
    assert mock_UpdateUserListUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]
    mock_add_user_update_to_game.assert_called_once_with(ANY)


@patch("pysaic.use_cases.ui.mode_change.add_user_update_to_game")
@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_trying_to_lower_higher_rank(
    mock_UpdateUserListUseCase,
    mock_add_user_update_to_game,
    event,
    payload,
    chat_users,
    user,
    mock_ui,
    mock_state,
):
    # given
    payload["mode"] = "-h"
    user.irc_mode = "&"

    # when
    ModeChangeUseCase.handle(mock_state, mock_ui, chat_users, event)

    # then
    assert user.irc_mode == "&"
    assert mock_UpdateUserListUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]
    mock_add_user_update_to_game.assert_called_once_with(ANY)
