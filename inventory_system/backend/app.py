from flask import Flask, request, jsonify
import mysql.connector
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

db = mysql.connector.connect(
    host="127.0.0.1",
    user="inventory_user",
    password="yourpassword",
    database="inventory_db"
)

# Get all items
@app.route('/items', methods=['GET'])
def get_items():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM items")
    items = cursor.fetchall()
    return jsonify(items)

# Add item
@app.route('/items', methods=['POST'])
def add_item():
    data = request.json
    cursor = db.cursor()

    sql = "INSERT INTO items (item_name, category_id, quantity, unit_price) VALUES (%s,%s,%s,%s)"
    val = (data['item_name'], data['category_id'], data['quantity'], data['unit_price'])

    cursor.execute(sql, val)
    db.commit()

    return jsonify({"message": "Item added"})

# Delete item
@app.route('/items/<int:id>', methods=['DELETE'])
def delete_item(id):
    cursor = db.cursor()
    cursor.execute("DELETE FROM items WHERE item_id=%s", (id,))
    db.commit()

    return jsonify({"message": "Item deleted"})

# Stock transaction
@app.route('/transactions', methods=['POST'])
def transaction():
    data = request.json
    cursor = db.cursor()

    item_id = data['item_id']
    quantity = data['quantity']
    ttype = data['type']

    if ttype == "IN":
        cursor.execute("UPDATE items SET quantity = quantity + %s WHERE item_id=%s",(quantity,item_id))
    else:
        cursor.execute("UPDATE items SET quantity = quantity - %s WHERE item_id=%s",(quantity,item_id))

    cursor.execute(
        "INSERT INTO transactions (item_id,type,quantity) VALUES (%s,%s,%s)",
        (item_id,ttype,quantity)
    )

    db.commit()

    return jsonify({"message":"Transaction recorded"})

# Get transactions
@app.route('/transactions', methods=['GET'])
def get_transactions():
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM transactions")
    data = cursor.fetchall()

    return jsonify(data)

if __name__ == '__main__':
    app.run(debug=True)