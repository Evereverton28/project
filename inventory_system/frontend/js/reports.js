const API_BASE = "http://127.0.0.1:5000";
const user_id  = sessionStorage.getItem("user_id");
if (!user_id) window.location.href = "login.html";

const PALETTE = [
  "#3b82f6","#10b981","#f59e0b","#ef4444",
  "#8b5cf6","#ec4899","#06b6d4","#84cc16"
];

/* track Chart.js instances so we can destroy before redraw */
const charts = {};

/* ================================================================
   STATE
================================================================ */
// FIX #14: load persisted threshold so Reports and Dashboard stay in sync
let activeDays       = 7;
let lowThreshold     = parseInt(sessionStorage.getItem("lowThreshold") || "5");
let cachedReportData = null;

/* ================================================================
   DATE HELPERS
================================================================ */
function todayStr() {
  return new Date().toISOString().slice(0, 10);
}

function daysAgoStr(n) {
  const d = new Date();
  d.setDate(d.getDate() - n);
  return d.toISOString().slice(0, 10);
}

function getDateRange() {
  const from = document.getElementById("dateFrom").value;
  const to   = document.getElementById("dateTo").value;
  return { from, to };
}

/* ================================================================
   QUICK RANGE BUTTONS
================================================================ */
document.querySelectorAll(".range-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".range-btn").forEach(b => b.classList.remove("active"));
    btn.classList.add("active");

    const days = parseInt(btn.dataset.days);
    activeDays = days;

    if (days === 0) {
      document.getElementById("dateFrom").value = "";
      document.getElementById("dateTo").value   = "";
    } else {
      document.getElementById("dateFrom").value = daysAgoStr(days);
      document.getElementById("dateTo").value   = todayStr();
    }

    loadReports();
  });
});

/* ================================================================
   LOW STOCK THRESHOLD SLIDER
   FIX #14: persist to sessionStorage so Dashboard can read the same value
================================================================ */
const sliderEl = document.getElementById("lowThreshold");
// Restore slider to the stored value on page load
sliderEl.value = lowThreshold;
document.getElementById("thresholdVal").textContent = lowThreshold;

sliderEl.addEventListener("input", function () {
  lowThreshold = parseInt(this.value);
  document.getElementById("thresholdVal").textContent = lowThreshold;
});

sliderEl.addEventListener("change", () => {
  // FIX #14: save so dashboard picks up the new threshold
  sessionStorage.setItem("lowThreshold", String(lowThreshold));
  loadReports();
});

/* ================================================================
   APPLY / REFRESH BUTTON
================================================================ */
document.getElementById("applyBtn").addEventListener("click", loadReports);

/* ================================================================
   EXPORT CSV
================================================================ */
document.getElementById("exportBtn").addEventListener("click", () => {
  if (!cachedReportData) { showToast("No data to export yet", "danger"); return; }

  const rep = cachedReportData;
  let csv = "";

  csv += "Summary\n";
  csv += `Total Items,${rep.total_items}\n`;
  csv += `Stock Value (KES),${rep.total_value}\n`;
  csv += `Transactions,${rep.total_transactions}\n`;
  csv += `Low Stock Items,${rep.low_stock.length}\n\n`;

  csv += "Stock by Category\nCategory,Qty,Value (KES)\n";
  rep.by_category.forEach(c => {
    csv += `"${c.category || 'Uncategorised'}",${c.total_qty},${(c.value || 0).toFixed(2)}\n`;
  });
  csv += "\n";

  csv += "Top 5 Most-Moved Items\nItem,Stock In,Stock Out,Transactions\n";
  rep.top_items.forEach(t => {
    csv += `"${t.item_name}",${t.total_in},${t.total_out},${t.txn_count}\n`;
  });
  csv += "\n";

  csv += "Low Stock Items\nItem,Quantity\n";
  rep.low_stock.forEach(i => {
    csv += `"${i.item_name}",${i.quantity}\n`;
  });
  csv += "\n";

  csv += "Turnover Rate\nItem,Current Stock,Units Out,Rate\n";
  rep.turnover.forEach(t => {
    csv += `"${t.item_name}",${t.current_stock},${t.total_out},${t.turnover_rate ?? "N/A"}\n`;
  });

  const blob = new Blob([csv], { type: "text/csv" });
  const url  = URL.createObjectURL(blob);
  const a    = document.createElement("a");
  a.href     = url;
  a.download = `inventory-report-${todayStr()}.csv`;
  a.click();
  URL.revokeObjectURL(url);
  showToast("Report exported", "success");
});

/* ================================================================
   CHART HELPER
================================================================ */
function makeChart(id, config) {
  if (charts[id]) { charts[id].destroy(); }
  charts[id] = new Chart(document.getElementById(id), config);
}

