/* CRMPro single-page application. */
const App = (() => {
  let currentUser = null;
  let currentPage = "dashboard";
  const state = {}; // per-page UI state (search, filters, page, sort)

  const TITLES = {
    dashboard: "Dashboard", clients: "Clients", deals: "Deals",
    tasks: "Tasks", support: "Support", analytics: "Analytics", users: "Users", profile: "Profile",
  };

  function setUser(user) { currentUser = user; }

  /* ---------- Boot / routing ---------- */
  async function start() {
    Api.setUnauthorizedHandler(logout);
    const token = sessionStorage.getItem("crm_token");
    if (token) {
      Api.setToken(token);
      try {
        currentUser = await Api.get("/auth/me");
        showApp();
        return;
      } catch (e) { /* fall through to login */ }
    }
    showLogin();
  }

  function logout() {
    Api.setToken(null);
    sessionStorage.removeItem("crm_token");
    currentUser = null;
    showLogin();
  }

  function showLogin() {
    document.getElementById("root").innerHTML = LoginView.render();
    LoginView.bind();
  }

  function showApp() {
    document.getElementById("root").innerHTML = Layout.render(currentUser);
    Layout.bind();
    navigate("dashboard");
  }

  function navigate(page) {
    currentPage = page;
    document.querySelectorAll(".nav-item").forEach((i) => i.classList.toggle("active", i.dataset.page === page));
    document.getElementById("page-title").textContent = TITLES[page] || page;
    closeSidebar();
    render();
  }

  function render() {
    const host = document.getElementById("content");
    const renderers = {
      dashboard: Pages.dashboard, clients: Pages.clients, deals: Pages.deals,
      tasks: Pages.tasks, support: Pages.support, analytics: Pages.analytics,
      users: Pages.users, profile: Pages.profile,
    };
    const fn = renderers[currentPage];
    if (!fn) { host.innerHTML = errorState("Page not found"); return; }
    host.innerHTML = loadingState();
    fn(host, state[currentPage] || (state[currentPage] = {})).catch((err) => {
      host.innerHTML = errorState(err.message || "Something went wrong");
    });
  }

  function refresh() { render(); }

  /* ---------- Sidebar (mobile) ---------- */
  function toggleSidebar() {
    document.getElementById("sidebar")?.classList.toggle("open");
    document.getElementById("backdrop")?.classList.toggle("show");
  }
  function closeSidebar() {
    document.getElementById("sidebar")?.classList.remove("open");
    document.getElementById("backdrop")?.classList.remove("show");
  }

  return { start, logout, navigate, render, refresh, setUser, showApp, toggleSidebar, closeSidebar, get user() { return currentUser; }, get page() { return currentPage; } };
})();

document.addEventListener("DOMContentLoaded", () => App.start());
// Overlay click-to-close (delegated).
document.addEventListener("click", (e) => {
  if (e.target && e.target.id === "overlay") closeModal();
});
// Escape closes modal.
document.addEventListener("keydown", (e) => {
  if (e.key === "Escape") closeModal();
});
