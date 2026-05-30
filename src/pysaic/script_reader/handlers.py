from pysaic.config import Config
from pysaic.entities import IncomingQueue, OutgoingQueue
from pysaic.script_reader.entities import (
    ChannelMessage,
    Handshake,
    Death,
    ConnectionLost,
    Money,
    ChannelChange,
    ActorStatus,
    Location,
    Achievement,
    Reputation,
    Rank,
    AFK,
    Item,
)
from pysaic.state import State
from pysaic.use_cases.game import (
    GameChannelMessageUseCase,
    GameHandshakeUseCase,
    PlayerDiedUseCase,
    ConnectionLostUseCase,
    MoneyChangeUseCase,
    channel_change_use_case,
    actor_status_use_case,
    location_use_case,
    achievement_use_case,
    reputation_use_case,
    rank_use_case,
    afk_use_case,
    item_add,
)


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


async def _handle_item(
    rest: str,
    _config: Config,
    incoming_queue: IncomingQueue,
    _outgoing_queue: OutgoingQueue,
    _state: State,
):
    await item_add(Item.from_line(rest), incoming_queue)
