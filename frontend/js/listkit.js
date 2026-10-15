/* Shared list-rendering helpers used across pages. */
const ListKit = (() => {
  function emptyCard(title, emptyHtml, actionHtml = "") {
    return `
    <div class="sbar"><div style="flex:1">${title ? `<span class="card-title">${esc(title)}</span>` : ""}</div>${actionHtml}</div>
    <div class="card"><div class="card-body">${emptyHtml}</div></div>`;
  }

  function pager({ page, pages, total }) {
    if (pages <= 1) return `<div class="pager"><span class="info">${fmtNum(total)} total</span></div>`;
    return `
    <div class="pager">
      <span class="info">Page ${page} of ${pages} · ${fmtNum(total)} total</span>
      <button class="btn btn-ghost btn-sm" ${page <= 1 ? "disabled" : ""} data-page-nav="${page - 1}">Prev</button>
      <button class="btn btn-ghost btn-sm" ${page >= pages ? "disabled" : ""} data-page-nav="${page + 1}">Next</button>
    </div>`;
  }

  function bindPager(host, st, onChange) {
    host.querySelectorAll("[data-page-nav]").forEach((btn) => {
      btn.addEventListener("click", () => { st.page = parseInt(btn.dataset.pageNav, 10); onChange(); });
    });
  }

  return { emptyCard, pager, bindPager };
})();
