const API_URL = "http://127.0.0.1:5000/items";

const itemForm = document.getElementById("itemForm");
const tableBody = document.getElementById("itemsTableBody");

// Load all items
function loadItems() {
  fetch(API_URL)
    .then(res => res.json())
    .then(items => {
      tableBody.innerHTML = "";
      items.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td><input value="${item.item_name}" data-id="${item.item_id}" class="nameInput"></td>
          <td><input value="${item.category}" data-id="${item.item_id}" class="categoryInput"></td>
          <td><input type="number" value="${item.quantity}" data-id="${item.item_id}" class="quantityInput" min="1"></td>
          <td><input type="number" value="${item.unit_price}" data-id="${item.item_id}" class="priceInput" min="0" step="0.01"></td>
          <td>
            <button onclick="updateItem(${item.item_id})">Update</button>
            <button onclick="deleteItem(${item.item_id})">Delete</button>
          </td>
        `;
        tableBody.appendChild(row);
      });
    });
}

// Add new item
itemForm.addEventListener("submit", e => {
  e.preventDefault();
  const name = document.getElementById("item_name").value.trim();
  const category = document.getElementById("category").value.trim();
  const quantity = parseInt(document.getElementById("quantity").value);
  const unit_price = parseFloat(document.getElementById("unit_price").value);

  fetch(API_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_name: name, category, quantity, unit_price })
  })
  .then(res => res.json())
  .then(() => {
    itemForm.reset();
    loadItems();
  });
});

// Update item
function updateItem(id) {
  const name = document.querySelector(`.nameInput[data-id='${id}']`).value;
  const category = document.querySelector(`.categoryInput[data-id='${id}']`).value;
  const quantity = parseInt(document.querySelector(`.quantityInput[data-id='${id}']`).value);
  const unit_price = parseFloat(document.querySelector(`.priceInput[data-id='${id}']`).value);

  fetch(`${API_URL}/${id}`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ item_name: name, category, quantity, unit_price })
  })
  .then(res => res.json())
  .then(() => loadItems());
}

// Delete item
function deleteItem(id) {
  fetch(`${API_URL}/${id}`, { method: "DELETE" })
    .then(res => res.json())
    .then(() => loadItems());
}

// Initial load
document.addEventListener("DOMContentLoaded", loadItems);