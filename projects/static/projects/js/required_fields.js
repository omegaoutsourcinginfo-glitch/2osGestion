/**
 * Required-field UX:
 * - NEVER show native browser "Please fill out this field" tooltip
 * - Treat Unfold asterisk (*) labels as required (inlines often lack HTML required)
 * - Validate fields in every tab (even if hidden), open that tab, scroll, mark red
 */
(function () {
  var INVALID = "field-invalid";
  var VALIDATED = "was-validated";

  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function hideTopErrorNotes(root) {
    (root || document)
      .querySelectorAll(".errornote, p.errornote")
      .forEach(function (el) {
        el.hidden = true;
        el.style.display = "none";
      });
  }

  function disableNativeValidation(form) {
    if (!form) {
      return;
    }
    form.setAttribute("novalidate", "novalidate");
    form.noValidate = true;
  }

  function syncTabs() {
    if (window.TwoosSpa && typeof window.TwoosSpa.syncUnfoldPrimaryTabs === "function") {
      window.TwoosSpa.syncUnfoldPrimaryTabs();
    }
  }

  function isInTabPanel(el) {
    return !!(
      el &&
      el.closest(
        "[data-inline-type], [data-uf-tab], .tab-wrapper, .inline-group, .js-inline-admin-formset"
      )
    );
  }

  function isInlineRowBlank(row) {
    var fields = row.querySelectorAll("input, select, textarea");
    for (var i = 0; i < fields.length; i++) {
      var f = fields[i];
      var t = (f.type || "").toLowerCase();
      if (t === "hidden" || t === "submit" || t === "button") {
        continue;
      }
      if (f.name && (f.name.indexOf("DELETE") >= 0 || f.name.indexOf("__prefix__") >= 0)) {
        continue;
      }
      if (t === "file") {
        if (f.files && f.files.length) {
          return false;
        }
        continue;
      }
      if (t === "checkbox" || t === "radio") {
        if (f.checked && !f.defaultChecked) {
          return false;
        }
        continue;
      }
      var val = String(f.value || "").trim();
      if (!val) {
        continue;
      }
      // Unchanged default <select> (e.g. unité m²) does not mean the row was started
      if (f.tagName === "SELECT" && (f.value === f.defaultValue || f.selectedIndex <= 0)) {
        continue;
      }
      if (val !== String(f.defaultValue || "").trim()) {
        return false;
      }
      if (f.tagName !== "SELECT") {
        return false;
      }
    }
    return true;
  }

  function isOptionalBlankExtraInline(el) {
    var row = el.closest(".inline-related");
    var group = el.closest("[data-inline-type], .inline-group, .js-inline-admin-formset");
    if (!row || !group || row.classList.contains("empty-form")) {
      return false;
    }
    var match = (el.name || "").match(/-(\d+)-/);
    if (!match) {
      return false;
    }
    var idx = parseInt(match[1], 10);
    var initialEl = group.querySelector('input[name$="-INITIAL_FORMS"]');
    var maxEl = group.querySelector('input[name$="-MAX_NUM_FORMS"]');
    var initialCount = initialEl ? parseInt(initialEl.value, 10) || 0 : 0;
    var maxNum = maxEl ? parseInt(maxEl.value, 10) : NaN;
    // Single-slot inlines (Terrain Mère, Permis): always validate row 0
    if (maxNum === 1 && idx === 0) {
      return false;
    }
    if (idx < initialCount) {
      return false;
    }
    return isInlineRowBlank(row);
  }

  function isOptionalMediaInlineField(el) {
    // Documents / images / intervenants are never required to create/save.
    var name = el.name || "";
    if (
      name.indexOf("documents-") === 0 ||
      name.indexOf("images-") === 0 ||
      name.indexOf("Project_intervenants-") === 0
    ) {
      return true;
    }
    if (
      el.closest(
        "#documents-group, #images-group, #Project_intervenants-group, [id*='intervenants-group']"
      )
    ) {
      return true;
    }
    return false;
  }

  function isSkippableField(el) {
    if (!el || el.disabled) {
      return true;
    }
    var type = (el.type || "").toLowerCase();
    if (type === "hidden" || type === "submit" || type === "button" || type === "reset") {
      return true;
    }
    if (el.name && el.name.indexOf("__prefix__") >= 0) {
      return true;
    }
    if (el.closest(".empty-form")) {
      return true;
    }
    // Soft-deleted inline row
    var row = el.closest(".inline-related");
    if (row) {
      var del = row.querySelector('input[type="checkbox"][name$="-DELETE"]');
      if (del && del.checked) {
        return true;
      }
    }
    // Documents / images: optional attachments (never block Enregistrer)
    if (isOptionalMediaInlineField(el)) {
      return true;
    }
    // Optional empty "extra" inline rows (intervenants, …) — like Django formsets
    if (isOptionalBlankExtraInline(el)) {
      return true;
    }
    // Truly hidden widgets — but NOT Unfold tab panels (we open the tab instead)
    if (el.closest("[hidden]") && !isInTabPanel(el)) {
      return true;
    }
    return false;
  }

  /** HTML required OR Unfold red asterisk on the label. */
  function isMarkedRequired(el) {
    if (!el) {
      return false;
    }
    if (el.required || el.getAttribute("aria-required") === "true") {
      return true;
    }
    var row = el.closest(".form-row, .field-box, .flex.flex-col, [class*='field-']");
    if (!row) {
      return false;
    }
    var label = row.querySelector("label");
    if (!label) {
      return false;
    }
    if (label.querySelector(".text-red-600, .text-red-500")) {
      return true;
    }
    return /\*\s*$/.test((label.textContent || "").replace(/\s+/g, " ").trim()) ||
      (label.textContent || "").indexOf("*") >= 0;
  }

  function isEmptyValue(el) {
    var type = (el.type || "").toLowerCase();
    if (type === "checkbox") {
      return isMarkedRequired(el) && !el.checked;
    }
    if (type === "radio") {
      var group = document.querySelectorAll('input[type="radio"][name="' + el.name + '"]');
      return ![].slice.call(group).some(function (r) {
        return r.checked;
      });
    }
    if (type === "file") {
      return !(el.files && el.files.length);
    }
    return !String(el.value || "").trim();
  }

  function markInvalid(el, on) {
    if (!el) {
      return;
    }
    el.classList.toggle(INVALID, !!on);
    var row = el.closest(".form-row, .field-box, [class*='field-']");
    if (row) {
      row.classList.toggle(INVALID, !!on);
      row.classList.toggle("errors", !!on);
      row.classList.toggle("group", true);
    }
    if (on) {
      el.setAttribute("aria-invalid", "true");
      el.setAttribute("data-twoos-invalid", "1");
      // Inline !important so red shows even if cached CSS is stale.
      el.style.setProperty("border-color", "#dc2626", "important");
      el.style.setProperty("background-color", "#fef2f2", "important");
      el.style.setProperty("box-shadow", "0 0 0 3px rgba(220, 38, 38, 0.25)", "important");
    } else {
      el.removeAttribute("aria-invalid");
      el.removeAttribute("data-twoos-invalid");
      el.style.removeProperty("border-color");
      el.style.removeProperty("background-color");
      el.style.removeProperty("box-shadow");
    }
  }

  function clearMarks(form) {
    form.querySelectorAll("." + INVALID).forEach(function (el) {
      markInvalid(el, false);
    });
    form.querySelectorAll("[aria-invalid='true']").forEach(function (el) {
      el.removeAttribute("aria-invalid");
    });
  }

  function setPrimaryTab(slug) {
    if (!slug) {
      return;
    }
    if (document.body) {
      document.body.setAttribute("data-active-tab", slug);
    }
    try {
      var stack = document.body && document.body._x_dataStack;
      if (stack && stack[0] && Object.prototype.hasOwnProperty.call(stack[0], "activeTab")) {
        stack[0].activeTab = slug;
      }
    } catch (err) {
      // ignore
    }
    try {
      history.replaceState(null, "", "#" + slug);
    } catch (err2) {
      window.location.hash = slug;
    }
    syncTabs();
  }

  function setFieldsetTab(name) {
    if (!name) {
      return false;
    }
    setPrimaryTab("general");

    var root = document.querySelector("[x-data*='activeFieldsetTab']");
    try {
      if (window.Alpine && typeof window.Alpine.$data === "function" && root) {
        window.Alpine.$data(root).activeFieldsetTab = name;
      } else if (root && root._x_dataStack && root._x_dataStack[0]) {
        root._x_dataStack[0].activeFieldsetTab = name;
      }
    } catch (err) {
      // ignore
    }

    // Force panel visibility + tab "active" class (Alpine x-bind can lag after SPA).
    // Never set the HTML `hidden` attribute — it is display:none !important and
    // blocks later Alpine x-show when the user clicks Identification/Localisation.
    document.querySelectorAll(".tab-wrapper").forEach(function (wrap) {
      var on = wrap.classList.contains("fieldset-" + name);
      wrap.removeAttribute("hidden");
      if (on) {
        wrap.style.removeProperty("display");
        wrap.style.display = "block";
      } else {
        wrap.style.display = "none";
      }
    });
    document.querySelectorAll("a").forEach(function (link) {
      var on =
        link.getAttribute("x-on:click") ||
        link.getAttribute("@click") ||
        "";
      if (on.indexOf("activeFieldsetTab") < 0) {
        return;
      }
      var match = on.match(/activeFieldsetTab\s*=\s*['"]([^'"]+)['"]/);
      var isOn = !!(match && match[1] === name);
      link.classList.toggle("active", isOn);
    });
    return true;
  }

  function openTabFor(el) {
    // 1) Nested fieldset tabs inside General (Identification / Localisation / Description)
    var wrap = el.closest(".tab-wrapper");
    if (wrap) {
      var name = null;
      [].slice.call(wrap.classList).forEach(function (cls) {
        if (cls.indexOf("fieldset-") === 0) {
          name = cls.slice("fieldset-".length);
        }
      });
      if (name) {
        setFieldsetTab(name);
        return;
      }
    }

    // 2) Top-level inline tabs: Terrain Mère, Permis, Intervenants…
    var inline = el.closest(
      "[data-inline-type], .inline-group, .js-inline-admin-formset"
    );
    if (inline) {
      var id = inline.id || "";
      var slug = id.replace(/-group$/, "").toLowerCase();
      if (slug) {
        setPrimaryTab(slug);
        return;
      }
    }

    setPrimaryTab("general");
  }

  function focusField(el) {
    openTabFor(el);
    syncTabs();
    window.setTimeout(function () {
      syncTabs();
      try {
        el.scrollIntoView({ behavior: "smooth", block: "center" });
      } catch (err) {
        el.scrollIntoView(true);
      }
      try {
        el.focus({ preventScroll: true });
      } catch (err2) {
        el.focus();
      }
    }, 180);
  }

  function collectInvalid(form) {
    return [].slice.call(form.querySelectorAll("input, select, textarea")).filter(function (el) {
      if (isSkippableField(el)) {
        return false;
      }
      if (!isMarkedRequired(el)) {
        return false;
      }
      return isEmptyValue(el);
    });
  }

  function validateForm(form) {
    disableNativeValidation(form);
    hideTopErrorNotes(form.closest("#content, #main") || document);
    form.classList.add(VALIDATED);
    clearMarks(form);
    var invalid = collectInvalid(form);
    invalid.forEach(function (el) {
      markInvalid(el, true);
    });
    if (invalid.length) {
      focusField(invalid[0]);
      return false;
    }
    return true;
  }

  function formFromSubmitter(el) {
    if (!el) {
      return null;
    }
    if (el.form) {
      return el.form;
    }
    var formId = el.getAttribute("form");
    if (formId) {
      return document.getElementById(formId);
    }
    return el.closest("form");
  }

  function submitWithoutNativeValidation(form, btn) {
    disableNativeValidation(form);
    if (btn && btn.name) {
      var existing = form.querySelector(
        'input[type="hidden"][data-spa-submit="' + btn.name + '"]'
      );
      if (!existing) {
        existing = document.createElement("input");
        existing.type = "hidden";
        existing.name = btn.name;
        existing.value = btn.value || "";
        existing.setAttribute("data-spa-submit", btn.name);
        form.appendChild(existing);
      } else {
        existing.value = btn.value || "";
      }
    }
    HTMLFormElement.prototype.submit.call(form);
  }

  function bindForm(form) {
    if (!form) {
      return;
    }
    disableNativeValidation(form);
    if (form.dataset.requiredFieldsBound === "1") {
      return;
    }
    form.dataset.requiredFieldsBound = "1";

    form.addEventListener(
      "submit",
      function (event) {
        disableNativeValidation(form);
        if (!validateForm(form)) {
          event.preventDefault();
          event.stopImmediatePropagation();
        }
      },
      true
    );

    function clearIfFixed(event) {
      var el = event.target;
      if (!el || !el.matches || !el.matches("input, select, textarea")) {
        return;
      }
      if (!isEmptyValue(el)) {
        markInvalid(el, false);
      }
    }
    form.addEventListener("input", clearIfFixed);
    form.addEventListener("change", clearIfFixed);
  }

  function onSubmitClick(event) {
    if (event.button !== 0) {
      return;
    }
    var btn =
      event.target.closest &&
      event.target.closest(
        'button[type="submit"], input[type="submit"], button[name="_save"]'
      );
    if (!btn) {
      return;
    }
    var form = formFromSubmitter(btn);
    if (!form || (form.id && form.id.indexOf("logout") >= 0)) {
      return;
    }
    if ((form.getAttribute("method") || "post").toLowerCase() === "get") {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    bindForm(form);
    disableNativeValidation(form);

    if (validateForm(form)) {
      submitWithoutNativeValidation(form, btn);
    }
  }

  function openTabFromErrorBadge() {
    var badge = document.querySelector(
      "#tabs-items a .bg-red-500, nav a .bg-red-500"
    );
    if (!badge) {
      return false;
    }
    var link = badge.closest("a[href^='#']");
    if (!link) {
      return false;
    }
    var href = link.getAttribute("href") || "";
    var slug = href.replace(/^#/, "");
    if (!slug) {
      return false;
    }
    setPrimaryTab(slug);
    return true;
  }

  function enhanceServerErrors(root) {
    hideTopErrorNotes(root);
    var scope = root || document;
    var first = null;
    var selectors = [
      ".form-row.errors input",
      ".form-row.errors select",
      ".form-row.errors textarea",
      "td.errors input",
      "td.errors select",
      "td.errors textarea",
      ".errors input:not([type='hidden'])",
      ".errors select",
      ".errors textarea",
      ".errorlist",
    ].join(", ");
    scope.querySelectorAll(selectors).forEach(function (el) {
      if (el.classList && el.classList.contains("errorlist")) {
        var near =
          el.parentElement &&
          el.parentElement.querySelector("input, select, textarea");
        if (near && !isSkippableField(near)) {
          markInvalid(near, true);
          if (!first) {
            first = near;
          }
        }
        return;
      }
      if (isSkippableField(el)) {
        return;
      }
      markInvalid(el, true);
      if (!first) {
        first = el;
      }
    });
    if (first) {
      var form = first.closest("form");
      if (form) {
        form.classList.add(VALIDATED);
        disableNativeValidation(form);
      }
      focusField(first);
      return;
    }
    // No field found, but Unfold shows a red count on a tab — open that tab.
    openTabFromErrorBadge();
  }

  function boot(root) {
    var scope = root || document;
    hideTopErrorNotes(scope);
    scope.querySelectorAll("form").forEach(function (form) {
      if (form.id && form.id.indexOf("logout") >= 0) {
        return;
      }
      if ((form.getAttribute("method") || "post").toLowerCase() === "get" && !form.id) {
        return;
      }
      bindForm(form);
    });
    enhanceServerErrors(scope);
  }

  function onFieldsetTabClick(event) {
    var link = event.target && event.target.closest && event.target.closest("a");
    if (!link) {
      return;
    }
    var on =
      link.getAttribute("x-on:click") ||
      link.getAttribute("@click") ||
      "";
    var match = on.match(/activeFieldsetTab\s*=\s*['"]([^'"]+)['"]/);
    if (!match) {
      return;
    }
    // After our validation may have set inline styles; re-apply cleanly on user click.
    window.setTimeout(function () {
      setFieldsetTab(match[1]);
    }, 0);
  }

  ready(function () {
    document.addEventListener("click", onSubmitClick, true);
    document.addEventListener("click", onFieldsetTabClick, false);
    boot(document);
  });

  document.addEventListener("htmx:afterSwap", function (event) {
    boot(event.detail && event.detail.target);
  });
  document.addEventListener("htmx:afterSettle", function (event) {
    boot(event.detail && event.detail.target);
  });
  document.addEventListener("twoos:spa-ready", function (event) {
    boot(event.detail && event.detail.root);
  });
})();
