/* Tasks page. */
const TasksPage = (() => {
  const val = (id) => document.getElementById(id).value.trim();
  const num = (id) => { const v = document.getElementById(id).value; return v ? parseInt(v, 10) : null; };

  async function fetchClients() { try { return (await Api.get("/clients", { params: { page_size: 200 } })).items; } catch (e) { return []; } }
  async function fetchUsers() { try { return await Api.get("/users"); } catch (e) { return []; } }

  async function render(host, st) {
    st.filter = st.filter ?? "open";
    host.innerHTML = `
      <div class="sbar">
        <div class="filters" id="tk-filters">
          ${["today", "upcoming", "overdue", "done", "open", ""].map((f) => {
            const labels = { today: "Today", upcoming: "Upcoming", overdue: "Overdue", done: "Completed", open: "Open", "": "All" };
            return `<button class="btn ${st.filter === f ? "btn-primary" : "btn-ghost"} btn-sm" data-filter="${f}">${labels[f]}</button>`;
          }).join("")}
        </div>
        <button class="btn btn-primary" id="tk-add" style="margin-left:auto">+ New task</button>
      </div>
      <div id="tk-body">${loadingState()}</div>`;
    document.getElementById("tk-add").addEventListener("click", () => editModal(host, st));
    document.querySelectorAll("#tk-filters [data-filter]").forEach((b) => b.addEventListener("click", () => { st.filter = b.dataset.filter; render(host, st); }));
    await load(host, st);
  }

  async function load(host, st) {
    const body = document.getElementById("tk-body");
    body.innerHTML = loadingState();
    try {
      const params = { page_size: 100 };
      if (st.filter) params.filter = st.filter;
      const data = await Api.get("/tasks", { params });
      const items = data.items;
      if (!items.length) {
        body.innerHTML = ListKit.emptyCard("Tasks", emptyState("✅", "No tasks here. Add one to get started."), `<button class="btn btn-primary" id="tk-add2">+ New task</button>`);
        document.getElementById("tk-add2").addEventListener("click", () => editModal(host, st));
        return;
      }
      body.innerHTML = `<div class="card"><div class="card-body">${items.map((t) => taskItem(t, host, st)).join("")}</div></div>`;
      body.querySelectorAll("[data-toggle]").forEach((el) => el.addEventListener("click", () => toggle(parseInt(el.dataset.toggle, 10), host, st)));
      body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editModal(host, st, parseInt(b.dataset.edit, 10))));
      body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host, st)));
    } catch (err) { body.innerHTML = errorState(err.message); }
  }

  function taskItem(t, host, st) {
    const done = t.status === "done";
    const overdue = !done && isOverdue(t.due_date);
    return `
    <div class="titem">
      <div class="tchk ${done ? "done" : ""}" data-toggle="${t.id}" role="checkbox" aria-checked="${done}" tabindex="0">${done ? "✓" : ""}</div>
      <div class="ti" style="flex:1">
        <h4 class="${done ? "done" : ""}">${esc(t.title)}</h4>
        <div class="meta">
          ${priorityBadge(t.priority)} ${taskStatusBadge(t.status)}
          ${t.client ? `<span>🏢 ${esc(t.client.name)}</span>` : ""}
          <span style="${overdue ? "color:var(--red)" : ""}">📅 ${fmtDate(t.due_date)}${overdue ? " (overdue)" : ""}</span>
          ${t.assignee ? `<span>👤 ${esc(t.assignee.full_name)}</span>` : ""}
        </div>
      </div>
      <div class="arow"><button class="btn btn-ghost btn-sm" data-edit="${t.id}">Edit</button><button class="btn btn-danger btn-sm" data-del="${t.id}">✕</button></div>
    </div>`;
  }

  async function toggle(id, host, st) {
    try {
      const t = await Api.get(`/tasks/${id}`);
      await Api.patch(`/tasks/${id}`, { status: t.status === "done" ? "todo" : "done" });
      load(host, st);
    } catch (err) { toast(err.message, "error"); }
  }

  async function editModal(host, st, id) {
    let t = null;
    if (id) { try { t = await Api.get(`/tasks/${id}`); } catch (e) { toast(e.message, "error"); return; } }
    const clients = await fetchClients();
    const users = await fetchUsers();
    openModal(id ? "Edit task" : "New task", `
      <div class="fg"><label>Title *</label><input id="t-title" value="${esc(t?.title || "")}" /></div>
      <div class="fg"><label>Description</label><textarea id="t-desc">${esc(t?.description || "")}</textarea></div>
      <div class="form-row">
        <div class="fg"><label>Client</label><select id="t-client"><option value="">—</option>${optionsHtml(clients, t?.client_id || "", (c) => c.name, (c) => c.id)}</select></div>
        <div class="fg"><label>Assignee</label><select id="t-assignee"><option value="">Unassigned</option>${optionsHtml(users, t?.assignee_id || "", (u) => u.full_name, (u) => u.id)}</select></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Priority</label><select id="t-priority">${optionsHtml(["low", "medium", "high", "critical"], t?.priority || "medium", (v) => PRIORITY_BADGE[v]?.[0] || v)}</select></div>
        <div class="fg"><label>Status</label><select id="t-status">${optionsHtml(["todo", "in_progress", "done"], t?.status || "todo", (v) => TASK_STATUS_BADGE[v]?.[0] || v)}</select></div>
      </div>
      <div class="fg"><label>Due date</label><input id="t-due" type="date" value="${t?.due_date || ""}" /></div>
      <div id="t-err"></div>
    `, `<button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="t-save">${id ? "Save changes" : "Create task"}</button>`);
    document.getElementById("t-save").addEventListener("click", () => save(host, st, id));
  }

  async function save(host, st, id) {
    const body = {
      title: val("t-title"), description: val("t-desc") || null, client_id: num("t-client"),
      assignee_id: num("t-assignee"), priority: val("t-priority"), status: val("t-status"),
      due_date: val("t-due") || null,
    };
    try {
      if (id) await Api.patch(`/tasks/${id}`, body); else await Api.post("/tasks", body);
      closeModal(); toast(id ? "Task updated" : "Task created");
      load(host, st);
    } catch (err) { document.getElementById("t-err").innerHTML = `<div class="login-error">${esc(err.message)}</div>`; }
  }

  async function remove(id, host, st) {
    const ok = await confirmDialog("Delete task", "This task will be permanently removed.", "Delete");
    if (!ok) return;
    try { await Api.del(`/tasks/${id}`); toast("Task deleted"); load(host, st); }
    catch (err) { toast(err.message, "error"); }
  }

  return { render };
})();
