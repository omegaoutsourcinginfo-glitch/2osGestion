(function () {
  function detailUrlFromRow(row) {
    var link = row.querySelector("a.project-detail-link[href]");
    return link ? link.getAttribute("href") : null;
  }

  function markRows() {
    var rows = document.querySelectorAll("table tbody tr");
    rows.forEach(function (row) {
      if (!detailUrlFromRow(row)) {
        return;
      }
      row.classList.add("project-row-clickable");
      row.setAttribute("title", "Voir le détail du projet");
    });
  }

  function onClick(event) {
    if (event.defaultPrevented || event.button !== 0) {
      return;
    }
    if (event.target.closest("a, input, button, label, [role='menu'], .actions, summary")) {
      return;
    }
    var row = event.target.closest("tr.project-row-clickable, table tbody tr");
    if (!row) {
      return;
    }
    var url = detailUrlFromRow(row);
    if (!url) {
      return;
    }
    window.location.href = url;
  }

  function bind() {
    markRows();
    document.addEventListener("click", onClick);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  document.addEventListener("htmx:afterSwap", markRows);
  document.addEventListener("htmx:afterSettle", markRows);
})();
