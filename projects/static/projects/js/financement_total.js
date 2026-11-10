/**
 * Planning financier + CPC tab:
 * - choosing a Projet autofills FP, CMT and Total (if a financement exists)
 * - FP / CMT are independent: editing them does NOT change Total
 * - Total comes from CPC ligne IV (live preview) or saved investissement_total
 */
(function () {
  var BY_PROJECT_URL = "/projets/financement/by-project/";
  var CPC_PREVIEW_URL = "/projets/cpc/preview-total/";
  var lastProjectId = null;

  function jq() {
    if (window.django && window.django.jQuery) {
      return window.django.jQuery;
    }
    return window.jQuery || window.$ || null;
  }

  function getCookie(name) {
    var cookies = document.cookie ? document.cookie.split(";") : [];
    for (var i = 0; i < cookies.length; i += 1) {
      var cookie = cookies[i].trim();
      if (cookie.indexOf(name + "=") === 0) {
        return decodeURIComponent(cookie.substring(name.length + 1));
      }
    }
    return "";
  }

  function csrfToken() {
    var input = document.querySelector("input[name=csrfmiddlewaretoken]");
    if (input && input.value) {
      return input.value;
    }
    return getCookie("csrftoken");
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

  function isCpcFileInput(el) {
    if (!el || el.type !== "file") {
      return false;
    }
    var name = el.name || "";
    var id = el.id || "";
    return (
      name === "cpc_excel" ||
      name.indexOf("-cpc_excel") !== -1 ||
      id === "id_cpc_excel" ||
      id.indexOf("-cpc_excel") !== -1
    );
  }

  function previewCpcTotal(fileInput) {
    if (!fileInput || !fileInput.files || !fileInput.files[0]) {
      setTotals("0,00");
      return;
    }
    var file = fileInput.files[0];
    var formData = new FormData();
    formData.append("cpc_excel", file, file.name);

    fetch(CPC_PREVIEW_URL, {
      method: "POST",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-With": "XMLHttpRequest",
        "X-CSRFToken": csrfToken(),
      },
      body: formData,
    })
      .then(function (response) {
        return response.json().then(function (payload) {
          return { ok: response.ok, payload: payload };
        });
      })
      .then(function (result) {
        if (result.ok && result.payload && result.payload.ok) {
          setTotals(result.payload.total_display || result.payload.total || "0,00");
          return;
        }
        var err =
          (result.payload && result.payload.error) ||
          "Impossible de lire le fichier CPC.";
        setTotals("0,00");
        window.console && console.warn("[CPC preview]", err);
      })
      .catch(function (err) {
        setTotals("0,00");
        window.console && console.warn("[CPC preview]", err);
      });
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
      if (isCpcFileInput(target)) {
        previewCpcTotal(target);
      }
    },
    true
  );
})();
