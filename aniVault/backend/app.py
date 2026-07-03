"""
AniVault backend — Flask + SQLite

Replaces localStorage persistence with a real REST API backed by SQLite.
Run with:  python app.py
Serves the API on http://localhost:5000/api/*
and (optionally) the frontend static files on http://localhost:5000/
"""

import csv
import io
import json
import sqlite3
from pathlib import Path

from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "anivault.db"
FRONTEND_DIR = BASE_DIR.parent / "frontend"

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


def init_db():
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

    # seed defaults for meta if empty
    cur = db.execute("SELECT COUNT(*) FROM meta")
    if cur.fetchone()[0] == 0:
        db.executemany(
            "INSERT INTO meta (key, value) VALUES (?, ?)",
            [("view", "grid"), ("sort", "default"), ("filter", "all")],
        )
        db.commit()

    db.close()


def row_to_anime(row):
    return {
        "id": row["id"],
        "name": row["name"],
        "status": row["status"],
        "episode": row["episode"] or "",
        "notes": row["notes"] or "",
        "coverUrl": row["cover_url"],
        "coverFetched": bool(row["cover_fetched"]),
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
        """INSERT INTO anime (name, status, episode, notes, cover_url, cover_fetched, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (
            name,
            data.get("status", "planned"),
            data.get("episode", ""),
            data.get("notes", ""),
            data.get("coverUrl"),
            int(bool(data.get("coverFetched", False))),
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
        "sort_order": data.get("order", row["sort_order"]),
    }
    db.execute(
        """UPDATE anime SET name=?, status=?, episode=?, notes=?, cover_url=?,
           cover_fetched=?, sort_order=? WHERE id=?""",
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
        """INSERT INTO anime (id, name, status, episode, notes, cover_url, cover_fetched, sort_order)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            anime_id,
            data["name"],
            data.get("status", "planned"),
            data.get("episode", ""),
            data.get("notes", ""),
            data.get("coverUrl"),
            int(bool(data.get("coverFetched", False))),
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
#  Cover cache (avoids re-hitting Jikan for names already looked up)
# ────────────────────────────────────────────
@app.get("/api/cover-cache/<path:name>")
def get_cached_cover(name):
    db = get_db()
    row = db.execute("SELECT url FROM cover_cache WHERE name = ?", (name,)).fetchone()
    if row is None:
        return jsonify({"cached": False})
    return jsonify({"cached": True, "url": row["url"]})


@app.post("/api/cover-cache")
def set_cached_cover():
    data = request.get_json(force=True)
    db = get_db()
    db.execute(
        "INSERT INTO cover_cache (name, url) VALUES (?, ?) "
        "ON CONFLICT(name) DO UPDATE SET url=excluded.url",
        (data["name"], data.get("url", "")),
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
            """INSERT INTO anime (name, status, episode, notes, cover_url, cover_fetched, sort_order)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (
                e.get("name", "").strip(),
                e.get("status", "planned"),
                e.get("episode", ""),
                e.get("notes", ""),
                e.get("coverUrl"),
                int(bool(e.get("coverFetched", False))),
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
