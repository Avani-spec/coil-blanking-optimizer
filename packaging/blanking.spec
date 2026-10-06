# Build:  pyinstaller packaging/blanking.spec   ->  dist/BlankingOptimizer/
# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata

datas = [("../app.py", "."), ("../src/blanking", "src/blanking")]
datas += collect_data_files("streamlit") + copy_metadata("streamlit")
hidden = collect_submodules("streamlit") + ["matplotlib.backends.backend_agg"]

a = Analysis(["run_app.py"], pathex=["../src"], datas=datas, hiddenimports=hidden,
             excludes=["torch", "tensorflow", "transformers", "IPython", "notebook"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="BlankingOptimizer", console=True)
coll = COLLECT(exe, a.binaries, a.datas, name="BlankingOptimizer")
