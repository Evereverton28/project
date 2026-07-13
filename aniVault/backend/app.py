"""
AniVault backend — Flask + SQLite

Runs identically in two modes:
  1. Dev mode:      python app.py            -> served at http://localhost:5000
  2. Desktop mode:  launched by desktop_app.py inside a pywebview window,
                    or from the frozen AniVault.exe built via anivault.spec.

See paths.py for how file locations differ between the two.
"""

import csv
import io
import json
import sqlite3
import sys
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS

import paths
import image_cache

RESOURCE_DIR = paths.get_resource_dir()
DATA_DIR     = paths.get_data_dir()

DB_PATH      = DATA_DIR / "anivault.db"
FRONTEND_DIR = RESOURCE_DIR / "frontend"
IMAGES_DIR   = image_cache.IMAGES_DIR


def get_seed_data_path():
    """
    seed_data.json is a bundled read-only resource, not user data.
    - Dev mode: backend/seed_data.json (RESOURCE_DIR is the project root)
    - Frozen: bundled at the root of the PyInstaller archive (see anivault.spec)
    """
    if paths.is_frozen():
        return RESOURCE_DIR / "seed_data.json"
    return RESOURCE_DIR / "backend" / "seed_data.json"


app = Flask(__name__, static_folder=str(FRONTEND_DIR), static_url_path="")
CORS(app)  # allow the frontend to be opened from file:// or a different port during dev


# ────────────────────────────────────────────
#  DB helpers
# ────────────────────────────────────────────
def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


@app.teardown_appcontext
def close_db(exception=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def _migrate_legacy_db_location():
    """
    Before this refactor, anivault.db lived directly in backend/ (or next to
    the exe). It now lives in a dedicated data/ subfolder so it's clearly
    separated from bundled resources. Move it automatically, once, so
    existing installs don't appear to lose their data.
    """
    if DB_PATH.exists():
        return  # already in the new location, nothing to do

    if paths.is_frozen():
        legacy_path = Path(sys.executable).resolve().parent / "anivault.db"
    else:
        legacy_path = Path(__file__).resolve().parent / "anivault.db"

    if legacy_path.exists():
        legacy_path.rename(DB_PATH)
        print(f"[migrate] Moved existing database: {legacy_path} -> {DB_PATH}")


def init_db():
    _migrate_legacy_db_location()
    db = sqlite3.connect(DB_PATH)
    db.executescript(
        """
        CREATE TABLE IF NOT EXISTS anime (
            id            INTEGER PRIMARY KEY AUTOINCREMENT,
            name          TEXT NOT NULL,
            status        TEXT NOT NULL DEFAULT 'planned',
            episode       TEXT DEFAULT '',
            notes         TEXT DEFAULT '',
            cover_url     TEXT,
            cover_fetched INTEGER DEFAULT 0,
            mal_id        INTEGER,
            sort_order    INTEGER DEFAULT 0
        );

        CREATE TABLE IF NOT EXISTS meta (
            key   TEXT PRIMARY KEY,
            value TEXT
        );

        CREATE TABLE IF NOT EXISTS cover_cache (
            name TEXT PRIMARY KEY,
            url  TEXT
        );
        """
    )
    db.commit()

    # Migrate DBs created before mal_id existed
    existing_cols = {row[1] for row in db.execute("PRAGMA table_info(anime)")}
    if "mal_id" not in existing_cols:
        db.execute("ALTER TABLE anime ADD COLUMN mal_id INTEGER")
        db.commit()

    # One-time repair: an earlier bug marked cover_fetched=1 even when a
    # Jikan request merely failed transiently (e.g. a 504), permanently
    # giving up on those entries. Anything left with cover_fetched=1 but
    # no cover_url AND no mal_id never actually succeeded — reset it so
    # it gets retried instead of staying stuck forever.
    reset = db.execute(
        "UPDATE anime SET cover_fetched=0 "
        "WHERE cover_fetched=1 AND cover_url IS NULL AND mal_id IS NULL"
    )
    if reset.rowcount:
        db.commit()
        print(f"[init_db] Reset {reset.rowcount} entr(y/ies) stuck from a prior transient cover-fetch failure")

    # seed defaults for meta if empty
    cur = db.execute("SELECT COUNT(*) FROM meta")
    if cur.fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [("view", "grid"), ("sort", "default"), ("filter", "all")],
        )
        db.commit()

    # First-run auto-seed: if the anime table is empty and a bundled
    # seed_data.json exists, load it. This is what makes the packaged
    # .exe work standalone — there's no separate seed.py to run by hand.
    anime_count = db.execute("SELECT COUNT(*) FROM anime").fetchone()[0]
    seed_path = get_seed_data_path()
    if anime_count == 0 and seed_path.exists():
        try:
            with open(seed_path, encoding="utf-8") as f:
                entries = json.load(f)
            for i, e in enumerate(entries):
                db.execute(
                    """INSERT INTO anime (name, status, episode, notes, sort_order)
                       VALUES (?, ?, ?, ?, ?)""",
                    (e.get("name", "").strip(), e.get("status", "planned"),
                     e.get("episode", ""), e.get("notes", ""), i),
                )
            db.commit()
            print(f"[init_db] Auto-seeded {len(entries)} entries from {seed_path}")
        except (OSError, json.JSONDecodeError) as err:
            print(f"[init_db] Auto-seed skipped — could not read {seed_path}: {err}")

    db.close()
    image_cache.ensure_images_dir()


