import secrets
from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash

from database import db, initialize_db

app = Flask(__name__)
CORS(app)

# FIX #10: initialize_db called exactly once, here only.
initialize_db()


# ================================================================
# AUTH HELPER  (FIX #6, #7)
# Every protected endpoint calls require_auth() first.
# The frontend sends the token in the Authorization header:
#   Authorization: Bearer <token>
# ================================================================

def require_auth():
    """
    Validate the Bearer token sent by the client.
    Returns (user_id, None) on success or (None, error_response) on failure.
    """
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None, (jsonify({"error": "Missing or invalid Authorization header"}), 401)

    token = auth_header[7:]
    with db() as conn:
        row = conn.execute(
            "SELECT user_id FROM sessions WHERE token=?", (token,)
        ).fetchone()

    if not row:
        return None, (jsonify({"error": "Invalid or expired token"}), 401)

    return row["user_id"], None


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
    try:
        with db() as conn:
            cursor = conn.execute(
                "INSERT INTO users (username, email, password) VALUES (?, ?, ?)",
                (username, email, hashed)
            )
            conn.commit()
            user_id = cursor.lastrowid

        token = _create_session(user_id)
        return jsonify({"user_id": user_id, "username": username, "token": token}), 201

    except Exception:
        return jsonify({"error": "Username or email already exists"}), 409


@app.route("/login", methods=["POST"])
def login():
    data     = request.get_json()
    username = data.get("username")
    password = data.get("password")

    with db() as conn:
        user = conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()

    if user and check_password_hash(user["password"], password):
        token = _create_session(user["id"])
        return jsonify({"user_id": user["id"], "username": user["username"], "token": token})

    return jsonify({"error": "Invalid credentials"}), 401


@app.route("/logout", methods=["POST"])
def logout():
    auth_user_id, err = require_auth()
    if err:
        return err

    auth_header = request.headers.get("Authorization", "")
    token = auth_header[7:]
    with db() as conn:
        conn.execute("DELETE FROM sessions WHERE token=?", (token,))
        conn.commit()
    return jsonify({"message": "Logged out"})


# FIX #7: delete_user now requires auth and only allows self-deletion.
@app.route("/users/<int:user_id>", methods=["DELETE"])
def delete_user(user_id):
    auth_user_id, err = require_auth()
    if err:
        return err

    if auth_user_id != user_id:
        return jsonify({"error": "Forbidden"}), 403

    with db() as conn:
        row = conn.execute("SELECT id FROM users WHERE id=?", (user_id,)).fetchone()
        if not row:
            return jsonify({"error": "User not found"}), 404
        conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        conn.execute("DELETE FROM sessions WHERE user_id=?", (user_id,))
        conn.commit()

    return jsonify({"success": True, "message": f"User {user_id} deleted"})


def _create_session(user_id):
    token = secrets.token_hex(32)
    with db() as conn:
        conn.execute(
            "INSERT INTO sessions (token, user_id) VALUES (?, ?)", (token, user_id)
        )
        conn.commit()
    return token


# ================================================================
# CATEGORIES
# ================================================================

@app.route("/categories", methods=["GET"])
def get_categories():
    _, err = require_auth()
    if err:
        return err

    with db() as conn:
        cats = [dict(r) for r in conn.execute(
            "SELECT * FROM categories ORDER BY category_name"
        ).fetchall()]
    return jsonify(cats)


@app.route("/categories", methods=["POST"])
def add_category():
    _, err = require_auth()
    if err:
        return err

    data = request.get_json()
    name = data.get("category_name", "").strip()
    if not name:
        return jsonify({"error": "category_name is required"}), 400

    try:
        with db() as conn:
            cursor = conn.execute(
                "INSERT INTO categories (category_name) VALUES (?)", (name,)
            )
            conn.commit()
            return jsonify({"category_id": cursor.lastrowid, "category_name": name}), 201
    except Exception:
        return jsonify({"error": "Category already exists"}), 409


