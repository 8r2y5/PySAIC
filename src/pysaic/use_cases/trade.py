import asyncio
import logging
import secrets
from datetime import datetime, timedelta
from typing import Optional

import inject

from pysaic.controllers.game import (
    add_item_to_inventory,
    send_trade_abort_to_game,
    send_trade_check_failed_to_game,
    send_trade_check_to_game,
    send_trade_open_to_game,
    send_trade_partner_accept_to_game,
    send_trade_partner_add_to_game,
    send_trade_partner_del_to_game,
    send_trade_reset_accept_to_game,
    send_trade_success_to_game,
    send_trade_verify_request_to_game,
)
from pysaic.entities import (
    IncomingEvent,
    IncomingQueue,
    OutgoingCTCP,
    OutgoingQueue,
)
from pysaic.enums import SAICCTCPEnum, SAICTrade
from pysaic.state import State, TradeItem, TradeSession, TradeStatus

logger = logging.getLogger(__name__)

PROTOCOL_VERSION = "1"
HANDSHAKE_TIMEOUT_SECONDS = 30


class TradeUseCase:
    # -------------------------------------------------------------------------
    # Internal Helpers to Eliminate Duplication
    # -------------------------------------------------------------------------

    @staticmethod
    def _send_info(incoming_queue: IncomingQueue, text: str):
        """Pushes an information message to the user UI/chat."""
        incoming_queue.put_nowait(IncomingEvent.create_information_event(text))

    @staticmethod
    def _send_trade_ctcp(
        outgoing_queue: OutgoingQueue,
        target: str,
        action: SAICTrade,
        session_id: str,
        *payload_parts: object,
    ):
        """Constructs and queues a standardized SAICTRADE CTCP NOTICE."""
        suffix = (
            ("/" + "/".join(str(p) for p in payload_parts))
            if payload_parts
            else ""
        )
        action_name = (
            action.name if isinstance(action, SAICTrade) else str(action)
        )
        action_str = getattr(SAICCTCPEnum.SAICTrade, action_name, action_name)
        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=target,
                content=f"{action_str} {PROTOCOL_VERSION}/{session_id}{suffix}",
            )
        )

    @staticmethod
    def _serialize_item_details(item: TradeItem) -> tuple[str, str, str]:
        """Serializes parts, upgrades, and attachments into game pipe-delimited format."""
        parts_string = (
            "|".join(
                f"{sec}:{cond}:{int(float(cond) * 1000)}"
                for sec, cond in item.parts.items()
            )
            if item.parts
            else "none"
        )
        upgrades_string = (
            "|".join(f"{upg}:1000" for upg in item.upgrades)
            if item.upgrades
            else "none"
        )
        attachments_string = (
            "|".join(
                f"{att_type}:{sec}:1000"
                for att_type, sec in item.attachments.items()
            )
            if item.attachments
            else "none"
        )
        return parts_string, upgrades_string, attachments_string

    @staticmethod
    def _reset_acceptance(session: TradeSession, notify_game: bool = True):
        """Resets offer acceptance flags for both parties when offer contents change."""
        session.my_accepted = False
        session.partner_accepted = False
        if notify_game:
            send_trade_reset_accept_to_game(session.session_id)

    @classmethod
    def _start_active_session(
        cls,
        state: State,
        session_id: str,
        partner: str,
        is_initiator: bool,
        incoming_queue: IncomingQueue,
    ):
        """Initializes a new active trade session and alerts the game client."""
        state.trade = TradeSession(
            session_id=session_id,
            partner_nick=partner,
            is_initiator=is_initiator,
            status=TradeStatus.ACTIVE,
            created_at=datetime.now(),
        )
        send_trade_open_to_game(session_id, partner)
        cls._send_info(
            incoming_queue, f"Trade session started with {partner}."
        )

    @staticmethod
    def _get_active_session_payload(
        state: State, payload: str, min_fields: int = 1
    ) -> tuple[Optional[TradeSession], list[str]]:
        """Validates that a trade session is active and matches the incoming socket payload session_id."""
        session = state.trade
        if not session:
            return None, []
        fields = payload.strip().split("/")
        if len(fields) < min_fields or session.session_id != fields[0]:
            return None, []
        return session, fields

    @staticmethod
    def _parse_game_item_components(
        fields: list[str],
    ) -> tuple[dict[str, float], list[str], dict[str, str]]:
        """Parses optional parts, upgrades, and attachments arrays from socket fields."""
        parts = {}
        if len(fields) > 6 and fields[6] != "none":
            for part in fields[6].split("|"):
                if ":" in part:
                    sec, cond = part.split(":")[:2]
                    parts[sec] = float(cond)

        upgrades = []
        if len(fields) > 7 and fields[7] != "none":
            for upg in fields[7].split("|"):
                sec = upg.split(":")[0]
                if sec:
                    upgrades.append(sec)

        attachments = {}
        if len(fields) > 8 and fields[8] != "none":
            for att in fields[8].split("|"):
                if ":" in att:
                    att_type, sec = att.split(":")[:2]
                    attachments[att_type] = sec

        return parts, upgrades, attachments

    @staticmethod
    def _is_valid_session(state: State, author: str, session_id: str) -> bool:
        if (
            state.trade is None
            or state.trade.partner_nick != author
            or state.trade.session_id != session_id
        ):
            logger.debug(
                "Trade message discarded: mismatch or no active trade. Author: %s, session: %s",
                author,
                session_id,
            )
            return False
        return True

    # -------------------------------------------------------------------------
    # Core Handshake & Lifecycle Use Cases
    # -------------------------------------------------------------------------

    @classmethod
    @inject.autoparams()
    def initiate_trade(
        cls,
        target: str,
        state: State,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ) -> bool:
        """
        Handles user executing /trade <target>.
        Validates readiness, matches mutual requests, or registers an outgoing request.
        """
        if not state.is_game_running:
            cls._send_info(incoming_queue, "You need to be in game to trade.")
            return False

        if target.startswith("@"):
            target = target[1:]

        if target == state.nick:
            cls._send_info(incoming_queue, "You cannot trade with yourself.")
            return False

        target_user = state.chat_users.get(target)
        if not target_user:
            cls._send_info(incoming_queue, f"{target!r} is not in the chat.")
            return False

        if not target_user.in_game:
            cls._send_info(incoming_queue, f"{target!r} is not in game.")
            return False

        if state.trade is not None:
            cls._send_info(
                incoming_queue,
                f"You are already in a trade session with {state.trade.partner_nick!r}. "
                "Type '/trade cancel' to abort.",
            )
            return False

        state.clean_expired_trades()

        # Mutual handshake match: partner already sent us a silent request
        if target in state.pending_incoming_trades:
            session_id, _ = state.pending_incoming_trades.pop(target)
            cls._start_active_session(
                state, session_id, target, False, incoming_queue
            )
            cls._send_trade_ctcp(
                outgoing_queue, target, SAICTrade.ACCEPT_REQ, session_id
            )
            return True

        # Check if we already have an active outgoing request to target
        if target in state.pending_outgoing_trades:
            cls._send_info(
                incoming_queue,
                f"Trade request to {target} is already pending. Waiting for response...",
            )
            return True

        # Generate unique 4-character hex session ID and record outgoing request
        session_id = secrets.token_hex(2).upper()
        expires_at = datetime.now() + timedelta(
            seconds=HANDSHAKE_TIMEOUT_SECONDS
        )
        state.pending_outgoing_trades[target] = (session_id, expires_at)

        cls._send_trade_ctcp(outgoing_queue, target, SAICTrade.REQ, session_id)
        cls._send_info(
            incoming_queue,
            f"Trade request sent to {target}. Waiting for {target} to type /trade {state.nick} ({HANDSHAKE_TIMEOUT_SECONDS}s timeout)...",
        )

        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                cls._schedule_handshake_timeout(target, session_id)
            )
        except RuntimeError:
            pass
        return True

    @classmethod
    @inject.autoparams()
    async def _schedule_handshake_timeout(
        cls,
        target: str,
        session_id: str,
        state: State,
        incoming_queue: IncomingQueue,
    ):
        await asyncio.sleep(HANDSHAKE_TIMEOUT_SECONDS)
        if target in state.pending_outgoing_trades:
            stored_session, _ = state.pending_outgoing_trades[target]
            if stored_session == session_id:
                state.pending_outgoing_trades.pop(target, None)
                cls._send_info(
                    incoming_queue, f"Trade request with {target} expired."
                )

    @classmethod
    @inject.autoparams()
    def cancel_active_trade(
        cls,
        reason: str = "cancelled",
        state: State = None,
        incoming_queue: IncomingQueue = None,
        outgoing_queue: OutgoingQueue = None,
    ):
        """Cancels active trade session or clears pending requests."""
        state.pending_incoming_trades.clear()
        state.pending_outgoing_trades.clear()

        if state.trade:
            session_id = state.trade.session_id
            partner = state.trade.partner_nick
            cls._send_trade_ctcp(
                outgoing_queue, partner, SAICTrade.CANCEL, session_id, reason
            )
            send_trade_abort_to_game(session_id, reason)
            cls._send_info(
                incoming_queue, f"Trade with {partner} aborted: {reason}."
            )
            state.trade = None
        else:
            cls._send_info(
                incoming_queue, "No active trade session to cancel."
            )

    # -------------------------------------------------------------------------
    # Incoming CTCP Routing (Partner -> PySAIC)
    # -------------------------------------------------------------------------

    @classmethod
    @inject.autoparams()
    def handle_incoming_ctcp(
        cls,
        author: str,
        content: str,
        state: State,
        incoming_queue: IncomingQueue,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Parses and handles incoming SAICTRADE CTCP messages:
        Format: SAICTRADE.<ACTION> <version>/<session_id>/<payload>
        """
        try:
            verb, rest = content.split(" ", 1)
        except ValueError:
            logger.warning("Malformed trade CTCP: %r", content)
            return

        action = verb.split(".", 1)[-1]
        try:
            parts = rest.split("/")
            version = parts[0]
            session_id = parts[1]
            payload = parts[2:]
        except Exception:
            logger.exception("Failed to parse trade CTCP parameters: %r", rest)
            return

        if version != PROTOCOL_VERSION:
            logger.warning(
                "Unsupported trade protocol version %r from %s",
                version,
                author,
            )
            return

        state.clean_expired_trades()

        # Session-bound actions require an active session matching author and session_id
        if action not in (
            SAICTrade.REQ,
            SAICTrade.ACCEPT_REQ,
            SAICTrade.CANCEL,
        ):
            if not cls._is_valid_session(state, author, session_id):
                return

        match action:
            case SAICTrade.REQ:
                logger.info(
                    "Received silent trade request from %s (session %s)",
                    author,
                    session_id,
                )
                state.pending_incoming_trades[author] = (
                    session_id,
                    datetime.now()
                    + timedelta(seconds=HANDSHAKE_TIMEOUT_SECONDS),
                )

            case SAICTrade.ACCEPT_REQ:
                if author in state.pending_outgoing_trades:
                    stored_session, _ = state.pending_outgoing_trades.pop(
                        author
                    )
                    if stored_session == session_id:
                        cls._start_active_session(
                            state, session_id, author, True, incoming_queue
                        )

            case SAICTrade.CHECK:
                if len(payload) >= 2:
                    ref_id, item_id = payload[0], payload[1]
                    send_trade_check_to_game(session_id, ref_id, item_id)

            case SAICTrade.CHECK_RESP:
                if len(payload) >= 2:
                    ref_id, status = payload[0], payload[1]
                    cls._handle_check_response(
                        ref_id, status, state, outgoing_queue, incoming_queue
                    )

            case SAICTrade.ADD:
                if len(payload) >= 4:
                    ref_id, item_id, amount, condition = payload[:4]
                    state.trade.partner_items[ref_id] = TradeItem(
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=int(amount),
                        condition=float(condition),
                    )
                    cls._reset_acceptance(state.trade)
                    send_trade_partner_add_to_game(
                        session_id=session_id,
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=amount,
                        condition=condition,
                    )

            case SAICTrade.ADDCOMPLEX:
                if len(payload) >= 4:
                    ref_id, item_id, amount, condition = payload[:4]
                    state.trade.partial_partner_items[ref_id] = TradeItem(
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=int(amount),
                        condition=float(condition),
                    )

            case SAICTrade.MODIFY:
                if len(payload) >= 3:
                    ref_id, mod_type, data = payload[0], payload[1], payload[2]
                    cls._handle_streamed_modify(ref_id, mod_type, data, state)

            case SAICTrade.ITEMDONE:
                if len(payload) >= 1:
                    cls._handle_complex_item_done(payload[0], state)

            case SAICTrade.DEL:
                if len(payload) >= 1:
                    ref_id = payload[0]
                    state.trade.partner_items.pop(ref_id, None)
                    state.trade.partial_partner_items.pop(ref_id, None)
                    cls._reset_acceptance(state.trade)
                    send_trade_partner_del_to_game(session_id, ref_id)

            case SAICTrade.ACCEPT:
                state.trade.partner_accepted = True
                send_trade_partner_accept_to_game(session_id)
                cls._check_both_accepted(state, outgoing_queue)

            case SAICTrade.COMMIT:
                cls._execute_trade_swap(state, incoming_queue)

            case SAICTrade.CANCEL:
                reason = payload[0] if payload else "Partner cancelled trade."
                if state.trade and state.trade.session_id == session_id:
                    send_trade_abort_to_game(session_id, reason)
                    cls._send_info(
                        incoming_queue, f"Trade aborted by {author}: {reason}."
                    )
                    state.trade = None

            case _:
                logger.warning("Unknown trade action: %r", action)

    @classmethod
    def _handle_check_response(
        cls,
        ref_id: str,
        status: str,
        state: State,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        session = state.trade
        if not session or ref_id not in session.my_items:
            return

        item = session.my_items[ref_id]
        if status != "1":
            logger.warning(
                "Target player does not have item section %r", item.item_id
            )
            session.my_items.pop(ref_id, None)
            send_trade_check_failed_to_game(
                session.session_id, ref_id, item.item_id
            )
            cls._send_info(
                incoming_queue,
                f"Target player's game does not recognize item: {item.item_id}",
            )
            return

        is_complex = bool(item.parts or item.upgrades or item.attachments)
        if not is_complex:
            cls._send_trade_ctcp(
                outgoing_queue,
                session.partner_nick,
                SAICTrade.ADD,
                session.session_id,
                ref_id,
                item.item_id,
                item.amount,
                item.condition,
            )
            return

        cls._handle_check_response_complex(
            ref_id, item, session, outgoing_queue
        )

    @staticmethod
    def _handle_streamed_modify(
        ref_id: str, mod_type: str, data: str, state: State
    ):
        item = state.trade.partial_partner_items.get(ref_id)
        if not item:
            return

        if mod_type == "parts":
            for part_entry in data.split(","):
                if ":" in part_entry:
                    p_sec, p_cond = part_entry.split(":", 1)
                    item.parts[p_sec] = float(p_cond)
                else:
                    logger.warning(f"Invalid part entry: {part_entry}")
        elif mod_type == "upgrades":
            for upg_sec in data.split(","):
                if upg_sec:
                    item.upgrades.append(upg_sec)
                else:
                    logger.warning(f"Invalid upgrade entry: {upg_sec}")
        elif mod_type == "attach":
            for att_entry in data.split(","):
                if ":" in att_entry:
                    att_sec, att_type = att_entry.split(":", 1)
                    item.attachments[att_type] = att_sec
                else:
                    logger.warning(f"Invalid attachment entry: {att_entry}")

    @classmethod
    def _handle_complex_item_done(cls, ref_id: str, state: State):
        session = state.trade
        item = session.partial_partner_items.pop(ref_id, None)
        if not item:
            return

        session.partner_items[ref_id] = item
        cls._reset_acceptance(session)

        parts_string, upgrades_string, attachments_string = (
            cls._serialize_item_details(item)
        )
        send_trade_partner_add_to_game(
            session_id=session.session_id,
            ref_id=ref_id,
            item_id=item.item_id,
            amount=str(item.amount),
            condition=str(item.condition),
            parts_string=parts_string,
            upgrades_string=upgrades_string,
            attachments_string=attachments_string,
        )

    @staticmethod
    def _check_both_accepted(state: State, outgoing_queue: OutgoingQueue):
        session = state.trade
        if session and session.my_accepted and session.partner_accepted:
            logger.info(
                "Both players accepted trade session %s. Requesting inventory verification.",
                session.session_id,
            )
            session.status = TradeStatus.COMMITTING
            send_trade_verify_request_to_game(session.session_id)

    @classmethod
    def _execute_trade_swap(cls, state: State, incoming_queue: IncomingQueue):
        session = state.trade
        if not session:
            return

        logger.info(
            "Executing final trade swap for session %s with %s",
            session.session_id,
            session.partner_nick,
        )

        for item in session.partner_items.values():
            parts_string, upgrades_string, attachments_string = (
                cls._serialize_item_details(item)
            )
            add_item_to_inventory(
                item_id=item.item_id,
                amount=str(item.amount),
                amount_type=item.amount_type,
                condition=str(item.condition),
                parts_string=parts_string,
                upgrades_string=upgrades_string,
                attachments_string=attachments_string,
            )

        send_trade_success_to_game(session.session_id)
        cls._send_info(
            incoming_queue,
            f"Trade Successful with {session.partner_nick}! Items swapped.",
        )
        state.trade = None

    @classmethod
    def _handle_check_response_complex(
        cls,
        ref_id: str,
        item: TradeItem,
        session: TradeSession,
        outgoing_queue: OutgoingQueue,
    ):
        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.ADDCOMPLEX,
            session.session_id,
            ref_id,
            item.item_id,
            item.amount,
            item.condition,
        )
        if item.parts:
            parts_str = ",".join(
                f"{sec}:{cond}" for sec, cond in item.parts.items()
            )
            cls._send_trade_ctcp(
                outgoing_queue,
                session.partner_nick,
                SAICTrade.MODIFY,
                session.session_id,
                ref_id,
                "parts",
                parts_str,
            )
        if item.upgrades:
            cls._send_trade_ctcp(
                outgoing_queue,
                session.partner_nick,
                SAICTrade.MODIFY,
                session.session_id,
                ref_id,
                "upgrades",
                ",".join(item.upgrades),
            )
        if item.attachments:
            attach_str = ",".join(
                f"{sec}:{att_type}"
                for att_type, sec in item.attachments.items()
            )
            cls._send_trade_ctcp(
                outgoing_queue,
                session.partner_nick,
                SAICTrade.MODIFY,
                session.session_id,
                ref_id,
                "attach",
                attach_str,
            )
        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.ITEMDONE,
            session.session_id,
            ref_id,
        )

    # -------------------------------------------------------------------------
    # Game Socket IPC Handlers (Game -> PySAIC)
    # -------------------------------------------------------------------------

    @classmethod
    @inject.autoparams()
    def handle_game_add_item(
        cls,
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game notified us player put item in barter window:
        Payload: session_id/ref_id/item_id/amount/amount_type/condition[/parts/upgrades/attachments]
        """
        session, fields = cls._get_active_session_payload(
            state, payload, min_fields=6
        )
        if not session:
            return

        session_id, ref_id, item_id, amount, amount_type, condition = fields[
            :6
        ]
        parts, upgrades, attachments = cls._parse_game_item_components(fields)

        item = TradeItem(
            ref_id=ref_id,
            item_id=item_id,
            amount=int(amount),
            amount_type=amount_type,
            condition=float(condition),
            parts=parts,
            upgrades=upgrades,
            attachments=attachments,
        )
        session.my_items[ref_id] = item
        cls._reset_acceptance(session, notify_game=False)

        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.CHECK,
            session_id,
            ref_id,
            item_id,
            amount,
            condition,
        )

    @classmethod
    @inject.autoparams()
    def handle_game_del_item(
        cls,
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game notified us player removed an item from barter window:
        Payload: session_id/ref_id
        """
        session, fields = cls._get_active_session_payload(
            state, payload, min_fields=2
        )
        if not session:
            return

        ref_id = fields[1]
        session.my_items.pop(ref_id, None)
        cls._reset_acceptance(session, notify_game=False)

        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.DEL,
            session.session_id,
            ref_id,
        )

    @classmethod
    @inject.autoparams()
    def handle_game_check_result(
        cls,
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game answered section existence check:
        Payload: session_id/ref_id/status (1=OK, 0=Missing)
        """
        session, fields = cls._get_active_session_payload(
            state, payload, min_fields=3
        )
        if not session:
            return

        ref_id, status = fields[1], fields[2]
        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.CHECK_RESP,
            session.session_id,
            ref_id,
            status,
        )

    @classmethod
    @inject.autoparams()
    def handle_game_accept(
        cls,
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Local player clicked `Accept` in game:
        Payload: session_id
        """
        session, _ = cls._get_active_session_payload(
            state, payload, min_fields=1
        )
        if not session:
            return

        session.my_accepted = True
        cls._send_trade_ctcp(
            outgoing_queue,
            session.partner_nick,
            SAICTrade.ACCEPT,
            session.session_id,
        )
        cls._check_both_accepted(state, outgoing_queue)

    @classmethod
    @inject.autoparams()
    def handle_game_verify_result(
        cls,
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Game finished pre-swap inventory integrity check:
        Payload: session_id/status (1=Verified, 0=Exploit/Missing)
        """
        session, fields = cls._get_active_session_payload(
            state, payload, min_fields=1
        )
        if not session:
            return

        status = fields[1] if len(fields) > 1 else "0"
        if status == "1":
            cls._send_trade_ctcp(
                outgoing_queue,
                session.partner_nick,
                SAICTrade.COMMIT,
                session.session_id,
            )
            cls._execute_trade_swap(state, incoming_queue)
        else:
            logger.warning(
                "Inventory verification failed for trade session %s",
                session.session_id,
            )
            cls.cancel_active_trade(reason="inventory_verification_failed")

    @classmethod
    @inject.autoparams()
    def handle_game_cancel(
        cls,
        payload: str,
        state: State,
    ):
        """
        Local player closed the trade window or pressed Esc in game:
        Payload: session_id/reason
        """
        fields = payload.strip().split("/")
        reason = fields[1] if len(fields) > 1 else "window_closed"
        cls.cancel_active_trade(reason=reason)
