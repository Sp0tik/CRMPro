/* Dashboard page — real KPIs from the analytics API. */
const DashboardPage = (() => {
  async function render(host, st) {
    host.innerHTML = loadingState("Loading dashboard…");
    try {
      const d = await Api.get("/analytics/dashboard");
      const meta = document.getElementById("topbar-meta");
      if (meta) meta.textContent = `${d.clients_total} clients · ${d.deals_active} active deals`;

      const stat = (cls, lbl, val, sub, subCls = "") =>
        `<div class="stat ${cls}"><div class="lbl">${esc(lbl)}</div><div class="val" style="font-size:22px">${val}</div><div class="sub ${subCls}">${sub}</div></div>`;

      const maxStage = Math.max(1, ...d.recent_deals.map((x) => x.amount));
      const funnel = ["Won revenue", "Open pipeline"].map((label, i) => {
        const v = i === 0 ? d.won_revenue : d.open_revenue;
        const col = i === 0 ? "var(--grn)" : "var(--acc)";
        return `<div class="cbar-row"><div class="cbar-lbl">${label}</div><div class="cbar-tr"><div class="cbar-fl" style="width:${Math.min(100, (v / (d.won_revenue + d.open_revenue || 1)) * 100)}%;background:${col}"></div></div><div class="cbar-v" style="color:${col}">${fmtMoney(v)}</div></div>`;
      }).join("");

      const recentDeals = d.recent_deals.length ? d.recent_deals.map((x) =>
        `<tr><td><div class="bold-tx">${esc(x.title)}</div><div class="sm-tx">${esc(x.client || "")}</div></td><td class="acc-tx">${fmtMoney(x.amount)}</td><td>${stageBadge(x.stage)}</td></tr>`).join("")
        : `<tr><td colspan="3">${emptyState("💼", "No deals yet.")}</td></tr>`;

      const taskList = d.upcoming_tasks.length ? d.upcoming_tasks.map((t) =>
        `<div class="titem"><div class="tchk"></div><div class="ti" style="flex:1"><h4>${esc(t.title)}</h4><div class="meta">${priorityBadge(t.priority)}<span>📅 ${fmtDate(t.due_date)}</span>${t.assignee ? `<span>👤 ${esc(t.assignee)}</span>` : ""}</div></div></div>`).join("")
        : `<div style="padding:12px" class="sm-tx">No upcoming tasks.</div>`;

      const activityList = d.recent_activities.length ? `<div class="timeline">${d.recent_activities.map((a) =>
        `<div class="timeline-item"><div class="t-msg">${esc(a.message)}</div><div class="t-meta">${esc(a.actor || "System")} · ${fmtDateTime(a.created_at)}</div></div>`).join("")}</div>`
        : emptyState("🕘", "No recent activity.");

      host.innerHTML = `
        <div class="stats-grid">
          ${stat("s-acc", "Clients", fmtNum(d.clients_total), `${d.clients_active} active`)}
          ${stat("s-grn", "Won revenue", fmtMoney(d.won_revenue), `${d.deals_won} deals won`, "up")}
          ${stat("s-amb", "Open pipeline", fmtMoney(d.open_revenue), `${d.deals_active} active deals`)}
          ${stat("s-pur", "Open tickets", fmtNum(d.tickets_open), `${d.tasks_open} open tasks`)}
        </div>
        <div class="g2">
          <div class="card"><div class="card-hd"><div class="card-title">Revenue overview</div></div><div class="card-body">
            <div style="margin-bottom:14px"><span class="sm-tx">Win rate</span> <strong style="color:var(--tx)">${d.win_rate}%</strong> · <span class="sm-tx">Avg deal</span> <strong style="color:var(--tx)">${fmtMoney(d.avg_deal_size)}</strong> · <span class="sm-tx">Weighted</span> <strong style="color:var(--tx)">${fmtMoney(d.weighted_pipeline)}</strong></div>
            ${funnel}
          </div></div>
          <div class="card"><div class="card-hd"><div class="card-title">Upcoming tasks</div></div><div class="card-body">${taskList}</div></div>
        </div>
        <div class="g2">
          <div class="card"><div class="card-hd"><div class="card-title">Recent deals</div></div>
            <div class="table-wrap"><table><thead><tr><th>Deal</th><th>Amount</th><th>Stage</th></tr></thead><tbody>${recentDeals}</tbody></table></div></div>
          <div class="card"><div class="card-hd"><div class="card-title">Recent activity</div></div><div class="card-body">${activityList}</div></div>
        </div>`;
    } catch (err) {
      host.innerHTML = errorState(err.message);
    }
  }

  return { render };
})();
