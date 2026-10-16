(function () {
  function parseAmount(value) {
    if (value == null || value === "") {
      return 0;
    }
    var normalized = String(value).trim().replace(/\s/g, "").replace(",", ".");
    var amount = Number(normalized);
    return Number.isFinite(amount) ? amount : 0;
  }

  function formatAmount(value) {
    return value.toLocaleString("fr-FR", {
      minimumFractionDigits: 2,
      maximumFractionDigits: 2,
    });
  }

  function findTotalTarget() {
    var byId = document.getElementById("id_investissement_total_live");
    if (byId) {
      return byId;
    }

    var input = document.getElementById("id_investissement_total");
    if (input) {
      return input;
    }

    var labels = document.querySelectorAll("label");
    for (var i = 0; i < labels.length; i++) {
      if ((labels[i].textContent || "").indexOf("Total investissement") === -1) {
        continue;
      }
      var row = labels[i].closest(".form-row, .field-box, div");
      if (!row) {
        continue;
      }
      var readonly = row.querySelector(".readonly, [class*='readonly']");
      if (readonly) {
        return readonly;
      }
    }
    return null;
  }

  function updateTotal() {
    var fp = document.getElementById("id_fonds_propres_fp");
    var cmt = document.getElementById("id_credit_moyen_terme_cmt");
    var target = findTotalTarget();
    if (!fp || !cmt || !target) {
      return;
    }

    var total = parseAmount(fp.value) + parseAmount(cmt.value);
    var formatted = formatAmount(total);

    if (target.tagName === "INPUT" || target.tagName === "TEXTAREA") {
      target.value = formatted;
    } else {
      target.textContent = formatted;
    }
  }

  function bind() {
    var fp = document.getElementById("id_fonds_propres_fp");
    var cmt = document.getElementById("id_credit_moyen_terme_cmt");
    if (!fp || !cmt) {
      return;
    }
    ["input", "change", "keyup", "blur"].forEach(function (eventName) {
      fp.addEventListener(eventName, updateTotal);
      cmt.addEventListener(eventName, updateTotal);
    });
    updateTotal();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", bind);
  } else {
    bind();
  }
})();
