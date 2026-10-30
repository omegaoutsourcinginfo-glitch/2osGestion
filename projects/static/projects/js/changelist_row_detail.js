(function () {
  function detailUrlFromRow(row) {
    var link = row.querySelector("a.project-detail-link[href]");
    return link ? link.getAttribute("href") : null;
  }

  function isActionsClick(event) {
    var t = event.target;
    if (!t || !t.closest) {
      return false;
    }
    if (t.closest("[data-no-row-nav], td.field-actions_holder, .field-actions_holder")) {
      return true;
    }
    var td = t.closest("td");
    var tr = t.closest("tr");
    if (td && tr && tr.lastElementChild === td) {
      var ths = document.querySelectorAll("#result_list thead th");
      if (ths.length && /actions/i.test((ths[ths.length - 1].textContent || "").trim())) {
        return true;
      }
      if (td.classList.contains("field-actions_holder") || td.querySelector(".material-symbols-outlined")) {
        return true;
      }
    }
    if ((t.textContent || "").trim() === "more_horiz") {
      return true;
    }
    return false;
  }

  function markRows() {
    var rows = document.querySelectorAll("#result_list tbody tr, table tbody tr");
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
    if (isActionsClick(event)) {
      return;
    }
    // Links are handled by spa_nav.js (project-detail-link).
    if (event.target.closest("a.project-detail-link")) {
      return;
    }
    if (
      event.target.closest(
        "a, input, button, label, [role='menu'], .actions, summary, nav"
      )
    ) {
      return;
    }
    var row = event.target.closest("tr.project-row-clickable");
    if (!row) {
      return;
    }
    var url = detailUrlFromRow(row);
    if (!url) {
      return;
    }
    event.preventDefault();
    event.stopPropagation();
    if (window.TwoosSpa && window.TwoosSpa.openFicheFromHref) {
      window.TwoosSpa.openFicheFromHref(url);
      return;
    }
    window.location.href = url;
  }

  function bind() {
    markRows();
    document.addEventListener("click", onClick, true);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  document.addEventListener("htmx:afterSwap", markRows);
  document.addEventListener("htmx:afterSettle", markRows);
})();
