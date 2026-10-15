/* Deals page: Kanban pipeline + table. */
const DealsPage = (() => {
  const PAGE_SIZE = 12;
  const STAGES = ["qualification", "proposal", "negotiation", "won", "lost"];
  const val = (id) => document.getElementById(id).value.trim();
  const num = (id) => { const v = document.getElementById(id).value; return v ? parseInt(v, 10) : null; };

  async function fetchClients() { try { return (await Api.get("/clients", { params: { page_size: 200 } })).items; } catch (e) { return []; } }
  async function fetchUsers() { try { return await Api.get("/users"); } catch (e) { return []; } }

  async function render(host, st) {
    st.view = st.view ?? "board";
    host.innerHTML = `
      <div class="sbar">
        <input class="sinput" id="dl-q" placeholder="🔍 Search deals…" value="${esc(st.q || "")}" />
        <div class="filters">
          <select id="dl-view">
            <option value="board" ${st.view === "board" ? "selected" : ""}>Kanban board</option>
            <option value="table" ${st.view === "table" ? "selected" : ""}>Table</option>
          </select>
        </div>
        <button class="btn btn-primary" id="dl-add">+ New deal</button>
      </div>
      <div id="dl-body">${loadingState()}</div>`;
    document.getElementById("dl-add").addEventListener("click", () => editModal(host, st));
    document.getElementById("dl-view").addEventListener("change", (e) => { st.view = e.target.value; render(host, st); });
    document.getElementById("dl-q").addEventListener("input", debounce(() => { st.q = val("dl-q"); load(host, st); }));
    await load(host, st);
  }

  async function load(host, st) {
    const body = document.getElementById("dl-body");
    body.innerHTML = loadingState();
    try {
      // Fetch a large page for the board; use server search when provided.
      const params = { page_size: 200 };
      if (st.q) params.q = st.q;
      const data = await Api.get("/deals", { params });
      if (st.view === "board") renderBoard(body, data.items, host, st);
      else renderTable(body, data.items, host, st);
    } catch (err) { body.innerHTML = errorState(err.message); }
  }

  function renderBoard(body, deals, host, st) {
    if (!deals.length) {
      body.innerHTML = ListKit.emptyCard("Pipeline", emptyState("💼", st.q ? "No deals match your search." : "No deals yet. Create your first deal."), `<button class="btn btn-primary" onclick="DealsPage.refresh()">+ New deal</button>`);
      return;
    }
    const cols = STAGES.map((stage) => {
      const items = deals.filter((d) => d.stage === stage);
      const cards = items.map((d) => `
        <div class="pcard">
          <h4>${esc(d.title)}</h4>
          <div class="pc">🏢 ${esc(d.client?.name || "—")}</div>
          <div style="display:flex;justify-content:space-between;align-items:center">
            <div class="pa">${fmtMoney(d.amount, d.currency)}</div><span class="sm-tx">${d.probability}%</span>
          </div>
          <div class="pbar"><div class="pbar-f" style="width:${d.probability}%"></div></div>
          <div class="sm-tx" style="margin-top:6px">👤 ${esc(d.manager?.full_name || "—")}${d.deadline ? ` · 📅 ${fmtDate(d.deadline)}` : ""}</div>
          <div class="pcard-actions">
            <select class="select-inline" data-stage="${d.id}">
              ${optionsHtml(STAGES, d.stage, (s) => STAGE_BADGE[s]?.[0] || s)}
            </select>
            <button class="btn btn-ghost btn-sm" data-edit="${d.id}">Edit</button>
            <button class="btn btn-danger btn-sm" data-del="${d.id}">✕</button>
          </div>
        </div>`).join("");
      return `<div class="pipe-col"><div class="pipe-col-hd">${esc(STAGE_BADGE[stage]?.[0] || stage)}<span>${items.length}</span></div>${cards || `<div class="sm-tx" style="text-align:center;padding:12px">Drop deals here</div>`}</div>`;
    }).join("");
    body.innerHTML = `<div class="pipeline">${cols}</div>`;
    body.querySelectorAll("[data-stage]").forEach((sel) => sel.addEventListener("change", (e) => changeStage(parseInt(sel.dataset.stage, 10), e.target.value, host, st)));
    body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editModal(host, st, parseInt(b.dataset.edit, 10))));
    body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host, st)));
  }

  function renderTable(body, deals, host, st) {
    if (!deals.length) { body.innerHTML = ListKit.emptyCard("Deals", emptyState("💼", "No deals yet.")); return; }
    const rows = deals.map((d) => `
      <tr>
        <td class="bold-tx">${esc(d.title)}</td>
        <td>${esc(d.client?.name || "—")}</td>
        <td class="acc-tx">${fmtMoney(d.amount, d.currency)}</td>
        <td>${stageBadge(d.stage)}</td>
        <td>${esc(d.manager?.full_name || "—")}</td>
        <td class="sm-tx">${fmtDate(d.deadline)}</td>
        <td><div class="arow"><button class="btn btn-ghost btn-sm" data-edit="${d.id}">Edit</button><button class="btn btn-danger btn-sm" data-del="${d.id}">✕</button></div></td>
      </tr>`).join("");
    body.innerHTML = `<div class="card"><div class="table-wrap"><table>
      <thead><tr><th>Deal</th><th>Client</th><th>Amount</th><th>Stage</th><th>Manager</th><th>Deadline</th><th>Actions</th></tr></thead>
      <tbody>${rows}</tbody></table></div></div>`;
    body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editModal(host, st, parseInt(b.dataset.edit, 10))));
    body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host, st)));
  }

  async function changeStage(id, stage, host, st) {
    try {
      const body = { stage };
      if (stage === "lost") body.loss_reason = prompt("Reason for loss (optional):") || null;
      await Api.put(`/deals/${id}/stage`, body);
      toast("Deal stage updated");
      load(host, st);
    } catch (err) { toast(err.message, "error"); load(host, st); }
  }

  async function editModal(host, st, id) {
    let d = null;
    if (id) { try { d = await Api.get(`/deals/${id}`); } catch (e) { toast(e.message, "error"); return; } }
    const clients = await fetchClients();
    const users = await fetchUsers();
    if (!clients.length) { toast("Create a client first before adding a deal.", "info"); return; }
    openModal(id ? "Edit deal" : "New deal", `
      <div class="fg"><label>Title *</label><input id="d-title" value="${esc(d?.title || "")}" /></div>
      <div class="form-row">
        <div class="fg"><label>Client *</label><select id="d-client">${optionsHtml(clients, d?.client_id || "", (c) => c.name, (c) => c.id)}</select></div>
        <div class="fg"><label>Manager</label><select id="d-manager"><option value="">Unassigned</option>${optionsHtml(users, d?.manager_id || "", (u) => u.full_name, (u) => u.id)}</select></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Amount *</label><input id="d-amount" type="number" min="0" step="0.01" value="${d?.amount ?? ""}" /></div>
        <div class="fg"><label>Stage</label><select id="d-stage">${optionsHtml(STAGES, d?.stage || "qualification", (s) => STAGE_BADGE[s]?.[0] || s)}</select></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Probability (%)</label><input id="d-prob" type="number" min="0" max="100" value="${d?.probability ?? 30}" /></div>
        <div class="fg"><label>Deadline</label><input id="d-deadline" type="date" value="${d?.deadline || ""}" /></div>
      </div>
      <div class="fg"><label>Source</label><input id="d-source" value="${esc(d?.source || "")}" /></div>
      <div id="d-err"></div>
    `, `<button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="d-save">${id ? "Save changes" : "Create deal"}</button>`);
    document.getElementById("d-save").addEventListener("click", () => save(host, st, id));
  }

  async function save(host, st, id) {
    const body = {
      title: val("d-title"), client_id: num("d-client"), manager_id: num("d-manager"),
      amount: parseFloat(val("d-amount") || "0"), stage: val("d-stage"),
      probability: parseInt(val("d-prob") || "30", 10), deadline: val("d-deadline") || null,
      source: val("d-source") || null,
    };
    try {
      if (id) await Api.patch(`/deals/${id}`, body); else await Api.post("/deals", body);
      closeModal(); toast(id ? "Deal updated" : "Deal created");
      load(host, st);
    } catch (err) { document.getElementById("d-err").innerHTML = `<div class="login-error">${esc(err.message)}</div>`; }
  }

  async function remove(id, host, st) {
    const ok = await confirmDialog("Delete deal", "This deal will be permanently removed.", "Delete");
    if (!ok) return;
    try { await Api.del(`/deals/${id}`); toast("Deal deleted"); load(host, st); }
    catch (err) { toast(err.message, "error"); }
  }

  return { render, refresh() { App.navigate("deals"); } };
})();
