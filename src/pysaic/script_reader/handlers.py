import logging
from collections import Counter, defaultdict

from pysaic.config import Config
from pysaic.entities import IncomingQueue, OutgoingQueue
from pysaic.script_reader.entities import (
    AFK,
    Achievement,
    ActorStatus,
    ChannelChange,
    ChannelMessage,
    ConnectionLost,
    Death,
    Error,
    Handshake,
    InventoryItem,
    Item,
    Location,
    Money,
    Rank,
    Reputation,
)
from pysaic.state import State
from pysaic.use_cases.game import (
    ConnectionLostUseCase,
    GameChannelMessageUseCase,
    GameHandshakeUseCase,
    MoneyChangeUseCase,
    PlayerDiedUseCase,
    achievement_use_case,
    actor_status_use_case,
    afk_use_case,
    channel_change_use_case,
    item_add,
    location_use_case,
    rank_use_case,
    reputation_use_case,
)

logger = logging.getLogger(__name__)


async def _handle_channel_message(
    rest: str,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    _state: State,
):
    await GameChannelMessageUseCase(
        config,
        ChannelMessage.from_line(config.nick, rest),
        incoming_queue,
        outgoing_queue,
    ).execute()


async def _handle_handshake(
    rest: str,
    config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    state: State,
):
    await GameHandshakeUseCase(
        state, config, Handshake.from_line(rest), incoming_queue
    ).execute()


async def _handle_death(
    rest: str,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    _state: State,
):
    await PlayerDiedUseCase(
        config,
        Death.from_line(rest),
        incoming_queue,
        outgoing_queue,
    ).execute()


async def _handle_connection_lost(
    rest: str,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    _state: State,
):
    await ConnectionLostUseCase(
        config,
        ConnectionLost.from_line(rest),
        incoming_queue,
        outgoing_queue,
    ).execute()


async def _handle_money(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    _state: State,
):
    await MoneyChangeUseCase(
        Money.from_line(rest), incoming_queue, outgoing_queue
    ).execute()


async def _handle_actor_status(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await actor_status_use_case(ActorStatus.from_line(rest), incoming_queue)


async def _handle_channel_change(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await channel_change_use_case(
        ChannelChange.from_line(rest), incoming_queue
    )


async def _handle_location(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await location_use_case(Location.from_line(rest), incoming_queue)


async def _handle_achievement(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await achievement_use_case(Achievement.from_line(rest), incoming_queue)


async def _handle_reputation(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await reputation_use_case(Reputation.from_line(rest), incoming_queue)


async def _handle_rank(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await rank_use_case(Rank.from_line(rest), incoming_queue)


async def _handle_afk(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await afk_use_case(AFK.from_line(rest), incoming_queue)


class Inventory:
    logger = logger.getChild("Inventory")

    @classmethod
    async def _handle_inventory_start(
        cls,
        rest: str,
        _config: Config,
        _incoming_queue: IncomingQueue,
        _outgoing_queue: OutgoingQueue,
        state: State,
    ):
        cls.logger.info("Handling inventory start: %s", rest)
        state.inventory.clear()

    @classmethod
    async def _handle_inventory_end(
        cls,
        rest: str,
        _config: Config,
        _incoming_queue: IncomingQueue,
        _outgoing_queue: OutgoingQueue,
        state: State,
    ):
        state.inventory.release_lock()
        cls.logger.info("Handling inventory end: %s", rest)
        cls.logger.info("Inventory: %s", state.inventory)
        inventory = defaultdict(list)
        for item in state.inventory:
            inventory[item.item_id].append(item)

        cls.logger.info("Parsed inventory: %s", inventory)
        money_counter = Counter()
        for items in inventory.values():
            for item in items:
                money_counter[item.item_id] += (
                    item.estimated_value
                    + sum(part.estimated_value for part in item.parts)
                    + sum(upgrade.value for upgrade in item.upgrades)
                    + sum(attachment.value for attachment in item.attachments)
                )

        estimated_inventory_value = sum(money_counter.values())
        cls.logger.info(
            "Estimated inventory value: %s", estimated_inventory_value
        )

        most_expensive_item = max(
            money_counter, key=lambda item_id: money_counter[item_id]
        )
        cls.logger.info("Most expensive item: %s", most_expensive_item)

    @classmethod
    async def _handle_inventory_item(
        cls,
        rest: str,
        _config: Config,
        _incoming_queue: IncomingQueue,
        _outgoing_queue: OutgoingQueue,
        state: State,
    ):
        cls.logger.info("Handling inventory item: %s", rest)
        state.inventory.append_item(InventoryItem.from_line(rest))


async def _handle_item(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await item_add(Item.from_line(rest), incoming_queue)


async def _handle_error(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await incoming_queue.put(
        IncomingQueue.create_error_event(Error.from_line(rest).content)
    )


async def _handle_trade_add_item(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_add_item(rest)


async def _handle_trade_del_item(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_del_item(rest)


async def _handle_trade_check_result(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_check_result(rest)


async def _handle_trade_accept(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_accept(rest)


async def _handle_trade_verify_result(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_verify_result(rest)


async def _handle_trade_cancel(
    rest: str,
    _config: Config,
    _incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    from pysaic.use_cases.trade import TradeUseCase

    TradeUseCase.handle_game_cancel(rest)


async def _handle_query(
    rest: str,
    config: Config,
    incoming_queue: IncomingQueue,
    outgoing_queue: OutgoingQueue,
    state: State,
):
    await _handle_channel_message(
        f"/msg {rest}", config, incoming_queue, outgoing_queue, state
    )
