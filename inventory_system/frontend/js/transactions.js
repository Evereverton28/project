const API_ITEMS = "http://127.0.0.1:5000/items";
const API_TRANSACTIONS = "http://127.0.0.1:5000/transactions";

const itemSelect = document.getElementById("itemSelect");
const form = document.getElementById("transactionForm");
const table = document.getElementById("transactionTable");

// Get logged-in user_id
const user_id = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

// Load items into dropdown
function loadItems() {
  fetch(`${API_ITEMS}?user_id=${user_id}`)
    .then(res => res.json())
    .then(items => {
      itemSelect.innerHTML = "";
      items.forEach(item => {
        const option = document.createElement("option");
        option.value = item.item_id;
        option.textContent = `${item.item_name} (Stock: ${item.quantity})`;
        itemSelect.appendChild(option);
      });
    });
}

// Load transactions
function loadTransactions() {
  fetch(`${API_TRANSACTIONS}?user_id=${user_id}`)
    .then(res => res.json())
    .then(data => {
      table.innerHTML = "";
      data.forEach(t => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${t.item_name}</td>
          <td>${t.type}</td>
          <td>${t.quantity}</td>
          <td>${t.date}</td>
        `;
        table.appendChild(row);
      });
    });
}

// Submit transaction
form.addEventListener("submit", e => {
  e.preventDefault();
  const item_id = itemSelect.value;
  const type = document.getElementById("type").value;
  const quantity = parseInt(document.getElementById("quantity").value);

  fetch(API_TRANSACTIONS, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, item_id, type, quantity })
  })
  .then(res => res.json())
  .then(data => {
    alert(data.message || data.error);
    loadItems();
    loadTransactions();
    form.reset();
  });
});

document.addEventListener("DOMContentLoaded", () => {
  loadItems();
  loadTransactions();
});