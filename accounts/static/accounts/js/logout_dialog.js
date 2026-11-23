/**
 * Logout confirmation dialog — no Alpine teleport (SPA-safe).
 * Hidden by default; only opens from [data-twoos-logout-open].
 */
(function () {
  if (window.__twoosLogoutDialog && typeof window.__twoosLogoutDialog.destroy === "function") {
    window.__twoosLogoutDialog.destroy();
  }

  var DIALOG_ID = "twoos-logout-dialog";

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

  function logoutUrl() {
    var btn = qs("[data-twoos-logout-open]");
    if (btn && btn.getAttribute("data-logout-url")) {
      return btn.getAttribute("data-logout-url");
    }
    return "/admin/logout/";
  }

  function scrubOrphans() {
    // Remove broken Alpine teleports from older templates.
    document.querySelectorAll("[aria-labelledby='logout-dialog-title']").forEach(function (el) {
      if (el.id !== DIALOG_ID) el.remove();
    });
    document.querySelectorAll("#" + DIALOG_ID).forEach(function (el, idx) {
      if (idx > 0) el.remove();
    });
  }

  function ensureDialog() {
    scrubOrphans();
    var box = document.getElementById(DIALOG_ID);
    if (box) {
      if (box.parentElement !== document.body) {
        document.body.appendChild(box);
      }
      return box;
    }

    box = document.createElement("div");
    box.id = DIALOG_ID;
    box.className = "";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("aria-labelledby", "twoos-logout-title");
    box.setAttribute("hidden", "hidden");
    box.innerHTML =
      '<div class="twoos-logout-backdrop" data-twoos-logout-close></div>' +
      '<div class="twoos-logout-panel">' +
      '<h2 id="twoos-logout-title">Déconnexion</h2>' +
      "<p>Voulez-vous vraiment vous déconnecter&nbsp;?</p>" +
      '<div class="twoos-logout-actions">' +
      '<button type="button" class="twoos-logout-cancel" data-twoos-logout-close>Annuler</button>' +
      '<form id="twoos-logout-form" method="post" action="' +
      logoutUrl() +
      '" data-no-spa>' +
      '<input type="hidden" name="csrfmiddlewaretoken" value="">' +
      '<button type="submit" class="twoos-logout-confirm">Déconnexion</button>' +
      "</form>" +
      "</div></div>";
    document.body.appendChild(box);
    return box;
  }

  function closeDialog() {
    var box = document.getElementById(DIALOG_ID);
    if (!box) return;
    box.classList.remove("is-open");
    box.hidden = true;
    box.setAttribute("hidden", "hidden");
    box.setAttribute("aria-hidden", "true");
    box.setAttribute("inert", "");
  }

  function openDialog() {
    var box = ensureDialog();
    var form = qs("#twoos-logout-form", box);
    var csrf = qs("input[name=csrfmiddlewaretoken]", box);
    var token = csrfToken();
    if (form) {
      form.setAttribute("action", logoutUrl());
      form.action = logoutUrl();
    }
    if (csrf && token) csrf.value = token;

    box.hidden = false;
    box.removeAttribute("hidden");
    box.removeAttribute("aria-hidden");
    box.removeAttribute("inert");
    box.classList.add("is-open");
  }

  function onClick(event) {
    var t = event.target;
    if (!t || !t.closest) return;

    if (t.closest("[data-twoos-logout-open]")) {
      event.preventDefault();
      event.stopPropagation();
      openDialog();
      return;
    }

    if (t.closest("[data-twoos-logout-close]")) {
      event.preventDefault();
      event.stopPropagation();
      closeDialog();
    }
  }

  function onKey(event) {
    if (event.key === "Escape") closeDialog();
  }

  function onSpaReady() {
    scrubOrphans();
    closeDialog();
    ensureDialog();
    closeDialog();
  }

  document.addEventListener("click", onClick, true);
  document.addEventListener("keydown", onKey, true);
  document.addEventListener("twoos:spa-ready", onSpaReady);

  window.__twoosLogoutDialog = {
    open: openDialog,
    close: closeDialog,
    destroy: function () {
      document.removeEventListener("click", onClick, true);
      document.removeEventListener("keydown", onKey, true);
      document.removeEventListener("twoos:spa-ready", onSpaReady);
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onSpaReady);
  } else {
    onSpaReady();
  }
})();
