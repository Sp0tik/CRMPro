/* Analytics & reports page. */
const AnalyticsPage = (() => {
  async function render(host, st) {
    st.dateFrom = st.dateFrom ?? "";
    st.dateTo = st.dateTo ?? "";
    host.innerHTML = `
      <div class="sbar">
        <div class="filters">
          <input type="date" id="an-from" value="${esc(st.dateFrom)}" title="From" />
          <input type="date" id="an-to" value="${esc(st.dateTo)}" title="To" />
          <button class="btn btn-ghost btn-sm" id="an-apply">Apply</button>
          <button class="btn btn-ghost btn-sm" id="an-reset">Reset</button>
        </div>
        <button class="btn btn-primary" id="an-export" style="margin-left:auto">⬇ Export CSV</button>
      </div>
      <div id="an-body">${loadingState("Crunching numbers…")}</div>`;
    document.getElementById("an-apply").addEventListener("click", () => { st.dateFrom = document.getElementById("an-from").value; st.dateTo = document.getElementById("an-to").value; load(host, st); });
    document.getElementById("an-reset").addEventListener("click", () => { st.dateFrom = ""; st.dateTo = ""; render(host, st); });
    document.getElementById("an-export").addEventListener("click", () => exportCsv(st));
    await load(host, st);
  }

  async function exportCsv(st) {
    const params = {};
    if (st.dateFrom) params.date_from = st.dateFrom;
    if (st.dateTo) params.date_to = st.dateTo;
    const qs = new URLSearchParams(params).toString();
    const token = Api.getToken();
    const url = `${(window.CRM_API_BASE || "")}/api/v1/analytics/export.csv?${qs}`;
    const resp = await fetch(url, { headers: { Authorization: `Bearer ${token}` } });
    if (!resp.ok) { toast("Export failed", "error"); return; }
    const blob = await resp.blob();
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = "crmpro_report.csv";
    a.click();
    URL.revokeObjectURL(a.href);
    toast("Report exported");
  }

  async function load(host, st) {
    const body = document.getElementById("an-body");
    body.innerHTML = loadingState();
    try {
      const params = {};
      if (st.dateFrom) params.date_from = st.dateFrom;
      if (st.dateTo) params.date_to = st.dateTo;
      const r = await Api.get("/analytics/report", { params });

      const kpiCards = r.kpis.map((k) =>
        `<div class="stat s-acc"><div class="lbl">${esc(k.label)}</div><div class="val" style="font-size:22px">${esc(k.display)}</div>${k.hint ? `<div class="sub">${esc(k.hint)}</div>` : ""}</div>`).join("");

      const stageRows = r.stages.filter((s) => s.count > 0 || s.amount > 0).map((s) => {
        const col = s.stage === "won" ? "var(--grn)" : s.stage === "lost" ? "var(--red)" : "var(--acc)";
        return `<div class="cbar-row"><div class="cbar-lbl">${esc(STAGE_BADGE[s.stage]?.[0] || s.stage)}</div><div class="cbar-tr"><div class="cbar-fl" style="width:${s.share}%;background:${col}"></div></div><div class="cbar-v">${fmtMoney(s.amount)}</div></div>`;
      }).join("") || `<div class="sm-tx">No deal data in this period.</div>`;

      const trendRows = r.trend.length ? r.trend.slice(-12).map((t) => {
        const maxWon = Math.max(1, ...r.trend.map((x) => x.won_amount));
        return `<div class="cbar-row"><div class="cbar-lbl">${esc(t.period)}</div><div class="cbar-tr"><div class="cbar-fl" style="width:${(t.won_amount / maxWon) * 100}%;background:var(--grn)"></div></div><div class="cbar-v">${fmtMoney(t.won_amount)}</div></div>`;
      }).join("") : `<div class="sm-tx">No trend data yet.</div>`;

      const mgrRows = r.managers.length ? r.managers.map((m) => `
        <tr><td class="bold-tx">${esc(m.manager_name)}</td><td>${m.deals_total}</td><td>${m.deals_won}</td><td>${m.deals_lost}</td><td class="acc-tx">${fmtMoney(m.won_amount)}</td><td>${m.conversion}%</td></tr>`).join("")
        : `<tr><td colspan="6">${emptyState("👤", "No managers found.")}</td></tr>`;

      const period = r.period.date_from || r.period.date_to
        ? `${r.period.date_from || "…"} → ${r.period.date_to || "…"}` : "All time";

      body.innerHTML = `
        <div class="stats-grid">${kpiCards}</div>
        <div class="g2">
          <div class="card"><div class="card-hd"><div class="card-title">Revenue by stage</div></div><div class="card-body">${stageRows}</div></div>
          <div class="card"><div class="card-hd"><div class="card-title">Won revenue trend (monthly)</div></div><div class="card-body">${trendRows}</div></div>
        </div>
        <div class="card"><div class="card-hd"><div class="card-title">Manager performance · ${esc(period)}</div></div>
          <div class="table-wrap"><table><thead><tr><th>Manager</th><th>Deals</th><th>Won</th><th>Lost</th><th>Won revenue</th><th>Conversion</th></tr></thead><tbody>${mgrRows}</tbody></table></div></div>`;
    } catch (err) { body.innerHTML = errorState(err.message); }
  }

  return { render };
})();
