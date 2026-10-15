/* Clients page. */
const ClientsPage = (() => {
  const PAGE_SIZE = 12;
  const val = (id) => document.getElementById(id).value.trim();
  const num = (id) => { const v = document.getElementById(id).value; return v ? parseInt(v, 10) : null; };

  async function fetchUsers() {
    try { return await Api.get("/users"); } catch (e) { return []; }
  }

  async function render(host, st) {
    st.q = st.q ?? ""; st.status = st.status ?? ""; st.page = st.page ?? 1;
    host.innerHTML = `
      <div class="sbar">
        <input class="sinput" id="cl-q" placeholder="🔍 Search by name, email, company…" value="${esc(st.q)}" />
        <div class="filters">
          <select id="cl-status"><option value="">All statuses</option>
            ${optionsHtml(["active", "potential", "vip", "inactive"], st.status, (v) => STATUS_BADGE[v]?.[0] || v)}</select>
        </div>
        <button class="btn btn-primary" id="cl-add">+ New client</button>
      </div>
      <div id="cl-list">${loadingState()}</div>`;

    document.getElementById("cl-add").addEventListener("click", () => editModal(host, st));
    document.getElementById("cl-q").addEventListener("input", debounce(() => { st.q = val("cl-q"); st.page = 1; loadList(host, st); }));
    document.getElementById("cl-status").addEventListener("change", (e) => { st.status = e.target.value; st.page = 1; loadList(host, st); });
    await loadList(host, st);
  }

  async function loadList(host, st) {
    const listHost = document.getElementById("cl-list");
    listHost.innerHTML = loadingState();
    try {
      const data = await Api.get("/clients", { params: { q: st.q, status: st.status, page: st.page, page_size: PAGE_SIZE } });
      const items = data.items;
      if (!items.length) {
        listHost.innerHTML = ListKit.emptyCard("Clients",
          emptyState("👥", st.q || st.status ? "No clients match your filters." : "No clients yet. Create your first client."),
          `<button class="btn btn-primary" id="cl-add2">+ New client</button>`);
        document.getElementById("cl-add2").addEventListener("click", () => editModal(host, st));
        return;
      }
      const rows = items.map((c) => `
        <tr>
          <td><div class="bold-tx">${esc(c.name)}</div><div class="sm-tx">${esc(c.company || "")}</div></td>
          <td><div>${esc(c.email)}</div><div class="sm-tx">${esc(c.phone || "")}</div></td>
          <td>${esc(c.manager?.full_name || "—")}</td>
          <td>${clientStatusBadge(c.status)}</td>
          <td>${esc(c.segment || "—")}</td>
          <td><div class="arow">
            <button class="btn btn-ghost btn-sm" data-view="${c.id}">View</button>
            <button class="btn btn-ghost btn-sm" data-edit="${c.id}">Edit</button>
            <button class="btn btn-danger btn-sm" data-del="${c.id}">✕</button>
          </div></td>
        </tr>`).join("");
      listHost.innerHTML = `
        <div class="card">
          <div class="table-wrap"><table>
            <thead><tr><th>Client</th><th>Contact</th><th>Manager</th><th>Status</th><th>Segment</th><th>Actions</th></tr></thead>
            <tbody>${rows}</tbody>
          </table></div>
          ${ListKit.pager({ page: data.page, pages: data.pages, total: data.total })}
        </div>`;
      ListKit.bindPager(listHost, st, () => loadList(host, st));
      listHost.querySelectorAll("[data-view]").forEach((b) => b.addEventListener("click", () => view(parseInt(b.dataset.view, 10))));
      listHost.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editModal(host, st, parseInt(b.dataset.edit, 10))));
      listHost.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host, st)));
    } catch (err) {
      listHost.innerHTML = errorState(err.message);
    }
  }

  async function view(id) {
    try {
      const c = await Api.get(`/clients/${id}`);
      const row = (k, v) => `<div class="detail-row"><span class="k">${esc(k)}</span><span class="v">${v}</span></div>`;
      openModal(c.name, `
        <div class="detail-grid">
          ${row("Company", esc(c.company || "—"))}
          ${row("Email", esc(c.email))}
          ${row("Phone", esc(c.phone || "—"))}
          ${row("Status", clientStatusBadge(c.status))}
          ${row("Segment", esc(c.segment || "—"))}
          ${row("Source", esc(c.source || "—"))}
          ${row("Manager", esc(c.manager?.full_name || "—"))}
          ${row("Created", esc(fmtDate(c.created_at)))}
        </div>
        ${c.notes ? `<div class="fg" style="margin-top:12px"><label>Notes</label><div style="font-size:13px;color:var(--tx2)">${esc(c.notes)}</div></div>` : ""}
      `, `<button class="btn btn-ghost" onclick="closeModal()">Close</button>`);
    } catch (err) { toast(err.message, "error"); }
  }

  async function editModal(host, st, id) {
    let c = null;
    if (id) { try { c = await Api.get(`/clients/${id}`); } catch (e) { toast(e.message, "error"); return; } }
    const users = await fetchUsers();
    openModal(id ? "Edit client" : "New client", `
      <div class="form-row">
        <div class="fg"><label>Name *</label><input id="f-name" value="${esc(c?.name || "")}" /></div>
        <div class="fg"><label>Company</label><input id="f-company" value="${esc(c?.company || "")}" /></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Email *</label><input id="f-email" type="email" value="${esc(c?.email || "")}" /></div>
        <div class="fg"><label>Phone</label><input id="f-phone" value="${esc(c?.phone || "")}" /></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Status</label><select id="f-status">${optionsHtml(["active", "potential", "vip", "inactive"], c?.status || "potential", (v) => STATUS_BADGE[v]?.[0] || v)}</select></div>
        <div class="fg"><label>Segment</label><select id="f-segment"><option value="">—</option>${optionsHtml(["enterprise", "smb", "startup"], c?.segment || "")}</select></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Source</label><input id="f-source" value="${esc(c?.source || "")}" placeholder="referral, website…" /></div>
        <div class="fg"><label>Manager</label><select id="f-manager"><option value="">Unassigned</option>${optionsHtml(users, c?.manager_id || "", (u) => u.full_name, (u) => u.id)}</select></div>
      </div>
      <div class="fg"><label>Notes</label><textarea id="f-notes">${esc(c?.notes || "")}</textarea></div>
      <div id="f-err"></div>
    `, `<button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="f-save">${id ? "Save changes" : "Create client"}</button>`);
    document.getElementById("f-save").addEventListener("click", () => save(host, st, id));
  }

  async function save(host, st, id) {
    const body = {
      name: val("f-name"), company: val("f-company") || null, email: val("f-email"),
      phone: val("f-phone") || null, status: val("f-status"), segment: val("f-segment") || null,
      source: val("f-source") || null, manager_id: num("f-manager"), notes: val("f-notes") || null,
    };
    try {
      if (id) await Api.patch(`/clients/${id}`, body); else await Api.post("/clients", body);
      closeModal(); toast(id ? "Client updated" : "Client created");
      loadList(host, st);
    } catch (err) {
      document.getElementById("f-err").innerHTML = `<div class="login-error">${esc(err.message)}</div>`;
    }
  }

  async function remove(id, host, st) {
    const ok = await confirmDialog("Delete client", "This also removes the client's deals, tasks, tickets and activity. This cannot be undone.", "Delete");
    if (!ok) return;
    try { await Api.del(`/clients/${id}`); toast("Client deleted"); loadList(host, st); }
    catch (err) { toast(err.message, "error"); }
  }

  return { render };
})();
