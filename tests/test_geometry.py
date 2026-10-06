import itertools

import numpy as np
import pytest
from scipy.spatial.distance import pdist

from blanking.geometry import best_angle, layout

CASES = list(itertools.product([150, 260.5], [2, 4], [1, 2, 3, 5], [30, 35, 45, 59, 60, 61, 75, 90]))


@pytest.mark.parametrize("d,b,k,a", CASES)
def test_layout_is_physically_valid(d, b, k, a):
    L = layout(d, b, 5, k, a, 3000)
    P = L.centres(8 * L.pitch + d)
    if len(P) > 1:  # no two blanks closer than diameter + bridge
        assert pdist(P).min() >= d + b - 1e-6
    r = d / 2
    off = (L.coil_width - L.width_used) / 2
    assert P[:, 1].min() - r >= off + L.edge - 1e-6
    assert P[:, 1].max() + r <= L.coil_width - off - L.edge + 1e-6
    assert np.isclose(P[:, 1].max() - P[:, 1].min() + d + 2 * L.edge, L.width_used)


def test_hexagonal_is_densest_unconstrained():
    # with unlimited width, blanks per unit area peak at 60 deg and at 30 deg
    # (the same hexagonal packing rotated); 45 deg is strictly worse
    def dens(a):
        L = layout(200, 3, 0, 4, a, 1e9)
        return 1 / (L.pitch * L.lane_spacing)
    grid = {a: dens(a) for a in np.arange(30, 90.5, 0.5)}
    top = max(grid.values())
    assert np.isclose(grid[60.0], top) and np.isclose(grid[30.0], top)
    assert dens(45) < 0.9 * top


def test_blank_count_matches_centres():
    for k, a in [(1, 90), (3, 60), (4, 42.5), (2, 90)]:
        L = layout(220, 3, 5, k, a, 1500)
        for length in (500, 1234.5, 10_000):
            assert L.blanks_from_length(length) == len(L.centres(length))


def test_recovery_definition():
    L = layout(100, 0, 0, 1, 90, 100)
    assert np.isclose(L.recovery, np.pi / 4)          # one circle per square
    L = layout(100, 0, 0, 10, 60, 100 + 9 * 100 * np.sin(np.pi / 3))
    assert 0.85 < L.recovery < 0.907                   # approaching hex packing pi/sqrt(12)


@pytest.mark.parametrize("W", [800, 1000, 1100, 1250, 1350, 1500])
@pytest.mark.parametrize("k", [2, 3, 4, 5])
def test_closed_form_angle_matches_grid_search(W, k):
    d, b, e = 260, 3, 5
    grid = [layout(d, b, e, k, a, W) for a in np.arange(30, 90.0001, 0.01)]
    grid = [g for g in grid if g.feasible]
    a = best_angle(d, b, e, k, W)
    if not grid:
        assert a is None
    else:
        assert a is not None
        # the closed form is at least as good as a fine grid search
        assert layout(d, b, e, k, a, W).feasible
        assert layout(d, b, e, k, a, W).recovery >= max(g.recovery for g in grid) - 1e-12


def test_optimiser_includes_exact_angle():
    from blanking.optimizer import Constraints, Order, optimise
    best = optimise(Order(260, 1.0, bridge=3, edge=5), Constraints([1100], max_lanes=5), top=1).iloc[0]
    exact = best_angle(260, 3, 5, int(best.lanes), 1100)
    assert abs(best.angle - exact) < 0.01
