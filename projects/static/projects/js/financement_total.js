/**
 * Planning financier:
 * - choosing a Projet autofills FP, CMT and Total (if a financement exists)
 * - FP / CMT are independent: editing them does NOT change Total
 * - Total comes from the saved investissement_total (ex: CPC ligne IV)
 */
(function () {
  var BY_PROJECT_URL = "/projets/financement/by-project/";
  var lastProjectId = null;

  function jq() {
    if (window.django && window.django.jQuery) {
      return window.django.jQuery;
    }
    return window.jQuery || window.$ || null;
  }

  function findTotalTargets() {
    return Array.prototype.slice.call(
      document.querySelectorAll(
        ".js-investissement-total-live, #id_investissement_total_live"
      )
    );
  }

  function setTotals(displayValue) {
    var text = displayValue == null ? "0,00" : String(displayValue);
    findTotalTargets().forEach(function (target) {
      if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
        target.value = text;
      } else {
        target.textContent = text;
      }
    });
  }

  function setInputAmount(input, value) {
    if (!input) {
      return;
    }
    input.value = String(value);
  }

  function applyFinancementPayload(payload) {
    var fp = document.getElementById("id_fonds_propres_fp");
    var cmt = document.getElementById("id_credit_moyen_terme_cmt");
    if (!fp || !cmt) {
      return;
    }
    setInputAmount(fp, payload.fonds_propres_fp || "0.00");
    setInputAmount(cmt, payload.credit_moyen_terme_cmt || "0.00");
    // Total is independent from FP/CMT — use saved total only.
    setTotals(payload.investissement_total_display || "0,00");
  }

  function loadFinancementForProject(projectId) {
    if (!document.getElementById("id_fonds_propres_fp")) {
      return;
    }
    if (!projectId) {
      applyFinancementPayload({
        fonds_propres_fp: "0.00",
        credit_moyen_terme_cmt: "0.00",
        investissement_total_display: "0,00",
      });
      return;
    }

    fetch(BY_PROJECT_URL + "?project=" + encodeURIComponent(projectId), {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
      },
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (result.ok && result.payload && result.payload.ok) {
          applyFinancementPayload(result.payload);
        }
      })
      .catch(function () {});
  }

  function onProjectSelected(projectEl) {
    if (!projectEl) {
      return;
    }
    loadFinancementForProject(projectEl.value || "");
  }

  function bindSelect2Project(project) {
    var $ = jq();
    if (!$ || !project) {
      return false;
    }
    try {
      $(project)
        .off(".financementAutofill")
        .on(
          "select2:select.financementAutofill select2:clear.financementAutofill change.financementAutofill",
          function () {
            onProjectSelected(project);
          }
        );
      return true;
    } catch (err) {
      return false;
    }
  }

  function startProjectWatch() {
    if (window.__financementProjectWatch) {
      return;
    }
    window.__financementProjectWatch = window.setInterval(function () {
      var project = document.getElementById("id_project");
      var fp = document.getElementById("id_fonds_propres_fp");
      if (!project || !fp) {
        lastProjectId = null;
        return;
      }
      var projectId = project.value || "";
      if (projectId === lastProjectId) {
        return;
      }
      lastProjectId = projectId;
      onProjectSelected(project);
    }, 200);
  }

  function bindProjectSelect2() {
    var project = document.getElementById("id_project");
    if (!project || project.disabled) {
      return;
    }
    var tries = 0;
    var timer = window.setInterval(function () {
      tries += 1;
      if (bindSelect2Project(project) || tries >= 40) {
        window.clearInterval(timer);
      }
    }, 250);
  }

  function bind() {
    bindProjectSelect2();
    startProjectWatch();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }

  document.addEventListener("twoos:spa-ready", function () {
    lastProjectId = null;
    bind();
  });

  document.addEventListener(
    "change",
    function (event) {
      var target = event.target;
      if (target && target.id === "id_project") {
        onProjectSelected(target);
      }
    },
    true
  );
})();
