from unittest.mock import patch

import pytest
from pysaic.config import Config
from pysaic.enums import FactionsEnum


@pytest.mark.parametrize(
    "name,faction,expected_avatar",
    (
        (
            "Dean_Sharp",
            FactionsEnum.Loner.name,
            "pysaic_icon_actor_stalker_51",
        ),
        ("Dima_Bolt", FactionsEnum.Loner.name, "crc_icon_actor_stalker_12"),
        (
            "Tomas_Loner",
            FactionsEnum.Loner.name,
            "pysaic_icon_actor_stalker_12",
        ),
        (
            "Dean_Sharp",
            FactionsEnum.Bandit.name,
            "pysaic_icon_actor_bandit_18",
        ),
        ("Dima_Bolt", FactionsEnum.Bandit.name, "crc_icon_actor_bandit_6"),
        (
            "Tomas_Loner",
            FactionsEnum.Bandit.name,
            "pysaic_icon_actor_bandit_35",
        ),
        (
            "Dean_Sharp",
            FactionsEnum.Mercenary.name,
            "pysaic_icon_actor_killer_22",
        ),
        ("Dima_Bolt", FactionsEnum.Mercenary.name, "crc_icon_actor_killer_6"),
        (
            "Tomas_Loner",
            FactionsEnum.Mercenary.name,
            "pysaic_icon_actor_killer_39",
        ),
    ),
)
def test_avatar_based_on_name(name, faction, expected_avatar, mock_server):
    # given
    config = Config.create_instance_from_config(
        {"nick": name, "current_faction": faction, "server": mock_server}
    )

    # when
    with patch.object(
        Config, "save_config", return_value=None
    ) as mock_save_config:
        config.recalculate_avatar()

    # then
    assert config.current_avatar == expected_avatar
    mock_save_config.assert_called_once_with()
