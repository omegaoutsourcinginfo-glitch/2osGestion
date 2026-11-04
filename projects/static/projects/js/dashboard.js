/* Dashboard: Projets récents — filter by first letter(s) of code/title. */
(function () {
  function bindRecentSearch() {
    var input = document.getElementById("dash-recent-q");
    if (!input || typeof htmx === "undefined") {
      return;
    }

    var endpoint = input.getAttribute("data-hx-get") || input.getAttribute("hx-get");
    if (!endpoint) {
      return;
    }

    input.setAttribute("name", "q");
    input.setAttribute("hx-get", endpoint);
    input.setAttribute(
      "hx-trigger",
      "input changed delay:150ms, keyup changed delay:150ms, search"
    );
    input.setAttribute("hx-target", "#dash-recent-list");
    input.setAttribute("hx-swap", "outerHTML");
    input.removeAttribute("hx-vals");
    input.removeAttribute("hx-include");

    if (input.dataset.dashRecentBound === "1") {
      htmx.process(input);
      return;
    }
    input.dataset.dashRecentBound = "1";

    input.addEventListener("htmx:configRequest", function (event) {
      var detail = event.detail || {};
      detail.parameters = detail.parameters || {};
      detail.parameters.q = input.value || "";
    });

    htmx.process(input);
  }

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  ready(function () {
    bindRecentSearch();
    document.addEventListener("htmx:afterSwap", bindRecentSearch);
    document.addEventListener("htmx:afterSettle", bindRecentSearch);
    document.addEventListener("twoos:spa-ready", bindRecentSearch);
  });
})();
