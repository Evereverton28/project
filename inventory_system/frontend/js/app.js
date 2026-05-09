const API_ITEMS = "http://127.0.0.1:5000/items";
const user_id   = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

const itemForm       = document.getElementById("itemForm");
const itemsTableBody = document.getElementById("itemsTableBody");

/* ============================
   LOAD ITEMS
============================ */
function loadItems() {
  itemsTableBody.innerHTML = `
    <tr>
      <td colspan="5" class="loading-state">
        <i class="fa-solid fa-spinner fa-spin"></i> Loading items...
      </td>
    </tr>`;

  // FIX #6: pass Authorization header
  fetch(API_ITEMS, { headers: authHeaders() })
    .then(res => res.json())
    .then(items => {
      itemsTableBody.innerHTML = "";

      if (items.length === 0) {
        itemsTableBody.innerHTML = `
          <tr>
            <td colspan="5" class="empty-state">
              <i class="fa-solid fa-box-open"></i>
              <p>No items yet — add your first item above</p>
            </td>
          </tr>`;
        return;
      }

      items.forEach(item => {
        const row = document.createElement("tr");
        const lowStock = item.quantity < 5;
        row.innerHTML = `
          <td>${item.item_name}</td>
          <td>${item.category || "—"}</td>
          <td>
            ${item.quantity}
            ${lowStock ? `<span class="badge danger" style="margin-left:6px">Low</span>` : ""}
          </td>
          <td>KES ${Number(item.unit_price).toLocaleString()}</td>
          <td>
            <button class="action-btn edit-btn" onclick="editItem(${item.item_id}, this)" title="Edit">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="action-btn delete-btn" onclick="deleteItem(${item.item_id})" title="Delete">
              <i class="fa-solid fa-trash"></i>
            </button>
          </td>`;
        itemsTableBody.appendChild(row);
      });
    })
    .catch(() => {
      itemsTableBody.innerHTML = `
        <tr><td colspan="5" class="empty-state error">Could not load items. Is the server running?</td></tr>`;
    });
}

/* ============================
   ADD ITEM
============================ */
itemForm.addEventListener("submit", e => {
  e.preventDefault();
  const name       = document.getElementById("item_name").value.trim();
  const category   = document.getElementById("category").value.trim();
  const quantity   = parseInt(document.getElementById("quantity").value);
  const unit_price = parseFloat(document.getElementById("unit_price").value);

  if (!name || !category || isNaN(quantity) || isNaN(unit_price)) {
    showToast("Please fill in all fields correctly", "danger");
    return;
  }

  // FIX #6: authHeaders includes Bearer token
  fetch(API_ITEMS, {
    method: "POST",
    headers: authHeaders(),
    body: JSON.stringify({ user_id, item_name: name, category, quantity, unit_price }),
  })
  .then(res => res.json())
  .then(() => {
    showToast("Item added successfully", "success");
    itemForm.reset();
    loadItems();
  })
  .catch(() => showToast("Failed to add item", "danger"));
});

/* ============================
   DELETE ITEM
============================ */
function deleteItem(item_id) {
  if (!confirm("Delete this item? This cannot be undone.")) return;

  fetch(`${API_ITEMS}/${item_id}`, {
    method: "DELETE",
    headers: authHeaders(),
  })
    .then(res => res.json())
    .then(() => {
      showToast("Item deleted", "danger");
      loadItems();
    })
    .catch(() => showToast("Failed to delete item", "danger"));
}

/* ============================
   EDIT ITEM (inline)
   FIX #5: strip all non-numeric chars (except ".") from price cell
   FIX #11: editItem marks the row so filterItems won't corrupt it
============================ */
function editItem(id, btn) {
  const row   = btn.closest("tr");
  const cells = row.querySelectorAll("td");

  const name     = cells[0].innerText.trim();
  const category = cells[1].innerText === "—" ? "" : cells[1].innerText.trim();
  const quantity = cells[2].innerText.replace(/\s+.*/,"").trim();

  // FIX #5: robust price parsing — strip currency label and all non-numeric chars except "."
  const price = cells[3].innerText.replace("KES", "").replace(/[^0-9.]/g, "").trim();

  // FIX #11: mark row as editing so filterItems skips it
  row.dataset.editing = "true";

  row.innerHTML = `
    <td><input value="${name}"></td>
    <td><input value="${category}"></td>
    <td><input type="number" min="0" value="${quantity}"></td>
    <td><input type="number" min="0" step="0.01" value="${price}"></td>
    <td>
      <button class="action-btn edit-btn" onclick="saveItem(${id}, this)" title="Save">
        <i class="fa-solid fa-check"></i>
      </button>
      <button class="action-btn delete-btn" onclick="cancelEdit(this)" title="Cancel">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </td>`;
}

/* ============================
   CANCEL EDIT
   FIX #11: reload instead of leaving a broken row
============================ */
function cancelEdit(btn) {
  loadItems();
}

/* ============================
   SAVE EDIT
============================ */
function saveItem(id, btn) {
  const row    = btn.closest("tr");
  const inputs = row.querySelectorAll("input");

  const updatedItem = {
    item_name:  inputs[0].value.trim(),
    category:   inputs[1].value.trim(),
    quantity:   parseInt(inputs[2].value),
    unit_price: parseFloat(inputs[3].value),
    user_id,
  };

  if (!updatedItem.item_name || !updatedItem.category) {
    showToast("Name and category are required", "danger");
    return;
  }

  // FIX #6: authHeaders
  fetch(`${API_ITEMS}/${id}`, {
    method: "PUT",
    headers: authHeaders(),
    body: JSON.stringify(updatedItem),
  })
  .then(res => res.json())
  .then(() => {
    showToast("Item updated", "success");
    loadItems();
  })
  .catch(() => showToast("Failed to update item", "danger"));
}

/* ============================
   SEARCH FILTER
   FIX #11: skip rows that are in edit mode
============================ */
function filterItems() {
  const search = document.getElementById("searchInput").value.toLowerCase();
  document.querySelectorAll("#itemsTableBody tr").forEach(row => {
    // FIX #11: never hide the active edit row
    if (row.dataset.editing === "true") {
      row.style.display = "";
      return;
    }
    row.style.display = row.innerText.toLowerCase().includes(search) ? "" : "none";
  });
}

/* ============================
   INIT
============================ */
document.addEventListener("DOMContentLoaded", loadItems);
