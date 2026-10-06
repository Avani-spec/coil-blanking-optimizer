"""Analysis of historical blanking batches.

Expected columns: batch_id, date, diameter, thickness, coil_width, lanes,
angle, bridge, edge, input_kg, output_kg (good blanks).

* ``recovery`` = output_kg / input_kg for each batch
* baseline recovery by diameter
* high-loss batches: process loss (theoretical recovery of the layout used
  minus actual recovery) with a robust z-score (median / MAD) above ``z``
  (default 3). Using process loss rather than raw recovery separates bad
  batches from batches that simply used a less efficient layout.
* opportunity: theoretical recovery of the configuration used vs. the best
  feasible configuration found by the optimiser
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from .geometry import layout
from .optimizer import Constraints, Order, optimise


def add_recovery(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["recovery"] = df.output_kg / df.input_kg
    df["theoretical"] = [layout(r.diameter, r.bridge, r.edge, r.lanes, r.angle, r.coil_width).recovery
                         for r in df.itertuples()]
    # process losses = what the geometry allowed minus what was actually achieved
    df["process_loss"] = df.theoretical - df.recovery
    return df


def flag_high_loss(df: pd.DataFrame, z: float = 3.0) -> pd.DataFrame:
    df = df.copy()
    x = df.process_loss
    mad = (x - x.median()).abs().median() * 1.4826 + 1e-9
    df["robust_z"] = (x - x.median()) / mad
    df["high_loss"] = df.robust_z > z
    return df


def baseline(df: pd.DataFrame) -> pd.DataFrame:
    return df.groupby("diameter").agg(batches=("batch_id", "count"), input_t=("input_kg", lambda x: x.sum() / 1000),
                                      recovery_mean=("recovery", "mean"), recovery_p10=("recovery", lambda x: x.quantile(.1)),
                                      theoretical_mean=("theoretical", "mean"), high_loss=("high_loss", "sum"))


def opportunity(df: pd.DataFrame, constraints: Constraints) -> pd.DataFrame:
    """Best theoretical recovery per (diameter, thickness) vs what was used."""
    rows = []
    for (d, t), grp in df.groupby(["diameter", "thickness"]):
        r0 = grp.iloc[0]
        best = optimise(Order(d, t, bridge=r0.bridge, edge=r0.edge), constraints, top=1)
        if best.empty:
            continue
        b = best.iloc[0]
        used = np.average(grp.theoretical, weights=grp.input_kg)
        rows.append(dict(diameter=d, thickness=t, batches=len(grp), used_theoretical=used,
                         best_theoretical=b.recovery, gain_pp=(b.recovery - used) * 100,
                         best_width=b.coil_width, best_lanes=b.lanes, best_angle=b.angle,
                         input_t=grp.input_kg.sum() / 1000))
    out = pd.DataFrame(rows)
    if not out.empty:
        out["material_saved_t"] = out.input_t * (1 - out.used_theoretical / out.best_theoretical)
    return out


def synthetic_batches(n: int = 600, seed: int = 0) -> pd.DataFrame:
    """Fake production log for demos and tests. Operators pick configurations
    by habit (fixed angle, sometimes too-wide coils); actual recovery is the
    theoretical value minus process losses, with occasional bad batches."""
    rng = np.random.default_rng(seed)
    widths = [1000, 1100, 1250, 1350, 1500]
    rows = []
    for i in range(n):
        d = float(rng.choice([180, 220, 260, 300, 355, 405]))
        t = float(rng.choice([0.8, 1.0, 1.2, 1.5]))
        bridge, edge = 3.0, 5.0
        angle = float(rng.choice([60.0, 90.0], p=[0.6, 0.4]))
        W = float(rng.choice(widths))
        lanes = 1
        while layout(d, bridge, edge, lanes + 1, angle, W).feasible and lanes < 6:
            lanes += 1
        L = layout(d, bridge, edge, lanes, angle, W)
        input_kg = float(rng.uniform(2000, 6000))
        loss = rng.normal(0.02, 0.006) + (rng.random() < 0.04) * rng.uniform(0.04, 0.12)
        rows.append(dict(batch_id=f"B{i:05d}", date=pd.Timestamp("2025-01-01") + pd.Timedelta(days=int(i * 365 / n)),
                         diameter=d, thickness=t, coil_width=W, lanes=lanes, angle=angle,
                         bridge=bridge, edge=edge, input_kg=round(input_kg, 1),
                         output_kg=round(input_kg * max(L.recovery - loss, 0.05), 1)))
    return pd.DataFrame(rows)
