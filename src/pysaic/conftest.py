from unittest.mock import Mock, patch

import inject
import pytest

from pysaic.config import Config, Server, Channel
from pysaic.entities import ChatUser, ChatUsers, IncomingQueue, OutgoingQueue
from pysaic.state import State
from pysaic.ui.app import App


@pytest.fixture()
def user():
    return ChatUser("test nick")


@pytest.fixture()
def chat_users(user):
    return ChatUsers({"test nick": user})


@pytest.fixture()
def mock_state(chat_users):
    mock_state = Mock()
    mock_state.nick = "test nick"
    mock_state.chat_users = chat_users
    return mock_state


@pytest.fixture()
def mock_ui():
    mock_ui = Mock()
    mock_ui.users_list_scroll.get.return_value = (0.0, 0.0)
    return mock_ui


@pytest.fixture()
def mock_incoming_queue():
    return Mock()


@pytest.fixture()
def mock_outgoing_queue():
    return Mock()


@pytest.fixture(scope="session")
def mock_server():
    with patch.object(Server, "save_config", return_value=None):
        config = Server.create_default()
        config["channels"] = [Channel(**data) for data in config["channels"]]
        yield Server(**config)


@pytest.fixture()
def mock_config():
    mock_config = Mock()
    mock_config.nick = "test nick"
    mock_config.current_faction = "test faction"
    return mock_config


@pytest.fixture(scope="function", autouse=True)
def setup_injector(
    mock_ui, mock_state, mock_incoming_queue, mock_outgoing_queue, mock_config
):
    def binder(binder):
        binder.bind(App, mock_ui)
        binder.bind(State, mock_state)
        binder.bind(IncomingQueue, mock_incoming_queue)
        binder.bind(OutgoingQueue, mock_outgoing_queue)
        binder.bind(Config, mock_config)

    if inject.is_configured():
        inject.clear()

    return inject.configure(binder)
