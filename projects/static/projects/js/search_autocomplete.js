(function () {
  var ENDPOINT = "/projets/autocomplete/";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function ensureResultsHost(wrapper) {
    var host = document.getElementById("search-autocomplete-results");
    if (host) {
      return host;
    }
    host = document.createElement("div");
    host.id = "search-autocomplete-results";
    wrapper.appendChild(host);
    return host;
  }

  function clearResults() {
    var host = document.getElementById("search-autocomplete-results");
    if (host) {
      host.innerHTML = "";
      host.hidden = true;
    }
  }

  function highlightTableRow(code) {
    if (!code) {
      return;
    }
    var needle = String(code).toLowerCase();
    var rows = document.querySelectorAll("#result_list tbody tr");
    var match = null;
    rows.forEach(function (row) {
      row.classList.remove("search-row-highlight");
      var text = (row.textContent || "").toLowerCase();
      if (!match && text.indexOf(needle) >= 0) {
        match = row;
      }
    });
    if (!match) {
      return;
    }
    match.classList.add("search-row-highlight");
    try {
      match.scrollIntoView({ block: "center", behavior: "smooth" });
    } catch (err) {
      match.scrollIntoView(true);
    }
  }

  function highlightFromUrl() {
    try {
      var q = new URL(window.location.href).searchParams.get("q");
      if (q) {
        highlightTableRow(q.trim());
      }
    } catch (err) {
      // ignore
    }
  }

  function openItem(item) {
    var href = item.getAttribute("href");
    var code = item.getAttribute("data-project-code") || "";
    clearResults();
    if (!href) {
      return;
    }
    // Changelist / admin URLs: SPA navigate, then highlight the row in the table.
    if (window.TwoosSpa && typeof window.TwoosSpa.go === "function") {
      window.TwoosSpa.go(href, item);
      window.setTimeout(function () {
        highlightTableRow(code);
      }, 250);
      window.setTimeout(function () {
        highlightTableRow(code);
      }, 600);
      return;
    }
    window.location.href = href;
  }

  function bindSearch(input) {
    if (!input || input.dataset.htmxAutocomplete === "1") {
      return;
    }
    if (typeof htmx === "undefined") {
      return;
    }

    input.dataset.htmxAutocomplete = "1";
    input.setAttribute("autocomplete", "off");
    input.setAttribute("name", input.getAttribute("name") || "q");

    var wrapper = input.closest(".relative") || input.parentElement;
    if (wrapper) {
      wrapper.classList.add("search-autocomplete-wrap");
    }
    ensureResultsHost(wrapper);

    input.setAttribute("hx-get", ENDPOINT);
    input.setAttribute("hx-trigger", "keyup changed delay:200ms, focus");
    input.setAttribute("hx-target", "#search-autocomplete-results");
    input.setAttribute("hx-swap", "outerHTML");
    input.setAttribute("hx-include", "this");

    htmx.process(input);

    var form = input.closest("form");
    if (form && form.dataset.htmxAutocompleteSubmit !== "1") {
      form.dataset.htmxAutocompleteSubmit = "1";
      form.addEventListener("submit", function (event) {
        var host = document.getElementById("search-autocomplete-results");
        var first = host && host.querySelector("a.search-autocomplete-item[href]");
        if (!first) {
          return;
        }
        event.preventDefault();
        openItem(first);
      });
    }
  }

  function bindAll() {
    var input = document.getElementById("searchbar");
    if (input) {
      // After SPA swap the input is new — allow re-bind.
      if (input.dataset.htmxAutocomplete === "1" && !input.getAttribute("hx-get")) {
        delete input.dataset.htmxAutocomplete;
      }
      bindSearch(input);
    }
    highlightFromUrl();
  }

  ready(function () {
    bindAll();

    document.addEventListener(
      "click",
      function (event) {
        var item =
          event.target.closest && event.target.closest("a.search-autocomplete-item[href]");
        if (item) {
          event.preventDefault();
          event.stopImmediatePropagation();
          openItem(item);
          return;
        }
        var host = document.getElementById("search-autocomplete-results");
        var wrap = document.querySelector(".search-autocomplete-wrap");
        if (!host || !wrap) {
          return;
        }
        if (!wrap.contains(event.target)) {
          clearResults();
        }
      },
      true
    );

    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        clearResults();
      }
    });

    document.addEventListener("htmx:afterSwap", bindAll);
    document.addEventListener("htmx:afterSettle", bindAll);
    document.addEventListener("twoos:spa-ready", bindAll);
  });
})();