def row_to_anime(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "episode": row["episode"] or "",
        "notes": row["notes"] or "",
        "coverUrl": row["cover_url"],
        "coverFetched": bool(row["cover_fetched"]),
        "malId": row["mal_id"],
        "order": row["sort_order"],
    }


# ────────────────────────────────────────────
#  Anime CRUD
# ────────────────────────────────────────────
@app.get("/api/anime")
def list_anime():
    db = get_db()
    rows = db.execute("SELECT * FROM anime ORDER BY sort_order ASC").fetchall()
    return jsonify([row_to_anime(r) for r in rows])


@app.post("/api/anime")
def create_anime():
    data = request.get_json(force=True)
    name = (data.get("name") or "").strip()
    if not name:
        return jsonify({"error": "name is required"}), 400

    db = get_db()
    max_order = db.execute("SELECT MIN(sort_order) FROM anime").fetchone()[0]
    new_order = (max_order - 1) if max_order is not None else 0

    cur = db.execute(
        """INSERT INTO anime (name, status, episode, notes, cover_url, cover_fetched, mal_id, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            data.get("status", "planned"),
            data.get("episode", ""),
            data.get("notes", ""),
            data.get("coverUrl"),
            int(bool(data.get("coverFetched", False))),
            data.get("malId"),
            new_order,
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (cur.lastrowid,)).fetchone()
    return jsonify(row_to_anime(row)), 201


@app.put("/api/anime/<int:anime_id>")
def update_anime(anime_id):
    data = request.get_json(force=True)
    db = get_db()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404

    fields = {
        "name": data.get("name", row["name"]),
        "status": data.get("status", row["status"]),
        "episode": data.get("episode", row["episode"]),
        "notes": data.get("notes", row["notes"]),
        "cover_url": data.get("coverUrl", row["cover_url"]),
        "cover_fetched": int(bool(data.get("coverFetched", row["cover_fetched"]))),
        "mal_id": data.get("malId", row["mal_id"]),
        "sort_order": data.get("order", row["sort_order"]),
    }
    db.execute(
        """UPDATE anime SET name=?, status=?, episode=?, notes=?, cover_url=?,
           cover_fetched=?, mal_id=?, sort_order=? WHERE id=?""",
        (*fields.values(), anime_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    return jsonify(row_to_anime(row))


@app.patch("/api/anime/<int:anime_id>")
def patch_anime(anime_id):
    # partial update — used for cover-fetch results, status-only changes, etc.
    return update_anime(anime_id)


@app.delete("/api/anime/<int:anime_id>")
def delete_anime(anime_id):
    db = get_db()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    db.execute("DELETE FROM anime WHERE id = ?", (anime_id,))
    db.commit()
    return jsonify(row_to_anime(row))  # return the deleted row so the client can offer Undo


@app.post("/api/anime/<int:anime_id>/restore")
def restore_anime(anime_id):
    # Undo support: re-insert a previously deleted entry with the SAME id.
    data = request.get_json(force=True)
    db = get_db()
    db.execute(
        """INSERT INTO anime (id, name, status, episode, notes, cover_url, cover_fetched, mal_id, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            anime_id,
            data["name"],
            data.get("status", "planned"),
            data.get("episode", ""),
            data.get("notes", ""),
            data.get("coverUrl"),
            int(bool(data.get("coverFetched", False))),
            data.get("malId"),
            data.get("order", 0),
        ),
    )
    db.commit()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    return jsonify(row_to_anime(row)), 201


