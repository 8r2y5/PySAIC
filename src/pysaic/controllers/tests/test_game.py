import pytest

from pysaic.controllers.game import _get_message_metadata
from pysaic.entities import ChatUser


@pytest.mark.parametrize(
    ("message_type,additional_param,expected_result"),
    (
        ("dm", None, "dm,test_nick"),
        ("money_recv", None, "money_recv,None"),
        ("money_send", None, "money_send,None"),
        ("info", None, "info,"),
        ("error", None, "error,"),
        ("dm", 1337, "dm,test_nick"),
        ("money_recv", 80085, "money_recv,80085"),
        ("money_send", 1337, "money_send,1337"),
        ("info", 1337, "info,"),
        ("error", 80085, "error,"),
    ),
)
def test__get_message_medatada(
    message_type, additional_param, expected_result
):
    chat_user = ChatUser(name="@test_nick")

    assert (
        _get_message_metadata(message_type, chat_user, additional_param)
        == expected_result
    )
