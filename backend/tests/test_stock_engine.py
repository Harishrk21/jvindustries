from app.services.stock_engine import signed_qty


def test_signed_qty_directions():
    assert signed_qty("IN", 200000) == 200000
    assert signed_qty("OUT", 150000) == -150000
    assert signed_qty("OPENING", 100000) == 100000
    assert signed_qty("TRANSFER_IN", 10) == 10
    assert signed_qty("TRANSFER_OUT", 10) == -10


def test_plan_t03_close_balance_math():
    """TEST_PLAN: Open 100k + Recv 200k − Load 150k = Close 150k."""
    open_ = signed_qty("OPENING", 100000)
    recv = signed_qty("IN", 200000)
    load = signed_qty("OUT", 150000)
    assert open_ + recv + load == 150000
