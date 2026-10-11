import asyncio
import logging
import secrets
from datetime import datetime, timedelta

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
    @staticmethod
    @inject.autoparams()
    def initiate_trade(
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
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "You need to be in game to trade."
                )
            )
            return False

        if target.startswith("@"):
            target = target[1:]

        if target == state.nick:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "You cannot trade with yourself."
                )
            )
            return False

        target_user = state.chat_users.get(target)
        if not target_user:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"{target!r} is not in the chat."
                )
            )
            return False

        if not target_user.in_game:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"{target!r} is not in game."
                )
            )
            return False

        if state.trade is not None:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"You are already in a trade session with {state.trade.partner_nick!r}. "
                    "Type '/trade cancel' to abort."
                )
            )
            return False

        state.clean_expired_trades()

        # Check if target already sent us an incoming request (mutual handshake matched!)
        if target in state.pending_incoming_trades:
            session_id, _expires = state.pending_incoming_trades.pop(target)
            state.trade = TradeSession(
                session_id=session_id,
                partner_nick=target,
                is_initiator=False,
                status=TradeStatus.ACTIVE,
                created_at=datetime.now(),
            )

            # Send ACCEPT_REQ CTCP NOTICE back to partner
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=target,
                    content=f"{SAICCTCPEnum.SAICTrade.ACCEPT_REQ} {PROTOCOL_VERSION}/{session_id}",
                )
            )

            send_trade_open_to_game(session_id, target)
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Trade session started with {target}."
                )
            )
            return True

        # Check if we already have an active outgoing request to target
        if target in state.pending_outgoing_trades:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Trade request to {target} is already pending. Waiting for response..."
                )
            )
            return True

        # Generate unique 4-character hex session ID
        session_id = secrets.token_hex(2).upper()
        expires_at = datetime.now() + timedelta(
            seconds=HANDSHAKE_TIMEOUT_SECONDS
        )
        state.pending_outgoing_trades[target] = (session_id, expires_at)

        # Send silent CTCP NOTICE to target
        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=target,
                content=f"{SAICCTCPEnum.SAICTrade.REQ} {PROTOCOL_VERSION}/{session_id}",
            )
        )

        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Trade request sent to {target}. Waiting for {target} to type /trade {state.nick} ({HANDSHAKE_TIMEOUT_SECONDS}s timeout)..."
            )
        )

        # Schedule timeout check in background if event loop is running
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(
                TradeUseCase._schedule_handshake_timeout(target, session_id)
            )
        except RuntimeError:
            pass
        return True

    @staticmethod
    @inject.autoparams()
    async def _schedule_handshake_timeout(
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
                incoming_queue.put_nowait(
                    IncomingEvent.create_information_event(
                        f"Trade request with {target} expired."
                    )
                )

    @staticmethod
    @inject.autoparams()
    def cancel_active_trade(
        reason: str = "cancelled",
        state: State = None,
        incoming_queue: IncomingQueue = None,
        outgoing_queue: OutgoingQueue = None,
    ):
        """
        Cancels active trade session or all pending requests.
        """
        state.pending_incoming_trades.clear()
        state.pending_outgoing_trades.clear()

        if state.trade:
            session_id = state.trade.session_id
            partner = state.trade.partner_nick
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=partner,
                    content=f"{SAICCTCPEnum.SAICTrade.CANCEL} {PROTOCOL_VERSION}/{session_id}/{reason}",
                )
            )
            send_trade_abort_to_game(session_id, reason)
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Trade with {partner} aborted: {reason}."
                )
            )
            state.trade = None
        else:
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    "No active trade session to cancel."
                )
            )

    @staticmethod
    @inject.autoparams()
    def handle_incoming_ctcp(
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

        match action:
            case SAICTrade.REQ:
                # Silently record pending incoming trade. DO NOT show any in-game popups!
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
                # Target accepted our /trade request!
                if author in state.pending_outgoing_trades:
                    stored_session, _ = state.pending_outgoing_trades.pop(
                        author
                    )
                    if stored_session == session_id:
                        state.trade = TradeSession(
                            session_id=session_id,
                            partner_nick=author,
                            is_initiator=True,
                            status=TradeStatus.ACTIVE,
                            created_at=datetime.now(),
                        )
                        send_trade_open_to_game(session_id, author)
                        incoming_queue.put_nowait(
                            IncomingEvent.create_information_event(
                                f"Trade session started with {author}."
                            )
                        )

            case SAICTrade.CHECK:
                # Partner is pre-checking if item section exists in our modpack
                # Payload: ref_id/item_id/amount/condition
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 2:
                    ref_id = payload[0]
                    item_id = payload[1]
                    send_trade_check_to_game(session_id, ref_id, item_id)

            case SAICTrade.CHECK_RESP:
                # Response to our pre-check: ref_id/status (1=OK, 0=Missing)
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 2:
                    ref_id = payload[0]
                    status = payload[1]
                    TradeUseCase._handle_check_response(
                        ref_id, status, state, outgoing_queue, incoming_queue
                    )

            case SAICTrade.ADD:
                # Simple item added by partner: ref_id/item_id/amount/condition
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 4:
                    ref_id, item_id, amount, condition = payload[:4]
                    item = TradeItem(
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=int(amount),
                        condition=float(condition),
                    )
                    state.trade.partner_items[ref_id] = item
                    state.trade.my_accepted = False
                    state.trade.partner_accepted = False
                    send_trade_partner_add_to_game(
                        session_id=session_id,
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=amount,
                        condition=condition,
                    )
                    send_trade_reset_accept_to_game(session_id)

            case SAICTrade.ADDCOMPLEX:
                # Complex item root shell: ref_id/item_id/amount/condition
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 4:
                    ref_id, item_id, amount, condition = payload[:4]
                    state.trade.partial_partner_items[ref_id] = TradeItem(
                        ref_id=ref_id,
                        item_id=item_id,
                        amount=int(amount),
                        condition=float(condition),
                    )

            case SAICTrade.MODIFY:
                # Streamed component chunk: ref_id/type/data
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 3:
                    ref_id, mod_type, data = payload[0], payload[1], payload[2]
                    TradeUseCase._handle_streamed_modify(
                        ref_id, mod_type, data, state
                    )

            case SAICTrade.ITEMDONE:
                # Finalized complex item: ref_id
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 1:
                    ref_id = payload[0]
                    TradeUseCase._handle_complex_item_done(ref_id, state)

            case SAICTrade.DEL:
                # Partner removed item: ref_id
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                if len(payload) >= 1:
                    ref_id = payload[0]
                    state.trade.partner_items.pop(ref_id, None)
                    state.trade.partial_partner_items.pop(ref_id, None)
                    state.trade.my_accepted = False
                    state.trade.partner_accepted = False
                    send_trade_partner_del_to_game(session_id, ref_id)
                    send_trade_reset_accept_to_game(session_id)

            case SAICTrade.ACCEPT:
                # Partner clicked accept
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                state.trade.partner_accepted = True
                send_trade_partner_accept_to_game(session_id)
                TradeUseCase._check_both_accepted(state, outgoing_queue)

            case SAICTrade.COMMIT:
                # Partner confirmed inventory verification and committed swap
                if not TradeUseCase._is_valid_session(
                    state, author, session_id
                ):
                    return
                TradeUseCase._execute_trade_swap(state, incoming_queue)

            case SAICTrade.CANCEL:
                # Trade aborted by partner
                reason = payload[0] if payload else "Partner cancelled trade."
                if state.trade and state.trade.session_id == session_id:
                    send_trade_abort_to_game(session_id, reason)
                    incoming_queue.put_nowait(
                        IncomingEvent.create_information_event(
                            f"Trade aborted by {author}: {reason}."
                        )
                    )
                    state.trade = None

            case _:
                logger.warning("Unknown trade action: %r", action)

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

    @staticmethod
    def _handle_check_response(
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
            # Modpack mismatch! Target client does not recognize item section
            logger.warning(
                "Target player does not have item section %r", item.item_id
            )
            session.my_items.pop(ref_id, None)
            send_trade_check_failed_to_game(
                session.session_id, ref_id, item.item_id
            )
            incoming_queue.put_nowait(
                IncomingEvent.create_information_event(
                    f"Target player's game does not recognize item: {item.item_id}"
                )
            )
            return

        # Modpack matched: send item details!
        is_complex = bool(item.parts or item.upgrades or item.attachments)
        if not is_complex:
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=session.partner_nick,
                    content=(
                        f"{SAICCTCPEnum.SAICTrade.ADD} {PROTOCOL_VERSION}/{session.session_id}/"
                        f"{ref_id}/{item.item_id}/{item.amount}/{item.condition}"
                    ),
                )
            )
        else:
            # Stream complex item sequentially
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=session.partner_nick,
                    content=(
                        f"{SAICCTCPEnum.SAICTrade.ADDCOMPLEX} {PROTOCOL_VERSION}/{session.session_id}/"
                        f"{ref_id}/{item.item_id}/{item.amount}/{item.condition}"
                    ),
                )
            )
            if item.parts:
                parts_str = ",".join(
                    f"{sec}:{cond}" for sec, cond in item.parts.items()
                )
                outgoing_queue.put_nowait(
                    OutgoingCTCP(
                        target=session.partner_nick,
                        content=(
                            f"{SAICCTCPEnum.SAICTrade.MODIFY} {PROTOCOL_VERSION}/{session.session_id}/"
                            f"{ref_id}/parts/{parts_str}"
                        ),
                    )
                )
            if item.upgrades:
                upgrades_str = ",".join(item.upgrades)
                outgoing_queue.put_nowait(
                    OutgoingCTCP(
                        target=session.partner_nick,
                        content=(
                            f"{SAICCTCPEnum.SAICTrade.MODIFY} {PROTOCOL_VERSION}/{session.session_id}/"
                            f"{ref_id}/upgrades/{upgrades_str}"
                        ),
                    )
                )
            if item.attachments:
                attach_str = ",".join(
                    f"{sec}:{att_type}"
                    for att_type, sec in item.attachments.items()
                )
                outgoing_queue.put_nowait(
                    OutgoingCTCP(
                        target=session.partner_nick,
                        content=(
                            f"{SAICCTCPEnum.SAICTrade.MODIFY} {PROTOCOL_VERSION}/{session.session_id}/"
                            f"{ref_id}/attach/{attach_str}"
                        ),
                    )
                )
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=session.partner_nick,
                    content=f"{SAICCTCPEnum.SAICTrade.ITEMDONE} {PROTOCOL_VERSION}/{session.session_id}/{ref_id}",
                )
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
        elif mod_type == "upgrades":
            for upg_sec in data.split(","):
                if upg_sec:
                    item.upgrades.append(upg_sec)
        elif mod_type == "attach":
            for att_entry in data.split(","):
                if ":" in att_entry:
                    att_sec, att_type = att_entry.split(":", 1)
                    item.attachments[att_type] = att_sec

    @staticmethod
    def _handle_complex_item_done(ref_id: str, state: State):
        session = state.trade
        item = session.partial_partner_items.pop(ref_id, None)
        if not item:
            return

        session.partner_items[ref_id] = item
        session.my_accepted = False
        session.partner_accepted = False

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
        send_trade_reset_accept_to_game(session.session_id)

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

    @staticmethod
    def _execute_trade_swap(state: State, incoming_queue: IncomingQueue):
        session = state.trade
        if not session:
            return

        logger.info(
            "Executing final trade swap for session %s with %s",
            session.session_id,
            session.partner_nick,
        )

        # 1. Add all received partner items into our actor's inventory
        for item in session.partner_items.values():
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
            add_item_to_inventory(
                item_id=item.item_id,
                amount=str(item.amount),
                amount_type=item.amount_type,
                condition=str(item.condition),
                parts_string=parts_string,
                upgrades_string=upgrades_string,
                attachments_string=attachments_string,
            )

        # 2. Tell game that trade succeeded so it releases our offered items
        send_trade_success_to_game(session.session_id)

        incoming_queue.put_nowait(
            IncomingEvent.create_information_event(
                f"Trade Successful with {session.partner_nick}! Items swapped."
            )
        )
        state.trade = None

    # -------------------------------------------------------------------------
    # Game Socket IPC Handlers (Game -> PySAIC)
    # -------------------------------------------------------------------------

    @staticmethod
    @inject.autoparams()
    def handle_game_add_item(
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game notified us player put item in barter window:
        Payload: session_id/ref_id/item_id/amount/amount_type/condition[/parts/upgrades/attachments]
        """
        session = state.trade
        if not session:
            return

        fields = payload.split("/")
        if len(fields) < 6:
            return

        session_id, ref_id, item_id, amount, amount_type, condition = fields[
            :6
        ]
        if session.session_id != session_id:
            return

        parts_dict = {}
        if len(fields) > 6 and fields[6] != "none":
            for part in fields[6].split("|"):
                if ":" in part:
                    p_sec, p_cond = part.split(":")[:2]
                    parts_dict[p_sec] = float(p_cond)

        upgrades_list = []
        if len(fields) > 7 and fields[7] != "none":
            for upg in fields[7].split("|"):
                upg_sec = upg.split(":")[0]
                if upg_sec:
                    upgrades_list.append(upg_sec)

        attachments_dict = {}
        if len(fields) > 8 and fields[8] != "none":
            for att in fields[8].split("|"):
                if ":" in att:
                    att_type, att_sec = att.split(":")[:2]
                    attachments_dict[att_type] = att_sec

        item = TradeItem(
            ref_id=ref_id,
            item_id=item_id,
            amount=int(amount),
            amount_type=amount_type,
            condition=float(condition),
            parts=parts_dict,
            upgrades=upgrades_list,
            attachments=attachments_dict,
        )
        session.my_items[ref_id] = item
        session.my_accepted = False
        session.partner_accepted = False

        # Pre-check item with target client before streaming
        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=session.partner_nick,
                content=(
                    f"{SAICCTCPEnum.SAICTrade.CHECK} {PROTOCOL_VERSION}/{session_id}/"
                    f"{ref_id}/{item_id}/{amount}/{condition}"
                ),
            )
        )

    @staticmethod
    @inject.autoparams()
    def handle_game_del_item(
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game notified us player removed item from barter window:
        Payload: session_id/ref_id
        """
        session = state.trade
        if not session:
            return

        fields = payload.split("/")
        if len(fields) < 2:
            return
        session_id, ref_id = fields[0], fields[1]
        if session.session_id != session_id:
            return

        session.my_items.pop(ref_id, None)
        session.my_accepted = False
        session.partner_accepted = False

        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=session.partner_nick,
                content=f"{SAICCTCPEnum.SAICTrade.DEL} {PROTOCOL_VERSION}/{session_id}/{ref_id}",
            )
        )

    @staticmethod
    @inject.autoparams()
    def handle_game_check_result(
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Game answered section existence check:
        Payload: session_id/ref_id/status (1=OK, 0=Missing)
        """
        session = state.trade
        if not session:
            return

        fields = payload.split("/")
        if len(fields) < 3:
            return
        session_id, ref_id, status = fields[0], fields[1], fields[2]
        if session.session_id != session_id:
            return

        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=session.partner_nick,
                content=f"{SAICCTCPEnum.SAICTrade.CHECK_RESP} {PROTOCOL_VERSION}/{session_id}/{ref_id}/{status}",
            )
        )

    @staticmethod
    @inject.autoparams()
    def handle_game_accept(
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
    ):
        """
        Local player clicked Accept in game:
        Payload: session_id
        """
        session = state.trade
        if not session or session.session_id != payload.strip():
            return

        session.my_accepted = True
        outgoing_queue.put_nowait(
            OutgoingCTCP(
                target=session.partner_nick,
                content=f"{SAICCTCPEnum.SAICTrade.ACCEPT} {PROTOCOL_VERSION}/{session.session_id}",
            )
        )
        TradeUseCase._check_both_accepted(state, outgoing_queue)

    @staticmethod
    @inject.autoparams()
    def handle_game_verify_result(
        payload: str,
        state: State,
        outgoing_queue: OutgoingQueue,
        incoming_queue: IncomingQueue,
    ):
        """
        Game finished pre-swap inventory integrity check:
        Payload: session_id/status (1=Verified, 0=Exploit/Missing)
        """
        session = state.trade
        if not session:
            return

        fields = payload.split("/")
        session_id = fields[0]
        status = fields[1] if len(fields) > 1 else "0"
        if session.session_id != session_id:
            return

        if status == "1":
            # Verification passed: send COMMIT
            outgoing_queue.put_nowait(
                OutgoingCTCP(
                    target=session.partner_nick,
                    content=f"{SAICCTCPEnum.SAICTrade.COMMIT} {PROTOCOL_VERSION}/{session_id}",
                )
            )
            # If partner also committed, finish swap
            TradeUseCase._execute_trade_swap(state, incoming_queue)
        else:
            # Verification failed! Abort immediately
            logger.warning(
                "Inventory verification failed for trade session %s",
                session_id,
            )
            TradeUseCase.cancel_active_trade(
                reason="inventory_verification_failed"
            )

    @staticmethod
    @inject.autoparams()
    def handle_game_cancel(
        payload: str,
        state: State,
    ):
        """
        Local player closed trade window or pressed Esc in game:
        Payload: session_id/reason
        """
        fields = payload.split("/")
        reason = fields[1] if len(fields) > 1 else "window_closed"
        TradeUseCase.cancel_active_trade(reason=reason)
