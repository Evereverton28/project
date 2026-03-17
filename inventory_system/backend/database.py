import sqlite3

DB_FILE = "inventory.db"  # SQLite database file

def get_connection():
    """
    Returns a SQLite connection object.
    Creates the database file if it doesn't exist.
    """
    try:
        connection = sqlite3.connect(DB_FILE)
        connection.row_factory = sqlite3.Row  # Allows dictionary-like access
        return connection
    except sqlite3.Error as e:
        print("Error connecting to SQLite:", e)
        return None

def close_connection(connection):
    """
    Closes the SQLite connection safely.
    """
    if connection:
        connection.close()

def initialize_db():
    """
    Create tables if they don't exist.
    Call this once at app start.
    """
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        category TEXT,
        quantity INTEGER NOT NULL,
        price REAL NOT NULL
    )
    """)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transactions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        item_id INTEGER NOT NULL,
        type TEXT NOT NULL,
        quantity INTEGER NOT NULL,
        timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(item_id) REFERENCES items(id)
    )
    """)
    conn.commit()
    close_connection(conn)