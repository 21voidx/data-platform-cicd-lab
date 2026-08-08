from transform import calculate_net_revenue


def test_calculate_net_revenue():
    assert calculate_net_revenue(100_000, 20_000) == 80_000