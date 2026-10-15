/* Login screen. */
const LoginView = (() => {
  function render() {
    return `
    <div class="login-wrap">
      <form class="login-card" id="login-form" novalidate>
        <h1>CRM<span>pro</span></h1>
        <p class="sub">Sign in to your workspace</p>
        <div id="login-error"></div>
        <div class="fg"><label for="li-email">Email</label>
          <input id="li-email" type="email" autocomplete="username" placeholder="you@company.com" required /></div>
        <div class="fg"><label for="li-pass">Password</label>
          <input id="li-pass" type="password" autocomplete="current-password" placeholder="••••••••" required /></div>
        <button class="btn btn-primary" type="submit" style="width:100%;justify-content:center;margin-top:6px" id="li-btn">Sign in</button>
        <div class="demo-hint">Local demo login (after <code>seed</code>):<br/>
          <code>admin@crmpro.local</code> / <code>Admin123!</code></div>
      </form>
    </div>`;
  }

  async function submit(e) {
    e.preventDefault();
    const email = document.getElementById("li-email").value.trim();
    const password = document.getElementById("li-pass").value;
    const errBox = document.getElementById("login-error");
    const btn = document.getElementById("li-btn");
    errBox.innerHTML = "";
    if (!email || !password) {
      errBox.innerHTML = `<div class="login-error">Please enter your email and password.</div>`;
      return;
    }
    btn.disabled = true; btn.textContent = "Signing in…";
    try {
      const data = await Api.post("/auth/login", { email, password });
      Api.setToken(data.access_token);
      sessionStorage.setItem("crm_token", data.access_token);
      App.setUser(data.user);
      App.showApp();
    } catch (err) {
      errBox.innerHTML = `<div class="login-error">${esc(err.message)}</div>`;
    } finally {
      btn.disabled = false; btn.textContent = "Sign in";
    }
  }

  function bind() {
    document.getElementById("login-form").addEventListener("submit", submit);
  }

  return { render, bind };
})();
