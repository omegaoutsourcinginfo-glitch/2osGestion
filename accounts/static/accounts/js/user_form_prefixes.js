/**
 * User form — Alpine.js (+ HTMX SPA re-init via twoos:spa-ready / htmx:afterSettle).
 */
(function () {
  var MAP = {
    id_email: { icon: "mail", placeholder: "email@exemple.com" },
    id_phone: { icon: "call", placeholder: "+212 6 …" },
    id_first_name: { icon: "person", placeholder: "Prénom" },
    id_last_name: { icon: "badge", placeholder: "Nom" },
  };

  var WRAP_CLS =
    "uf-input-wrap relative block w-full overflow-hidden rounded-none border border-base-300 bg-base-50 shadow-none dark:border-base-600 dark:bg-base-800";
  var ICON_CLS =
    "material-symbols-outlined uf-input-prefix pointer-events-none absolute left-3 top-1/2 z-[2] -translate-y-1/2 text-lg text-base-400";
  var INPUT_CLS =
    "uf-has-prefix w-full rounded-none border-0 bg-transparent py-2.5 pl-10 pr-3 shadow-none outline-none ring-0 focus:border-0 focus:shadow-none focus:outline-none focus:ring-0 dark:bg-transparent dark:text-font-default-dark";

  function hide(el) {
    if (el) el.classList.add("hidden");
  }

  function userForm() {
    return {
      init: function () {
        this.$nextTick(function () {
          this.decorate();
        }.bind(this));
      },

      decorate: function () {
        var shell = this.$el;
        if (!shell || !shell.classList.contains("uf-shell")) return;

        this.hideUnfoldChrome(shell);
        this.flattenChrome(shell);
        this.attachSubmit(shell);
        this.decorateInputs(shell);
      },

      hideUnfoldChrome: function (shell) {
        var isAdd = document.body.classList.contains("user-add-form");

        document
          .querySelectorAll(
            "#content > h1, .uf-body > h1, .uf-body .breadcrumb, #content-start"
          )
          .forEach(hide);

        document
          .querySelectorAll('a[title="Retour à la liste"]')
          .forEach(function (a) {
            if (isAdd) {
              a.classList.remove("hidden");
              a.classList.add("inline-flex");
            } else {
              hide(a);
            }
          });

        shell
          .querySelectorAll(
            "fieldset > h2, .fieldset-heading, fieldset legend"
          )
          .forEach(hide);

      },

      flattenChrome: function (shell) {
        shell.classList.add("bg-white", "shadow-none");

        shell.querySelectorAll("fieldset").forEach(function (fs) {
          fs.classList.add(
            "m-0",
            "rounded-none",
            "border-0",
            "bg-transparent",
            "p-4",
            "shadow-none"
          );
        });

        shell.querySelectorAll(".form-rows").forEach(function (rows) {
          rows.classList.add("block", "rounded-none", "shadow-none");
          rows.classList.remove("shadow", "shadow-xs", "shadow-sm");
        });

        shell.querySelectorAll('[class*="shadow"]').forEach(function (el) {
          el.classList.remove(
            "shadow",
            "shadow-xs",
            "shadow-sm",
            "shadow-md",
            "shadow-lg"
          );
          el.classList.add("shadow-none");
        });

        shell
          .querySelectorAll('[class*="rounded"], .user-alert, .uf-input-wrap')
          .forEach(function (el) {
            Array.from(el.classList).forEach(function (c) {
              if (c.indexOf("rounded") === 0 && c !== "rounded-none") {
                el.classList.remove(c);
              }
            });
            el.classList.add("rounded-none");
          });

        shell.querySelectorAll('[class*="border-b"]').forEach(function (el) {
          el.classList.remove(
            "border-b",
            "border-base-200",
            "dark:border-base-800"
          );
          el.classList.add("border-b-0");
        });
      },

      // Move Tailwind submit_line into .form-rows (classes live in HTML, not here).
      attachSubmit: function (shell) {
        var submit = document.getElementById("submit-row");
        if (!submit) return;

        var rows =
          shell.querySelector("fieldset .form-rows") ||
          shell.querySelector(".form-rows") ||
          shell.querySelector("fieldset") ||
          shell.querySelector("form");
        if (!rows) return;

        rows.appendChild(submit);
        shell.classList.add("has-submit");
      },

      decorateInputs: function (shell) {
        Object.keys(MAP).forEach(function (id) {
          var el = shell.querySelector("#" + id) || document.getElementById(id);
          if (!el || el.closest(".uf-input-wrap")) return;

          var meta = MAP[id];
          var wrap = document.createElement("div");
          wrap.className = WRAP_CLS;
          wrap.setAttribute("data-uf-prefix", meta.icon);

          var icon = document.createElement("span");
          icon.className = ICON_CLS;
          icon.setAttribute("aria-hidden", "true");
          icon.textContent = meta.icon;

          el.parentNode.insertBefore(wrap, el);
          wrap.appendChild(icon);
          wrap.appendChild(el);
          el.classList.add.apply(el.classList, INPUT_CLS.split(/\s+/));

          if (meta.placeholder && !el.getAttribute("placeholder")) {
            el.setAttribute("placeholder", meta.placeholder);
          }
        });
      },
    };
  }

  function registerAlpine() {
    if (!window.Alpine || typeof window.Alpine.data !== "function") return;
    // Avoid double-register errors on SPA reloads of this script.
    try {
      window.Alpine.data("userForm", userForm);
    } catch (e) {
      /* already registered */
    }
  }

  function bootShell(root) {
    var shell = (root || document).querySelector
      ? (root || document).querySelector(".uf-shell")
      : null;
    if (!shell) return;

    if (window.Alpine && typeof window.Alpine.initTree === "function") {
      if (!shell._x_dataStack) {
        shell.setAttribute("x-data", "userForm");
        shell.setAttribute("x-init", "init()");
        try {
          window.Alpine.initTree(shell);
        } catch (e) {
          /* ignore */
        }
      } else {
        // Already Alpine-bound — call decorate again after HTMX swap.
        var data = shell._x_dataStack && shell._x_dataStack[0];
        if (data && typeof data.decorate === "function") data.decorate();
      }
    }
  }

  document.addEventListener("alpine:init", registerAlpine);
  if (window.Alpine) registerAlpine();

  // HTMX SPA: after #main settles, re-init Alpine user form
  document.body.addEventListener("htmx:afterSettle", function (ev) {
    var t = ev.target;
    if (t && (t.id === "main" || (t.querySelector && t.querySelector(".uf-shell")))) {
      registerAlpine();
      bootShell(t.id === "main" ? t : document);
    }
  });

  document.addEventListener("twoos:spa-ready", function () {
    registerAlpine();
    bootShell(document);
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", function () {
      registerAlpine();
      bootShell(document);
    });
  } else {
    registerAlpine();
    bootShell(document);
  }
})();
