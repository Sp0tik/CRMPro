/* Users management (admin). */
const UsersPage = (() => {
  const val = (id) => document.getElementById(id).value.trim();

  async function render(host, st) {
    host.innerHTML = `
      <div class="sbar"><span class="card-title">Team members</span>
        <button class="btn btn-primary" id="us-add" style="margin-left:auto">+ New user</button></div>
      <div id="us-body">${loadingState()}</div>`;
    document.getElementById("us-add").addEventListener("click", () => editModal(host));
    await load(host);
  }

  async function load(host) {
    const body = document.getElementById("us-body");
    body.innerHTML = loadingState();
    try {
      const users = await Api.get("/users");
      if (!users.length) { body.innerHTML = ListKit.emptyCard("Users", emptyState("🛡️", "No users.")); return; }
      const rows = users.map((u) => `
        <tr>
          <td><div class="bold-tx">${esc(u.full_name)}</div><div class="sm-tx">${esc(u.email)}</div></td>
          <td>${roleBadge(u.role)}</td>
          <td>${u.is_active ? `<span class="badge bg-grn">Active</span>` : `<span class="badge bg-gry">Disabled</span>`}</td>
          <td class="sm-tx">${fmtDate(u.created_at)}</td>
          <td><div class="arow"><button class="btn btn-ghost btn-sm" data-edit="${u.id}">Edit</button><button class="btn btn-danger btn-sm" data-del="${u.id}">✕</button></div></td>
        </tr>`).join("");
      body.innerHTML = `<div class="card"><div class="table-wrap"><table>
        <thead><tr><th>User</th><th>Role</th><th>Status</th><th>Created</th><th>Actions</th></tr></thead>
        <tbody>${rows}</tbody></table></div></div>`;
      body.querySelectorAll("[data-edit]").forEach((b) => b.addEventListener("click", () => editModal(host, parseInt(b.dataset.edit, 10))));
      body.querySelectorAll("[data-del]").forEach((b) => b.addEventListener("click", () => remove(parseInt(b.dataset.del, 10), host)));
    } catch (err) { body.innerHTML = errorState(err.message); }
  }

  async function editModal(host, id) {
    let u = null;
    if (id) { try { u = await Api.get(`/users/${id}`); } catch (e) { const list = await Api.get("/users"); u = list.find((x) => x.id === id); } }
    openModal(id ? "Edit user" : "New user", `
      <div class="form-row">
        <div class="fg"><label>Full name *</label><input id="u-name" value="${esc(u?.full_name || "")}" /></div>
        <div class="fg"><label>Email *</label><input id="u-email" type="email" value="${esc(u?.email || "")}" /></div>
      </div>
      <div class="form-row">
        <div class="fg"><label>Role</label><select id="u-role">${optionsHtml(["manager", "admin"], u?.role || "manager", (v) => ROLE_BADGE[v]?.[0] || v)}</select></div>
        <div class="fg"><label>${id ? "New password (optional)" : "Password *"}</label><input id="u-pass" type="password" placeholder="${id ? "Leave blank to keep" : "Min. 8 characters"}" /></div>
      </div>
      ${id ? `<div class="fg"><label>Status</label><select id="u-active"><option value="true" ${u?.is_active ? "selected" : ""}>Active</option><option value="false" ${!u?.is_active ? "selected" : ""}>Disabled</option></select></div>` : ""}
      <div id="u-err"></div>
    `, `<button class="btn btn-ghost" onclick="closeModal()">Cancel</button>
        <button class="btn btn-primary" id="u-save">${id ? "Save changes" : "Create user"}</button>`);
    document.getElementById("u-save").addEventListener("click", () => save(host, id));
  }

  async function save(host, id) {
    const body = { full_name: val("u-name"), email: val("u-email"), role: document.getElementById("u-role").value };
    const pass = document.getElementById("u-pass").value;
    if (pass) body.password = pass;
    if (id) { const a = document.getElementById("u-active"); if (a) body.is_active = a.value === "true"; }
    try {
      if (id) await Api.patch(`/users/${id}`, body); else await Api.post("/users", body);
      closeModal(); toast(id ? "User updated" : "User created");
      load(host);
    } catch (err) { document.getElementById("u-err").innerHTML = `<div class="login-error">${esc(err.message)}</div>`; }
  }

  async function remove(id, host) {
    const ok = await confirmDialog("Delete user", "The user will be permanently removed.", "Delete");
    if (!ok) return;
    try { await Api.del(`/users/${id}`); toast("User deleted"); load(host); }
    catch (err) { toast(err.message, "error"); }
  }

  return { render };
})();

const ProfilePage = (() => {
  const val = (id) => document.getElementById(id).value.trim();

  async function render(host) {
    const u = App.user;
    host.innerHTML = `
      <div class="card" style="max-width:560px"><div class="card-hd"><div class="card-title">My profile</div></div>
      <div class="card-body">
        <div class="detail-grid">
          <div class="detail-row"><span class="k">Name</span><span class="v">${esc(u?.full_name || "")}</span></div>
          <div class="detail-row"><span class="k">Email</span><span class="v">${esc(u?.email || "")}</span></div>
          <div class="detail-row"><span class="k">Role</span><span class="v">${roleBadge(u?.role)}</span></div>
        </div>
        <hr style="border:none;border-top:1px solid var(--brd);margin:16px 0" />
        <div class="card-title" style="margin-bottom:10px">Change password</div>
        <div class="fg"><label>Current password</label><input id="p-cur" type="password" /></div>
        <div class="form-row">
          <div class="fg"><label>New password</label><input id="p-new" type="password" /></div>
          <div class="fg"><label>Confirm new password</label><input id="p-conf" type="password" /></div>
        </div>
        <div id="p-err"></div>
        <button class="btn btn-primary" id="p-save">Update password</button>
      </div></div>`;
    document.getElementById("p-save").addEventListener("click", async () => {
      const cur = val("p-cur"), nw = val("p-new"), conf = val("p-conf");
      const err = document.getElementById("p-err");
      if (nw !== conf) { err.innerHTML = `<div class="login-error">New passwords do not match.</div>`; return; }
      if (nw.length < 8) { err.innerHTML = `<div class="login-error">Password must be at least 8 characters.</div>`; return; }
      try {
        await Api.post("/auth/password", { current_password: cur, new_password: nw });
        toast("Password updated");
        ["p-cur", "p-new", "p-conf"].forEach((id) => (document.getElementById(id).value = ""));
        err.innerHTML = "";
      } catch (e) { err.innerHTML = `<div class="login-error">${esc(e.message)}</div>`; }
    });
  }

  return { render };
})();

