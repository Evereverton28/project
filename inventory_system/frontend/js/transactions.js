const API_ITEMS        = "http://127.0.0.1:5000/items";
const API_TRANSACTIONS = "http://127.0.0.1:5000/transactions";

const itemSelect = document.getElementById("itemSelect");
const form       = document.getElementById("transactionForm");
const table      = document.getElementById("transactionTable");

const user_id = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

/* ============================
   LOAD ITEMS INTO DROPDOWN
============================ */
function loadItems() {
  fetch(`${API_ITEMS}?user_id=${user_id}`)
    .then(res => res.json())
    .then(items => {
      itemSelect.innerHTML = "";
      if (items.length === 0) {
        itemSelect.innerHTML = `<option disabled>No items found — add items first</option>`;
        return;
      }
      items.forEach(item => {
        const opt = document.createElement("option");
        opt.value       = item.item_id;
        opt.textContent = `${item.item_name} (Stock: ${item.quantity})`;
        itemSelect.appendChild(opt);
      });
    })
    .catch(() => showToast("Could not load items", "danger"));
}

/* ============================
   LOAD TRANSACTIONS
============================ */
function loadTransactions() {
  table.innerHTML = `
    <tr><td colspan="4" class="loading-state">
      <i class="fa-solid fa-spinner fa-spin"></i> Loading transactions...
    </td></tr>`;

  fetch(`${API_TRANSACTIONS}?user_id=${user_id}`)
    .then(res => res.json())
    .then(data => {
      table.innerHTML = "";

      if (data.length === 0) {
        table.innerHTML = `
          <tr><td colspan="4" class="empty-state">
            <i class="fa-solid fa-inbox"></i>
            <p>No transactions recorded yet</p>
          </td></tr>`;
        return;
      }

      /* newest first */
      [...data].reverse().forEach(t => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${t.item_name}</td>
          <td><span class="badge ${t.type === 'IN' ? 'success' : 'danger'}">${t.type}</span></td>
          <td>${t.quantity}</td>
          <td>${new Date(t.date).toLocaleString()}</td>`;
        table.appendChild(row);
      });
    })
    .catch(() => {
      table.innerHTML = `<tr><td colspan="4" class="empty-state error">Could not load transactions</td></tr>`;
    });
}

/* ============================
   SUBMIT TRANSACTION
============================ */
form.addEventListener("submit", e => {
  e.preventDefault();

  const item_id  = itemSelect.value;
  const type     = document.getElementById("type").value;
  const quantity = parseInt(document.getElementById("quantity").value);

  if (!item_id || isNaN(quantity) || quantity <= 0) {
    showToast("Please select an item and enter a valid quantity", "danger");
    return;
  }

  fetch(API_TRANSACTIONS, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ user_id, item_id, type, quantity })
  })
  .then(res => res.json())
  .then(data => {
    if (data.error) {
      showToast(data.error, "danger");
    } else {
      showToast(`Transaction recorded — ${type} ${quantity} units`, "success");
      form.reset();
      loadItems();
      loadTransactions();
    }
  })
  .catch(() => showToast("Transaction failed", "danger"));
});

/* ============================
   INIT
============================ */
document.addEventListener("DOMContentLoaded", () => {
  loadItems();
  loadTransactions();
});
