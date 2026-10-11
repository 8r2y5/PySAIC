from datetime import datetime, timedelta
from unittest.mock import Mock, patch

import pytest

from pysaic.entities import ChatUser
from pysaic.state import TradeItem, TradeSession, TradeStatus
from pysaic.use_cases.trade import TradeUseCase


@pytest.fixture
def trade_state():
    state = Mock()
    state.nick = "Actor_A"
    state.is_game_running = True
    user_b = ChatUser("Actor_B", in_game=True)
    state.chat_users = {
        "Actor_B": user_b,
        "Actor_A": ChatUser("Actor_A", in_game=True),
    }
    state.trade = None
    state.pending_incoming_trades = {}
    state.pending_outgoing_trades = {}
    state.clean_expired_trades = Mock()
    return state


def test_initiate_trade_not_in_game(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.is_game_running = False

    result = TradeUseCase.initiate_trade(
        "Actor_B",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is False
    assert mock_outgoing_queue.put_nowait.call_count == 0
    mock_incoming_queue.put_nowait.assert_called_once()
    event = mock_incoming_queue.put_nowait.call_args[0][0]
    assert "You need to be in game to trade" in event.event.content


def test_initiate_trade_with_self(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    result = TradeUseCase.initiate_trade(
        "Actor_A",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is False
    event = mock_incoming_queue.put_nowait.call_args[0][0]
    assert "You cannot trade with yourself" in event.event.content


def test_initiate_trade_target_not_in_chat(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    result = TradeUseCase.initiate_trade(
        "Unknown_Player",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is False
    event = mock_incoming_queue.put_nowait.call_args[0][0]
    assert "not in the chat" in event.event.content


def test_initiate_trade_target_not_in_game(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.chat_users["Actor_B"].in_game = False

    result = TradeUseCase.initiate_trade(
        "Actor_B",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is False
    event = mock_incoming_queue.put_nowait.call_args[0][0]
    assert "not in game" in event.event.content


def test_initiate_trade_first_time_sends_silent_req(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    result = TradeUseCase.initiate_trade(
        "Actor_B",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is True
    assert "Actor_B" in trade_state.pending_outgoing_trades
    assert mock_outgoing_queue.put_nowait.call_count == 1
    ctcp = mock_outgoing_queue.put_nowait.call_args[0][0]
    assert ctcp.target == "Actor_B"
    assert "SAICTRADE.REQ" in ctcp.content


@patch("pysaic.use_cases.trade.send_trade_open_to_game")
def test_initiate_trade_mutual_match_accepts(
    mock_open_game, trade_state, mock_incoming_queue, mock_outgoing_queue
):
    # Given Actor_B already sent an incoming request with session FF1A
    trade_state.pending_incoming_trades["Actor_B"] = (
        "FF1A",
        datetime.now() + timedelta(seconds=20),
    )

    result = TradeUseCase.initiate_trade(
        "Actor_B",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert result is True
    assert trade_state.trade is not None
    assert trade_state.trade.session_id == "FF1A"
    assert trade_state.trade.partner_nick == "Actor_B"
    assert trade_state.trade.status == TradeStatus.ACTIVE
    assert "Actor_B" not in trade_state.pending_incoming_trades

    mock_open_game.assert_called_once_with("FF1A", "Actor_B")
    ctcp = mock_outgoing_queue.put_nowait.call_args[0][0]
    assert ctcp.target == "Actor_B"
    assert "SAICTRADE.ACCEPT_REQ 1/FF1A" in ctcp.content


def test_handle_incoming_ctcp_req_silent_storage(
    trade_state, mock_incoming_queue, mock_outgoing_queue
):
    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.REQ 1/A7F2",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    # Must be stored in memory silently: NO outgoing messages, NO game calls
    assert "Actor_B" in trade_state.pending_incoming_trades
    session_id, _ = trade_state.pending_incoming_trades["Actor_B"]
    assert session_id == "A7F2"
    assert mock_incoming_queue.put_nowait.call_count == 0
    assert mock_outgoing_queue.put_nowait.call_count == 0


@patch("pysaic.use_cases.trade.send_trade_open_to_game")
def test_handle_incoming_ctcp_accept_req(
    mock_open_game, trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.pending_outgoing_trades["Actor_B"] = (
        "A7F2",
        datetime.now() + timedelta(seconds=20),
    )

    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.ACCEPT_REQ 1/A7F2",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert trade_state.trade is not None
    assert trade_state.trade.session_id == "A7F2"
    assert trade_state.trade.partner_nick == "Actor_B"
    mock_open_game.assert_called_once_with("A7F2", "Actor_B")


@patch("pysaic.use_cases.trade.send_trade_check_to_game")
def test_handle_incoming_ctcp_check(
    mock_check_game, trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.trade = TradeSession(
        session_id="A7F2",
        partner_nick="Actor_B",
        is_initiator=True,
        status=TradeStatus.ACTIVE,
        created_at=datetime.now(),
    )

    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.CHECK 1/A7F2/1/beer/3/1",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    mock_check_game.assert_called_once_with("A7F2", "1", "beer")


@patch("pysaic.use_cases.trade.send_trade_partner_add_to_game")
@patch("pysaic.use_cases.trade.send_trade_reset_accept_to_game")
def test_handle_incoming_ctcp_add_simple_item(
    mock_reset, mock_add, trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.trade = TradeSession(
        session_id="A7F2",
        partner_nick="Actor_B",
        is_initiator=True,
        status=TradeStatus.ACTIVE,
        created_at=datetime.now(),
    )

    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.ADD 1/A7F2/1/beer/3/1",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    assert "1" in trade_state.trade.partner_items
    item = trade_state.trade.partner_items["1"]
    assert item.item_id == "beer"
    assert item.amount == 3
    mock_add.assert_called_once_with(
        session_id="A7F2",
        ref_id="1",
        item_id="beer",
        amount="3",
        condition="1",
    )
    mock_reset.assert_called_once_with("A7F2")


@patch("pysaic.use_cases.trade.send_trade_partner_add_to_game")
def test_handle_incoming_ctcp_complex_streaming(
    mock_add, trade_state, mock_incoming_queue, mock_outgoing_queue
):
    trade_state.trade = TradeSession(
        session_id="A7F2",
        partner_nick="Actor_B",
        is_initiator=True,
        status=TradeStatus.ACTIVE,
        created_at=datetime.now(),
    )

    # 1. ADDCOMPLEX
    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.ADDCOMPLEX 1/A7F2/1/wpn_ak74/1/0.85",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )
    assert "1" in trade_state.trade.partial_partner_items
    assert mock_add.call_count == 0

    # 2. MODIFY parts
    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.MODIFY 1/A7F2/1/parts/barrel:0.65,trigger:0.90",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )
    partial_item = trade_state.trade.partial_partner_items["1"]
    assert partial_item.parts == {"barrel": 0.65, "trigger": 0.90}

    # 3. MODIFY upgrades
    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.MODIFY 1/A7F2/1/upgrades/up_firsta_ak74",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )
    assert partial_item.upgrades == ["up_firsta_ak74"]

    # 4. ITEMDONE
    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.ITEMDONE 1/A7F2/1",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )
    assert "1" in trade_state.trade.partner_items
    assert "1" not in trade_state.trade.partial_partner_items
    mock_add.assert_called_once()


@patch("pysaic.use_cases.trade.add_item_to_inventory")
@patch("pysaic.use_cases.trade.send_trade_success_to_game")
def test_handle_incoming_ctcp_commit_swaps_items(
    mock_success,
    mock_add_item,
    trade_state,
    mock_incoming_queue,
    mock_outgoing_queue,
):
    trade_state.trade = TradeSession(
        session_id="A7F2",
        partner_nick="Actor_B",
        is_initiator=True,
        status=TradeStatus.COMMITTING,
        created_at=datetime.now(),
        partner_items={
            "1": TradeItem(ref_id="1", item_id="beer", amount=3, condition=1.0)
        },
    )

    TradeUseCase.handle_incoming_ctcp(
        author="Actor_B",
        content="SAICTRADE.COMMIT 1/A7F2",
        state=trade_state,
        incoming_queue=mock_incoming_queue,
        outgoing_queue=mock_outgoing_queue,
    )

    mock_add_item.assert_called_once_with(
        item_id="beer",
        amount="3",
        amount_type="single",
        condition="1.0",
        parts_string="none",
        upgrades_string="none",
        attachments_string="none",
    )
    mock_success.assert_called_once_with("A7F2")
    assert trade_state.trade is None
