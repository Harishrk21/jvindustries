from app.services.calculations import compute_production_loss, loss_requires_approval


def test_plan_excess_loss():
    """TEST_PLAN: In 100000 Out 97500 → 2.50% vs limit 2.00% → approval."""
    loss_qty, loss_pct = compute_production_loss(qty_in=100000, qty_out=97500)
    assert loss_qty == 2500.0
    assert loss_pct == 2.5
    assert loss_requires_approval(loss_percent=loss_pct, loss_limit_percent=2.0) is True


def test_within_limit():
    _, loss_pct = compute_production_loss(qty_in=100000, qty_out=98500)
    assert loss_pct == 1.5
    assert loss_requires_approval(loss_percent=loss_pct, loss_limit_percent=2.0) is False
