"""Bundle the Streamlit app into ONE self-contained HTML file that runs
entirely in the browser via stlite (Streamlit on Pyodide/WebAssembly).
No Python install or server needed: open the file, or host it on any static
site. (The first load downloads the Pyodide runtime from the CDN.)

    python stlite/build.py            ->  docs/index.html  (serve with GitHub Pages)
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
STLITE = "1.9.2"  # @stlite/browser version
FILES = ["app.py", *sorted(str(p.relative_to(ROOT)) for p in (ROOT / "src" / "blanking").glob("*.py"))]

files = {f: (ROOT / f).read_text() for f in FILES}
html = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Circle blanking layout</title>
  <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.css" />
</head>
<body>
  <div id="root"></div>
  <script type="module">
    import {{ mount }} from "https://cdn.jsdelivr.net/npm/@stlite/browser@{STLITE}/build/stlite.js";
    mount({{
      requirements: ["matplotlib", "pandas", "numpy"],
      entrypoint: "app.py",
      files: {json.dumps(files)},
    }}, document.getElementById("root"));
  </script>
</body>
</html>
"""
out = ROOT / "docs" / "index.html"
out.parent.mkdir(exist_ok=True)
out.write_text(html)
print(f"wrote {out} ({out.stat().st_size / 1024:.0f} KB, {len(files)} files embedded)")
