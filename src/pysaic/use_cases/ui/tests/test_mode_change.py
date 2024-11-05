from unittest.mock import Mock, patch, call

import inject
import pytest

from pysaic.config import Config
from pysaic.entities import (
    IncomingEvent,
    IrcEvent,
    ChatUser,
    OutgoingQueue,
    IncomingQueue,
)
from pysaic.enums import IrcEvents
from pysaic.state import ChatUsers, State
from pysaic.ui.app import App
from pysaic.use_cases.ui.mode_change import ModeChangeUseCase


@pytest.fixture()
def mock_state(chat_users):
    mock_state = Mock()
    mock_state.chat_users = chat_users
    return mock_state


@pytest.fixture()
def mock_ui():
    mock_ui = Mock()
    mock_ui.users_list_scroll.get.return_value = (0.0, 0.0)
    return mock_ui


@pytest.fixture(scope="function", autouse=True)
def setup_injector(mock_ui, mock_state):
    def binder(binder):
        binder.bind(App, mock_ui)
        binder.bind(State, mock_state)
        binder.bind(IncomingQueue, Mock())
        binder.bind(OutgoingQueue, Mock())
        binder.bind(Config, Mock())

    if inject.is_configured():
        inject.clear()

    return inject.configure(binder)


@pytest.fixture()
def user():
    return ChatUser("brzys")


@pytest.fixture()
def chat_users(user):
    return ChatUsers({"brzys": user})


@pytest.fixture()
def payload():
    return {"mode": "", "nick": "brzys"}


@pytest.fixture
def event(payload):
    return IncomingEvent(
        author="author",
        target="target",
        event=IrcEvent(type=IrcEvents.MODE, payload=payload),
    )


@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_adding_highest_rank_mode(
    mock_UpdateUsersUseCase,
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
    assert user.irc_mode == "&"
    assert mock_UpdateUsersUseCase.mock_calls == [
        call(mock_state, mock_ui),
        call().execute(),
    ]


@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_removing_highest_rank_mode(
    mock_UpdateUsersUseCase,
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


@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_lowering_rank_from_owner_to_op(
    mock_UpdateUserListUseCase,
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


@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_lowering_current_rank_from_owner_to_op(
    mock_UpdateUserListUseCase,
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


@patch("pysaic.use_cases.ui.mode_change.UpdateUsersUseCase")
def test_trying_to_lower_higher_rank(
    mock_UpdateUserListUseCase,
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
