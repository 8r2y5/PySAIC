from decimal import Decimal

from pysaic.state import (
    AlwaysNetworkDestructionStrategy,
    MalformOnlyNetworkDestructionStrategy,
    NeverNetworkDestructionStrategy,
    WeightsNetworkDestructionStrategy,
)


def test_weight_network_destruction_strategy_weights():
    total_weight = Decimal(
        sum(WeightsNetworkDestructionStrategy.STRATEGY_WEIGHTS.values())
    )
    data = {
        strategy: {
            "percentage": round((weight / total_weight) * 100, 2),
            "one_in_x": round(total_weight / weight, 2),
        }
        for strategy, weight in WeightsNetworkDestructionStrategy.STRATEGY_WEIGHTS.items()
    }

    assert total_weight == 15
    assert data == {
        NeverNetworkDestructionStrategy: {
            "one_in_x": Decimal("15.00"),
            "percentage": Decimal("6.67"),
        },
        AlwaysNetworkDestructionStrategy: {
            "one_in_x": Decimal("1.50"),
            "percentage": Decimal("66.67"),
        },
        MalformOnlyNetworkDestructionStrategy: {
            "one_in_x": Decimal("3.75"),
            "percentage": Decimal("26.67"),
        },
    }
