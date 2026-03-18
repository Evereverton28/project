const API_ITEMS = "http://127.0.0.1:5000/items";
const itemForm = document.getElementById("itemForm");
const itemsTableBody = document.getElementById("itemsTableBody");

// Get logged-in user_id
const user_id = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

// ---------------- Load Items ----------------
function loadItems() {
  fetch(`${API_ITEMS}?user_id=${user_id}`)
    .then(res => res.json())
    .then(items => {
      itemsTableBody.innerHTML = "";
      items.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${item.item_name}</td>
          <td>${item.category}</td>
          <td>${item.quantity}</td>
          <td>${item.unit_price}</td>
          <td>
            <button class="deleteBtn" onclick="deleteItem(${item.item_id})">🗑️</button>
          </td>
        `;
        itemsTableBody.appendChild(row);
      });
    });
}

// ---------------- Add Item ----------------
itemForm.addEventListener("submit", e => {
  e.preventDefault();
  const name = document.getElementById("item_name").value.trim();
  const category = document.getElementById("category").value.trim();
  const quantity = parseInt(document.getElementById("quantity").value);
  const unit_price = parseFloat(document.getElementById("unit_price").value);

  fetch(API_ITEMS, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, item_name: name, category, quantity, unit_price })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message || data.error);
    itemForm.reset();
    loadItems();
  });
});

// ---------------- Delete Item ----------------
function deleteItem(item_id) {
  fetch(`${API_ITEMS}/${item_id}?user_id=${user_id}`, { method: "DELETE" })
    .then(res => res.json())
    .then(() => loadItems());
}

document.addEventListener("DOMContentLoaded", loadItems);