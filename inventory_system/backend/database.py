import sqlite3

DB_FILE = "inventory.db"

def get_connection():
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        print("Error connecting to SQLite:", e)
        return None

def close_connection(conn):
    if conn:
        conn.close()

def initialize_db():
    conn   = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id       INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        email    TEXT UNIQUE NOT NULL,
        password TEXT NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS categories (
        category_id   INTEGER PRIMARY KEY AUTOINCREMENT,
        category_name TEXT UNIQUE NOT NULL
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id    INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id    INTEGER NOT NULL,
        item_name  TEXT NOT NULL,
        category   TEXT,
        quantity   INTEGER DEFAULT 0,
        unit_price REAL    DEFAULT 0.0,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id)
    )""")

    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        transaction_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id        INTEGER NOT NULL,
        item_id        INTEGER NOT NULL,
        type           TEXT CHECK(type IN ('IN','OUT')),
        quantity       INTEGER,
        date           TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(id),
        FOREIGN KEY(item_id) REFERENCES items(item_id)
    )""")

    # indexes for fast per-user lookups
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_items_user    ON items(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_user      ON transactions(user_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_item      ON transactions(item_id)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_txn_date      ON transactions(date)")

    # trigger: keep updated_at fresh on item edits
    cursor.execute("""
    CREATE TRIGGER IF NOT EXISTS update_items_timestamp
    AFTER UPDATE ON items
    BEGIN
        UPDATE items SET updated_at = CURRENT_TIMESTAMP WHERE item_id = NEW.item_id;
    END
    """)

    conn.commit()
    close_connection(conn)

initialize_db()
