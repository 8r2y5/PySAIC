from tkinter import END
from unittest.mock import Mock, call

from pysaic.use_cases.ui.utils import add_content_of_message_to_messages_list


def test_add_content_of_message_to_messages_list():
    mock_message_list = Mock()
    mock_hyperlinks = Mock()

    def prepare_tags():
        count = 0
        while True:
            yield [f"test prepare_tags {count}"]
            count += 1

    mock_hyperlinks.prepare_tags.side_effect = prepare_tags()

    add_content_of_message_to_messages_list(
        mock_message_list,
        mock_hyperlinks,
        'This is a test message with a link: http://example.com and another link "http://pysaic.com" ',
        ["test tag"],
    )

    assert mock_hyperlinks.mock_calls == [
        call.prepare_tags("http://example.com"),
        call.prepare_tags("http://pysaic.com"),
    ]
    assert mock_message_list.mock_calls == [
        call.insert(END, "This", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "is", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "a", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "test", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "message", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "with", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "a", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "link:", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "", ["test tag"]),
        call.insert(
            END, "http://example.com", ["test tag", "test prepare_tags 0"]
        ),
        call.insert(END, "", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "and", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "another", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "link", ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, '"', ["test tag"]),
        call.insert(
            END, "http://pysaic.com", ["test tag", "test prepare_tags 1"]
        ),
        call.insert(END, '"', ["test tag"]),
        call.insert(END, " ", ["test tag"]),
        call.insert(END, "\n", ["test tag"]),
    ]
