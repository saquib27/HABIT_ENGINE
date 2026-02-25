// Frontend/js/dashboard.js
// Uses backend endpoints described in README & routes. :contentReference[oaicite:5]{index=5} :contentReference[oaicite:6]{index=6}

const drop = document.getElementById("drop");
const fileInput = document.getElementById("file");
const btnAnalyze = document.getElementById("btnAnalyze");
const btnClear = document.getElementById("btnClear");
const fileInfo = document.getElementById("fileInfo");
const previewTable = document.getElementById("previewTable");
const alertsTable = document.getElementById("alertsTable");
const errBox = document.getElementById("err");
const runOut = document.getElementById("runOut");

const apiBaseEl = document.getElementById("apiBase");
const btnPing = document.getElementById("btnPing");
const pingOut = document.getElementById("pingOut");
const btnRefreshCards = document.getElementById("btnRefreshCards");
const cardsWrap = document.getElementById("cards");

let parsedRows = [];   // normalized trade rows
let lastAlerts = [];

function apiBase() {
  return (apiBaseEl.value || "").trim().replace(/\/+$/, "");
}

function setErr(msg) {
  errBox.textContent = msg || "";
}

function esc(s) {
  return String(s ?? "").replace(/[&<>"']/g, (c) => ({
    "&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#039;"
  }[c]));
}

// --- CSV parsing (simple but good enough for normal trade CSVs)
function parseCSV(text) {
  // Handles commas + quoted values.
  const rows = [];
  let cur = "", inQ = false;
  const lines = [];

  for (let i = 0; i < text.length; i++) {
    const ch = text[i];
    const next = text[i + 1];

    if (ch === '"' && next === '"') { cur += '"'; i++; continue; }
    if (ch === '"') { inQ = !inQ; continue; }

    if (!inQ && (ch === "\n" || ch === "\r")) {
      if (ch === "\r" && next === "\n") i++;
      lines.push(cur);
      cur = "";
      continue;
    }
    cur += ch;
  }
  if (cur.length) lines.push(cur);

  for (const line of lines) {
    if (!line.trim()) continue;
    const cols = [];
    let cell = "", q = false;
    for (let i = 0; i < line.length; i++) {
      const ch = line[i];
      const next = line[i + 1];
      if (ch === '"' && next === '"') { cell += '"'; i++; continue; }
      if (ch === '"') { q = !q; continue; }
      if (!q && ch === ",") { cols.push(cell); cell = ""; continue; }
      cell += ch;
    }
    cols.push(cell);
    rows.push(cols.map(c => c.trim()));
  }
  return rows;
}

function normalizeRows(csvRows) {
  if (csvRows.length < 2) throw new Error("CSV must have header + at least 1 data row.");

  const header = csvRows[0].map(h => h.trim());
  const required = ["trade_id","symbol","action","quantity","price","price_before"];
  for (const r of required) {
    if (!header.includes(r)) throw new Error(`Missing required column: ${r}`);
  }

  const idx = Object.fromEntries(header.map((h, i) => [h, i]));

  const out = [];
  for (let i = 1; i < csvRows.length; i++) {
    const row = csvRows[i];
    if (row.every(x => !x)) continue;

    const obj = {
      trade_id: row[idx.trade_id] || `ROW_${i}`,
      symbol: (row[idx.symbol] || "").toUpperCase(),
      action: (row[idx.action] || "").toUpperCase(),
      quantity: Number(row[idx.quantity]),
      price: Number(row[idx.price]),
      price_before: Number(row[idx.price_before]),
    };

    // basic validation to match backend schema expectations :contentReference[oaicite:7]{index=7}
    if (!obj.symbol) throw new Error(`Row ${i}: symbol is empty`);
    if (!["BUY","SELL"].includes(obj.action)) throw new Error(`Row ${i}: action must be BUY/SELL`);
    if (!Number.isFinite(obj.quantity) || obj.quantity <= 0) throw new Error(`Row ${i}: quantity must be > 0`);
    if (!Number.isFinite(obj.price) || obj.price <= 0) throw new Error(`Row ${i}: price must be > 0`);
    if (!Number.isFinite(obj.price_before) || obj.price_before <= 0) throw new Error(`Row ${i}: price_before must be > 0`);

    out.push(obj);
  }
  return out;
}

function renderPreview(rows) {
  const head = ["trade_id","symbol","action","quantity","price","price_before"];
  const show = rows.slice(0, 20);

  let html = `<thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>`;
  for (const r of show) {
    html += `<tr>
      <td>${esc(r.trade_id)}</td>
      <td>${esc(r.symbol)}</td>
      <td>${esc(r.action)}</td>
      <td>${esc(r.quantity)}</td>
      <td>${esc(r.price)}</td>
      <td>${esc(r.price_before)}</td>
    </tr>`;
  }
  html += "</tbody>";
  previewTable.innerHTML = html;
}

function sevPill(sev) {
  const s = String(sev || "").toUpperCase();
  if (s.includes("CRITICAL") || s.includes("HIGH")) return `<span class="pill high">${esc(s)}</span>`;
  if (s.includes("MED")) return `<span class="pill med">${esc(s)}</span>`;
  return `<span class="pill low">${esc(s)}</span>`;
}

