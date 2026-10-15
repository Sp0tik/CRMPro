/* CRMPro API client.
   Thin wrapper around fetch. The JWT is kept in a module-level variable
   (in memory) only — never in localStorage/sessionStorage — as an XSS
   mitigation. On 401 the app redirects to the login screen. */
const API_BASE = (window.CRM_API_BASE || "") + "/api/v1";

const Api = (() => {
  let token = null;
  let onUnauthorized = () => {};

  function setToken(t) { token = t; }
  function getToken() { return token; }
  function setUnauthorizedHandler(fn) { onUnauthorized = fn; }

  async function request(method, path, { body, params } = {}) {
    const url = new URL(API_BASE + path, window.location.origin);
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== "") url.searchParams.set(k, v);
      });
    }
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;

    let resp;
    try {
      resp = await fetch(url, {
        method,
        headers,
        body: body !== undefined ? JSON.stringify(body) : undefined,
      });
    } catch (networkErr) {
      throw new ApiError(0, "Cannot reach the server. Please check your connection.");
    }

    if (resp.status === 401) {
      onUnauthorized();
      throw new ApiError(401, "Your session has expired. Please sign in again.");
    }
    if (resp.status === 204) return null;

    const contentType = resp.headers.get("content-type") || "";
    const data = contentType.includes("application/json") ? await resp.json() : await resp.text();

    if (!resp.ok) {
      const detail = typeof data === "object" && data && data.detail ? data.detail : "Request failed";
      throw new ApiError(resp.status, detail);
    }
    return data;
  }

  return {
    setToken, getToken, setUnauthorizedHandler,
    get: (p, o) => request("GET", p, o),
    post: (p, body, o = {}) => request("POST", p, { ...o, body }),
    put: (p, body, o = {}) => request("PUT", p, { ...o, body }),
    patch: (p, body, o = {}) => request("PATCH", p, { ...o, body }),
    del: (p, o) => request("DELETE", p, o),
  };
})();

class ApiError extends Error {
  constructor(status, message) {
    super(typeof message === "string" ? message : JSON.stringify(message));
    this.status = status;
    this.detail = message;
  }
}