/* ================================================================
   MAIN LOAD
   FIX #6: authHeaders on every fetch
================================================================ */
async function loadReports() {
  const { from, to } = getDateRange();

  let url = `${API_BASE}/reports?low_threshold=${lowThreshold}`;
  if (from) url += `&date_from=${from}`;
  if (to)   url += `&date_to=${to}`;

  let txnUrl = `${API_BASE}/transactions`;
  if (from) txnUrl += `?date_from=${from}`;
  if (to)   txnUrl += `${from ? "&" : "?"}date_to=${to}`;

  try {
    const [repRes, itemsRes, txnRes] = await Promise.all([
      fetch(url,                     { headers: authHeaders() }),
      fetch(`${API_BASE}/items`,     { headers: authHeaders() }),
      fetch(txnUrl,                  { headers: authHeaders() }),
    ]);
    const rep   = await repRes.json();
    const items = await itemsRes.json();
    const txns  = await txnRes.json();

    cachedReportData = rep;

    renderStatCards(rep);
    renderCategoryBar(items);
    renderValuePie(rep.by_category);
    renderTxnDoughnut(txns);
    renderTimeChart(txns);
    renderTopItems(rep.top_items);
    renderTurnover(rep.turnover);
    renderLowStock(rep.low_stock);

  } catch (err) {
    console.error("Reports error:", err);
    showToast("Could not load report data", "danger");
  }
}

/* ================================================================
   STAT CARDS
================================================================ */
function renderStatCards(rep) {
  document.getElementById("totalItems").textContent        = rep.total_items;
  document.getElementById("totalValue").textContent        = `KES ${Number(rep.total_value).toLocaleString()}`;
  document.getElementById("totalTransactions").textContent = rep.total_transactions;
  document.getElementById("lowCount").textContent          = rep.low_stock.length;
}

