# app.py
from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from database import get_connection, close_connection, initialize_db
from werkzeug.security import generate_password_hash, check_password_hash
import random, string

app = Flask(__name__)
CORS(app)

# Initialize DB (tables + structure)
initialize_db()

# ---------------- USERS ----------------
@app.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed = generate_password_hash(password)
    conn = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        user_id = cursor.lastrowid
        # ✅ Immediately log in the user
        return jsonify({"user_id": user_id, "username": username}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 409
    finally:
        close_connection(conn)

@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    close_connection(conn)

    if user and check_password_hash(user["password"], password):
        return jsonify({"user_id": user["id"], "username": user["username"]})
    return jsonify({"error": "Invalid credentials"}), 401

# ---------------- DELETE USER ----------------
@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    user = cursor.fetchone()
    if not user:
        close_connection(conn)
        return {"error": "User not found"}, 404
    
    # Delete the user
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    close_connection(conn)
    
    return {"success": True, "message": f"User {user_id} deleted"}

# ---------------- ITEMS ----------------
@app.route("/items", methods=["GET", "POST"])
def items():
    user_id = request.args.get("user_id") or request.json.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    if request.method == "GET":
        cursor.execute("SELECT * FROM items WHERE user_id=?", (user_id,))
        items = [dict(row) for row in cursor.fetchall()]
        close_connection(conn)
        return jsonify(items)

    if request.method == "POST":
        data = request.get_json()
        name = data.get("item_name")
        category = data.get("category")
        quantity = data.get("quantity", 0)
        unit_price = data.get("unit_price", 0.0)
        try:
            cursor.execute(
                "INSERT INTO items (user_id, item_name, category, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                (user_id, name, category, quantity, unit_price)
            )
            conn.commit()
            return jsonify({"message": "Item added"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            close_connection(conn)

@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE item_id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    close_connection(conn)
    return jsonify({"message": "Item deleted"})

# ---------------- TRANSACTIONS ----------------
@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    if request.method == "GET":
        user_id = request.args.get("user_id")
        if not user_id:
            return jsonify({"error": "Missing user_id"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT t.transaction_id, i.item_name, t.type, t.quantity, t.date
            FROM transactions t
            JOIN items i ON t.item_id = i.item_id
            WHERE t.user_id=?
            """,
            (user_id,)
        )
        txns = [dict(row) for row in cursor.fetchall()]
        close_connection(conn)
        return jsonify(txns)

    if request.method == "POST":
        data = request.get_json()
        user_id = data.get("user_id")
        item_id = data.get("item_id")
        ttype = data.get("type")
        quantity = data.get("quantity")

        if not all([user_id, item_id, ttype, quantity]):
            return jsonify({"error": "Missing fields"}), 400

        conn = get_connection()
        cursor = conn.cursor()
        try:
            # Update item quantity
            cursor.execute("SELECT quantity FROM items WHERE item_id=? AND user_id=?", (item_id, user_id))
            item = cursor.fetchone()
            if not item:
                return jsonify({"error": "Item not found"}), 404

            new_qty = item["quantity"] + quantity if ttype == "IN" else item["quantity"] - quantity
            if new_qty < 0:
                return jsonify({"error": "Insufficient stock"}), 400

            cursor.execute("UPDATE items SET quantity=? WHERE item_id=? AND user_id=?", (new_qty, item_id, user_id))
            cursor.execute(
                "INSERT INTO transactions (user_id, item_id, type, quantity) VALUES (?, ?, ?, ?)",
                (user_id, item_id, ttype, quantity)
            )
            conn.commit()
            return jsonify({"message": "Transaction recorded"}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            close_connection(conn)

# ---------------- REPORTS ----------------
@app.route("/reports", methods=["GET"])
def reports():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn = get_connection()
    cursor = conn.cursor()

    # Total items
    cursor.execute("SELECT COUNT(*) AS total FROM items WHERE user_id=?", (user_id,))
    total_items = cursor.fetchone()["total"]

    # Total stock value
    cursor.execute("SELECT SUM(quantity * unit_price) AS total_value FROM items WHERE user_id=?", (user_id,))
    total_value = cursor.fetchone()["total_value"] or 0

    # Total transactions
    cursor.execute("SELECT COUNT(*) AS total_txn FROM transactions WHERE user_id=?", (user_id,))
    total_transactions = cursor.fetchone()["total_txn"]

    # Low stock
    cursor.execute("SELECT item_name, quantity FROM items WHERE user_id=? AND quantity < 5", (user_id,))
    low_stock = [dict(row) for row in cursor.fetchall()]

    close_connection(conn)

    return jsonify({
        "total_items": total_items,
        "total_value": total_value,
        "total_transactions": total_transactions,
        "low_stock": low_stock
    })

if __name__ == "__main__":
    app.run(debug=True)