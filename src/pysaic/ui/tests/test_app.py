from unittest.mock import Mock, patch

import pytest

from pysaic.config import Channel, ColorsConfig, Config, FontConfig, Server


@pytest.fixture
def mock_state():
    return Mock()


@pytest.fixture
def mock_server():
    config = Server.create_default()
    config["channels"] = [Channel(**data) for data in config["channels"]]
    return Server(**config)


@pytest.fixture
@patch("pysaic.config.random_name")
def mock_config(mock_random_name, mock_server):
    mock_random_name.return_value = "test_user"

    config_dict = Config._default_config()
    config_dict["server"] = mock_server
    config_dict["colors"] = ColorsConfig()
    config_dict["font"] = FontConfig()
    config = Config(**config_dict)
    return config


@pytest.fixture
def mock_incoming_queue():
    return Mock()


@pytest.fixture
def mock_outgoing_queue():
    return Mock()


@pytest.fixture(scope="function")
def ui_app(mock_state, mock_config, mock_incoming_queue, mock_outgoing_queue):
    from pysaic.ui.app import App

    app = App(
        state=mock_state,
        config=mock_config,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )
    app.enable_input()
    yield app
    app.quit()
    app.destroy()


def test_nick_autocomplete_empty_input(ui_app):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == ""


def test_nick_autocomplete_input_start_with_one_letter_of_user_name(ui_app):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}
    ui_app.input_message.insert(0, "f")

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == "f"


@pytest.mark.parametrize(
    "input_value, expected_result", (("@fo", "@foo"), ("fo", "foo"))
)
def test_nick_autocomplete_input_start_with_two_letters_of_user_name(
    ui_app, input_value, expected_result
):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}
    ui_app.input_message.insert(0, input_value)

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == expected_result


@pytest.mark.parametrize(
    "input_value, expected_result",
    (("something @fo", "something @foo"), ("something fo", "something foo")),
)
def test_nick_autocomplete_input_start_with_something_and_two_letters_of_user_name(
    ui_app, input_value, expected_result
):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}
    ui_app.input_message.insert(0, input_value)
    ui_app.input_message.index("end")

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == expected_result


@pytest.mark.parametrize(
    "input_value, expected_result",
    (
        (
            "something @foo and @ba",
            "something @foo and @bar",
        ),
        (
            "something foo and ba",
            "something foo and bar",
        ),
        (
            "something foo and @ba",
            "something foo and @bar",
        ),
        (
            "something @foo and ba",
            "something @foo and bar",
        ),
    ),
)
def test_nick_autocomplete_another_nick_at_the_end(
    ui_app, input_value, expected_result
):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}
    ui_app.input_message.insert(0, input_value)
    ui_app.input_message.index("end")

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == expected_result


@pytest.mark.parametrize(
    "input_value, index_position, expected_result",
    (
        (
            "something @fo and @bar",
            13,
            "something @foo and @bar",
        ),
        (
            "something fo and bar",
            12,
            "something foo and bar",
        ),
        (
            "something fo and @bar",
            12,
            "something foo and @bar",
        ),
        (
            "something @fo and bar",
            13,
            "something @foo and bar",
        ),
    ),
)
def test_nick_autocomplete_another_nick_at_the_beginning(
    ui_app, input_value, index_position, expected_result
):
    ui_app.pysaic_state.chat_users = {"foo": None, "bar": None}
    ui_app.input_message.insert(0, input_value)
    ui_app.input_message.icursor(index_position)

    ui_app._nick_auto_complete(None)

    assert ui_app.input_message.get() == expected_result
