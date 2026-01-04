import pytest

from pysaic.controllers.game import _get_message_metadata
from pysaic.entities import ChatUser
from pysaic.enums import HistoryMessageEnum


@pytest.mark.parametrize(
    ("message_type,additional_param,expected_result"),
    (
        (HistoryMessageEnum.dm_to, None, "dm_to,test_nick"),
        (HistoryMessageEnum.dm_from, None, "dm_from,test_nick"),
        (HistoryMessageEnum.money_recv, None, "money_recv,None"),
        (HistoryMessageEnum.money_sent, None, "money_sent,None"),
        (HistoryMessageEnum.info, None, "info,"),
        (HistoryMessageEnum.error, None, "error,"),
        (HistoryMessageEnum.dm_to, 1337, "dm_to,test_nick"),
        (HistoryMessageEnum.dm_from, 1337, "dm_from,test_nick"),
        (HistoryMessageEnum.money_recv, 80085, "money_recv,80085"),
        (HistoryMessageEnum.money_sent, 1337, "money_sent,1337"),
        (HistoryMessageEnum.info, 1337, "info,"),
        (HistoryMessageEnum.error, 80085, "error,"),
    ),
)
def test__get_message_medatada_with_param(
    message_type, additional_param, expected_result
):
    chat_user = ChatUser(name="@test_nick")

    assert (
        _get_message_metadata(message_type, chat_user, additional_param)
        == expected_result
    )


@pytest.mark.parametrize(
    ("message_type,expected_result"),
    (
        (HistoryMessageEnum.dm_to, "dm_to,test_nick"),
        (HistoryMessageEnum.dm_from, "dm_from,test_nick"),
        (HistoryMessageEnum.money_recv, "money_recv,None"),
        (HistoryMessageEnum.money_sent, "money_sent,None"),
        (HistoryMessageEnum.info, "info,"),
        (HistoryMessageEnum.error, "error,"),
    ),
)
def test__get_message_medatada_no_param(message_type, expected_result):
    chat_user = ChatUser(name="@test_nick")

    assert _get_message_metadata(message_type, chat_user) == expected_result
