import asyncio
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, Mock, patch

import pytest

from pysaic.config import Config
from pysaic.entities import IncomingEvent, IrcEvent, IrcUser, OutgoingPart
from pysaic.enums import IrcEvents, NetworkDestroyReasonEnum
from pysaic.handlers import handle_part_event
from pysaic.router.irc_event_router import IrcEventRouter
from pysaic.script_reader.entities import ConnectionLost
from pysaic.state import State
from pysaic.use_cases.game import ConnectionLostUseCase


def test_connection_lost_parsing_psystorm():
    cl = ConnectionLost.from_line("true/PsyStorm")
    assert cl.lost is True
    assert cl.reason == NetworkDestroyReasonEnum.psystorm

    cl2 = ConnectionLost.from_line("true/psystorm")
    assert cl2.lost is True
    assert cl2.reason == NetworkDestroyReasonEnum.psystorm

    cl_surge = ConnectionLost.from_line("true/Surge")
    assert cl_surge.lost is True
    assert cl_surge.reason == NetworkDestroyReasonEnum.surge

    cl_none = ConnectionLost.from_line("false/None")
    assert cl_none.lost is False
    assert cl_none.reason == NetworkDestroyReasonEnum.none


@pytest.mark.asyncio
async def test_connection_lost_use_case_broadcast_psystorm():
    mock_config = Mock(spec=Config)
    mock_config.server = Mock()
    mock_config.server.previous_channel = "#crcr_english"

    mock_incoming_queue = AsyncMock()
    mock_outgoing_queue = AsyncMock()

    entity = ConnectionLost(
        lost=True, reason=NetworkDestroyReasonEnum.psystorm
    )
    use_case = ConnectionLostUseCase(
        mock_config, entity, mock_incoming_queue, mock_outgoing_queue
    )

    mock_state = Mock(spec=State)
    mock_state.fake_disconnect = True
    mock_state.is_in_channel = Mock()
    mock_state.is_in_channel.is_set.return_value = True
    mock_state.is_currently_under_network_destruction = None

    loop = asyncio.get_event_loop()

    with (
        patch("pysaic.use_cases.game.SLEEP_TIME_BEFORE_DISCONNECT", 0),
        patch(
            "pysaic.use_cases.game.add_signal_state"
        ) as mock_add_signal_state,
    ):
        use_case._do_full_disconnect(mock_state, loop)
        await asyncio.sleep(0.05)

        mock_add_signal_state.assert_called_with("True")
        mock_outgoing_queue.put.assert_called_once()
        sent_item = mock_outgoing_queue.put.call_args[0][0]
        assert isinstance(sent_item, OutgoingPart)
        assert sent_item.channel == "#crcr_english"
        assert sent_item.content == "Psystorm"


@pytest.mark.asyncio
async def test_handle_part_event_reasons():
    mock_conn = Mock()
    mock_incoming_queue = AsyncMock()

    # PsyStorm
    mock_message_psy = Mock()
    mock_message_psy.prefix = Mock(nick="Stalker1")
    mock_message_psy.parameters = ["#crcr_english", "PsyStorm"]

    await handle_part_event(mock_conn, mock_message_psy, mock_incoming_queue)
    event_psy = mock_incoming_queue.put.call_args[0][0]
    assert event_psy.event.payload["reason"] == "caught in psy storm."
    assert event_psy.event.payload["raw_reason"] == "PsyStorm"

    # Surge
    mock_message_surge = Mock()
    mock_message_surge.prefix = Mock(nick="Stalker2")
    mock_message_surge.parameters = ["#crcr_english", "Surge"]

    await handle_part_event(mock_conn, mock_message_surge, mock_incoming_queue)
    event_surge = mock_incoming_queue.put.call_args[0][0]
    assert event_surge.event.payload["reason"] == "caught in emission."
    assert event_surge.event.payload["raw_reason"] == "Surge"


def test_irc_event_router_synced_hazards_disabled(
    mock_state, mock_config, mock_ui
):
    mock_config.sync_hazards = False
    mock_config.sync_hazards_cooldown = 60

    event = IncomingEvent(
        author=IrcUser("Stalker1"),
        target="#crcr_english",
        event=IrcEvent(
            type=IrcEvents.PART,
            payload={
                "reason": "caught in emission.",
                "target": "#crcr_english",
                "raw_reason": "Surge",
            },
        ),
    )

    with patch(
        "pysaic.router.irc_event_router.trigger_hazard_in_game"
    ) as mock_trigger:
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_synced_hazards()
        mock_trigger.assert_not_called()
        assert mock_state.last_synced_hazard is None


@pytest.mark.asyncio
async def test_irc_event_router_synced_hazards_surge_triggered(
    mock_state, mock_config, mock_ui
):
    mock_config.sync_hazards = True
    mock_config.sync_hazards_cooldown = 60
    mock_state.last_synced_hazard = None

    event = IncomingEvent(
        author=IrcUser("Stalker1"),
        target="#crcr_english",
        event=IrcEvent(
            type=IrcEvents.PART,
            payload={
                "reason": "caught in emission.",
                "target": "#crcr_english",
                "raw_reason": "Surge",
            },
        ),
    )

    with (
        patch(
            "pysaic.router.irc_event_router.trigger_hazard_in_game"
        ) as mock_trigger,
        patch.object(IrcEventRouter, "_add_information_text") as mock_add_info,
        patch("pysaic.router.irc_event_router.randint", return_value=0),
    ):
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_synced_hazards()
        await asyncio.sleep(0.05)

        mock_add_info.assert_called_once_with(
            "Blowout is coming from Stalker1, it will arrive in approximately 10 sec"
        )
        mock_trigger.assert_called_once_with("Surge")
        assert mock_state.last_synced_hazard is not None


