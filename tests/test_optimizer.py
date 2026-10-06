from blanking.analysis import add_recovery, flag_high_loss, opportunity, synthetic_batches
from blanking.optimizer import Constraints, Order, enumerate_configs, optimise


def test_search_space_and_constraints():
    c = Constraints([1000, 1250, 1500], min_strip_width=1100, max_lanes=4, angle_step=0.5)
    df = enumerate_configs(Order(300, 1.0), c)
    assert len(df) >= 3 * (1 + 3 * 121)               # > 500 combinations (+ exact angles)
    best = optimise(Order(300, 1.0, quantity=10_000), c, top=50)
    assert (best.coil_width >= 1100).all() and (best.lanes <= 4).all()
    assert (best.width_used <= best.coil_width + 1e-9).all()
    assert best.recovery.is_monotonic_decreasing
    assert (best.coils_needed > 0).all()


def test_angle_limits_respected():
    best = optimise(Order(260, 1.0), Constraints([1250], angle_min=70, angle_max=90), top=20)
    assert ((best.angle >= 70) | (best.lanes == 1)).all()


def test_stock_constraint_reorders():
    c = Constraints([1000, 1500], coil_stock_kg={1000: 1e9, 1500: 0})
    best = optimise(Order(240, 1.0, quantity=100_000), c)
    assert best.iloc[0].coil_width == 1000 and bool(best.iloc[0].enough_stock)


def test_analysis_finds_bad_batches_and_opportunity():
    df = flag_high_loss(add_recovery(synthetic_batches(400, seed=1)))
    bad = df[df.high_loss]
    assert len(bad) > 0 and (bad.process_loss > df.process_loss.median()).all()
    opp = opportunity(df, Constraints([1000, 1100, 1250, 1350, 1500]))
    assert (opp.gain_pp >= -1e-9).all() and opp.gain_pp.max() > 0
