from unittest.mock import Mock, call, patch

import pytest

from pysaic.entities import ChatUser, IncomingEvent
from pysaic.enums import AppEventEnum
from pysaic.router.app_event_router import AppEventRouter


@pytest.fixture
def mock_ui():
    return Mock()


@pytest.fixture
def app_event_router(mock_state, mock_config, mock_ui):
    return AppEventRouter(mock_state, mock_config, mock_ui, Mock())


@pytest.mark.parametrize("got_password", (True, False))
@patch(
    "pysaic.router.app_event_router.AppEventRouter._handle_nickname_changed_collision"
)
@patch("pysaic.router.app_event_router.AppEventRouter._add_information_text")
@patch("pysaic.router.app_event_router.AppEventRouter._update_ui_user_list")
@patch("pysaic.router.app_event_router.logger")
def test__handle_nickname_changed_nick_conflict_no_password(
    mock_logger,
    mock__update_ui_user_list,
    mock__add_information_text,
    mock__handle_nickname_changed_collision,
    mock_state,
    mock_config,
    app_event_router,
    got_password,
):
    # given
    mock_state.nick = "old_nick"
    mock_config.nick = "old_nick"
    mock_state.chat_users = {
        "old_nick": ChatUser(name="old_nick"),
        "new_nick": ChatUser(name="new_nick"),
    }
    event = IncomingEvent.create_app_event(
        what=AppEventEnum.NICKNAME_CHANGED,
        payload={"nick": "new_nick", "got_password": got_password},
    )

    # when
    app_event_router.event = event
    app_event_router._handle_nickname_changed()

    # then
    assert mock_state.nick == "old_nick"
    assert mock_config.nick == "old_nick"
    assert mock_logger.mock_calls == [
        call.debug("Handling NICKNAME_CHANGED event"),
    ]
    mock_config.save_config.assert_not_called()
    mock__update_ui_user_list.assert_not_called()
    mock__add_information_text.assert_not_called()
    mock__handle_nickname_changed_collision.assert_called_once_with("new_nick")


@patch("pysaic.router.app_event_router.AppEventRouter._add_information_text")
@patch("pysaic.router.app_event_router.AppEventRouter._update_ui_user_list")
@patch("pysaic.router.app_event_router.logger")
def test__handle_nickname_changed_happy_path_with_password_no_other_nick(
    mock_logger,
    mock__update_ui_user_list,
    mock__add_information_text,
    mock_state,
    mock_ui,
    mock_config,
    app_event_router,
):
    # given
    mock_state.nick = "old_nick"
    mock_state.player.create_chat_user.return_value = ChatUser(
        name="test_new_nick"
    )
    mock_config.nick = "old_nick"
    mock_state.chat_users = {
        "old_nick": ChatUser(name="old_nick"),
    }
    event = IncomingEvent.create_app_event(
        what=AppEventEnum.NICKNAME_CHANGED,
        payload={"nick": "test_new_nick", "got_password": True},
    )

    # when
    app_event_router.event = event
    app_event_router._handle_nickname_changed()

    # then
    assert mock_state.nick == "test_new_nick"
    assert mock_config.nick == "old_nick"
    mock_config.save_config.assert_not_called()
    assert mock_logger.mock_calls == [
        call.debug("Handling NICKNAME_CHANGED event"),
        call.debug(
            'Recovering nick to "%s", temporary switching to %r',
            "old_nick",
            "test_new_nick",
        ),
    ]
    mock__update_ui_user_list.assert_called_once_with()
    mock__add_information_text.assert_called_once_with(
        "Nick changed to 'test_new_nick'"
    )
    mock_state.player.create_chat_user.assert_called_once_with()
    assert mock_state.chat_users.keys() == {"test_new_nick"}
    assert mock_state.chat_users["test_new_nick"].name == "test_new_nick"


@patch("pysaic.router.app_event_router.AppEventRouter._add_information_text")
@patch("pysaic.router.app_event_router.AppEventRouter._update_ui_user_list")
@patch("pysaic.router.app_event_router.logger")
def test__handle_nickname_changed_happy_path_no_password_no_other_nick(
    mock_logger,
    mock__update_ui_user_list,
    mock__add_information_text,
    mock_state,
    mock_ui,
    mock_config,
    app_event_router,
):
    # given
    mock_state.nick = "old_nick"
    mock_state.player.create_chat_user.return_value = ChatUser(
        name="test_new_nick"
    )
    mock_config.nick = "old_nick"
    mock_state.chat_users = {
        "old_nick": ChatUser(name="old_nick"),
    }
    event = IncomingEvent.create_app_event(
        what=AppEventEnum.NICKNAME_CHANGED,
        payload={"nick": "test_new_nick", "got_password": False},
    )

    # when
    app_event_router.event = event
    app_event_router._handle_nickname_changed()

    # then
    assert mock_state.nick == "test_new_nick"
    assert mock_config.nick == "old_nick"

    assert mock_logger.mock_calls == [
        call.debug("Handling NICKNAME_CHANGED event"),
        call.debug(
            'Recovering nick to "%s", temporary switching to %r',
            "old_nick",
            "test_new_nick",
        ),
    ]
    mock__update_ui_user_list.assert_called_once_with()
    mock__add_information_text.assert_called_once_with(
        "Nick changed to 'test_new_nick'"
    )
    mock_state.player.create_chat_user.assert_called_once_with()
    assert mock_state.chat_users.keys() == {"test_new_nick"}
    assert mock_state.chat_users["test_new_nick"].name == "test_new_nick"
