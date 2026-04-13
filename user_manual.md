# Smart Inventory Management System (SIMS)

## User Manual

**Project Title:** Smart Inventory Management System (SIMS)
**Developer:** Ng’ang’a Everton Kairu
**Registration Number:** 24/05787
**Course:** Bachelor of Science in Data Science
**Supervisor:** Mr. Fredrick Omondi
**Date:** April 2026

---

## 1. Introduction

The Smart Inventory Management System (SIMS) is a Flask-based web application designed to automate inventory management processes. It uses an SQLite database to store and manage data related to users, items, and transactions.

The system operates through REST API endpoints and communicates using JSON. Each user is assigned a unique `user_id`, which ensures proper data isolation and secure inventory tracking.

SIMS replaces manual inventory systems with a structured, automated, and reliable digital solution.

---

## 2. Purpose of the System

The system was developed to:

- Automate inventory management operations
- Improve the accuracy of stock records
- Enable real-time inventory tracking
- Provide secure authentication
- Support stock-in and stock-out transactions
- Generate inventory reports
- Reduce manual errors in stock control

---

## 3. System Requirements

### 3.1 Hardware Requirements
- 4GB RAM minimum
- Intel Core i3 or higher
- 500MB free storage

### 3.2 Software Requirements
- Python 3.x
- Flask framework
- Flask-CORS
- Werkzeug security library
- SQLite database
- Postman or web browser for testing APIs

---

## 4. Installation Guide

### 4.1 Install Dependencies

```bash
pip install flask flask-cors werkzeug
```

---

### 4.2 Run the System

```bash
python app.py
```

---

### 4.3 Access the System

Open the application in a browser at:

`http://127.0.0.1:5000`

---

## 5. User Management Module

### 5.1 User Registration (Signup)

**Endpoint:** `POST /signup`

Request:
```json
{
  "username": "john",
  "email": "john@email.com",
  "password": "1234"
}
```

Process:
- Validates input fields
- Hashes the password securely
- Stores the user in the database

Response:
```json
{
  "user_id": 1,
  "username": "john"
}
```

Error response:
```json
{
  "error": "Username or email already exists"
}
```

---

### 5.2 User Login

**Endpoint:** `POST /login`

Request:
```json
{
  "username": "john",
  "password": "1234"
}
```

Response:
```json
{
  "user_id": 1,
  "username": "john"
}
```

Failure response:
```json
{
  "error": "Invalid credentials"
}
```

---

## 6. Item Management Module

All items are linked to a unique `user_id`.

---

### 6.1 Add Item

**Endpoint:** `POST /items`

Request:
```json
{
  "user_id": 1,
  "item_name": "Laptop",
  "category": "Electronics",
  "quantity": 10,
  "unit_price": 50000
}
```

Response:
```json
{
  "message": "Item added"
}
```

---

### 6.2 View Items

**Endpoint:** `GET /items?user_id=1`

Response example:
```json
[
  {
    "item_name": "Laptop",
    "category": "Electronics",
    "quantity": 10,
    "unit_price": 50000
  }
]
```

---

### 6.3 Update Item

**Endpoint:** `PUT /items/<item_id>`

Request:
```json
{
  "user_id": 1,
  "item_name": "Laptop Pro",
  "category": "Electronics",
  "quantity": 8,
  "unit_price": 60000
}
```

Response:
```json
{
  "message": "Item updated successfully"
}
```

---

### 6.4 Delete Item

**Endpoint:** `DELETE /items/<item_id>?user_id=1`

Response:
```json
{
  "message": "Item deleted"
}
```

---

## 7. Transactions Module

### 7.1 Record Transaction

**Endpoint:** `POST /transactions`

Request:
```json
{
  "user_id": 1,
  "item_id": 2,
  "type": "IN",
  "quantity": 5
}
```

Response example:
```json
{
  "message": "Transaction recorded",
  "transaction_id": 1
}
```

---

### 7.2 Transaction Types

- `IN` — Adds stock
- `OUT` — Removes stock

---

### 7.3 Stock Logic

- `IN:` `new_quantity = current_quantity + quantity`
- `OUT:` `new_quantity = current_quantity - quantity`

The system prevents negative stock values.

---

### 7.4 Validation Rules

- Item must exist
- Quantity must be valid
- Stock cannot go below zero
- All fields are required

---

## 8. Reporting Module

**Endpoint:** `GET /reports?user_id=1`

Response example:
```json
{
  "total_items": 10,
  "total_value": 250000,
  "total_transactions": 15,
  "low_stock": [
    {
      "item_name": "Mouse",
      "quantity": 2
    }
  ]
}
```

---

## 9. Security Features

- Password hashing using Werkzeug
- SQL parameterized queries
- User-based data isolation
- Input validation
- Secure transaction updates

---

## 10. Database Structure

USERS:
- id
- username
- email
- password

ITEMS:
- item_id
- user_id
- item_name
- category
- quantity
- unit_price

TRANSACTIONS:
- transaction_id
- user_id
- item_id
- type
- quantity
- date

---

## 11. System Limitations

- No role-based access control
- Local deployment only
- SQLite is intended for single-user or low-concurrency use
- No dedicated frontend framework separation
- No cloud integration

---

## 12. Troubleshooting

- Server not starting → Run `python app.py`
- Login failure → Check credentials
- Missing `user_id` → Add it to the request
- Database error → Reset the database
- Item not updating → Check `item_id`

---

## 13. Best Practices

- Always include `user_id`
- Use Postman for testing
- Keep database backups
- Do not edit SQLite manually
- Use valid JSON format

---

## 14. System Workflow

1. Sign up
2. Login
3. Add items
4. Record transactions
5. Generate reports

---

# 16. SOURCE CODE REPOSITORY

The full source code for the Smart Inventory Management System (SIMS) is hosted on GitHub for version control, collaboration, and backup purposes.

GitHub Repository:
https://github.com/Evereverton28/project

The repository includes:
- Flask backend source code
- Database initialization scripts
- Frontend templates (if any)
- Project configuration files
- Setup instructions

## 16. Conclusion

SIMS provides an efficient and secure inventory management solution using Flask and SQLite. It improves accuracy, reduces manual errors, and enhances operational efficiency.

---

## End of User Manual