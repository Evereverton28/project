from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
from database import get_connection, close_connection, initialize_db
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
CORS(app)

initialize_db()

# ================================================================
# USERS
# ================================================================

@app.route("/signup", methods=["POST"])
def signup():
    data     = request.get_json()
    username = data.get("username")
    email    = data.get("email")
    password = data.get("password")

    if not username or not email or not password:
        return jsonify({"error": "Missing fields"}), 400

    hashed = generate_password_hash(password)
    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(
            "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
            (username, email, hashed)
        )
        conn.commit()
        return jsonify({"user_id": cursor.lastrowid, "username": username}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Username or email already exists"}), 409
    finally:
        close_connection(conn)


@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username")
    password = data.get("password")

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE username=?", (username,))
    user = cursor.fetchone()
    close_connection(conn)

    if user and check_password_hash(user["password"], password):
        return jsonify({"user_id": user["id"], "username": user["username"]})
    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE id=?", (user_id,))
    if not cursor.fetchone()  :
        close_connection(conn)
        return jsonify({"error": "User not found"}), 404
    cursor.execute("DELETE FROM users WHERE id=?", (user_id,))
    conn.commit()
    close_connection(conn)
    return jsonify({"success": True, "message": f"User {user_id} deleted"})


# ================================================================
# CATEGORIES
# ================================================================

@app.route("/categories", methods=["GET"])
def get_categories():
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM categories ORDER BY category_name")
    cats = [dict(row) for row in cursor.fetchall()]
    close_connection(conn)
    return jsonify(cats)


@app.route("/categories", methods=["POST"])
def add_category():
    data = request.get_json()
    name = data.get("category_name", "").strip()
    if not name:
        return jsonify({"error": "category_name is required"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("INSERT INTO categories (category_name) VALUES (?)", (name,))
        conn.commit()
        return jsonify({"category_id": cursor.lastrowid, "category_name": name}), 201
    except sqlite3.IntegrityError:
        return jsonify({"error": "Category already exists"}), 409
    finally:
        close_connection(conn)


@app.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
    conn.commit()
    close_connection(conn)
    return jsonify({"message": "Category deleted"})


# ================================================================
# ITEMS
# ================================================================

@app.route("/items", methods=["GET", "POST"])
def items():
    conn   = get_connection()
    cursor = conn.cursor()

    if request.method == "GET":
        user_id = request.args.get("user_id")
        if not user_id:
            close_connection(conn)
            return jsonify({"error": "Missing user_id"}), 400
        cursor.execute("SELECT * FROM items WHERE user_id=? ORDER BY item_name", (user_id,))
        result = [dict(row) for row in cursor.fetchall()]
        close_connection(conn)
        return jsonify(result)

    if request.method == "POST":
        data       = request.get_json()
        user_id    = data.get("user_id")
        name       = data.get("item_name", "").strip()
        category   = data.get("category", "").strip()
        quantity   = data.get("quantity", 0)
        unit_price = data.get("unit_price", 0.0)

        if not user_id or not name:
            close_connection(conn)
            return jsonify({"error": "user_id and item_name are required"}), 400

        if category:
            cursor.execute(
                "INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (category,)
            )

        try:
            cursor.execute(
                "INSERT INTO items (user_id, item_name, category, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                (user_id, name, category, quantity, unit_price)
            )
            conn.commit()
            return jsonify({"message": "Item added", "item_id": cursor.lastrowid}), 201
        except Exception as e:
            return jsonify({"error": str(e)}), 500
        finally:
            close_connection(conn)


@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    data       = request.get_json()
    user_id    = data.get("user_id")
    name       = data.get("item_name", "").strip()
    category   = data.get("category", "").strip()
    quantity   = data.get("quantity")
    unit_price = data.get("unit_price")

    if not all([user_id, name, category, quantity is not None, unit_price is not None]):
        return jsonify({"error": "Missing fields"}), 400

    conn   = get_connection()
    cursor = conn.cursor()

    if category:
        cursor.execute("INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (category,))

    cursor.execute(
        "UPDATE items SET item_name=?, category=?, quantity=?, unit_price=? WHERE item_id=? AND user_id=?",
        (name, category, quantity, unit_price, item_id, user_id)
    )
    conn.commit()
    close_connection(conn)
    return jsonify({"message": "Item updated successfully"})


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    conn   = get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM items WHERE item_id=? AND user_id=?", (item_id, user_id))
    conn.commit()
    close_connection(conn)
    return jsonify({"message": "Item deleted"})


# ================================================================
# TRANSACTIONS
# ================================================================

@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    conn   = get_connection()
    cursor = conn.cursor()

    if request.method == "GET":
        user_id     = request.args.get("user_id")
        type_filter = request.args.get("type")
        date_from   = request.args.get("date_from")
        date_to     = request.args.get("date_to")

        if not user_id:
            close_connection(conn)
            return jsonify({"error": "Missing user_id"}), 400

        query  = """
            SELECT t.transaction_id, i.item_name, t.type, t.quantity, t.date
            FROM transactions t
            JOIN items i ON t.item_id = i.item_id
            WHERE t.user_id=?
        """
        params = [user_id]

        if type_filter in ("IN", "OUT"):
            query += " AND t.type=?"
            params.append(type_filter)
        if date_from:
            query += " AND DATE(t.date) >= ?"
            params.append(date_from)
        if date_to:
            query += " AND DATE(t.date) <= ?"
            params.append(date_to)

        query += " ORDER BY t.date DESC"

        cursor.execute(query, params)
        txns = [dict(row) for row in cursor.fetchall()]
        close_connection(conn)
        return jsonify(txns)

    if request.method == "POST":
        data     = request.get_json()
        user_id  = data.get("user_id")
        item_id  = data.get("item_id")
        ttype    = data.get("type")
        quantity = data.get("quantity")

        if not all([user_id, item_id, ttype, quantity is not None]):
            close_connection(conn)
            return jsonify({"error": "Missing fields"}), 400

        if ttype not in ("IN", "OUT"):
            close_connection(conn)
            return jsonify({"error": "type must be IN or OUT"}), 400

        try:
            user_id  = int(user_id)
            item_id  = int(item_id)
            quantity = int(quantity)
        except (ValueError, TypeError):
            close_connection(conn)
            return jsonify({"error": "user_id, item_id and quantity must be integers"}), 400

        if quantity <= 0:
            close_connection(conn)
            return jsonify({"error": "quantity must be a positive integer"}), 400

        try:
            cursor.execute(
                "SELECT quantity FROM items WHERE item_id=? AND user_id=?", (item_id, user_id)
            )
            item = cursor.fetchone()
            if not item:
                close_connection(conn)
                return jsonify({"error": "Item not found"}), 404

            new_qty = item["quantity"] + quantity if ttype == "IN" else item["quantity"] - quantity
            if new_qty < 0:
                close_connection(conn)
                return jsonify({"error": "Insufficient stock"}), 400

            cursor.execute(
                "UPDATE items SET quantity=? WHERE item_id=? AND user_id=?",
                (new_qty, item_id, user_id)
            )
            cursor.execute(
                "INSERT INTO transactions (user_id, item_id, type, quantity) VALUES (?, ?, ?, ?)",
                (user_id, item_id, ttype, quantity)
            )
            conn.commit()
            close_connection(conn)
            return jsonify({"message": "Transaction recorded", "new_quantity": new_qty}), 201

        except Exception as e:
            close_connection(conn)
            return jsonify({"error": str(e)}), 500


# ================================================================
# REPORTS  (single endpoint — all data in one call)
# ================================================================

@app.route("/reports", methods=["GET"])
def reports():
    user_id = request.args.get("user_id")
    if not user_id:
        return jsonify({"error": "Missing user_id"}), 400

    low_threshold = int(request.args.get("low_threshold", 5))
    date_from     = request.args.get("date_from")   # YYYY-MM-DD, optional
    date_to       = request.args.get("date_to")     # YYYY-MM-DD, optional

    conn   = get_connection()
    cursor = conn.cursor()

    # total items & stock value — always full scope
    cursor.execute("SELECT COUNT(*) AS total FROM items WHERE user_id=?", (user_id,))
    total_items = cursor.fetchone()["total"]

    cursor.execute(
        "SELECT SUM(quantity * unit_price) AS total_value FROM items WHERE user_id=?", (user_id,)
    )
    total_value = cursor.fetchone()["total_value"] or 0

    # transaction count — respects date filter
    txn_q = "SELECT COUNT(*) AS n FROM transactions WHERE user_id=?"
    txn_p = [user_id]
    if date_from:
        txn_q += " AND DATE(date) >= ?"; txn_p.append(date_from)
    if date_to:
        txn_q += " AND DATE(date) <= ?"; txn_p.append(date_to)
    cursor.execute(txn_q, txn_p)
    total_transactions = cursor.fetchone()["n"]

    # low stock
    cursor.execute(
        "SELECT item_name, quantity FROM items WHERE user_id=? AND quantity < ? ORDER BY quantity ASC",
        (user_id, low_threshold)
    )
    low_stock = [dict(row) for row in cursor.fetchall()]

    # stock value by category (current snapshot)
    cursor.execute(
        """
        SELECT category,
               SUM(quantity * unit_price) AS value,
               SUM(quantity)              AS total_qty
        FROM items
        WHERE user_id=?
        GROUP BY category
        ORDER BY value DESC
        """,
        (user_id,)
    )
    by_category = [dict(row) for row in cursor.fetchall()]

    # top 5 most-moved items — date-filtered
    top_q = """
        SELECT i.item_name,
               SUM(CASE WHEN t.type='IN'  THEN t.quantity ELSE 0 END) AS total_in,
               SUM(CASE WHEN t.type='OUT' THEN t.quantity ELSE 0 END) AS total_out,
               COUNT(t.transaction_id)                                  AS txn_count
        FROM transactions t
        JOIN items i ON t.item_id = i.item_id
        WHERE t.user_id=?
    """
    top_p = [user_id]
    if date_from:
        top_q += " AND DATE(t.date) >= ?"; top_p.append(date_from)
    if date_to:
        top_q += " AND DATE(t.date) <= ?"; top_p.append(date_to)
    top_q += " GROUP BY t.item_id ORDER BY (total_in + total_out) DESC LIMIT 5"
    cursor.execute(top_q, top_p)
    top_items = [dict(row) for row in cursor.fetchall()]

    # turnover rate = total_out / current_stock  (top 10 by rate)
    cursor.execute(
        """
        SELECT i.item_name,
               i.quantity AS current_stock,
               SUM(CASE WHEN t.type='OUT' THEN t.quantity ELSE 0 END) AS total_out,
               CASE
                 WHEN i.quantity > 0
                 THEN ROUND(
                   CAST(SUM(CASE WHEN t.type='OUT' THEN t.quantity ELSE 0 END) AS REAL)
                   / i.quantity, 2)
                 ELSE NULL
               END AS turnover_rate
        FROM items i
        LEFT JOIN transactions t ON i.item_id = t.item_id AND t.user_id = ?
        WHERE i.user_id = ?
        GROUP BY i.item_id
        ORDER BY turnover_rate DESC NULLS LAST
        LIMIT 10
        """,
        (user_id, user_id)
    )
    turnover = [dict(row) for row in cursor.fetchall()]

    close_connection(conn)

    return jsonify({
        "total_items":        total_items,
        "total_value":        round(total_value, 2),
        "total_transactions": total_transactions,
        "low_stock":          low_stock,
        "by_category":        by_category,
        "top_items":          top_items,
        "turnover":           turnover,
    })


if __name__ == "__main__":
    app.run(debug=True)
