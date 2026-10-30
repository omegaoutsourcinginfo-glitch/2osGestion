/**
 * Global SPA navigation for the whole admin app (HTMX 2 / Unfold).
 * Any internal /admin or /projets link swaps #main instead of full reload.
 */
(function () {
  function ready(fn) {
    if (document.readyState === "loading") {
      document.addEventListener("DOMContentLoaded", fn);
    } else {
      fn();
    }
  }

  function ensureDashRoot() {
    var existing = document.getElementById("dash-root");
    if (existing) {
      return existing;
    }
    var content = document.getElementById("content");
    if (!content) {
      return null;
    }
    content.innerHTML = '<div class="studio" id="dash-root"></div>';
    return document.getElementById("dash-root");
  }

  function codeFromUrl(url) {
    if (!url) {
      return null;
    }
    try {
      var parsed = new URL(url, window.location.origin);
      return parsed.searchParams.get("projet") || parsed.searchParams.get("project");
    } catch (err) {
      return null;
    }
  }

  function activateTab(id) {
    if (!id) {
      return;
    }
    document.querySelectorAll(".pi-nav-inner [data-tab]").forEach(function (tab) {
      var on = tab.getAttribute("data-tab") === id;
      tab.classList.toggle("is-active", on);
      tab.setAttribute("aria-selected", on ? "true" : "false");
    });
  }

  function pushUrl(url) {
    if (!url || typeof history === "undefined" || !history.pushState) {
      return;
    }
    try {
      history.pushState({ htmx: true, twoos: true }, "", url);
      rememberSpaPath(url);
    } catch (err) {
      // ignore invalid URL
    }
  }

  function normalizePath(url) {
    try {
      return new URL(url, window.location.origin).pathname.replace(/\/$/, "") || "/";
    } catch (err) {
      return "";
    }
  }

  /** Path + query only (ignore hash). Used so Unfold tab switches never refetch. */
  function pathAndQuery(url) {
    try {
      var parsed = new URL(url || window.location.href, window.location.origin);
      return (parsed.pathname.replace(/\/$/, "") || "/") + (parsed.search || "");
    } catch (err) {
      return "";
    }
  }

  // Last path+query loaded into #main (hash ignored). Tab switches update hash only.
  var lastSpaPath = pathAndQuery(window.location.href);

  function rememberSpaPath(url) {
    lastSpaPath = pathAndQuery(url || window.location.href);
  }

  function isAlreadyOnPath(url) {
    return !!url && pathAndQuery(url) === lastSpaPath;
  }

  function updateSidebarActive(url) {
    var path = normalizePath(url);
    document.querySelectorAll("#nav-sidebar a[href], #nav-sidebar-inner a[href]").forEach(function (a) {
      var href = a.getAttribute("href");
      if (!href || href.charAt(0) === "#") {
        return;
      }
      var on = normalizePath(href) === path;
      a.classList.toggle("active", on);
      a.classList.toggle("bg-base-100", on);
      a.classList.toggle("font-semibold", on);
      a.classList.toggle("text-primary-600", on);
    });
  }

  function parseHref(href) {
    try {
      return new URL(href, window.location.origin);
    } catch (err) {
      return null;
    }
  }

  function isInternalAppUrl(url) {
    var parsed = typeof url === "string" ? parseHref(url) : url;
    if (!parsed || parsed.origin !== window.location.origin) {
      return false;
    }
    return (
      parsed.pathname.indexOf("/admin") === 0 ||
      parsed.pathname.indexOf("/projets") === 0
    );
  }

  function isSkippableNavLink(link) {
    if (!link || !link.getAttribute) {
      return true;
    }
    var href = link.getAttribute("href");
    if (!href || href === "#" || href.indexOf("javascript:") === 0 || href.indexOf("mailto:") === 0) {
      return true;
    }
    // In-page Unfold tabs (#general, #terrain_mere, …) must NOT trigger SPA reload.
    if (href.charAt(0) === "#") {
      return true;
    }
    if (link.getAttribute("target") === "_blank") {
      return true;
    }
    if (link.hasAttribute("download")) {
      return true;
    }
    if (link.closest("[data-no-spa]")) {
      return true;
    }
    // Inline formset "add another" rows must keep default behavior.
    if (link.classList.contains("add-row")) {
      return true;
    }
    var lower = href.toLowerCase();
    if (
      lower.indexOf("logout") >= 0 ||
      lower.indexOf("login") >= 0 ||
      lower.indexOf("/media/") >= 0 ||
      lower.indexOf("/static/") >= 0
    ) {
      return true;
    }
    var parsed = parseHref(href);
    if (!parsed || !isInternalAppUrl(parsed)) {
      return true;
    }
    // Same-page hash only (e.g. /admin/.../add/#general) — tab switch, not navigation.
    try {
      var here = new URL(window.location.href);
      if (
        parsed.origin === here.origin &&
        parsed.pathname.replace(/\/$/, "") === here.pathname.replace(/\/$/, "") &&
        parsed.search === here.search &&
        parsed.hash
      ) {
        return true;
      }
    } catch (err) {
      // ignore
    }
    // Django admin popup windows.
    if (parsed.searchParams.get("_popup")) {
      return true;
    }
    return false;
  }

  function isAdminSpaLink(link) {
    return !!(link && !isSkippableNavLink(link));
  }

  function isDashboardFicheUrl(href) {
    var parsed = parseHref(href);
    if (!parsed || !codeFromUrl(href)) {
      return false;
    }
    var path = parsed.pathname.replace(/\/$/, "") || "/";
    return path === "/admin";
  }

  function readActiveTab() {
    var hash = (window.location.hash || "").replace(/^#/, "");
    if (hash) {
      return hash;
    }
    // Keep the open primary tab when hash is cleared (formset add-row uses href="#").
    var current = document.body && document.body.getAttribute("data-active-tab");
    if (current) {
      return current;
    }
    return "general";
  }

  function addUnfoldInlineRow(addLink) {
    var formset = addLink.closest(".formset");
    var formsetWrapper = addLink.closest(".formset-wrapper");
    if (!formset || !formsetWrapper || !formset.dataset.inlineFormset) {
      return null;
    }
    var totalForms = formsetWrapper.querySelector("input[type=hidden][name$='TOTAL_FORMS']");
    var maxNumForms = formsetWrapper.querySelector("input[type=hidden][name$='MAX_NUM_FORMS']");
    var template = formset.querySelector(":scope > .empty-form");
    if (!totalForms || !maxNumForms || !template) {
      return null;
    }
    if (parseInt(totalForms.value, 10) >= parseInt(maxNumForms.value, 10)) {
      return null;
    }
    var options = JSON.parse(formset.dataset.inlineFormset).options;
    var index = formset.querySelectorAll(":scope > .form-group").length - 1;
    var row = template.cloneNode(true);
    row.classList.remove("empty-form");
    formset.insertBefore(row, template);
    var formRow = row.querySelector(":scope > .form-row");
    if (formRow) {
      formRow.innerHTML = formRow.innerHTML.replaceAll(/__prefix__/g, String(index));
    }
    row.innerHTML = row.innerHTML
      .split(options.prefix + "-__prefix__")
      .join(options.prefix + "-" + index)
      .split("__prefix__")
      .join(String(index));
    totalForms.value = String(parseInt(totalForms.value, 10) + 1);
    if (parseInt(totalForms.value, 10) >= parseInt(maxNumForms.value, 10)) {
      addLink.classList.add("hidden");
    }
    row.dispatchEvent(
      new CustomEvent("formsetGroup:added", {
        bubbles: true,
        detail: { formsetName: options.prefix, row: row, index: index },
      })
    );
    document.dispatchEvent(
      new CustomEvent("formset:added", {
        bubbles: true,
        detail: { formsetName: options.prefix, row: row, index: index },
      })
    );
    return row;
  }

  function syncBodyChangeFormClass() {
    if (!document.body) {
      return;
    }
    var path = (window.location.pathname || "").replace(/\/$/, "") || "/";
    var onChangeForm =
      /\/add$/.test(path) ||
      /\/change$/.test(path) ||
      !!document.querySelector("#content-main .tab-wrapper, #content-main [data-inline-type]");
    document.body.classList.toggle("change-form", onChangeForm);
  }

  function setAlpineActiveTab(tab) {
    try {
      var stack = document.body && document.body._x_dataStack;
      if (stack && stack[0] && Object.prototype.hasOwnProperty.call(stack[0], "activeTab")) {
        stack[0].activeTab = tab;
      }
    } catch (err) {
      // ignore
    }
  }

  function slugTab(value) {
    // Match Django/Unfold slugify for formset prefixes (keeps underscores):
    // Project_intervenants-group ↔ #project_intervenants
    return String(value || "")
      .replace(/-group$/, "")
      .toLowerCase();
  }

  /**
   * Keep only the active Unfold primary tab panel visible.
   * Sets body[data-active-tab] so CSS can force-hide inlines on General
   * even after Alpine re-applies styles on tab clicks.
   */
  function syncUnfoldPrimaryTabs() {
    syncBodyChangeFormClass();
    var form = document.querySelector(".change-form form, form.change-form, #content-main form");
    if (!form && !document.querySelector(".change-form") && !document.querySelector("#content-main .tab-wrapper")) {
      if (document.body) {
        document.body.removeAttribute("data-active-tab");
      }
      return;
    }
    var tab = readActiveTab() || "general";
    var tabSlug = slugTab(tab) || "general";
    if (document.body) {
      document.body.setAttribute("data-active-tab", tabSlug);
    }
    setAlpineActiveTab(tabSlug);

    document.querySelectorAll(".change-form [data-inline-type], #content-main [data-inline-type]").forEach(
      function (el) {
        var id = (el.id || "").replace(/-group$/, "");
        var idSlug = slugTab(id);
        // Match Unfold slugify: Project_intervenants-group ↔ #project_intervenants
        var on = tabSlug !== "general" && idSlug === tabSlug;
        el.classList.toggle("uf-tab-open", on);
        el.setAttribute("data-uf-tab", idSlug || "1");
        // Do not use el.hidden — it fights Alpine/CSS with display:none !important.
        el.removeAttribute("hidden");
        if (on) {
          el.style.removeProperty("display");
        }
      }
    );

    document.querySelectorAll(".change-form [x-show], #content-main [x-show]").forEach(function (el) {
      var expr = el.getAttribute("x-show") || "";
      // Nested Identification/Localisation/Description panels: Alpine-only.
      if (expr.indexOf("activeFieldsetTab") >= 0) {
        el.removeAttribute("hidden");
        return;
      }
      if (el.hasAttribute("data-inline-type")) {
        return;
      }
      var match = expr.match(/activeTab\s*==\s*['"]([^'"]+)['"]/);
      if (!match) {
        return;
      }
      var want = slugTab(match[1]);
      var on = want === tabSlug;
      el.classList.toggle("uf-tab-open", on);
      el.setAttribute("data-uf-tab", want);
      el.removeAttribute("hidden");
      // Clear Alpine display:none left from a stale activeTab after SPA.
      if (on) {
        el.style.removeProperty("display");
      }
    });

    // Clear any leftover hidden attrs on fieldset sub-tabs after SPA swaps.
    document.querySelectorAll(".tab-wrapper").forEach(function (wrap) {
      wrap.removeAttribute("hidden");
    });
  }

  function isPanelVisible(el) {
    if (!el) {
      return true;
    }
    if (el.classList && el.classList.contains("uf-tab-open")) {
      return true;
    }
    var style = window.getComputedStyle(el);
    if (style.display === "none" || style.visibility === "hidden") {
      return false;
    }
    return !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  }

  function selectPanel(el) {
    return (
      el.closest("[data-inline-type], .inline-group, [data-uf-tab]") ||
      el.closest(".tabular") ||
      null
    );
  }

  function panelMatchesActiveTab(panel) {
    if (!panel || !document.body) {
      return false;
    }
    var active = document.body.getAttribute("data-active-tab") || "";
    if (!active || active === "general") {
      return false;
    }
    var tab =
      panel.getAttribute("data-uf-tab") ||
      slugTab((panel.id || "").replace(/-group$/, ""));
    return !!(tab && slugTab(tab) === active);
  }

  function shouldEnhanceSelect(el) {
    var panel = selectPanel(el);
    if (!panel) {
      return true;
    }
    if (panelMatchesActiveTab(panel) || panel.classList.contains("uf-tab-open")) {
      return true;
    }
    return isPanelVisible(panel);
  }

  function styleSelect2Container($container) {
    if (!$container || !$container.length) {
      return;
    }
    $container.css({ width: "100%", "max-width": "28rem", display: "block" });
    $container.find(".select2-selection--single").css({
      "min-height": "2.5rem",
      display: "flex",
      "align-items": "center",
    });
  }

  function hideUnfoldSelectChevron(selectEl) {
    if (!selectEl) {
      return;
    }
    var wrap = selectEl.closest(".grow.relative, .relative") || selectEl.parentElement;
    if (!wrap) {
      return;
    }
    wrap.querySelectorAll(".material-symbols-outlined").forEach(function (icon) {
      if ((icon.textContent || "").trim() === "expand_more") {
        icon.style.display = "none";
      }
    });
  }

  function destroySelect2($el) {
    try {
      if ($el.data("select2")) {
        $el.select2("destroy");
      }
    } catch (err) {
      // ignore
    }
    var el = $el[0];
    if (el) {
      el.classList.remove("select2-hidden-accessible");
      el.removeAttribute("data-select2-id");
      el.removeAttribute("aria-hidden");
      el.removeAttribute("tabindex");
      el.style.removeProperty("display");
    }
    $el.next(".select2-container").remove();
    // Orphan containers sometimes sit after Unfold chevron
    if (el && el.parentElement) {
      el.parentElement.querySelectorAll(":scope > .select2-container").forEach(function (node) {
        node.remove();
      });
    }
  }

  function mountPlainSelect2($, $el, force) {
    var el = $el[0];
    if (!el || el.closest(".empty-form")) {
      return;
    }
    if (!shouldEnhanceSelect(el) && !force) {
      return;
    }
    var already = !!$el.data("select2");
    var hasContainer = !!(el.parentElement && el.parentElement.querySelector(".select2-container"));
    if (already && hasContainer && !force) {
      hideUnfoldSelectChevron(el);
      return;
    }
    destroySelect2($el);
    if (!el.getAttribute("data-placeholder")) {
      el.setAttribute("data-placeholder", "Rechercher…");
    }
    var hasEmptyOption = $el.find('option[value=""]').length > 0;
    var opts = {
      width: "100%",
      theme: "admin-autocomplete",
      minimumResultsForSearch: 0,
      allowClear: !el.required && hasEmptyOption,
      placeholder: el.getAttribute("data-placeholder") || "Rechercher…",
      dropdownParent: $(document.body),
    };
    try {
      $el.select2(opts);
    } catch (err1) {
      try {
        delete opts.theme;
        delete opts.language;
        $el.select2(opts);
      } catch (err2) {
        return;
      }
    }
    el.classList.add("select2-hidden-accessible");
    el.style.setProperty("display", "none", "important");
    hideUnfoldSelectChevron(el);
    styleSelect2Container($el.next(".select2-container"));
    // Select2 may insert container as last child of parent, not next sibling
    if (!$el.next(".select2-container").length && el.parentElement) {
      styleSelect2Container($(el.parentElement.querySelector(".select2-container")));
    }
  }

  function reinitDjangoAutocomplete(root, force) {
    try {
      if (!window.django || !django.jQuery) {
        return;
      }
      var $ = django.jQuery;
      if (!$.fn.select2 && window.jQuery && window.jQuery.fn && window.jQuery.fn.select2) {
        // Recover if django.jQuery lost the plugin after a second jquery.init.
        $.fn.select2 = window.jQuery.fn.select2;
      }
      var $scope = root ? $(root) : $(document);

      // Autocomplete FK fields (Intervenants, Projet, …)
      if ($.fn.djangoAdminSelect2) {
        $scope.find("select.admin-autocomplete").not("[name*=__prefix__]").each(function () {
          var el = this;
          var $el = $(el);
          if (!shouldEnhanceSelect(el) && !force) {
            return;
          }
          if (!el.getAttribute("data-placeholder")) {
            el.setAttribute("data-placeholder", "Rechercher…");
          }
          destroySelect2($el);
          $el.djangoAdminSelect2();
          el.style.setProperty("display", "none", "important");
          hideUnfoldSelectChevron(el);
          styleSelect2Container($el.next(".select2-container"));
        });
      }

      // Plain dropdowns: same searchable Select2 design site-wide.
      if ($.fn.select2) {
        $scope
          .find("select")
          .not(".admin-autocomplete")
          .not("[name*=__prefix__]")
          .not("[multiple]")
          .each(function () {
            mountPlainSelect2($, $(this), !!force);
          });
      }
    } catch (err2) {
      // ignore autocomplete re-init errors
    }
  }

  function reinitSwappedUi(root) {
    if (!root) {
      return;
    }
    // Safety net: SPA landed on a form with autocomplete but admin JS missing.
    if (
      root.querySelector &&
      root.querySelector("select.admin-autocomplete") &&
      !hasDjangoAutocomplete()
    ) {
      window.location.reload();
      return;
    }
    if (typeof htmx !== "undefined") {
      htmx.process(root);
    }
    if (window.Alpine && typeof window.Alpine.initTree === "function") {
      try {
        window.Alpine.initTree(root);
      } catch (err) {
        // ignore alpine re-init errors
      }
    }
    var dash = document.getElementById("dash-root");
    if (dash) {
      dash.classList.add("is-ready");
    }
    syncUnfoldPrimaryTabs();
    reinitDjangoAutocomplete(root, true);
    window.setTimeout(function () {
      syncUnfoldPrimaryTabs();
      reinitDjangoAutocomplete(root || document, true);
    }, 0);
    document.dispatchEvent(new CustomEvent("twoos:spa-ready", { detail: { root: root } }));
  }

  function spaGet(url, target, swap, push, source, select) {
    if (typeof htmx === "undefined") {
      window.location.href = push || url;
      return;
    }
    if (target === "#dash-root" && !ensureDashRoot()) {
      window.location.href = push || url;
      return;
    }

    var opts = {
      target: target,
      swap: swap || "innerHTML",
    };
    if (source) {
      opts.source = source;
    }
    if (select) {
      opts.select = select;
    }

    // Hash is client-only (fiche tabs); strip it from the HTMX request URL.
    var requestUrl = url;
    try {
      var req = new URL(url, window.location.origin);
      requestUrl = req.pathname + req.search;
    } catch (errReq) {
      // keep url
    }

    var result = htmx.ajax("GET", requestUrl, opts);
    if (push) {
      pushUrl(push);
      updateSidebarActive(push);
    }
    if (source && source.getAttribute("data-tab")) {
      activateTab(source.getAttribute("data-tab"));
    }
    return result;
  }

  function isChangeFormPath(url) {
    var path = normalizePath(url);
    return /\/add$/.test(path) || /\/change$/.test(path);
  }

  function hasDjangoAutocomplete() {
    try {
      return !!(
        window.django &&
        django.jQuery &&
        django.jQuery.fn &&
        django.jQuery.fn.djangoAdminSelect2
      );
    } catch (err) {
      return false;
    }
  }

  function isAuthPageUrl(url) {
    var path = normalizePath(url);
    return (
      path === "/admin/login" ||
      path.indexOf("/admin/login") === 0 ||
      path.indexOf("/logout") >= 0 ||
      path.indexOf("/password_reset") >= 0
    );
  }

  function navigateAdmin(url, source) {
    // Login / logout must be full page loads so the CSRF cookie and form match.
    if (isAuthPageUrl(url)) {
      window.location.href = url;
      return;
    }
    // Change-form pages need django.jQuery + Select2 from form.media.
    // Those scripts are not on the dashboard — SPA swap leaves Intervenants empty.
    if (isChangeFormPath(url) && !hasDjangoAutocomplete()) {
      window.location.href = url;
      return;
    }
    if (!document.getElementById("main")) {
      window.location.href = url;
      return;
    }
    spaGet(url, "#main", "innerHTML", url, source, "#main > *");
  }

  function openFicheFromHref(href) {
    var code = codeFromUrl(href);
    if (!code) {
      navigateAdmin(href, null);
      return;
    }
    if (!document.getElementById("dash-root")) {
      navigateAdmin(href, null);
      return;
    }
    spaGet(
      "/projets/" + encodeURIComponent(code) + "/fiche/",
      "#dash-root",
      "outerHTML",
      href,
      null
    );
  }

  function go(href, source) {
    // Same path already in #main (possibly different hash) — keep form data.
    if (isAlreadyOnPath(href)) {
      syncUnfoldPrimaryTabs();
      window.setTimeout(function () {
        reinitDjangoAutocomplete(document, false);
      }, 0);
      return;
    }
    if (isDashboardFicheUrl(href)) {
      openFicheFromHref(href);
      return;
    }
    rememberSpaPath(href);
    navigateAdmin(href, source || null);
  }

  function onClick(event) {
    if (event.defaultPrevented || event.button !== 0) {
      return;
    }
    if (event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) {
      return;
    }

    // Unfold formset "add another" uses href="#". Handle it ourselves so we
    // keep the current tab hash and reliably clone the empty-form row.
    var addRow =
      event.target.closest && event.target.closest("a.add-row");
    if (addRow) {
      event.preventDefault();
      event.stopImmediatePropagation();
      var newRow = addUnfoldInlineRow(addRow);
      if (newRow && window.TwoosSpa) {
        // Select2 / tabs refresh via formset listeners below.
      }
      return;
    }
    var deleteRow =
      event.target.closest && event.target.closest("a.delete-template");
    if (deleteRow) {
      event.preventDefault();
      // Let Unfold handle delete; only block the hash jump.
      return;
    }

    var detailLink = event.target.closest && event.target.closest("a.project-detail-link[href]");
    if (detailLink && !isSkippableNavLink(detailLink)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      openFicheFromHref(detailLink.getAttribute("href"));
      return;
    }

    var el = event.target.closest && event.target.closest("a[hx-get], button[hx-get]");
    if (el && typeof htmx !== "undefined") {
      var hxUrl = el.getAttribute("hx-get");
      if (hxUrl) {
        event.preventDefault();
        event.stopImmediatePropagation();
        spaGet(
          hxUrl,
          el.getAttribute("hx-target") || "#dash-root",
          el.getAttribute("hx-swap") || "innerHTML",
          el.getAttribute("hx-push-url"),
          el
        );
        return;
      }
    }

    var link = event.target.closest && event.target.closest("a[href]");
    if (link && isAdminSpaLink(link)) {
      event.preventDefault();
      event.stopImmediatePropagation();
      go(link.getAttribute("href"), link);
    }
  }

  function onSubmit(event) {
    var form = event.target;
    if (!form || !form.tagName || form.tagName.toLowerCase() !== "form") {
      return;
    }
    // Never SPA-intercept auth forms (login is POST; keep this explicit).
    if (
      form.id === "login-form" ||
      form.id === "logout-form" ||
      (form.getAttribute("action") || "").indexOf("login") >= 0 ||
      (form.getAttribute("action") || "").indexOf("logout") >= 0
    ) {
      return;
    }
    if ((form.getAttribute("method") || "get").toLowerCase() !== "get") {
      return;
    }
    if (form.target === "_blank" || form.closest("[data-no-spa]")) {
      return;
    }

    var action = form.getAttribute("action") || window.location.href;
    if (!isInternalAppUrl(action)) {
      return;
    }

    event.preventDefault();
    event.stopImmediatePropagation();

    var url = parseHref(action);
    if (!url) {
      window.location.href = action;
      return;
    }
    var data = new FormData(form);
    data.forEach(function (value, key) {
      if (value !== null && value !== undefined && String(value) !== "") {
        url.searchParams.append(key, String(value));
      }
    });
    go(url.toString(), form);
  }

  function afterSwap(event) {
    var target = event.detail && event.detail.target;
    if (!target) {
      return;
    }
    // If HTMX followed a redirect to login, do a real navigation (fresh CSRF).
    if (
      target.querySelector &&
      (target.querySelector("#login-form") || target.querySelector("body.login"))
    ) {
      window.location.href = "/admin/login/";
      return;
    }
    rememberSpaPath(window.location.href);
    reinitSwappedUi(target);
    updateSidebarActive(window.location.href);
  }

  function afterRequest(event) {
    var xhr = event.detail && event.detail.xhr;
    if (!xhr) {
      return;
    }
    try {
      var finalUrl = xhr.responseURL || "";
      if (finalUrl && isAuthPageUrl(finalUrl)) {
        window.location.href = finalUrl;
        return;
      }
    } catch (errAuth) {
      // ignore
    }
    if (!event.detail.successful) {
      return;
    }
    try {
      var doc = new DOMParser().parseFromString(xhr.responseText, "text/html");
      if (doc.querySelector("#login-form")) {
        window.location.href = "/admin/login/";
        return;
      }
      if (doc.querySelector("#main") && doc.title) {
        document.title = doc.title;
      }
    } catch (err) {
      // ignore
    }
  }

  function onPopState() {
    if (typeof htmx === "undefined" || !document.getElementById("main")) {
      window.location.reload();
      return;
    }
    // Hash-only history entries (Unfold tabs / alpine.anchor) must NOT reload #main
    // — that wiped every field the user typed when switching tabs.
    go(window.location.href, null);
  }

  function onPrimaryTabClick(event) {
    var link = event.target && event.target.closest && event.target.closest("a[href^='#']");
    if (!link) {
      return;
    }
    var href = link.getAttribute("href") || "";
    if (!href || href === "#" || href.indexOf("#") !== 0) {
      return;
    }
    var slug = slugTab(href.slice(1)) || "general";
    if (document.body) {
      // Apply immediately so CSS hides inlines before paint when returning to General.
      document.body.setAttribute("data-active-tab", slug);
      setAlpineActiveTab(slug);
    }
    // Defer so Alpine/CSS show the panel first, then force Select2 remount.
    function afterTabShown() {
      syncUnfoldPrimaryTabs();
      reinitDjangoAutocomplete(document, true);
    }
    window.setTimeout(afterTabShown, 0);
    window.setTimeout(afterTabShown, 50);
    window.setTimeout(afterTabShown, 150);
    window.setTimeout(afterTabShown, 300);
  }

  function onHashChange() {
    var hash = (window.location.hash || "").replace(/^#/, "");
    // Bare "#" from formset add-row must not switch back to General.
    if (!hash) {
      return;
    }
    syncUnfoldPrimaryTabs();
    window.setTimeout(function () {
      reinitDjangoAutocomplete(document, true);
    }, 0);
    window.setTimeout(function () {
      reinitDjangoAutocomplete(document, true);
    }, 50);
    window.setTimeout(function () {
      reinitDjangoAutocomplete(document, true);
    }, 200);
  }

  ready(function () {
    document.addEventListener("click", onClick, true);
    document.addEventListener("click", onPrimaryTabClick, true);
    document.addEventListener("submit", onSubmit, true);
    document.addEventListener("htmx:afterSwap", afterSwap);
    document.addEventListener("htmx:afterSettle", afterSwap);
    document.addEventListener("htmx:afterRequest", afterRequest);
    function afterFormsetRow(row) {
      // Keep current primary tab (e.g. #documents) after "add another".
      syncUnfoldPrimaryTabs();
      window.setTimeout(function () {
        reinitDjangoAutocomplete(row || document, true);
      }, 0);
      window.setTimeout(function () {
        reinitDjangoAutocomplete(row || document, true);
      }, 50);
      window.setTimeout(function () {
        reinitDjangoAutocomplete(document, true);
      }, 150);
    }
    document.addEventListener("formset:added", function (event) {
      afterFormsetRow((event.detail && event.detail.row) || event.target);
    });
    document.addEventListener("formsetGroup:added", function (event) {
      afterFormsetRow((event.detail && event.detail.row) || event.target);
    });
    window.addEventListener("popstate", onPopState);
    window.addEventListener("hashchange", onHashChange);
    var root = document.getElementById("dash-root");
    if (root) {
      root.classList.add("is-ready");
    }
    updateSidebarActive(window.location.href);
    syncUnfoldPrimaryTabs();
    reinitDjangoAutocomplete(document, true);
    window.setTimeout(function () {
      syncUnfoldPrimaryTabs();
      reinitDjangoAutocomplete(document, true);
    }, 0);
    window.setTimeout(function () {
      syncUnfoldPrimaryTabs();
      reinitDjangoAutocomplete(document, true);
    }, 100);
    window.setTimeout(function () {
      reinitDjangoAutocomplete(document, true);
    }, 350);
  });

  window.TwoosSpa = {
    openFicheFromHref: openFicheFromHref,
    spaGet: spaGet,
    ensureDashRoot: ensureDashRoot,
    navigateAdmin: navigateAdmin,
    go: go,
    syncUnfoldPrimaryTabs: syncUnfoldPrimaryTabs,
    reinitDjangoAutocomplete: reinitDjangoAutocomplete,
  };
})();
