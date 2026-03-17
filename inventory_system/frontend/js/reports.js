const API_REPORTS = "http://127.0.0.1:5000/reports";

function loadReports() {
  fetch(API_REPORTS)
    .then(res => res.json())
    .then(data => {
      document.getElementById("totalItems").textContent = data.total_items;
      document.getElementById("totalValue").textContent = data.total_value;
      document.getElementById("totalTransactions").textContent = data.total_transactions;

      const table = document.getElementById("lowStockTable");
      table.innerHTML = "";

      data.low_stock.forEach(item => {
        const row = document.createElement("tr");
        row.innerHTML = `
          <td>${item.item_name}</td>
          <td>${item.quantity}</td>
        `;
        table.appendChild(row);
      });
    });
}

document.addEventListener("DOMContentLoaded", loadReports);