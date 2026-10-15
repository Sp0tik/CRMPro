/* App shell: sidebar + topbar. */
const Layout = (() => {
  function navItem(page, icon, label, extra = "") {
    return `<button class="nav-item" data-page="${page}"><span class="ico">${icon}</span>${label}${extra}</button>`;
  }

  function render(user) {
    const isAdmin = user && user.role === "admin";
    const adminNav = isAdmin
      ? `<div class="nav-sec">Administration</div>${navItem("users", "🛡️", "Users")}`
      : "";
    return `
    <div class="app">
      <div class="backdrop" id="backdrop"></div>
      <aside class="sidebar" id="sidebar">
        <div class="logo"><h1>CRM<span>pro</span></h1><p>Customer Relations</p></div>
        <nav class="nav">
          <div class="nav-sec">Navigation</div>
          ${navItem("dashboard", "📊", "Dashboard")}
          ${navItem("clients", "👥", "Clients")}
          ${navItem("deals", "💼", "Deals")}
          ${navItem("tasks", "✅", "Tasks")}
          ${navItem("support", "🎫", "Support")}
          ${navItem("analytics", "📈", "Analytics")}
          ${adminNav}
        </nav>
        <div class="sb-foot">
          <div class="user-row">
            <div class="avatar">${esc(initials(user?.full_name))}</div>
            <div class="ui"><p>${esc(user?.full_name || "User")}</p><span>${esc(user?.role || "")}</span></div>
          </div>
        </div>
      </aside>
      <main class="main">
        <div class="topbar">
          <div class="topbar-left">
            <button class="hamburger" id="hamburger" aria-label="Toggle menu">☰</button>
            <h2 id="page-title">Dashboard</h2>
          </div>
          <div style="display:flex;align-items:center;gap:10px">
            <span class="topbar-meta" id="topbar-meta"></span>
            <button class="btn btn-ghost btn-sm" id="nav-profile">Profile</button>
            <button class="btn btn-ghost btn-sm" id="nav-logout">Log out</button>
          </div>
        </div>
        <div class="content" id="content"></div>
      </main>
    </div>`;
  }

  function bind() {
    document.querySelectorAll(".nav-item").forEach((el) => {
      el.addEventListener("click", () => App.navigate(el.dataset.page));
    });
    document.getElementById("hamburger")?.addEventListener("click", () => App.toggleSidebar());
    document.getElementById("backdrop")?.addEventListener("click", () => App.closeSidebar());
    document.getElementById("nav-logout")?.addEventListener("click", () => App.logout());
    document.getElementById("nav-profile")?.addEventListener("click", () => App.navigate("profile"));
  }

  return { render, bind };
})();
