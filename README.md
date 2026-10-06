# Circle blanking layout optimizer

Picks the coil width, number of lanes and blanking angle that recover the
most material when punching circular blanks from aluminium coil. It also
analyses production logs to baseline recovery and flag high-loss batches.

> **About this repository.** This is an independent, generic
> re-implementation of a problem I worked on during a data-science
> internship. It contains no company code or data. All bundled data is
> synthetic, and the numbers shown here come from that synthetic data.

## The problem

Circular blanks (later spun or drawn into cookware and similar parts) are
punched from coil in one or more lanes. Recovery is the share of the coil's
area that ends up as blanks. It depends on:

- **coil width** W, chosen from what is in stock
- **lanes** k, limited by the die
- **blanking angle** θ, the stagger between adjacent lanes
- **bridge** b (minimum web between blanks) and **edge trim** e (each side)

With centre spacing s = D + b, adjacent lanes sit s·sin θ apart and the
pitch along the coil is max(s, 2s·cos θ). θ = 60° is hexagonal packing,
θ = 30° is the same packing rotated, and θ = 90° is a square grid. The
pattern fits if 2e + D + (k − 1)·s·sin θ ≤ W, and

```
recovery = k · πD²/4  /  (W · pitch)
```

A wider coil can take an extra lane, but only if the stagger angle is reduced
enough for the pattern to fit. That means a longer pitch and wasted side
strips, so the best choice isn't obvious by eye.

## What it does

- **Grid search.** Every stocked width × lane count × angle (0.5° steps,
  typically 500+ combinations) is checked against strip-width limits, die
  lane limits and allowed angles. For each width and lane count it also adds
  the exact closed-form optimum angle: where the pattern exactly fills the
  coil, which usually falls between grid points.
- **Order planning.** For a required quantity it computes coil length from
  mass, blanks per coil (exact per-lane counts, minus head and tail scrap),
  coils needed and scrap in kg. Configurations whose width is out of stock
  can be ranked last.
- **Production log analysis.** For each batch it computes actual and
  theoretical recovery. Batches are flagged when their *process loss*
  (theoretical − actual) is a robust outlier (median/MAD z > 3). That
  separates genuinely bad batches from batches that just used a worse
  layout. It also estimates how much material a better configuration would
  have saved.
- **Operator dashboard (Streamlit).** Enter order and tooling details and get
  ranked configurations, a to-scale layout preview, a check of the current
  setting with clear error messages, and recovery versus angle.
- **Runs without a server or cloud.**
  - `stlite/build.py` produces `docs/index.html`, one HTML file that runs
    Streamlit entirely in the browser (Pyodide/WebAssembly). Enable GitHub
    Pages on the `docs/` folder and the repo gets a live demo link.
  - `packaging/blanking.spec` builds a PyInstaller desktop executable that
    serves the app on localhost.

## Usage

```bash
pip install -r requirements.txt
pytest -q                                      # 161 tests
streamlit run app.py
python scripts/analyse_batches.py --synthetic  # or --csv your_log.csv
python stlite/build.py                         # -> docs/index.html
cd packaging && pyinstaller blanking.spec      # -> packaging/dist/BlankingOptimizer/
```

PyInstaller builds for the operating system it runs on, so build the Windows
`.exe` on a Windows machine. The executable starts the app on
`127.0.0.1:8501` and opens the browser itself.

A log CSV for `analyse_batches.py` needs these columns: `batch_id, date,
diameter, thickness, coil_width, lanes, angle, bridge, edge, input_kg,
output_kg`.

## Verification

The tests check the geometry against first principles rather than against
the code's own formulas:

- No two generated blank centres are closer than D + b (brute-force pairwise
  distances), and every blank stays inside the edge trim, across 128
  combinations of diameter, bridge, lanes and angle.
- Blank counts from the closed-form formula match the explicitly generated
  layout.
- Unconstrained density peaks at the hexagonal angles (30° and 60°).
- The closed-form optimum angle is at least as good as a 0.01° grid search
  for every tested width and lane count.
- The Streamlit app, including the copy embedded in the stlite bundle, runs
  headlessly without errors.

## Layout

```
src/blanking/geometry.py   layout model, closed-form optimum angle
src/blanking/optimizer.py  constrained search, order planning
src/blanking/analysis.py   recovery baseline, high-loss detection, opportunity
src/blanking/plot.py       to-scale layout drawing
app.py                     Streamlit dashboard
stlite/build.py            single-file browser build
packaging/                 PyInstaller launcher + spec
scripts/analyse_batches.py
```
