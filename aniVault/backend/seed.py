"""Run once, after `python app.py` has been started at least once
(so anivault.db / tables exist), to load the original default list:

    python seed.py
"""
import json
import sqlite3
from pathlib import Path

from app import init_db, DB_PATH

init_db()

with open(Path(__file__).parent / "seed_data.json") as f:
    entries = json.load(f)

db = sqlite3.connect(DB_PATH)
existing = db.execute("SELECT COUNT(*) FROM anime").fetchone()[0]
if existing:
    print(f"anime table already has {existing} rows — skipping seed. "
          f"Delete {DB_PATH} first if you want a clean reseed.")
else:
    for i, e in enumerate(entries):
        db.execute(
            "INSERT INTO anime (name, status, episode, notes, sort_order) VALUES (?, ?, ?, ?, ?)",
            (e["name"], e["status"], e["episode"], e["notes"], i),
        )
    db.commit()
    print(f"Seeded {len(entries)} anime entries.")
db.close()
