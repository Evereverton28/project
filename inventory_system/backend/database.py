import mysql.connector
from mysql.connector import Error

def get_connection():
    """
    Returns a MySQL connection object.
    Update user, password, host, database to match your setup.
    """
    try:
        connection = mysql.connector.connect(
            host="127.0.0.1",
            user="inventory_user",
            password="yourpassword",    
            database="inventory_db"
        )
        if connection.is_connected():
            return connection
    except Error as e:
        print("Error while connecting to MySQL", e)
        return None

def close_connection(connection):
    """
    Closes the MySQL connection safely.
    """
    if connection is not None and connection.is_connected():
        connection.close()