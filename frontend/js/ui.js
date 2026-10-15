/* UI helpers: formatting, escaping, toasts, modals, badges, states. */

function esc(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;").replace(/'/g, "&#39;");
}

const fmtMoney = (n, cur = "UAH") =>
  new Intl.NumberFormat("uk-UA", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(Number(n) || 0);

const fmtNum = (n) => new Intl.NumberFormat("uk-UA").format(Number(n) || 0);

function fmtDate(d) {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt)) return String(d);
  return dt.toLocaleDateString("uk-UA", { year: "numeric", month: "short", day: "numeric" });
}

function fmtDateTime(d) {
  if (!d) return "—";
  const dt = new Date(d);
  if (isNaN(dt)) return String(d);
  return dt.toLocaleString("uk-UA", { year: "numeric", month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
}

function initials(name) {
  if (!name) return "??";
  return name.split(/\s+/).map((w) => w[0]).slice(0, 2).join("").toUpperCase();
}

/* ---------- Toasts ---------- */
function toast(message, type = "success") {
  let host = document.getElementById("toasts");
  if (!host) {
    host = document.createElement("div");
    host.id = "toasts";
    host.className = "toasts";
    document.body.appendChild(host);
  }
  const el = document.createElement("div");
  el.className = `toast ${type}`;
  el.setAttribute("role", "status");
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateX(16px)"; }, 2600);
  setTimeout(() => el.remove(), 3000);
}

/* ---------- Modal ---------- */
function openModal(title, bodyHtml, footerHtml, { wide = false } = {}) {
  const overlay = document.getElementById("overlay");
  document.getElementById("modal-title").textContent = title;
  document.getElementById("modal-body").innerHTML = bodyHtml;
  document.getElementById("modal-ft").innerHTML = footerHtml || "";
  const modal = overlay.querySelector(".modal");
  if (modal) modal.style.width = wide ? "760px" : "";
  overlay.style.display = "flex";
  document.body.style.overflow = "hidden";
  // Focus first field for keyboard users.
  const first = overlay.querySelector("input, select, textarea, button");
  if (first) setTimeout(() => first.focus(), 30);
}
function closeModal() {
  document.getElementById("overlay").style.display = "none";
  document.body.style.overflow = "";
}

function confirmDialog(title, message, confirmLabel = "Delete") {
  return new Promise((resolve) => {
    openModal(
      title,
      `<p style="font-size:14px;color:var(--tx2)">${esc(message)}</p>`,
      `<button class="btn btn-ghost" id="cf-cancel">Cancel</button>
       <button class="btn btn-danger" id="cf-ok">${esc(confirmLabel)}</button>`
    );
    document.getElementById("cf-cancel").onclick = () => { closeModal(); resolve(false); };
    document.getElementById("cf-ok").onclick = () => { closeModal(); resolve(true); };
  });
}

/* ---------- Badges (English labels) ---------- */
const STATUS_BADGE = { active: ["Active", "bg-grn"], vip: ["VIP", "bg-pur"], potential: ["Potential", "bg-blu"], inactive: ["Inactive", "bg-gry"] };
const STAGE_BADGE = {
  qualification: ["Qualification", "bg-blu"], proposal: ["Proposal", "bg-amb"],
  negotiation: ["Negotiation", "bg-amb"], won: ["Won", "bg-grn"], lost: ["Lost", "bg-red"],
};
const PRIORITY_BADGE = { low: ["Low", "bg-grn"], medium: ["Medium", "bg-amb"], high: ["High", "bg-red"], critical: ["Critical", "bg-red"] };
const TASK_STATUS_BADGE = { todo: ["To do", "bg-gry"], in_progress: ["In progress", "bg-amb"], done: ["Done", "bg-grn"] };
const TICKET_STATUS_BADGE = { open: ["Open", "bg-red"], in_progress: ["In progress", "bg-amb"], closed: ["Closed", "bg-gry"] };
const ROLE_BADGE = { admin: ["Admin", "bg-pur"], manager: ["Manager", "bg-blu"] };

function badge(map, value) {
  const entry = map[value] || [value, "bg-gry"];
  return `<span class="badge ${entry[1]}">${esc(entry[0])}</span>`;
}
const clientStatusBadge = (v) => badge(STATUS_BADGE, v);
const stageBadge = (v) => badge(STAGE_BADGE, v);
const priorityBadge = (v) => badge(PRIORITY_BADGE, v);
const taskStatusBadge = (v) => badge(TASK_STATUS_BADGE, v);
const ticketStatusBadge = (v) => badge(TICKET_STATUS_BADGE, v);
const roleBadge = (v) => badge(ROLE_BADGE, v);

/* ---------- States ---------- */
function loadingState(text = "Loading…") {
  return `<div class="spinner"></div><div class="loading-text">${esc(text)}</div>`;
}
function emptyState(icon, message) {
  return `<div class="empty"><div class="ico">${icon}</div><p>${esc(message)}</p></div>`;
}
function errorState(message) {
  return `<div class="empty"><div class="ico">⚠️</div><p>${esc(message)}</p></div>`;
}

/* ---------- Options helpers ---------- */
function optionsHtml(list, selected, labelFn = (x) => x, valueFn = (x) => x) {
  return list.map((o) => `<option value="${esc(valueFn(o))}" ${String(valueFn(o)) === String(selected ?? "") ? "selected" : ""}>${esc(labelFn(o))}</option>`).join("");
}

function debounce(fn, ms = 300) {
  let t;
  return (...args) => { clearTimeout(t); t = setTimeout(() => fn(...args), ms); };
}

function isOverdue(dueDate) {
  if (!dueDate) return false;
  const today = new Date(); today.setHours(0, 0, 0, 0);
  return new Date(dueDate) < today;
}
