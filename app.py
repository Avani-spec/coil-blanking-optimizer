"""Operator dashboard.  streamlit run app.py"""
import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from blanking.geometry import layout  # noqa: E402
from blanking.optimizer import Constraints, Order, enumerate_configs, optimise  # noqa: E402
from blanking.plot import draw_layout  # noqa: E402

st.set_page_config(page_title="Circle blanking layout", layout="wide")
st.title("Circle blanking layout")

with st.sidebar:
    st.header("Order")
    d = st.number_input("Blank diameter (mm)", 20.0, 1500.0, 260.0, 1.0)
    t = st.number_input("Thickness (mm)", 0.2, 10.0, 1.0, 0.1)
    qty = st.number_input("Blanks required", 0, 10_000_000, 50_000, 1000)
    st.header("Tooling")
    bridge = st.number_input("Bridge between blanks (mm)", 0.0, 50.0, 3.0, 0.5)
    edge = st.number_input("Edge trim per side (mm)", 0.0, 50.0, 5.0, 0.5)
    max_lanes = st.slider("Max lanes on die", 1, 10, 6)
    amin, amax = st.slider("Allowed blanking angle (°)", 30.0, 90.0, (30.0, 90.0), 0.5)
    st.header("Line and stock")
    widths_txt = st.text_input("Coil widths in stock (mm, comma separated)", "1000, 1100, 1250, 1350, 1500")
    wmin, wmax = st.slider("Line strip width limits (mm)", 100, 2500, (600, 1600), 10)
    coil_kg = st.number_input("Coil mass (kg)", 100.0, 30000.0, 3000.0, 100.0)
    head_tail = st.number_input("Head + tail scrap per coil (mm)", 0.0, 20000.0, 1500.0, 100.0)

try:
    widths = sorted({float(w) for w in widths_txt.replace(";", ",").split(",") if w.strip()})
except ValueError:
    st.error("Coil widths must be numbers separated by commas, e.g. 1000, 1250, 1500.")
    st.stop()

order = Order(d, t, int(qty), bridge, edge)
cons = Constraints(widths, wmin, wmax, max_lanes, amin, amax, 0.5, None, head_tail, coil_kg)
best = optimise(order, cons, top=10)
n_eval = len(enumerate_configs(order, cons))

if best.empty:
    st.error("No configuration fits. Check that at least one coil width is inside the line limits "
             "and wider than the blank plus both edge trims.")
    st.stop()

st.caption(f"Evaluated {n_eval:,} coil width × lane × angle combinations.")
top = best.iloc[0]
c1, c2, c3, c4 = st.columns(4)
c1.metric("Best recovery", f"{top.recovery:.1%}")
c2.metric("Coil width", f"{top.coil_width:g} mm")
c3.metric("Lanes / angle", f"{int(top.lanes)} @ {top.angle:g}°")
if qty:
    c4.metric("Coils for order", f"{int(top.coils_needed)}")

left, right = st.columns([3, 2])
with left:
    st.subheader("Ranked configurations")
    show = best.copy()
    show["recovery"] = (show.recovery * 100).round(2)
    cols = ["coil_width", "lanes", "angle", "pitch", "width_used", "side_scrap", "recovery", "blanks_per_m"]
    if qty:
        cols += ["blanks_per_coil", "coils_needed", "scrap_kg"]
    st.dataframe(show[cols].rename(columns={"recovery": "recovery %"}).round(1), hide_index=True,
                 width="stretch")
    pick = st.selectbox("Preview configuration", show.index,
                        format_func=lambda i: f"#{i + 1}: {show.at[i, 'coil_width']:g} mm, "
                                              f"{int(show.at[i, 'lanes'])} lanes @ {show.at[i, 'angle']:g}°")
    r = best.loc[pick]
    L = layout(d, bridge, edge, int(r.lanes), r.angle, r.coil_width)
    st.pyplot(draw_layout(L).figure)

with right:
    st.subheader("Check a current setting")
    cw = st.selectbox("Coil width", widths, index=len(widths) - 1)
    lanes = st.number_input("Lanes", 1, 10, 3)
    ang = st.number_input("Angle (°)", 30.0, 90.0, 60.0, 0.5)
    cur = layout(d, bridge, edge, lanes, ang, cw)
    if not cur.feasible:
        st.error(f"Does not fit: needs {cur.width_used:.1f} mm of strip, coil is {cw:g} mm.")
    else:
        st.write(f"Recovery **{cur.recovery:.1%}**, pitch {cur.pitch:.1f} mm, side scrap {cur.side_scrap:.1f} mm.")
        gain = (top.recovery - cur.recovery) * 100
        if gain > 0.05:
            st.success(f"The top configuration recovers {gain:.1f} percentage points more material.")
        else:
            st.info("This setting is already as good as the best configuration found.")
    st.subheader("Recovery vs angle")
    all_cfg = enumerate_configs(order, cons)
    sub = all_cfg[all_cfg.feasible & (all_cfg.coil_width == cw) & (all_cfg.lanes > 1)]
    if not sub.empty:
        chart = sub.pivot_table(index="angle", columns="lanes", values="recovery").mul(100)
        chart.columns = [f"{c} lanes" for c in chart.columns]
        st.line_chart(chart)