@app.post("/api/anime/reorder")
def reorder_anime():
    """Body: [{"id": 1, "order": 0}, {"id": 5, "order": 1}, ...]"""
    data = request.get_json(force=True)
    db = get_db()
    for item in data:
        db.execute("UPDATE anime SET sort_order=? WHERE id=?", (item["order"], item["id"]))
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/anime/<int:anime_id>/cover")
def fetch_cover(anime_id):
    """
    Resolve + download this anime's cover art and cache it locally.

    - If we already have a cached image for this row's mal_id, no network
      call is made at all.
    - Otherwise resolves via Jikan, downloads once to data/images/<mal_id>.jpg,
      and returns the local path from then on.
    - cover_fetched is only set to 1 when the outcome is PERMANENT (found +
      cached, or Jikan confirmed no match exists). A transient failure
      (Jikan down, timeout, 5xx) leaves cover_fetched at 0 so the frontend
      retries it on the next sync instead of giving up on it forever.
    """
    db = get_db()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404

    mal_id, local_url, permanent = image_cache.get_or_fetch_cover(row["name"], row["mal_id"])

    db.execute(
        "UPDATE anime SET cover_url=?, cover_fetched=?, mal_id=? WHERE id=?",
        (local_url, int(permanent), mal_id, anime_id),
    )
    db.commit()
    row = db.execute("SELECT * FROM anime WHERE id = ?", (anime_id,)).fetchone()
    return jsonify(row_to_anime(row))


@app.get("/static/images/<path:filename>")
def serve_cached_image(filename):
    return send_from_directory(IMAGES_DIR, filename)


# ────────────────────────────────────────────
#  Meta (view / sort / filter prefs)
# ────────────────────────────────────────────
@app.get("/api/meta")
def get_meta():
    db = get_db()
    rows = db.execute("SELECT key, value FROM meta").fetchall()
    return jsonify({r["key"]: r["value"] for r in rows})


@app.post("/api/meta")
def set_meta():
    data = request.get_json(force=True)
    db = get_db()
    for k, v in data.items():
        db.execute(
            "INSERT INTO meta (key, value) VALUES (?, ?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (k, str(v)),
        )
    db.commit()
    return jsonify({"ok": True})


# ────────────────────────────────────────────
#  Import / Export
# ────────────────────────────────────────────
@app.get("/api/export/json")
def export_json():
    db = get_db()
    rows = db.execute("SELECT * FROM anime ORDER BY sort_order ASC").fetchall()
    payload = [row_to_anime(r) for r in rows]
    return app.response_class(
        json.dumps(payload, indent=2),
        mimetype="application/json",
        headers={"Content-Disposition": "attachment; filename=anivault-export.json"},
    )


@app.get("/api/export/csv")
def export_csv():
    db = get_db()
    rows = db.execute("SELECT * FROM anime ORDER BY sort_order ASC").fetchall()
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["name", "status", "episode", "notes"])
    for r in rows:
        writer.writerow([r["name"], r["status"], r["episode"] or "", r["notes"] or ""])
    return app.response_class(
        buf.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment; filename=anivault-export.csv"},
    )


@app.post("/api/import")
def import_data():
    """Body: {"format": "json"|"csv", "content": "<raw file text>"}
    Replaces the whole anime table with the imported entries."""
    data = request.get_json(force=True)
    fmt = data.get("format", "json")
    content = data.get("content", "")

    if fmt == "csv":
        reader = csv.DictReader(io.StringIO(content))
        entries = [
            {
                "name": row.get("name", "").strip(),
                "status": row.get("status", "planned"),
                "episode": row.get("episode", ""),
                "notes": row.get("notes", ""),
            }
            for row in reader
            if row.get("name", "").strip()
        ]
    else:
        raw = json.loads(content)
        entries = raw if isinstance(raw, list) else raw.get("anime", [])

    db = get_db()
    db.execute("DELETE FROM anime")
    for i, e in enumerate(entries):
        db.execute(
            """INSERT INTO anime (name, status, episode, notes, cover_url, cover_fetched, mal_id, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                e.get("name", "").strip(),
                e.get("status", "planned"),
                e.get("episode", ""),
                e.get("notes", ""),
                e.get("coverUrl"),
                int(bool(e.get("coverFetched", False))),
                e.get("malId"),
                i,
            ),
        )
    db.commit()
    rows = db.execute("SELECT * FROM anime ORDER BY sort_order ASC").fetchall()
    return jsonify([row_to_anime(r) for r in rows])


# ────────────────────────────────────────────
#  Serve frontend (optional convenience — you can also just open index.html
#  directly and point storage.js at http://localhost:5000)
# ────────────────────────────────────────────
@app.get("/")
def serve_index():
    return send_from_directory(FRONTEND_DIR, "index.html")


@app.get("/<path:path>")
def serve_static(path):
    return send_from_directory(FRONTEND_DIR, path)


if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)