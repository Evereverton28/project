from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3

app = Flask(__name__)
CORS(app)  # Allow frontend requests

# ---------------- Database setup ----------------
def get_db():
    conn = sqlite3.connect("inventory.db")
    conn.row_factory = sqlite3.Row  # So we get dict-like rows
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category TEXT NOT NULL,
        quantity INTEGER DEFAULT 0,
        unit_price REAL DEFAULT 0.0
    )
    """)
    conn.commit()
    conn.close()

init_db()  # Ensure table exists

# ---------------- CRUD ROUTES ----------------

# READ: Get all items
@app.route("/items", methods=["GET"])
def get_items():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM items")
    items = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(items)

# CREATE: Add new item
@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()
    name = data.get("item_name")
    category = data.get("category")
    quantity = data.get("quantity", 0)
    unit_price = data.get("unit_price", 0.0)

    if not name or not category or quantity < 1 or unit_price < 0:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO items (item_name, category, quantity, unit_price) VALUES (?, ?, ?, ?)",
        (name, category, quantity, unit_price)
    )
    conn.commit()
    conn.close()
    return jsonify({"message": "Item added successfully"}), 201

# UPDATE: Modify an existing item
@app.route("/items/<int:item_id>", methods=["PATCH"])
def update_item(item_id):
    data = request.get_json()
    name = data.get("item_name")
    category = data.get("category")
    quantity = data.get("quantity")
    unit_price = data.get("unit_price")

    if not name or not category or quantity < 0 or unit_price < 0:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE items
        SET item_name=?, category=?, quantity=?, unit_price=?
        WHERE item_id=?
    """, (name, category, quantity, unit_price, item_id))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item updated successfully"})

# DELETE: Remove an item
@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE item_id=?", (item_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Item deleted successfully"})

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)