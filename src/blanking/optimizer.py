"""Enumerate coil width × lanes × angle configurations under machine and
order constraints and rank them by material recovery."""
from __future__ import annotations

import math
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

import math as _m

from .geometry import AL_DENSITY_KG_MM3, best_angle, layout


@dataclass
class Constraints:
    coil_widths: list[float]                      # widths available in stock (mm)
    min_strip_width: float = 0.0                  # line / straightener limits (mm)
    max_strip_width: float = 2000.0
    max_lanes: int = 6                            # die / press limit
    angle_min: float = 30.0
    angle_max: float = 90.0
    angle_step: float = 0.5
    coil_stock_kg: dict | None = None             # width -> kg available (optional)
    head_tail_mm: float = 0.0                     # scrap at each coil's start+end
    coil_kg: float = 3000.0                       # typical coil mass


@dataclass
class Order:
    diameter: float
    thickness: float
    quantity: int = 0
    bridge: float = 3.0
    edge: float = 5.0


def enumerate_configs(order: Order, c: Constraints) -> pd.DataFrame:
    angles = np.round(np.arange(c.angle_min, c.angle_max + 1e-9, c.angle_step), 4)
    rows = []
    for W in c.coil_widths:
        for k in range(1, c.max_lanes + 1):
            cand = [90.0] if k == 1 else list(angles)
            if k > 1:
                # the exact optimum often lies between grid points (the angle at
                # which the pattern exactly fills the coil); add it, rounded
                # down to 0.01 deg so it still fits
                exact = best_angle(order.diameter, order.bridge, order.edge, k, W, c.angle_min, c.angle_max)
                if exact is not None:
                    exact = _m.floor(exact * 100) / 100
                    if exact >= c.angle_min and exact not in cand:
                        cand.append(exact)
            for a in cand:
                L = layout(order.diameter, order.bridge, order.edge, k, a, W)
                reason = None
                if not L.feasible:
                    reason = "pattern wider than coil"
                elif not (c.min_strip_width <= W <= c.max_strip_width):
                    reason = "coil width outside line limits"
                rows.append(dict(coil_width=W, lanes=k, angle=float(a), pitch=L.pitch,
                                 width_used=L.width_used, side_scrap=L.side_scrap,
                                 recovery=L.recovery, blanks_per_m=L.blanks_per_metre,
                                 feasible=reason is None, reason=reason))
    return pd.DataFrame(rows)


def plan_order(row, order: Order, c: Constraints) -> dict:
    """Coils, metres and kg of input needed to produce ``order.quantity`` blanks."""
    L = layout(order.diameter, order.bridge, order.edge, row.lanes, row.angle, row.coil_width)
    coil_len = L.coil_length(c.coil_kg, order.thickness)
    per_coil = L.blanks_from_length(coil_len, c.head_tail_mm)
    if per_coil == 0:
        return dict(blanks_per_coil=0, coils_needed=math.inf, input_kg=math.inf, scrap_kg=math.inf)
    coils = math.ceil(order.quantity / per_coil) if order.quantity else 0
    input_kg = coils * c.coil_kg
    blank_kg = order.quantity * L.blank_area * order.thickness * AL_DENSITY_KG_MM3
    return dict(blanks_per_coil=per_coil, coils_needed=coils, input_kg=input_kg,
                scrap_kg=input_kg - blank_kg,
                effective_recovery=blank_kg / input_kg if input_kg else L.recovery)


def optimise(order: Order, c: Constraints, top: int = 10, dedupe_angles: bool = True) -> pd.DataFrame:
    """Rank feasible configurations. Among angles giving the same recovery for
    one width and lane count, keep the one closest to 60° (most robust)."""
    df = enumerate_configs(order, c)
    ok = df[df.feasible].copy()
    if ok.empty:
        return ok
    ok["recovery_r"] = ok.recovery.round(6)
    if dedupe_angles:
        ok["dist60"] = (ok.angle - 60).abs()
        ok = ok.sort_values(["recovery_r", "dist60"], ascending=[False, True])
        ok = ok.drop_duplicates(["coil_width", "lanes", "recovery_r"])
    ok = ok.sort_values("recovery", ascending=False)
    if order.quantity:
        plans = pd.DataFrame([plan_order(r, order, c) for r in ok.itertuples()], index=ok.index)
        ok = pd.concat([ok, plans], axis=1)
        if c.coil_stock_kg:
            stock = ok.coil_width.map(c.coil_stock_kg).fillna(0)
            ok["enough_stock"] = stock >= ok.input_kg
            ok = ok.sort_values(["enough_stock", "recovery"], ascending=[False, False])
    return ok.drop(columns=["recovery_r", "dist60", "feasible", "reason"], errors="ignore").head(top).reset_index(drop=True)
