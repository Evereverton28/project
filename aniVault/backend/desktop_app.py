"""
AniVault — Desktop entry point

Runs the exact same Flask app as `python app.py`, but instead of telling you
to open a browser, it opens a native window (via pywebview) pointing at the
local server. This is the file PyInstaller packages into AniVault.exe.

Dev usage:   python desktop_app.py
Packaged:    AniVault.exe  (see anivault.spec)
"""

import socket
import threading
import time

import webview

import app as flask_app_module  # backend/app.py

HOST = "127.0.0.1"
PORT = 5000


def _port_is_open(host, port, timeout=0.3):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)
        return sock.connect_ex((host, port)) == 0


def _run_flask():
    # debug=False and use_reloader=False are required here — Flask's reloader
    # spawns a second process, which breaks both threading and PyInstaller's
    # single-exe bundling.
    flask_app_module.app.run(host=HOST, port=PORT, debug=False, use_reloader=False)


def main():
    flask_app_module.init_db()

    server_thread = threading.Thread(target=_run_flask, daemon=True)
    server_thread.start()

    # Wait for Flask to actually be listening before opening the window,
    # instead of a blind fixed delay.
    for _ in range(50):  # up to ~5 seconds
        if _port_is_open(HOST, PORT):
            break
        time.sleep(0.1)

    webview.create_window(
        "AniVault",
        f"http://{HOST}:{PORT}",
        width=1440,
        height=900,
        min_size=(1000, 650),
    )
    webview.start()


if __name__ == "__main__":
    main()