# FIX #2: delete_category now returns 404 when category doesn't exist.
@app.route("/categories/<int:category_id>", methods=["DELETE"])
def delete_category(category_id):
    _, err = require_auth()
    if err:
        return err

    with db() as conn:
        row = conn.execute(
            "SELECT category_id FROM categories WHERE category_id=?", (category_id,)
        ).fetchone()
        if not row:
            return jsonify({"error": "Category not found"}), 404
        conn.execute("DELETE FROM categories WHERE category_id=?", (category_id,))
        conn.commit()

    return jsonify({"message": "Category deleted"})


# ================================================================
# ITEMS
# ================================================================

@app.route("/items", methods=["GET", "POST"])
def items():
    auth_user_id, err = require_auth()
    if err:
        return err

    if request.method == "GET":
        # FIX #6: ignore the query-param user_id — use the authenticated user's id.
        with db() as conn:
            result = [dict(r) for r in conn.execute(
                "SELECT * FROM items WHERE user_id=? ORDER BY item_name", (auth_user_id,)
            ).fetchall()]
        return jsonify(result)

    # POST
    data       = request.get_json()
    name       = data.get("item_name", "").strip()
    category   = data.get("category", "").strip()
    quantity   = data.get("quantity", 0)
    unit_price = data.get("unit_price", 0.0)

    if not name:
        return jsonify({"error": "item_name is required"}), 400

    try:
        with db() as conn:
            if category:
                conn.execute(
                    "INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (category,)
                )
            cursor = conn.execute(
                "INSERT INTO items (user_id, item_name, category, quantity, unit_price) VALUES (?, ?, ?, ?, ?)",
                (auth_user_id, name, category, quantity, unit_price)
            )
            conn.commit()
            return jsonify({"message": "Item added", "item_id": cursor.lastrowid}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# FIX #3 + FIX #6: update_item uses authenticated user; fixed quantity=0 falsy bug.
@app.route("/items/<int:item_id>", methods=["PUT"])
def update_item(item_id):
    auth_user_id, err = require_auth()
    if err:
        return err

    data       = request.get_json()
    name       = data.get("item_name", "").strip()
    category   = data.get("category", "").strip()
    quantity   = data.get("quantity")
    unit_price = data.get("unit_price")

    # FIX #3: use explicit None checks so quantity=0 is valid
    if not name or not category or quantity is None or unit_price is None:
        return jsonify({"error": "Missing fields"}), 400

    with db() as conn:
        if category:
            conn.execute(
                "INSERT OR IGNORE INTO categories (category_name) VALUES (?)", (category,)
            )
        conn.execute(
            "UPDATE items SET item_name=?, category=?, quantity=?, unit_price=? "
            "WHERE item_id=? AND user_id=?",
            (name, category, quantity, unit_price, item_id, auth_user_id)
        )
        conn.commit()

    return jsonify({"message": "Item updated successfully"})


@app.route("/items/<int:item_id>", methods=["DELETE"])
def delete_item(item_id):
    auth_user_id, err = require_auth()
    if err:
        return err

    with db() as conn:
        conn.execute(
            "DELETE FROM items WHERE item_id=? AND user_id=?", (item_id, auth_user_id)
        )
        conn.commit()

    return jsonify({"message": "Item deleted"})


# ================================================================
# TRANSACTIONS
# ================================================================

@app.route("/transactions", methods=["GET", "POST"])
def transactions():
    auth_user_id, err = require_auth()
    if err:
        return err

    if request.method == "GET":
        type_filter = request.args.get("type")
        date_from   = request.args.get("date_from")
        date_to     = request.args.get("date_to")

        query  = """
            SELECT t.transaction_id, i.item_name, t.type, t.quantity, t.date
            FROM transactions t
            JOIN items i ON t.item_id = i.item_id
            WHERE t.user_id=?
        """
        params = [auth_user_id]

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

        with db() as conn:
            txns = [dict(r) for r in conn.execute(query, params).fetchall()]
        return jsonify(txns)

    # POST
    data     = request.get_json()
    item_id  = data.get("item_id")
    ttype    = data.get("type")
    quantity = data.get("quantity")

    if not all([item_id, ttype, quantity is not None]):
        return jsonify({"error": "Missing fields"}), 400

    if ttype not in ("IN", "OUT"):
        return jsonify({"error": "type must be IN or OUT"}), 400

    try:
        item_id  = int(item_id)
        quantity = int(quantity)
    except (ValueError, TypeError):
        return jsonify({"error": "item_id and quantity must be integers"}), 400

    if quantity <= 0:
        return jsonify({"error": "quantity must be a positive integer"}), 400

    try:
        with db() as conn:
            item = conn.execute(
                "SELECT quantity FROM items WHERE item_id=? AND user_id=?",
                (item_id, auth_user_id)
            ).fetchone()

            if not item:
                return jsonify({"error": "Item not found"}), 404

            new_qty = item["quantity"] + quantity if ttype == "IN" else item["quantity"] - quantity
            if new_qty < 0:
                return jsonify({"error": "Insufficient stock"}), 400

            conn.execute(
                "UPDATE items SET quantity=? WHERE item_id=? AND user_id=?",
                (new_qty, item_id, auth_user_id)
            )
            conn.execute(
                "INSERT INTO transactions (user_id, item_id, type, quantity) VALUES (?, ?, ?, ?)",
                (auth_user_id, item_id, ttype, quantity)
            )
            conn.commit()

        return jsonify({"message": "Transaction recorded", "new_quantity": new_qty}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ================================================================
# REPORTS
# ================================================================

@app.route("/reports", methods=["GET"])
def reports():
    auth_user_id, err = require_auth()
    if err:
        return err

    low_threshold = int(request.args.get("low_threshold", 5))
    date_from     = request.args.get("date_from")
    date_to       = request.args.get("date_to")

    with db() as conn:
        total_items = conn.execute(
            "SELECT COUNT(*) AS total FROM items WHERE user_id=?", (auth_user_id,)
        ).fetchone()["total"]

        total_value = conn.execute(
            "SELECT SUM(quantity * unit_price) AS total_value FROM items WHERE user_id=?",
            (auth_user_id,)
        ).fetchone()["total_value"] or 0

        txn_q = "SELECT COUNT(*) AS n FROM transactions WHERE user_id=?"
        txn_p = [auth_user_id]
        if date_from:
            txn_q += " AND DATE(date) >= ?"; txn_p.append(date_from)
        if date_to:
            txn_q += " AND DATE(date) <= ?"; txn_p.append(date_to)
        total_transactions = conn.execute(txn_q, txn_p).fetchone()["n"]

        low_stock = [dict(r) for r in conn.execute(
            "SELECT item_name, quantity FROM items WHERE user_id=? AND quantity < ? ORDER BY quantity ASC",
            (auth_user_id, low_threshold)
        ).fetchall()]

        by_category = [dict(r) for r in conn.execute(
            """
            SELECT category,
                   SUM(quantity * unit_price) AS value,
                   SUM(quantity)              AS total_qty
            FROM items
            WHERE user_id=?
            GROUP BY category
            ORDER BY value DESC
            """,
            (auth_user_id,)
        ).fetchall()]

        top_q = """
            SELECT i.item_name,
                   SUM(CASE WHEN t.type='IN'  THEN t.quantity ELSE 0 END) AS total_in,
                   SUM(CASE WHEN t.type='OUT' THEN t.quantity ELSE 0 END) AS total_out,
                   COUNT(t.transaction_id)                                  AS txn_count
            FROM transactions t
            JOIN items i ON t.item_id = i.item_id
            WHERE t.user_id=?
        """
        top_p = [auth_user_id]
        if date_from:
            top_q += " AND DATE(t.date) >= ?"; top_p.append(date_from)
        if date_to:
            top_q += " AND DATE(t.date) <= ?"; top_p.append(date_to)
        top_q += " GROUP BY t.item_id ORDER BY (total_in + total_out) DESC LIMIT 5"
        top_items = [dict(r) for r in conn.execute(top_q, top_p).fetchall()]

        turnover = [dict(r) for r in conn.execute(
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
            (auth_user_id, auth_user_id)
        ).fetchall()]

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
