/**
 * When a select marked [data-autre-precision] is set to AUTRE,
 * show a small popup to fill the linked « Si Autre, préciser » field.
 */
(function () {
  var AUTRE = "AUTRE";

  function findPrecisionInput(select) {
    if (!select || !select.name) {
      return null;
    }
    var precisionName = select.name.replace(
      /type_(permis|intervenant)\b/,
      "precision_autre"
    );
    if (precisionName === select.name) {
      return null;
    }
    return (
      document.querySelector('[name="' + precisionName + '"]') ||
      document.getElementById("id_" + precisionName)
    );
  }

  function findPrecisionRow(input) {
    if (!input) {
      return null;
    }
    return input.closest(
      ".form-row, .field-box, .field-precision_autre, [class*='field-precision_autre']"
    );
  }

  function setPrecisionVisible(select, visible) {
    var input = findPrecisionInput(select);
    var row = findPrecisionRow(input);
    if (row) {
      row.style.display = visible ? "" : "none";
    }
    if (input && !visible && select.value !== AUTRE) {
      input.value = "";
    }
  }

  function ensureDialog() {
    var existing = document.getElementById("autre-precision-dialog");
    if (existing) {
      return existing;
    }
    var dialog = document.createElement("div");
    dialog.id = "autre-precision-dialog";
    dialog.setAttribute("role", "dialog");
    dialog.setAttribute("aria-modal", "true");
    dialog.style.cssText =
      "display:none;position:fixed;inset:0;z-index:9999;align-items:center;justify-content:center;background:rgba(15,23,42,.45);";
    dialog.innerHTML =
      '<div style="background:#fff;border-radius:12px;max-width:420px;width:92%;padding:1.25rem 1.35rem;box-shadow:0 20px 45px rgba(0,0,0,.2);">' +
      '<h3 style="margin:0 0 .35rem;font-size:1.05rem;">Si Autre, préciser</h3>' +
      '<p style="margin:0 0 .9rem;color:#64748b;font-size:.9rem;">Indiquez le détail pour le type « Autre ».</p>' +
      '<input id="autre-precision-input" type="text" maxlength="255" ' +
      'style="width:100%;box-sizing:border-box;border:1px solid #cbd5e1;border-radius:8px;padding:.55rem .7rem;margin-bottom:1rem;" />' +
      '<div style="display:flex;gap:.5rem;justify-content:flex-end;">' +
      '<button type="button" id="autre-precision-cancel" style="padding:.45rem .9rem;border-radius:8px;border:1px solid #cbd5e1;background:#fff;cursor:pointer;">Annuler</button>' +
      '<button type="button" id="autre-precision-ok" style="padding:.45rem .9rem;border-radius:8px;border:0;background:#0f172a;color:#fff;cursor:pointer;">Valider</button>' +
      "</div></div>";
    document.body.appendChild(dialog);
    return dialog;
  }

  function openDialog(select) {
    var input = findPrecisionInput(select);
    if (!input) {
      return;
    }
    setPrecisionVisible(select, true);
    var dialog = ensureDialog();
    var field = document.getElementById("autre-precision-input");
    var ok = document.getElementById("autre-precision-ok");
    var cancel = document.getElementById("autre-precision-cancel");
    field.value = input.value || "";
    dialog.style.display = "flex";
    field.focus();
    field.select();

    function close() {
      dialog.style.display = "none";
      ok.onclick = null;
      cancel.onclick = null;
      dialog.onclick = null;
      field.onkeydown = null;
    }

    ok.onclick = function () {
      var value = (field.value || "").trim();
      input.value = value;
      input.dispatchEvent(new Event("input", { bubbles: true }));
      input.dispatchEvent(new Event("change", { bubbles: true }));
      close();
    };
    cancel.onclick = function () {
      if (!(input.value || "").trim()) {
        select.value = "";
        setPrecisionVisible(select, false);
        select.dispatchEvent(new Event("change", { bubbles: true }));
      }
      close();
    };
    dialog.onclick = function (event) {
      if (event.target === dialog) {
        cancel.onclick();
      }
    };
    field.onkeydown = function (event) {
      if (event.key === "Enter") {
        event.preventDefault();
        ok.onclick();
      }
      if (event.key === "Escape") {
        event.preventDefault();
        cancel.onclick();
      }
    };
  }

  function onTypeChange(select) {
    var isAutre = select.value === AUTRE;
    setPrecisionVisible(select, isAutre);
    if (isAutre) {
      openDialog(select);
    }
  }

  function bindSelect(select) {
    if (!select || select.dataset.autreBound === "1") {
      return;
    }
    select.dataset.autreBound = "1";
    setPrecisionVisible(select, select.value === AUTRE);
    select.addEventListener("change", function () {
      onTypeChange(select);
    });
  }

  function bindAll() {
    document
      .querySelectorAll("select[data-autre-precision], select[name*='type_permis'], select[name*='type_intervenant']")
      .forEach(bindSelect);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bindAll);
  } else {
    bindAll();
  }
  document.addEventListener("formset:added", bindAll);
})();
