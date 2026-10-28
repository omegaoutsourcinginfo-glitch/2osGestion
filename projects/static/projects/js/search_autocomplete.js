(function () {
  var ENDPOINT = "/projets/autocomplete/";
  var MIN_CHARS = 1;
  var DEBOUNCE_MS = 200;

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function debounce(fn, wait) {
    var timer;
    return function () {
      var args = arguments;
      var ctx = this;
      clearTimeout(timer);
      timer = setTimeout(function () {
        fn.apply(ctx, args);
      }, wait);
    };
  }

  function ensureDropdown(wrapper) {
    var list = wrapper.querySelector(".search-autocomplete-list");
    if (list) {
      return list;
    }
    list = document.createElement("ul");
    list.className = "search-autocomplete-list";
    list.hidden = true;
    wrapper.appendChild(list);
    return list;
  }

  function hideList(list) {
    list.hidden = true;
    list.innerHTML = "";
  }

  function selectSuggestion(input, form, item, list) {
    input.value = item.titre;
    hideList(list);
    if (form) {
      form.submit();
    }
  }

  function renderResults(list, input, form, results) {
    list.innerHTML = "";
    if (!results.length) {
      hideList(list);
      return;
    }
    results.forEach(function (item) {
      var li = document.createElement("li");
      var btn = document.createElement("button");
      btn.type = "button";
      btn.className = "search-autocomplete-item";
      btn.innerHTML =
        '<span class="search-autocomplete-code">' +
        escapeHtml(item.code) +
        '</span><span class="search-autocomplete-titre">' +
        escapeHtml(item.titre) +
        "</span>";
      btn.addEventListener("mousedown", function (event) {
        event.preventDefault();
        selectSuggestion(input, form, item, list);
      });
      li.appendChild(btn);
      list.appendChild(li);
    });
    list.hidden = false;
  }

  function escapeHtml(value) {
    return String(value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function fetchSuggestions(q) {
    return fetch(ENDPOINT + "?q=" + encodeURIComponent(q), {
      headers: { Accept: "application/json" },
      credentials: "same-origin",
    }).then(function (response) {
      if (!response.ok) {
        throw new Error("autocomplete failed");
      }
      return response.json();
    });
  }

  function bindSearch(input) {
    if (input.dataset.autocompleteBound === "1") {
      return;
    }
    input.dataset.autocompleteBound = "1";
    input.setAttribute("autocomplete", "off");

    var form = input.closest("form");
    var wrapper = input.closest(".relative") || input.parentElement;
    if (wrapper) {
      wrapper.classList.add("search-autocomplete-wrap");
    }
    var list = ensureDropdown(wrapper);

    var onInput = debounce(function () {
      var q = (input.value || "").trim();
      if (q.length < MIN_CHARS) {
        hideList(list);
        return;
      }
      fetchSuggestions(q)
        .then(function (data) {
          renderResults(list, input, form, data.results || []);
        })
        .catch(function () {
          hideList(list);
        });
    }, DEBOUNCE_MS);

    input.addEventListener("input", onInput);
    input.addEventListener("focus", onInput);
    input.addEventListener("keydown", function (event) {
      if (event.key === "Escape") {
        hideList(list);
      }
    });
    document.addEventListener("click", function (event) {
      if (!wrapper.contains(event.target)) {
        hideList(list);
      }
    });
  }

  ready(function () {
    var input = document.getElementById("searchbar");
    if (input) {
      bindSearch(input);
    }
  });
})();