@pytest.mark.asyncio
async def test_irc_event_router_synced_hazards_psystorm_triggered(
    mock_state, mock_config, mock_ui
):
    mock_config.sync_hazards = True
    mock_config.sync_hazards_cooldown = 60
    mock_state.last_synced_hazard = None

    event = IncomingEvent(
        author=IrcUser("Stalker2"),
        target="#crcr_english",
        event=IrcEvent(
            type=IrcEvents.PART,
            payload={
                "reason": "caught in psy storm.",
                "target": "#crcr_english",
                "raw_reason": "Psystorm",
            },
        ),
    )

    with (
        patch(
            "pysaic.router.irc_event_router.trigger_hazard_in_game"
        ) as mock_trigger,
        patch.object(IrcEventRouter, "_add_information_text") as mock_add_info,
        patch("pysaic.router.irc_event_router.randint", return_value=0),
    ):
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_synced_hazards()
        await asyncio.sleep(0.05)

        mock_add_info.assert_called_once_with(
            "Psy Storm is coming from Stalker2, it will arrive in approximately 10 sec"
        )
        mock_trigger.assert_called_once_with("PsyStorm")
        assert mock_state.last_synced_hazard is not None


@pytest.mark.asyncio
async def test_irc_event_router_synced_hazards_cooldown(
    mock_state, mock_config, mock_ui
):
    mock_config.sync_hazards = True
    mock_config.sync_hazards_cooldown = 60
    # Last hazard was 10 minutes ago -> should be ignored (cooldown is 60m)
    ten_minutes_ago = datetime.now() - timedelta(minutes=10)
    mock_state.last_synced_hazard = ten_minutes_ago

    event = IncomingEvent(
        author=IrcUser("Stalker1"),
        target="#crcr_english",
        event=IrcEvent(
            type=IrcEvents.PART,
            payload={
                "reason": "caught in emission.",
                "target": "#crcr_english",
                "raw_reason": "Surge",
            },
        ),
    )

    with (
        patch(
            "pysaic.router.irc_event_router.trigger_hazard_in_game"
        ) as mock_trigger,
        patch.object(IrcEventRouter, "_add_information_text") as mock_add_info,
    ):
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_synced_hazards()

        mock_add_info.assert_not_called()
        mock_trigger.assert_not_called()
        assert mock_state.last_synced_hazard == ten_minutes_ago

    # Now simulate 65 minutes passed -> should trigger
    mock_state.last_synced_hazard = datetime.now() - timedelta(minutes=65)
    with (
        patch(
            "pysaic.router.irc_event_router.trigger_hazard_in_game"
        ) as mock_trigger,
        patch.object(IrcEventRouter, "_add_information_text") as mock_add_info,
        patch("pysaic.router.irc_event_router.randint", return_value=0),
    ):
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_synced_hazards()
        await asyncio.sleep(0.05)

        mock_add_info.assert_called_once()
        mock_trigger.assert_called_once_with("Surge")
        assert mock_state.last_synced_hazard > ten_minutes_ago


@pytest.mark.asyncio
async def test_irc_event_router_handle_part_or_quit_integration(
    mock_state, mock_config, mock_ui
):
    mock_config.sync_hazards = True
    mock_config.sync_hazards_cooldown = 60
    mock_state.last_synced_hazard = None

    event = IncomingEvent(
        author=IrcUser("Stalker1"),
        target="#crcr_english",
        event=IrcEvent(
            type=IrcEvents.PART,
            payload={
                "reason": "caught in emission.",
                "target": "#crcr_english",
                "raw_reason": "Surge",
            },
        ),
    )

    with (
        patch(
            "pysaic.router.irc_event_router.trigger_hazard_in_game"
        ) as mock_trigger,
        patch.object(IrcEventRouter, "_add_information_text") as mock_add_info,
        patch.object(IrcEventRouter, "_update_ui_user_list"),
        patch("pysaic.router.irc_event_router.remove_user_from_game"),
        patch("pysaic.router.irc_event_router.randint", return_value=0),
    ):
        router = IrcEventRouter(mock_state, mock_config, mock_ui, event)
        router._handle_part_or_quit()
        await asyncio.sleep(0.05)

        mock_trigger.assert_called_once_with("Surge")
        mock_add_info.assert_any_call("Stalker1 caught in emission.")
        mock_add_info.assert_any_call(
            "Blowout is coming from Stalker1, it will arrive in approximately 10 sec"
        )


def test_trigger_hazard_in_game():
    from pysaic.controllers.game import trigger_hazard_in_game

    mock_state = Mock()
    mock_state.game_location = "some/path"

    with patch(
        "pysaic.controllers.game.add_to_crc_input_file"
    ) as mock_add_to_file:
        trigger_hazard_in_game("Surge", state=mock_state)
        mock_add_to_file.assert_called_once_with("Hazard/Surge")

    with patch(
        "pysaic.controllers.game.add_to_crc_input_file"
    ) as mock_add_to_file:
        trigger_hazard_in_game("PsyStorm", state=mock_state)
        mock_add_to_file.assert_called_once_with("Hazard/PsyStorm")


def test_config_sync_hazards_fields(mock_server):
    config = Config.create_instance_from_config(
        {"nick": "Tester", "server": mock_server}
    )
    assert config.sync_hazards is False
    assert config.sync_hazards_cooldown == 60

    config_custom = Config.create_instance_from_config(
        {
            "nick": "Tester",
            "server": mock_server,
            "sync_hazards": True,
            "sync_hazards_cooldown": 45,
        }
    )
    assert config_custom.sync_hazards is True
    assert config_custom.sync_hazards_cooldown == 45
