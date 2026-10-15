/* Support tickets page. */
const SupportPage = (() => {
  const val = (id) => document.getElementById(id).value.trim();
  const num = (id) => { const v = document.getElementById(id).value; return v ? parseInt(v, 10) : null; };

  async function fetchClients() { try { return (await Api.get("/clients", { params: { page_size: 200 } })).items; } catch (e) { return []; } }
  async function fetchUsers() { try { return await Api.get("/users"); } catch (e) { return []; } }

  async function render(host, st) {
    st.status = st.status ?? "";
    host.innerHTML = `
      <div class="sbar">
        <div class="filters">
          <select id="sp-status"><option value="">All statuses</option>
            ${optionsHtml(["open", "in_progress", "closed"], st.status, (v) => TICKET_STATUS_BADGE[v]?.[0] || v)}</select>
        </div>
        <button class="btn btn-primary" id="sp-add" style="margin-left:auto">+ New ticket</button>
      </div>
      <div id="sp-body">${loadingState()}</div>`;
    document.getElementById("sp-add").addEventListener("click", () => editModal(host, st));
    document.getElementById("sp-status").addEventListener("change", (e) => { st.status = e.target.value; load(host, st); });
    await load(host, st);
  }

  async function load(host, st) {
    const body = document.getElementById("sp-body");
    body.innerHTML = loadingState();
    try {
      const params = { page_size: 100 };
      if (st.status) params.status = st.status;
      const data = await Api.get("/tickets", { params });
      const items = data.items;
      if (!items.length) {
        body.innerHTML = ListKit.emptyCard("Support tickets", emptyState("🎫", "No tickets. All clear!"), `<button class="btn btn-primary" id="sp-add2">+ New ticket</button>`);
        document.getElementById("sp-add2").addEventListener("click", () => editModal(host, st));
        return;
      }
      const rows = items.map((t) => `
        <tr>
          <td class="bold-tx">${esc(t.title)}</td>
          <td>${esc(t.client?.name || "—")}</td>
          <td>${priorityBadge(t.priority)}</td>
          <td>${esc(t.assignee?.full_name || "—")}</td>
          <td><select class="select-inline" data-status="${t.id}">${optionsHtml(["open", "in_progress", "closed"], t.status, (v) => TICKET_STATUS_BADGE[v]?.[0] || v)}</select></td>
          <td class="sm-tx">${fmtDate(t.created_at)}</td>
          <td><div class="arow"><button class="btn btn-ghost btn-sm" data-view="${t.id}">Open</button><button class="btn btn-danger btn-sm" data-del="${t.id}">✕</button></div></td>
        </tr>`).join("");
      body.innerHTML = `<div class="card"><div class="table-wrap"><table>
        <thead><tr><th>Ticket</th><th>Client</th><th>Priority</th><th>Assignee</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
        <tbody>${rows}</tbody></table></div></div>`;
      body.querySelectorAll("[data-status]").forEach((sel) => sel.addEventListener("change", (e) => changeStatus(parseInt(sel.dataset.status, 10), e.target.value, host, st)));
      body.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => view(parseInt(b.dataset.view, 10), host, st)));
      body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host, st)));
    } catch (err) { body.innerHTML = errorState(err.message); }
  }

  async function changeStatus(id, status, host, st) {
    try { await Api.put(`/tickets/${id}/status`, { status }); toast("Status updated"); load(host, st); }
    catch (err) { toast(err.message, "error"); load(host, st); }
  }

  async function view(id, host, st) {
    try {
      const t = await Api.get(`/tickets/${id}`);
      const canReply = t.status !== "closed";
      openModal(t.title, `
        <div class="detail-grid" style="margin-bottom:14px">
          <div class="detail-row"><span class="k">Client</span><span class="v">${esc(t.client?.name || "—")}</span></div>
          <div class="detail-row"><span class="k">Status</span><span class="v">${ticketStatusBadge(t.status)}</span></div>
          <div class="detail-row"><span class="k">Priority</span><span class="v">${priorityBadge(t.priority)}</span></div>
          <div class="detail-row"><span class="k">Assignee</span><span class="v">${esc(t.assignee?.full_name || "—")}</span></div>
        </div>
        ${t.description ? `<div class="fg"><label>Description</label><div style="font-size:13px;color:var(--tx2)">${esc(t.description)}</div></div>` : ""}
        <div class="fg"><label>Conversation</label>
          <div class="messages" id="sp-msgs">
            ${t.messages.length ? t.messages.map((m) => `<div class="msg"><div class="m-body">${esc(m.body)}</div><div class="m-meta">${esc(m.author?.full_name || "System")} · ${fmtDateTime(m.created_at)}</div></div>`).join("") : `<div class="sm-tx">No messages yet.</div>`}
          </div>
          ${canReply ? `<div class="form-row"><div class="fg" style="flex:2;margin:0"><input id="sp-reply" placeholder="Type a reply…" /></div><button class="btn btn-primary" id="sp-send" style="align-self:flex-end">Send</button></div>` : `<div class="sm-tx">This ticket is closed. Reopen it to reply.</div>`}
        </div>
      `, `<button class="btn btn-ghost" onclick="closeModal()">Close</button>`);
      if (canReply) document.getElementById("sp-send").addEventListener("click", () => reply(id, host, st));
    } catch (err) { toast(err.message, "error"); }
  }

  async function reply(id, host, st) {
    const body = val("sp-reply");
    if (!body) return;
    try { await Api.post(`/tickets/${id}/messages`, { body }); view(id, host, st); }
    catch (err) { toast(err.message, "error"); }
  }

  async function editModal(host, st) {
    const clients = await fetchClients();
    const users = await fetchUsers();
    openModal("New ticket", `
      <div class="fg"><label>Title *</label><input id="sp-title" placeholder="Brief summary" /></div>
      <div class="fg"><label>Description</label><textarea id="sp-desc" placeholder="Details of the issue…"></textarea></div>
      <div class="form-row">
        <div class="fg"><label>Client</label><select id="sp-client"><option value="">—</option>${optionsHtml(clients, "", (c) => c.name, (c) => c.id)}</select></div>
        <div class="fg"><label>Priority</label><select id="sp-priority">${optionsHtml(["low", "medium", "high", "critical"], "medium", (v) => PRIORITY_BADGE[v]?.[0] || v)}</select></div>
      </div>
      <div class="fg"><label>Assignee</label><select id="sp-assignee"><option value="">Unassigned</option>${optionsHtml(users, "", (u) => u.full_name, (u) => u.id)}</select></div>
      <div id="sp-err"></div>
    `, `<button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="sp-save">Create ticket</button>`);
    document.getElementById("sp-save").addEventListener("click", () => save(host, st));
  }

  async function save(host, st) {
    const body = { title: val("sp-title"), description: val("sp-desc") || null, client_id: num("sp-client"), priority: val("sp-priority"), assignee_id: num("sp-assignee") };
    try { await Api.post("/tickets", body); closeModal(); toast("Ticket created"); load(host, st); }
    catch (err) { document.getElementById("sp-err").innerHTML = `<div class="login-error">${esc(err.message)}</div>`; }
  }

  async function remove(id, host, st) {
    const ok = await confirmDialog("Delete ticket", "This ticket and its messages will be removed.", "Delete");
    if (!ok) return;
    try { await Api.del(`/tickets/${id}`); toast("Ticket deleted"); load(host, st); }
    catch (err) { toast(err.message, "error"); }
  }

  return { render };
})();
