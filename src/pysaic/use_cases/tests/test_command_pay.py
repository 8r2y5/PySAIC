import pytest

from pysaic.use_cases.command import parse_human_readable


@pytest.mark.parametrize(
    "value,expected_result",
    (
        ("1000", 1000),
        ("1k", 1000),
        ("1kk", 1000000),
        ("1.5K", 1500),
        ("1.532K", 1532),
        ("7.5 K", 7500),
        ("7.6                  K", 7600),
        ("3K K", 3000),
        ("", None),
        (None, None),
        (0, None),
        ("0", 0),
        ("string", None),
    ),
)
def test_parse_human_readable(value, expected_result):
    assert parse_human_readable(value) == expected_result
