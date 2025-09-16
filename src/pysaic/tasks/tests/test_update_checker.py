from packaging.version import Version

from pysaic.enums import AppEventEnum
from pysaic.tasks.update_checker import _check_for_update
from unittest.mock import Mock, patch, PropertyMock

import pytest


@pytest.fixture
def mock_incoming_queue():
    return Mock()


@pytest.mark.parametrize(
    "url, our_version, should_notify",
    [
        ("https://example.com/1.2.3", "1.0.0", True),
        ("https://example.com/1.0.0", "1.0.0", False),
        ("https://example.com/0.9.9", "1.0.0", False),
        ("https://example.com/2.0.0", "1.0.0", True),
        ("https://example.com/1.0.1", "1.0.0", True),
        ("https://example.com/1.0.0b", "1.0.0", False),
        ("https://example.com/1.0.0", "1.0.0b1", True),
        ("https://example.com/0.3.0", "0.3.0b2", True),
        ("https://example.com/0.3.0b2", "0.3.0b1", True),
        ("https://example.com/0.1.0", "0.3.0b1", False),
        ("https://example.com/0.3.0b1", "0.2.0", False),
    ],
)
@patch("pysaic.tasks.update_checker.logger")
@patch("pysaic.tasks.update_checker.IncomingEvent")
def test__check_for_update(
    mock_IncomingEvent,
    mock_logger,
    mock_incoming_queue,
    url,
    our_version,
    should_notify,
):
    mock_IncomingEvent.create_app_event.return_value = "test incoming_event"
    mock_url = Mock(path=url)

    with patch(
        "pysaic.tasks.update_checker.settings", new_callable=PropertyMock
    ) as mock_settings:
        mock_settings.CURRENT_VERSION = Version(our_version)
        _check_for_update(
            incoming_queue=mock_incoming_queue,
            url=mock_url,
        )

    if should_notify:
        mock_logger.info.assert_called_once_with(
            "New version available: %s", mock_url
        )
        mock_IncomingEvent.create_app_event.assert_called_once_with(
            AppEventEnum.NEW_VERSION, mock_url
        )
        mock_incoming_queue.put_nowait.assert_called_once_with(
            "test incoming_event"
        )
    else:
        mock_IncomingEvent.create_app_event.assert_not_called()
        mock_incoming_queue.put_nowait.assert_not_called()
