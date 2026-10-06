"""Entry point for the PyInstaller executable: starts the Streamlit server on
localhost and opens the browser. No internet or cloud services needed.

Headless mode skips Streamlit's first-run e-mail prompt, which would
otherwise block the console; the browser is opened by this script instead.
"""
import os
import sys
import threading
import time
import urllib.request
import webbrowser

from streamlit.web import cli as stcli

PORT = 8501
URL = f"http://127.0.0.1:{PORT}"


def open_when_ready():
    for _ in range(120):
        try:
            urllib.request.urlopen(URL + "/_stcore/health", timeout=1)
            webbrowser.open(URL)
            return
        except OSError:
            time.sleep(0.5)


def main():
    base = getattr(sys, "_MEIPASS", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    sys.path.insert(0, os.path.join(base, "src"))
    threading.Thread(target=open_when_ready, daemon=True).start()
    sys.argv = ["streamlit", "run", os.path.join(base, "app.py"),
                "--global.developmentMode=false", "--server.headless=true",
                f"--server.port={PORT}", "--server.address=127.0.0.1",
                "--browser.gatherUsageStats=false"]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