/* ================================================================
   CHART 1 — stock quantity by category (bar)
================================================================ */
function renderCategoryBar(items) {
  const catMap = {};
  items.forEach(item => {
    const cat = item.category || "Uncategorised";
    catMap[cat] = (catMap[cat] || 0) + item.quantity;
  });

  makeChart("categoryChart", {
    type: "bar",
    data: {
      labels: Object.keys(catMap),
      datasets: [{
        label: "Stock quantity",
        data: Object.values(catMap),
        backgroundColor: PALETTE.slice(0, Object.keys(catMap).length),
        borderRadius: 4,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
      scales: {
        y: { beginAtZero: true, ticks: { stepSize: 1 } },
        x: { ticks: { autoSkip: false } },
      },
    },
  });
}

/* ================================================================
   CHART 2 — stock VALUE by category (pie)
================================================================ */
function renderValuePie(byCategory) {
  const labels = byCategory.map(c => c.category || "Uncategorised");
  const data   = byCategory.map(c => parseFloat((c.value || 0).toFixed(2)));

  makeChart("valueChart", {
    type: "pie",
    data: {
      labels,
      datasets: [{
        data,
        backgroundColor: PALETTE.slice(0, labels.length),
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: { legend: { display: false } },
    },
  });

  document.getElementById("valueLegend").innerHTML = labels.map((l, i) => `
    <div class="legend-item">
      <span class="legend-dot" style="background:${PALETTE[i % PALETTE.length]}"></span>
      ${l} — KES ${Number(data[i]).toLocaleString()}
    </div>
  `).join("");
}

/* ================================================================
   CHART 3 — IN vs OUT doughnut
================================================================ */
function renderTxnDoughnut(txns) {
  const inCount  = txns.filter(t => t.type === "IN").length;
  const outCount = txns.filter(t => t.type === "OUT").length;

  makeChart("txnChart", {
    type: "doughnut",
    data: {
      labels: ["Stock In", "Stock Out"],
      datasets: [{
        data: [inCount, outCount],
        backgroundColor: ["#10b981", "#ef4444"],
        borderWidth: 0,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      cutout: "65%",
      plugins: { legend: { display: false } },
    },
  });

  document.getElementById("txnLegend").innerHTML = `
    <div class="legend-item"><span class="legend-dot" style="background:#10b981"></span>Stock In — ${inCount}</div>
    <div class="legend-item"><span class="legend-dot" style="background:#ef4444"></span>Stock Out — ${outCount}</div>
  `;
}

/* ================================================================
   CHART 4 — transactions over time (line)
   FIX #4: parse SQLite timestamps as local time ("2024-01-15 10:30:00" → "2024-01-15T10:30:00")
   FIX #12: fallback uses activeDays (7) not hardcoded 30
================================================================ */
function renderTimeChart(txns) {
  const { from, to } = getDateRange();

  const endDate   = to   ? new Date(to)   : new Date();
  const startDate = from
    ? new Date(from)
    : (() => {
        const d = new Date();
        // FIX #12: was (activeDays || 30) — now (activeDays || 7)
        d.setDate(d.getDate() - (activeDays || 7));
        return d;
      })();

  const msPerDay = 86400000;
  const numDays  = Math.round((endDate - startDate) / msPerDay) + 1;
  const days     = Math.min(numDays, 180);

  const labels    = [];
  const inCounts  = new Array(days).fill(0);
  const outCounts = new Array(days).fill(0);
  const inQty     = new Array(days).fill(0);
  const outQty    = new Array(days).fill(0);

  for (let i = 0; i < days; i++) {
    const d = new Date(startDate);
    d.setDate(startDate.getDate() + i);
    labels.push(d.toLocaleDateString("en-KE", { month: "short", day: "numeric" }));
  }

  txns.forEach(t => {
    // FIX #4: replace space with "T" so the date is parsed as local time, not UTC
    const txDate = new Date(t.date.replace(" ", "T"));
    const idx    = Math.round((txDate - startDate) / msPerDay);
    if (idx >= 0 && idx < days) {
      if (t.type === "IN")  { inCounts[idx]++;  inQty[idx]  += t.quantity; }
      else                  { outCounts[idx]++; outQty[idx] += t.quantity; }
    }
  });

  makeChart("timeChart", {
    type: "line",
    data: {
      labels,
      datasets: [
        {
          label: "Stock In (count)",
          data: inCounts,
          borderColor: "#10b981",
          backgroundColor: "rgba(16,185,129,0.08)",
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          yAxisID: "yCount",
        },
        {
          label: "Stock Out (count)",
          data: outCounts,
          borderColor: "#ef4444",
          backgroundColor: "rgba(239,68,68,0.06)",
          fill: true,
          tension: 0.4,
          pointRadius: 3,
          borderDash: [5, 3],
          yAxisID: "yCount",
        },
        {
          label: "Units In",
          data: inQty,
          borderColor: "#3b82f6",
          backgroundColor: "transparent",
          tension: 0.4,
          pointRadius: 2,
          borderWidth: 1.5,
          borderDash: [2, 2],
          yAxisID: "yQty",
        },
        {
          label: "Units Out",
          data: outQty,
          borderColor: "#f59e0b",
          backgroundColor: "transparent",
          tension: 0.4,
          pointRadius: 2,
          borderWidth: 1.5,
          borderDash: [2, 2],
          yAxisID: "yQty",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { mode: "index", intersect: false },
      plugins: { legend: { position: "bottom", labels: { boxWidth: 12 } } },
      scales: {
        yCount: {
          beginAtZero: true,
          position: "left",
          ticks: { stepSize: 1 },
          title: { display: true, text: "Transactions" },
        },
        yQty: {
          beginAtZero: true,
          position: "right",
          grid: { drawOnChartArea: false },
          title: { display: true, text: "Units moved" },
        },
        x: { ticks: { autoSkip: true, maxTicksLimit: 10, maxRotation: 0 } },
      },
    },
  });
}

/* ================================================================
   TOP 5 MOST-MOVED ITEMS TABLE
================================================================ */
function renderTopItems(topItems) {
  const tbody = document.getElementById("topItemsBody");
  if (!topItems || topItems.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No transaction data in this period</td></tr>`;
    return;
  }
  tbody.innerHTML = topItems.map((t, i) => `
    <tr>
      <td><span class="rank-badge">#${i + 1}</span> ${t.item_name}</td>
      <td><span class="badge success">+${t.total_in}</span></td>
      <td><span class="badge danger">-${t.total_out}</span></td>
      <td>${t.txn_count}</td>
    </tr>
  `).join("");
}

/* ================================================================
   TURNOVER RATE TABLE
================================================================ */
function renderTurnover(turnover) {
  const tbody = document.getElementById("turnoverBody");
  if (!turnover || turnover.length === 0) {
    tbody.innerHTML = `<tr><td colspan="4" class="empty-state">No data available</td></tr>`;
    return;
  }

  const max = Math.max(...turnover.map(t => t.turnover_rate || 0));

  tbody.innerHTML = turnover.map(t => {
    const rate = t.turnover_rate;
    const pct  = max > 0 && rate ? Math.round((rate / max) * 100) : 0;
    const cls  = rate > 2 ? "success" : rate > 0.5 ? "" : "danger";
    return `
      <tr>
        <td>${t.item_name}</td>
        <td>${t.current_stock}</td>
        <td>${t.total_out}</td>
        <td>
          ${rate !== null ? `
            <div style="display:flex;align-items:center;gap:8px;">
              <div class="turnover-bar-wrap">
                <div class="turnover-bar ${cls}" style="width:${pct}%"></div>
              </div>
              <span class="badge ${cls}">${rate}x</span>
            </div>` : '<span style="color:var(--color-text-tertiary)">N/A</span>'}
        </td>
      </tr>
    `;
  }).join("");
}

/* ================================================================
   LOW STOCK TABLE
================================================================ */
function renderLowStock(lowStock) {
  const tbody = document.getElementById("lowStockBody");
  if (lowStock.length === 0) {
    tbody.innerHTML = `<tr><td colspan="3" class="empty-state"><i class="fa-solid fa-circle-check"></i> All items are well stocked</td></tr>`;
    return;
  }
  tbody.innerHTML = lowStock.map(item => `
    <tr>
      <td>${item.item_name}</td>
      <td>${item.quantity}</td>
      <td><span class="badge danger">${item.quantity === 0 ? "Out of stock" : "Low stock"}</span></td>
    </tr>
  `).join("");
}

/* ================================================================
   INIT
================================================================ */
document.addEventListener("DOMContentLoaded", () => {
  document.getElementById("dateFrom").value = daysAgoStr(7);
  document.getElementById("dateTo").value   = todayStr();
  loadReports();
});
