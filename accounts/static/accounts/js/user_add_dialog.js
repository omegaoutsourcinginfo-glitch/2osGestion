/**
 * Add user dialog — Tailwind classes only (Unfold). No custom CSS file.
 * Opens from + / add links on users changelist; POST returns JSON.
 */
(function () {
  if (window.__userAddDialog && typeof window.__userAddDialog.destroy === "function") {
    window.__userAddDialog.destroy();
  }

  var DIALOG_ID = "user-add-dialog";
  var ADD_PATH = "/admin/users/user/add";
  var submitting = false;
  var onDocClick = null;
  var onKey = null;

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrfToken() {
    var input = qs("#" + DIALOG_ID + " input[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    var any = qs('input[name="csrfmiddlewaretoken"]');
    if (any && any.value) return any.value;
    return getCookie("csrftoken");
  }

  function isUsersChangelist() {
    var p = (window.location.pathname || "").replace(/\/+$/, "");
    return p === "/admin/users/user" || p.indexOf("/admin/users/user/?") === 0;
  }

  function isAddUrl(href) {
    if (!href) return false;
    try {
      var u = new URL(href, window.location.origin);
      var path = u.pathname.replace(/\/+$/, "");
      return path === ADD_PATH || path.indexOf(ADD_PATH + "/") === 0;
    } catch (e) {
      return /\/admin\/users\/user\/add\/?/.test(href);
    }
  }

  function showToast(message, isError) {
    if (window.__ucUsersMenu && typeof window.__ucUsersMenu.showToast === "function") {
      window.__ucUsersMenu.showToast(message, isError);
      return;
    }
    var old = qs("#uc-toast");
    if (old) old.remove();
    var el = document.createElement("div");
    el.id = "uc-toast";
    el.setAttribute("role", "status");
    el.className =
      "fixed bottom-4 left-1/2 z-[2147483001] -translate-x-1/2 rounded-lg px-4 py-2.5 text-sm font-semibold text-white shadow-lg " +
      (isError ? "bg-red-600" : "bg-primary-600");
    el.textContent = message;
    document.body.appendChild(el);
    setTimeout(function () {
      if (el.parentNode) el.remove();
    }, 3200);
  }

  function styleInputs(root) {
    (root || document).querySelectorAll("#user-add-dialog-form input[type=text], #user-add-dialog-form input[type=email], #user-add-dialog-form input[type=tel], #user-add-dialog-form input:not([type])").forEach(function (el) {
      if (el.name === "csrfmiddlewaretoken" || el.name === "_dialog") return;
      el.className =
        "h-10 w-full rounded-lg border border-base-200 bg-white py-2 pl-9 pr-3 text-sm shadow-none outline-none ring-0 focus:border-primary-500 focus:ring-2 focus:ring-primary-600/15 dark:border-base-600 dark:bg-base-800 dark:text-font-default-dark";
    });
  }

  function ensureDialog() {
    var box = document.getElementById(DIALOG_ID);
    if (box) {
      if (box.parentElement !== document.body) document.body.appendChild(box);
      return box;
    }

    box = document.createElement("div");
    box.id = DIALOG_ID;
    box.className = "fixed inset-0 hidden items-center justify-center p-4";
    box.style.zIndex = "2147483000";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-labelledby", "user-add-dialog-title");
    box.setAttribute("hidden", "hidden");
    box.innerHTML =
      '<div class="absolute inset-0 bg-base-900/55" data-uad-close></div>' +
      '<div class="relative z-[1] flex w-full max-w-xl max-h-[92dvh] flex-col overflow-hidden rounded-2xl border border-base-200 bg-white shadow-xl dark:border-base-700 dark:bg-base-900">' +
      '<header class="flex shrink-0 items-center gap-3 border-b border-base-100 px-4 py-3 dark:border-base-800">' +
      '<div class="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-primary-600 text-white" aria-hidden="true">' +
      '<span class="material-symbols-outlined text-[1.35rem]">person_add</span></div>' +
      '<div class="min-w-0 flex-1">' +
      '<h2 id="user-add-dialog-title" class="m-0 text-base font-semibold tracking-tight text-font-important-light dark:text-font-important-dark">Créer un utilisateur</h2>' +
      '<p class="m-0 mt-0.5 text-xs text-base-500 dark:text-base-400"><span class="font-semibold text-primary-700 dark:text-primary-300">Mot de passe automatique</span> · envoyé par e-mail</p>' +
      "</div>" +
      '<button type="button" class="inline-flex h-8 w-8 items-center justify-center rounded-lg text-base-400 hover:bg-base-100 hover:text-base-700 dark:hover:bg-base-800" data-uad-close aria-label="Fermer">' +
      '<span class="material-symbols-outlined text-[1.25rem]">close</span></button>' +
      "</header>" +
      '<div id="user-add-dialog-body" class="min-h-0 flex-1 overflow-auto px-4 py-3.5"></div>' +
      "</div>";
    document.body.appendChild(box);
    return box;
  }

  function closeDialog() {
    var box = document.getElementById(DIALOG_ID);
    if (!box) return;
    box.classList.add("hidden");
    box.classList.remove("flex");
    box.hidden = true;
    box.setAttribute("hidden", "hidden");
    box.setAttribute("aria-hidden", "true");
    submitting = false;
  }

  function openShell() {
    var box = ensureDialog();
    box.hidden = false;
    box.removeAttribute("hidden");
    box.removeAttribute("aria-hidden");
    box.classList.remove("hidden");
    box.classList.add("flex");
    return box;
  }

  function setBodyHtml(html) {
    var body = qs("#user-add-dialog-body");
    if (!body) return;
    body.innerHTML = html;
    styleInputs(body);
    var first = qs("#user-add-dialog-form input:not([type=hidden])", body);
    if (first) {
      setTimeout(function () {
        try {
          first.focus();
        } catch (e) {}
      }, 30);
    }
  }

  function loadingHtml() {
    return (
      '<div class="flex items-center justify-center gap-2 py-10 text-sm text-base-500">' +
      '<span class="material-symbols-outlined animate-spin text-base-400">progress_activity</span>' +
      "Chargement…" +
      "</div>"
    );
  }

  function dialogUrl() {
    return ADD_PATH + "/?dialog=1";
  }

  function openDialog() {
    openShell();
    setBodyHtml(loadingHtml());

    fetch(dialogUrl(), {
      method: "GET",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-Dialog": "1",
        Accept: "text/html",
      },
    })
      .then(function (res) {
        return res.text().then(function (html) {
          return { ok: res.ok, status: res.status, html: html };
        });
      })
      .then(function (result) {
        if (!result.ok) {
          setBodyHtml(
            '<p class="m-0 py-6 text-center text-sm text-red-600">Impossible de charger le formulaire.</p>'
          );
          return;
        }
        setBodyHtml(result.html);
      })
      .catch(function () {
        setBodyHtml(
          '<p class="m-0 py-6 text-center text-sm text-red-600">Erreur réseau.</p>'
        );
      });
  }

  function refreshChangelist() {
    var url = "/admin/users/user/";
    if (window.htmx && typeof window.htmx.ajax === "function") {
      window.htmx.ajax("GET", url, { target: "#main", swap: "innerHTML" });
      return;
    }
    window.location.href = url;
  }

  function onSubmit(ev) {
    var form = ev.target;
    if (!form || form.id !== "user-add-dialog-form") return;
    ev.preventDefault();
    ev.stopPropagation();
    if (submitting) return;
    submitting = true;

    var btn = qs("#user-add-dialog-submit", form);
    if (btn) btn.disabled = true;

    var fd = new FormData(form);
    fd.set("_dialog", "1");

    fetch(form.getAttribute("action") || dialogUrl(), {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "X-Requested-With": "XMLHttpRequest",
        "X-Dialog": "1",
        Accept: "application/json",
        "X-CSRFToken": csrfToken(),
      },
      body: fd,
    })
      .then(function (res) {
        var ct = res.headers.get("content-type") || "";
        if (ct.indexOf("application/json") !== -1) {
          return res.json().then(function (data) {
            return { ok: res.ok, json: data, html: null };
          });
        }
        return res.text().then(function (html) {
          return { ok: res.ok, json: null, html: html };
        });
      })
      .then(function (result) {
        submitting = false;
        if (btn) btn.disabled = false;

        if (result.json && result.json.ok) {
          showToast(result.json.message || "Utilisateur créé.", false);
          closeDialog();
          refreshChangelist();
          return;
        }

        if (result.html) {
          setBodyHtml(result.html);
          return;
        }

        showToast(
          (result.json && result.json.message) || "Création impossible.",
          true
        );
      })
      .catch(function () {
        submitting = false;
        if (btn) btn.disabled = false;
        showToast("Erreur réseau lors de la création.", true);
      });
  }

  function maybeAutoOpen() {
    try {
      var params = new URLSearchParams(window.location.search || "");
      if (params.get("open_add") === "1" && isUsersChangelist()) {
        params.delete("open_add");
        var next =
          window.location.pathname +
          (params.toString() ? "?" + params.toString() : "") +
          (window.location.hash || "");
        window.history.replaceState({}, "", next);
        openDialog();
      }
    } catch (e) {}
  }

  function bind() {
    onDocClick = function (ev) {
      var closeEl = ev.target.closest("[data-uad-close]");
      if (closeEl && qs("#" + DIALOG_ID) && qs("#" + DIALOG_ID).contains(closeEl)) {
        ev.preventDefault();
        closeDialog();
        return;
      }

      var a = ev.target.closest("a");
      if (!a) return;
      var href = a.getAttribute("href") || "";
      if (!isAddUrl(href)) return;
      // Only intercept when we can show dialog (users area / global admin)
      if (
        a.classList.contains("addlink") ||
        isUsersChangelist() ||
        /\/admin\/users\/user/.test(window.location.pathname)
      ) {
        ev.preventDefault();
        ev.stopPropagation();
        openDialog();
      }
    };

    onKey = function (ev) {
      if (ev.key === "Escape") {
        var box = document.getElementById(DIALOG_ID);
        if (box && !box.classList.contains("hidden")) closeDialog();
      }
    };

    document.addEventListener("click", onDocClick, true);
    document.addEventListener("keydown", onKey, true);
    document.addEventListener("submit", onSubmit, true);
  }

  function destroy() {
    if (onDocClick) document.removeEventListener("click", onDocClick, true);
    if (onKey) document.removeEventListener("keydown", onKey, true);
    document.removeEventListener("submit", onSubmit, true);
    closeDialog();
  }

  bind();
  maybeAutoOpen();
  document.addEventListener("twoos:spa-ready", maybeAutoOpen);

  window.__userAddDialog = {
    open: openDialog,
    close: closeDialog,
    destroy: destroy,
  };
})();
