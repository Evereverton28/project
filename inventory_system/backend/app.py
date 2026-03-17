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

# Initialize database and create tables if they don't exist
def init_db():
    conn = get_db()
    cursor = conn.cursor()
    
    # Items table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_name TEXT NOT NULL,
        category_id INTEGER,
        quantity INTEGER DEFAULT 0,
        unit_price REAL DEFAULT 0.0,
        FOREIGN KEY (category_id) REFERENCES categories(category_id)
    )
    """)

    # Categories table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL
    )
    """)
    
    # Transactions table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER,
        type TEXT CHECK(type IN ('IN','OUT')),
        quantity INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (item_id) REFERENCES items(item_id)
    )
    """)

    conn.commit()
    conn.close()

init_db()

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

# ---------------- Transactions ROUTES ----------------
# READ: Get all transactions
@app.route("/transactions", methods=["GET"])
def get_transactions():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT t.transaction_id, t.item_id, t.type, t.quantity, t.date, i.item_name
        FROM transactions t
        LEFT JOIN items i ON t.item_id = i.item_id
        ORDER BY t.date DESC
    """)
    transactions = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(transactions)

# CREATE: Add a transaction (stock in/out)
@app.route("/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json()
    item_id = data.get("item_id")
    trans_type = data.get("type")
    quantity = data.get("quantity")

    if trans_type not in ["IN", "OUT"] or quantity < 1:
        return jsonify({"error": "Invalid input"}), 400

    conn = get_db()
    cursor = conn.cursor()

    # Get current stock
    cursor.execute("SELECT quantity FROM items WHERE item_id=?", (item_id,))
    item = cursor.fetchone()

    if not item:
        conn.close()
        return jsonify({"error": "Item not found"}), 404

    current_qty = item[0]

    # Prevent negative stock
    if trans_type == "OUT" and quantity > current_qty:
        conn.close()
        return jsonify({"error": "Not enough stock"}), 400

    # Update stock
    if trans_type == "IN":
        new_qty = current_qty + quantity
    else:
        new_qty = current_qty - quantity

    cursor.execute("UPDATE items SET quantity=? WHERE item_id=?", (new_qty, item_id))

    # Save transaction
    cursor.execute(
        "INSERT INTO transactions (item_id, type, quantity) VALUES (?, ?, ?)",
        (item_id, trans_type, quantity)
    )

    conn.commit()
    conn.close()

    return jsonify({"message": "Transaction recorded"}), 201

# ---------------- Reports ROUTES ----------------
@app.route("/reports", methods=["GET"])
def get_reports():
    conn = get_db()
    cursor = conn.cursor()

    # Total items count
    cursor.execute("SELECT COUNT(*) FROM items")
    total_items = cursor.fetchone()[0]

    # Total stock value
    cursor.execute("SELECT SUM(quantity * unit_price) FROM items")
    total_value = cursor.fetchone()[0] or 0

    # Low stock items (less than 5)
    cursor.execute("SELECT item_name, quantity FROM items WHERE quantity < 5")
    low_stock = cursor.fetchall()

    # Total transactions
    cursor.execute("SELECT COUNT(*) FROM transactions")
    total_transactions = cursor.fetchone()[0]

    conn.close()

    return jsonify({
        "total_items": total_items,
        "total_value": total_value,
        "low_stock": [dict(row) for row in low_stock],
        "total_transactions": total_transactions
    })

# ---------------- Categories ROUTES ----------------
# READ: Get all categories
@app.route("/categories", methods=["GET"])
def get_categories():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    categories = [dict(row) for row in cursor.fetchall()]
    conn.close()
    return jsonify(categories)

# CREATE: Add new category
@app.route("/categories", methods=["POST"])
def add_category():
    data = request.get_json()
    name = data.get("category_name")
    if not name:
        return jsonify({"error": "Category name required"}), 400

    conn = get_db()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (name,))
        conn.commit()
    except:
        conn.close()
        return jsonify({"error": "Category already exists"}), 400

    conn.close()
    return jsonify({"message": "Category added"}), 201

# ---------------- Run App ----------------
if __name__ == "__main__":
    app.run(debug=True)