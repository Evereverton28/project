"""
AniVault — path resolution

Two different kinds of paths matter here, and they must NOT be confused:

1. RESOURCE paths — read-only files bundled with the app (frontend HTML/CSS/JS,
   favicon, seed_data.json). When frozen by PyInstaller these live inside the
   temporary extraction folder (sys._MEIPASS) and disappear when the app closes.
   That's fine because nothing ever writes to them.

2. DATA paths — the SQLite database and cached cover images. These MUST persist
   across restarts, so they are written next to the .exe itself (or next to
   this file during normal `python app.py` development), never inside the
   PyInstaller temp bundle.
"""

import sys
from pathlib import Path


def is_frozen():
    """True when running inside a PyInstaller-built executable."""
    return getattr(sys, "frozen", False)


def get_resource_dir():
    """
    Root for bundled, read-only resources.
    - Dev mode: the project root (parent of backend/), so `resource_dir / "frontend"`
      resolves the same way it always has.
    - Frozen: PyInstaller's extraction folder, populated by the `datas` entries
      in anivault.spec (which bundle "frontend" at the same relative location).
    """
    if is_frozen():
        return Path(sys._MEIPASS)
    return Path(__file__).resolve().parent.parent


def get_data_dir():
    """
    Root for writable, persistent data (SQLite db + cached images).
    - Dev mode: backend/data/
    - Frozen: <folder containing the .exe>/data/
    Created automatically if missing.
    """
    if is_frozen():
        base = Path(sys.executable).resolve().parent
    else:
        base = Path(__file__).resolve().parent
    data_dir = base / "data"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir