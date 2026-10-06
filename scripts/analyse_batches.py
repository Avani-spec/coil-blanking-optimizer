"""Analyse a production log (CSV) or synthetic data.

    python scripts/analyse_batches.py --csv data/batches.csv
    python scripts/analyse_batches.py --synthetic
"""
import argparse
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from blanking.analysis import add_recovery, baseline, flag_high_loss, opportunity, synthetic_batches  # noqa: E402
from blanking.optimizer import Constraints  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("--csv"); ap.add_argument("--synthetic", action="store_true")
ap.add_argument("--widths", default="1000,1100,1250,1350,1500")
ap.add_argument("--out", default="reports")
a = ap.parse_args()
df = synthetic_batches() if a.synthetic else pd.read_csv(a.csv, parse_dates=["date"])
df = flag_high_loss(add_recovery(df))
out = Path(a.out); out.mkdir(exist_ok=True)
pd.set_option("display.width", 140)
print("Baseline by diameter\n", baseline(df).round(3), "\n")
hl = df[df.high_loss].sort_values("robust_z", ascending=False)
print(f"{len(hl)} high-loss batches (process-loss robust z > 3), worst 10:\n",
      hl[["batch_id", "date", "diameter", "coil_width", "lanes", "angle", "recovery", "theoretical", "process_loss", "robust_z"]].head(10).round(3), "\n")
opp = opportunity(df, Constraints([float(w) for w in a.widths.split(",")]))
print("Configuration opportunity\n", opp.round(3).to_string(index=False))
hl.to_csv(out / "high_loss_batches.csv", index=False); opp.to_csv(out / "opportunity.csv", index=False)
print(f"\nCSV files written to {out}/")