function renderAlerts(alerts) {
  const head = ["type","severity","risk_score","symbol","action","quantity","price","message"];
  let html = `<thead><tr>${head.map(h=>`<th>${esc(h)}</th>`).join("")}</tr></thead><tbody>`;
  for (const a of alerts) {
    html += `<tr>
      <td>${esc(a.type)}</td>
      <td>${sevPill(a.severity)}</td>
      <td>${esc(a.risk_score)}</td>
      <td>${esc(a.symbol)}</td>
      <td>${esc(a.action)}</td>
      <td>${esc(a.quantity)}</td>
      <td>${esc(a.price)}</td>
      <td>${esc(a.message)}</td>
    </tr>`;
  }
  html += "</tbody>";
  alertsTable.innerHTML = html;
}

async function jsonFetch(url, opts) {
  const res = await fetch(url, opts);
  const text = await res.text();
  let data = null;
  try { data = text ? JSON.parse(text) : null; } catch { /* ignore */ }
  if (!res.ok) {
    const detail = data?.detail ? JSON.stringify(data.detail) : text;
    throw new Error(`HTTP ${res.status}: ${detail}`);
  }
  return data;
}

// --- Backend interactions
async function pingHealth() {
  pingOut.textContent = "Pinging...";
  try {
    const data = await jsonFetch(`${apiBase()}/health`);
    pingOut.innerHTML = `<span class="ok">OK:</span> ${esc(data.status)} • version ${esc(data.version)}`;
  } catch (e) {
    pingOut.innerHTML = `<span class="err">${esc(e.message)}</span>`;
  }
}

// Stats cards endpoint exists: /charts/stats-summary :contentReference[oaicite:8]{index=8}
async function refreshCards() {
  cardsWrap.innerHTML = "";
  try {
    const data = await jsonFetch(`${apiBase()}/charts/stats-summary`);
    const cards = data?.cards || [];
    cardsWrap.innerHTML = cards.map(c => `
      <div class="stat">
        <div class="label">${esc(c.label)}</div>
        <div class="value">${esc(c.value)} <span class="muted">${esc(c.unit || "")}</span></div>
      </div>
    `).join("");
  } catch (e) {
    cardsWrap.innerHTML = `<div class="err">Failed to load cards: ${esc(e.message)}</div>`;
  }
}

// Analyze CSV: send each row to POST /trades/analyze :contentReference[oaicite:9]{index=9}
async function analyzeCSV() {
  if (!parsedRows.length) return;

  setErr("");
  btnAnalyze.disabled = true;
  runOut.textContent = "Analyzing… (sending rows to backend)";

  lastAlerts = [];
  const start = performance.now();

  // sequential (safer). If you want faster, we can batch later.
  for (let i = 0; i < parsedRows.length; i++) {
    const t = parsedRows[i];
    try {
      const res = await jsonFetch(`${apiBase()}/trades/analyze`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(t),
      });

      const alerts = res?.alerts || [];
      lastAlerts.push(...alerts);

    } catch (e) {
      // stop on first hard failure
      setErr(`Row ${i + 1} failed:\n${e.message}`);
      break;
    }
  }

  const ms = Math.round(performance.now() - start);
  runOut.textContent = `Done. Trades: ${parsedRows.length} • Alerts: ${lastAlerts.length} • Time: ${ms}ms`;

  renderAlerts(lastAlerts);
  await refreshCards();

  btnAnalyze.disabled = false;
}

// --- File handling
function onFile(file) {
  setErr("");
  if (!file) return;

  fileInfo.textContent = `Selected: ${file.name} • ${(file.size / 1024).toFixed(1)} KB`;
  btnClear.disabled = false;

  const reader = new FileReader();
  reader.onload = () => {
    try {
      const raw = String(reader.result || "");
      const rows = parseCSV(raw);
      parsedRows = normalizeRows(rows);
      renderPreview(parsedRows);
      btnAnalyze.disabled = parsedRows.length === 0;
      runOut.textContent = "";
      alertsTable.innerHTML = "";
    } catch (e) {
      parsedRows = [];
      previewTable.innerHTML = "";
      btnAnalyze.disabled = true;
      setErr(e.message);
    }
  };
  reader.readAsText(file);
}

function clearAll() {
  parsedRows = [];
  lastAlerts = [];
  previewTable.innerHTML = "";
  alertsTable.innerHTML = "";
  fileInfo.textContent = "";
  runOut.textContent = "";
  setErr("");
  fileInput.value = "";
  btnAnalyze.disabled = true;
  btnClear.disabled = true;
}

// --- Drag/drop UI
drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag"); });
drop.addEventListener("dragleave", () => drop.classList.remove("drag"));
drop.addEventListener("drop", (e) => {
  e.preventDefault();
  drop.classList.remove("drag");
  const f = e.dataTransfer.files?.[0];
  if (f) onFile(f);
});

fileInput.addEventListener("change", () => onFile(fileInput.files?.[0]));

btnAnalyze.addEventListener("click", analyzeCSV);
btnClear.addEventListener("click", clearAll);
btnPing.addEventListener("click", pingHealth);
btnRefreshCards.addEventListener("click", refreshCards);

// initial load
pingHealth();
refreshCards();