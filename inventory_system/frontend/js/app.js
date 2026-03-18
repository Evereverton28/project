const API_ITEMS = "http://127.0.0.1:5000/items";
const itemForm = document.getElementById("itemForm");
const itemsTableBody = document.getElementById("itemsTableBody");

const user_id = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

/* =========================
   LOAD ITEMS
========================= */
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
            <button class="action-btn edit-btn" onclick="editItem(${item.item_id}, this)">
              <i class="fa-solid fa-pen"></i>
            </button>
            <button class="action-btn delete-btn" onclick="deleteItem(${item.item_id})">
              <i class="fa-solid fa-trash"></i>
            </button>
          </td>
        `;

        itemsTableBody.appendChild(row);
      });
    });
}

/* =========================
   ADD ITEM
========================= */
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
  .then(() => {
    showMessage("Item added successfully ✅");
    itemForm.reset();
    loadItems();
  });
});

/* =========================
   DELETE ITEM (CONFIRM)
========================= */
function deleteItem(item_id) {
  if (!confirm("Delete this item?")) return;

  fetch(`${API_ITEMS}/${item_id}?user_id=${user_id}`, {
    method: "DELETE"
  })
  .then(res => res.json())
  .then(() => {
    showMessage("Item deleted 🗑️");
    loadItems();
  });
}

/* =========================
   EDIT ITEM (INLINE)
========================= */
function editItem(id, btn) {
  const row = btn.closest("tr");
  const cells = row.querySelectorAll("td");

  const name = cells[0].innerText;
  const category = cells[1].innerText;
  const quantity = cells[2].innerText;
  const price = cells[3].innerText;

  row.innerHTML = `
    <td><input value="${name}"></td>
    <td><input value="${category}"></td>
    <td><input type="number" value="${quantity}"></td>
    <td><input type="number" value="${price}"></td>
    <td>
      <button class="action-btn edit-btn" onclick="saveItem(${id}, this)">
        <i class="fa-solid fa-check"></i>
      </button>
      <button class="action-btn delete-btn" onclick="loadItems()">
        <i class="fa-solid fa-xmark"></i>
      </button>
    </td>
  `;
}

/* =========================
   SAVE EDIT
========================= */
function saveItem(id, btn) {
  const row = btn.closest("tr");
  const inputs = row.querySelectorAll("input");

  const updatedItem = {
    item_name: inputs[0].value,
    category: inputs[1].value,
    quantity: parseInt(inputs[2].value),
    unit_price: parseFloat(inputs[3].value),
    user_id
  };

  fetch(`${API_ITEMS}/${id}`, {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(updatedItem)
  })
  .then(res => res.json())
  .then(() => {
    showMessage("Item updated ✏️");
    loadItems();
  });
}

/* =========================
   SEARCH FILTER
========================= */
function filterItems() {
  const search = document.getElementById("searchInput").value.toLowerCase();
  const rows = document.querySelectorAll("#itemsTableBody tr");

  rows.forEach(row => {
    const text = row.innerText.toLowerCase();
    row.style.display = text.includes(search) ? "" : "none";
  });
}

/* =========================
   CUSTOM MESSAGE (NO ALERT)
========================= */
function showMessage(msg) {
  let box = document.getElementById("msgBox");

  if (!box) {
    box = document.createElement("div");
    box.id = "msgBox";
    box.style.position = "fixed";
    box.style.bottom = "20px";
    box.style.right = "20px";
    box.style.background = "#1e3a8a";
    box.style.color = "white";
    box.style.padding = "10px 15px";
    box.style.borderRadius = "8px";
    document.body.appendChild(box);
  }

  box.textContent = msg;
  box.style.display = "block";

  setTimeout(() => box.style.display = "none", 2000);
}

/* =========================
   INIT
========================= */
document.addEventListener("DOMContentLoaded", loadItems);