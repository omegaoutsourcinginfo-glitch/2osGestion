/**
 * User cards — ⋮ menu + delete without full page refresh (SPA / Alpine safe).
 */
(function () {
  if (window.__ucUsersMenu && typeof window.__ucUsersMenu.destroy === "function") {
    window.__ucUsersMenu.destroy();
  }

  var activeBtn = null;
  var pendingCard = null;
  var pendingUrl = "";
  var deleting = false;
  var sendingPassword = false;
  var ignoreScrollUntil = 0;

  function qs(sel, root) {
    return (root || document).querySelector(sel);
  }

  function cleanupDuplicates(id) {
    var nodes = document.querySelectorAll("#" + id);
    var keep = null;
    nodes.forEach(function (node) {
      if (keep) keep.remove();
      keep = node;
    });
    if (keep && keep.parentElement !== document.body) {
      document.body.appendChild(keep);
    }
    return keep;
  }

  function ensurePortal() {
    var menu = cleanupDuplicates("uc-portal-menu");
    if (!menu) {
      menu = document.createElement("div");
      menu.id = "uc-portal-menu";
      menu.className = "uc-portal-menu";
      menu.setAttribute("role", "menu");
      menu.setAttribute("hidden", "hidden");
      menu.innerHTML =
        '<a id="uc-portal-detail" class="uc-portal-item" role="menuitem" href="#">' +
        '<span class="material-symbols-outlined" aria-hidden="true">visibility</span>Détail</a>' +
        '<a id="uc-portal-edit" class="uc-portal-item" role="menuitem" href="#">' +
        '<span class="material-symbols-outlined" aria-hidden="true">edit</span>Modifier</a>' +
        '<button id="uc-portal-send-password" type="button" class="uc-portal-item" role="menuitem" hidden>' +
        '<span class="material-symbols-outlined" aria-hidden="true">key</span>Envoyer mot de passe</button>' +
        '<button id="uc-portal-delete" type="button" class="uc-portal-item is-danger" role="menuitem" hidden>' +
        '<span class="material-symbols-outlined" aria-hidden="true">delete</span>Supprimer</button>';
      document.body.appendChild(menu);
    } else if (!qs("#uc-portal-send-password", menu)) {
      var delBtn = qs("#uc-portal-delete", menu);
      var sendBtn = document.createElement("button");
      sendBtn.id = "uc-portal-send-password";
      sendBtn.type = "button";
      sendBtn.className = "uc-portal-item";
      sendBtn.setAttribute("role", "menuitem");
      sendBtn.setAttribute("hidden", "hidden");
      sendBtn.innerHTML =
        '<span class="material-symbols-outlined" aria-hidden="true">key</span>Envoyer mot de passe';
      if (delBtn) menu.insertBefore(sendBtn, delBtn);
      else menu.appendChild(sendBtn);
    }
    return menu;
  }

  function ensureDialog() {
    var box = cleanupDuplicates("user-delete-dialog");
    if (box) return box;

    box = document.createElement("div");
    box.id = "user-delete-dialog";
    box.className = "uc-delete-dialog";
    box.setAttribute("role", "dialog");
    box.setAttribute("aria-modal", "true");
    box.setAttribute("hidden", "hidden");
    box.innerHTML =
      '<div class="uc-delete-backdrop" data-uc-delete-close></div>' +
      '<div class="uc-delete-panel">' +
      "<h2>Supprimer l'utilisateur ?</h2>" +
      "<p>Voulez-vous vraiment supprimer <strong id=\"user-delete-dialog-name\"></strong> " +
      '(<span id="user-delete-dialog-email" class="break-all"></span>) ?</p>' +
      '<div class="uc-delete-actions">' +
      '<button type="button" class="uc-delete-cancel" data-uc-delete-close>Non</button>' +
      '<form id="user-delete-dialog-form" method="post" action="" data-no-spa>' +
      '<input type="hidden" name="csrfmiddlewaretoken" value="">' +
      '<input type="hidden" name="post" value="yes">' +
      "</form>" +
      '<button type="button" id="user-delete-dialog-confirm" class="uc-delete-confirm">Oui, supprimer</button>' +
      "</div></div>";
    document.body.appendChild(box);
    return box;
  }

  function getCookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([^;]*)"));
    return match ? decodeURIComponent(match[1]) : "";
  }

  function csrfToken() {
    var input = qs("#user-delete-dialog-form input[name=csrfmiddlewaretoken]");
    if (input && input.value) return input.value;
    var meta = qs('input[name="csrfmiddlewaretoken"]');
    if (meta && meta.value) return meta.value;
    return getCookie("csrftoken");
  }

  function showToast(message, isError) {
    var old = qs("#uc-toast");
    if (old) old.remove();

    var el = document.createElement("div");
    el.id = "uc-toast";
    el.setAttribute("role", "status");
    el.className = "uc-toast" + (isError ? " is-error" : " is-ok");
    el.textContent = message;
    document.body.appendChild(el);

    requestAnimationFrame(function () {
      el.classList.add("is-visible");
    });
    window.setTimeout(function () {
      el.classList.remove("is-visible");
      window.setTimeout(function () {
        if (el.parentNode) el.remove();
      }, 280);
    }, 3200);
  }

  function closePortal() {
    var menu = qs("#uc-portal-menu");
    if (!menu) return;
    menu.hidden = true;
    menu.setAttribute("hidden", "hidden");
    menu.classList.remove("is-open");
    menu.style.visibility = "hidden";
    if (activeBtn) {
      activeBtn.setAttribute("aria-expanded", "false");
      activeBtn = null;
    }
  }

  function openPortal(btn) {
    var menu = ensurePortal();
    if (!menu) return;

    var detail = qs("#uc-portal-detail", menu) || qs("#uc-portal-detail");
    var edit = qs("#uc-portal-edit", menu) || qs("#uc-portal-edit");
    var sendPwd = qs("#uc-portal-send-password", menu) || qs("#uc-portal-send-password");
    var del = qs("#uc-portal-delete", menu) || qs("#uc-portal-delete");

    if (detail) detail.href = btn.getAttribute("data-detail-url") || "#";
    if (edit) edit.href = btn.getAttribute("data-change-url") || "#";

    var sendUrl = btn.getAttribute("data-send-password-url");
    if (sendPwd) {
      if (sendUrl) {
        sendPwd.hidden = false;
        sendPwd.removeAttribute("hidden");
        sendPwd.setAttribute("data-send-password-url", sendUrl);
        sendPwd.setAttribute(
          "data-send-password-email",
          btn.getAttribute("data-send-password-email") || ""
        );
        sendPwd.disabled = false;
      } else {
        sendPwd.hidden = true;
        sendPwd.setAttribute("hidden", "hidden");
      }
    }

    var deleteUrl = btn.getAttribute("data-delete-url");
    if (del) {
      if (deleteUrl) {
        del.hidden = false;
        del.removeAttribute("hidden");
        del.setAttribute("data-delete-url", deleteUrl);
        del.setAttribute("data-delete-name", btn.getAttribute("data-delete-name") || "");
        del.setAttribute("data-delete-email", btn.getAttribute("data-delete-email") || "");
      } else {
        del.hidden = true;
        del.setAttribute("hidden", "hidden");
      }
    }

    ignoreScrollUntil = Date.now() + 400;
    activeBtn = btn;
    pendingCard = btn.closest(".uc-card");
    btn.setAttribute("aria-expanded", "true");

    var rect = btn.getBoundingClientRect();
    var menuW = 200;
    var menuH = 200;
    var left = Math.min(window.innerWidth - menuW - 8, Math.max(8, rect.right - menuW));
    var top = rect.bottom + 6;
    if (top + menuH > window.innerHeight) {
      top = Math.max(8, rect.top - menuH);
    }

    menu.style.left = left + "px";
    menu.style.top = top + "px";
    menu.style.visibility = "visible";
    menu.hidden = false;
    menu.removeAttribute("hidden");
    menu.classList.add("is-open");
  }

  function openDeleteDialog(src) {
    var box = ensureDialog();
    if (!box) {
      showToast("Dialogue de suppression introuvable. Rechargez la page.", true);
      return;
    }
    var url = src.getAttribute("data-delete-url") || "";
    var name = src.getAttribute("data-delete-name") || "";
    var email = src.getAttribute("data-delete-email") || "";
    if (!url) {
      showToast("URL de suppression manquante.", true);
      return;
    }

    pendingUrl = url;
    if (!pendingCard && activeBtn) {
      pendingCard = activeBtn.closest(".uc-card");
    }

    var nameEl = qs("#user-delete-dialog-name");
    var emailEl = qs("#user-delete-dialog-email");
    var form = qs("#user-delete-dialog-form");
    var confirmBtn = qs("#user-delete-dialog-confirm");

    if (nameEl) nameEl.textContent = name;
    if (emailEl) emailEl.textContent = email;
    if (form) {
      form.setAttribute("action", url);
      form.action = url;
      var csrfInput = form.querySelector("input[name=csrfmiddlewaretoken]");
      var token = csrfToken();
      if (csrfInput && token) csrfInput.value = token;
    }
    if (confirmBtn) {
      confirmBtn.setAttribute("data-delete-url", url);
      confirmBtn.disabled = false;
    }

    box.removeAttribute("hidden");
    box.hidden = false;
    box.classList.add("is-open");
    box.setAttribute("data-alpine-ignore", "");
    closePortal();
  }

  function closeDeleteDialog() {
    var box = qs("#user-delete-dialog");
    if (!box) return;
    box.classList.remove("is-open");
    box.hidden = true;
    box.setAttribute("hidden", "hidden");
  }

  function updateResultCount(delta) {
    var badges = document.querySelectorAll(".changelist-result-count");
    badges.forEach(function (badge) {
      var raw = (badge.textContent || "").trim();
      var n = parseInt(raw, 10);
      if (isNaN(n)) return;
      var next = Math.max(0, n + delta);
      badge.textContent = String(next);
      var title = badge.getAttribute("title") || "";
      if (title) {
        badge.setAttribute("title", title.replace(String(n), String(next)));
      }
      badge.hidden = next === 0;
    });
  }

  function removeCard(card) {
    if (!card || !card.parentNode) return;
    card.classList.add("is-removing");
    window.setTimeout(function () {
      if (card.parentNode) card.remove();
      updateResultCount(-1);
      var grid = qs(".uc-grid");
      if (grid && !grid.querySelector(".uc-card")) {
        var wrap = qs(".uc-wrap");
        if (wrap) {
          wrap.innerHTML =
            '<p class="uc-empty">Aucun utilisateur. <a href="add/">Ajouter</a></p>';
        }
      }
    }, 220);
  }

  function doDelete(url) {
    if (!url || deleting) return;
    deleting = true;

    var confirmBtn = qs("#user-delete-dialog-confirm");
    if (confirmBtn) confirmBtn.disabled = true;

    var token = csrfToken();
    var body = new URLSearchParams();
    body.set("csrfmiddlewaretoken", token);
    body.set("post", "yes");

    var card = pendingCard;

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: body.toString(),
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { okHttp: res.ok, data: data };
        });
      })
      .then(function (result) {
        closeDeleteDialog();
        if (result.data && result.data.ok) {
          removeCard(card);
          showToast(result.data.message || "Utilisateur supprimé.", false);
        } else {
          showToast(
            (result.data && result.data.message) || "Suppression impossible.",
            true
          );
        }
      })
      .catch(function () {
        closeDeleteDialog();
        showToast("Erreur réseau lors de la suppression.", true);
      })
      .finally(function () {
        deleting = false;
        pendingCard = null;
        pendingUrl = "";
        if (confirmBtn) confirmBtn.disabled = false;
      });
  }

  function doSendPassword(url, email) {
    if (!url || sendingPassword) return;
    sendingPassword = true;
    closePortal();

    var btn = qs("#uc-portal-send-password");
    if (btn) btn.disabled = true;

    var token = csrfToken();
    var body = new URLSearchParams();
    body.set("csrfmiddlewaretoken", token);
    body.set("post", "yes");

    showToast("Envoi du mot de passe" + (email ? " à " + email : "") + "…", false);

    fetch(url, {
      method: "POST",
      headers: {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
        "X-CSRFToken": token,
        "X-Requested-With": "XMLHttpRequest",
        Accept: "application/json",
      },
      body: body.toString(),
      credentials: "same-origin",
    })
      .then(function (res) {
        return res.json().then(function (data) {
          return { okHttp: res.ok, data: data };
        });
      })
      .then(function (result) {
        if (result.data && result.data.ok) {
          showToast(result.data.message || "Mot de passe envoyé.", false);
        } else {
          showToast(
            (result.data && result.data.message) || "Envoi impossible.",
            true
          );
        }
      })
      .catch(function () {
        showToast("Erreur réseau lors de l'envoi du mot de passe.", true);
      })
      .finally(function () {
        sendingPassword = false;
        if (btn) btn.disabled = false;
      });
  }

  function onDocClick(event) {
    var t = event.target;
    if (!t || !t.closest) return;

    var menuBtn = t.closest(".uc-menu-btn");
    if (menuBtn) {
      event.preventDefault();
      event.stopPropagation();
      var menu = ensurePortal();
      if (activeBtn === menuBtn && menu && !menu.hidden && menu.classList.contains("is-open")) {
        closePortal();
      } else {
        openPortal(menuBtn);
      }
      return;
    }

    if (t.closest("#uc-portal-send-password")) {
      event.preventDefault();
      event.stopPropagation();
      var sendEl = t.closest("#uc-portal-send-password");
      doSendPassword(
        sendEl.getAttribute("data-send-password-url") || "",
        sendEl.getAttribute("data-send-password-email") || ""
      );
      return;
    }

    if (t.closest("#uc-portal-delete")) {
      event.preventDefault();
      event.stopPropagation();
      openDeleteDialog(t.closest("#uc-portal-delete"));
      return;
    }

    if (t.closest("#user-delete-dialog-confirm")) {
      event.preventDefault();
      event.stopPropagation();
      var btn = t.closest("#user-delete-dialog-confirm");
      var url =
        btn.getAttribute("data-delete-url") ||
        pendingUrl ||
        (qs("#user-delete-dialog-form") &&
          qs("#user-delete-dialog-form").getAttribute("action")) ||
        "";
      doDelete(url);
      return;
    }

    if (t.closest("[data-uc-delete-close]")) {
      event.preventDefault();
      closeDeleteDialog();
      return;
    }

    if (t.closest("#uc-portal-menu") || t.closest("#user-delete-dialog .uc-delete-panel")) {
      return;
    }

    closePortal();
  }

  function onKey(event) {
    if (event.key === "Escape") {
      closePortal();
      closeDeleteDialog();
    }
  }

  function onScroll(event) {
    if (Date.now() < ignoreScrollUntil) return;
    // Nested container scroll (card grid) used to close the menu immediately.
    var target = event && event.target;
    if (target && target !== document && target !== document.documentElement && target !== document.body) {
      return;
    }
    closePortal();
  }

  function onSpaReady() {
    ensurePortal();
    ensureDialog();
    closePortal();
    closeDeleteDialog();
    var main = document.getElementById("main");
    if (main && window.Alpine && typeof window.Alpine.initTree === "function") {
      try {
        window.Alpine.initTree(main);
      } catch (e) {
        /* ignore */
      }
    }
  }

  document.addEventListener("click", onDocClick, true);
  document.addEventListener("keydown", onKey, true);
  window.addEventListener("scroll", onScroll, true);
  document.addEventListener("twoos:spa-ready", onSpaReady);

  window.__ucUsersMenu = {
    destroy: function () {
      document.removeEventListener("click", onDocClick, true);
      document.removeEventListener("keydown", onKey, true);
      window.removeEventListener("scroll", onScroll, true);
      document.removeEventListener("twoos:spa-ready", onSpaReady);
    },
  };

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onSpaReady);
  } else {
    onSpaReady();
  }
})();
