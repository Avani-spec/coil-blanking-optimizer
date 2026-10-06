from pathlib import Path

from streamlit.testing.v1 import AppTest

APP = str(Path(__file__).resolve().parents[1] / "app.py")


def test_app_runs_and_reports():
    at = AppTest.from_file(APP, default_timeout=120).run()
    assert not at.exception
    assert at.metric[0].value.endswith("%")
    at.text_input[0].input("abc").run()
    assert at.error and "numbers" in at.error[0].value
