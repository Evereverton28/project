from flask import Flask, request, jsonify
from flask_cors import CORS
from database import get_connection, close_connection

app = Flask(__name__)
CORS(app)  # Allow frontend to make requests

# =========================
# CATEGORIES ENDPOINT
# =========================
@app.route("/categories", methods=["GET"])
def get_categories():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM categories")
    categories = cursor.fetchall()
    cursor.close()
    close_connection(conn)
    return jsonify(categories)

# =========================
# ITEMS ENDPOINTS
# =========================

# Get all items
@app.route("/items", methods=["GET"])
def get_items():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    # Join to get category name
    cursor.execute("""
        SELECT items.item_id, items.item_name, items.quantity, items.unit_price,
               categories.category_name
        FROM items
        LEFT JOIN categories ON items.category_id = categories.category_id
    """)
    items = cursor.fetchall()
    cursor.close()
    close_connection(conn)
    return jsonify(items)

# Add a new item
@app.route("/items", methods=["POST"])
def add_item():
    data = request.get_json()
    item_name = data.get("item_name")
    category_id = data.get("category_id")
    quantity = data.get("quantity", 0)
    unit_price = data.get("unit_price", 0.0)

    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor()
    query = "INSERT INTO items (item_name, category_id, quantity, unit_price) VALUES (%s, %s, %s, %s)"
    cursor.execute(query, (item_name, category_id, quantity, unit_price))
    conn.commit()
    cursor.close()
    close_connection(conn)
    return jsonify({"message": "Item added successfully"}), 201

# =========================
# TRANSACTIONS ENDPOINTS
# =========================

# Get all transactions
@app.route("/transactions", methods=["GET"])
def get_transactions():
    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor(dictionary=True)
    # Join to get item name
    cursor.execute("""
        SELECT transactions.transaction_id, transactions.item_id, transactions.type, transactions.quantity, transactions.date,
               items.item_name
        FROM transactions
        LEFT JOIN items ON transactions.item_id = items.item_id
        ORDER BY transactions.date DESC
    """)
    transactions = cursor.fetchall()
    cursor.close()
    close_connection(conn)
    return jsonify(transactions)

# Add a transaction
@app.route("/transactions", methods=["POST"])
def add_transaction():
    data = request.get_json()
    item_id = data.get("item_id")
    trans_type = data.get("type")  # IN or OUT
    quantity = data.get("quantity", 0)

    if trans_type not in ["IN", "OUT"]:
        return jsonify({"error": "Transaction type must be IN or OUT"}), 400

    conn = get_connection()
    if not conn:
        return jsonify({"error": "DB connection failed"}), 500

    cursor = conn.cursor()

    # Insert transaction
    query = "INSERT INTO transactions (item_id, type, quantity) VALUES (%s, %s, %s)"
    cursor.execute(query, (item_id, trans_type, quantity))

    # Update item quantity
    if trans_type == "IN":
        cursor.execute("UPDATE items SET quantity = quantity + %s WHERE item_id = %s", (quantity, item_id))
    else:
        cursor.execute("UPDATE items SET quantity = quantity - %s WHERE item_id = %s", (quantity, item_id))

    conn.commit()
    cursor.close()
    close_connection(conn)
    return jsonify({"message": "Transaction recorded successfully"}), 201

# =========================
# RUN APP
# =========================
if __name__ == "__main__":
    app.run(debug=True)