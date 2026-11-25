/**
 * User form — icon prefixes + placeholders on profile fields.
 */
(function () {
  var MAP = {
    id_email: { icon: "mail", placeholder: "email@exemple.com" },
    id_phone: { icon: "call", placeholder: "+212 6 …" },
    id_first_name: { icon: "person", placeholder: "Prénom" },
    id_last_name: { icon: "badge", placeholder: "Nom" },
  };

  function attachSubmitFooter() {
    var shell = document.querySelector(".uf-shell");
    var submit = document.getElementById("submit-row");
    if (!shell || !submit) return;
    if (submit.parentElement === shell) return;
    shell.appendChild(submit);
    shell.classList.add("has-submit");
  }

  function decorate() {
    if (!document.querySelector(".uf-shell")) return;
    attachSubmitFooter();

    Object.keys(MAP).forEach(function (id) {
      var el = document.getElementById(id);
      if (!el || el.closest(".uf-input-wrap")) return;

      var meta = MAP[id];
      var wrap = document.createElement("div");
      wrap.className = "uf-input-wrap";
      wrap.setAttribute("data-uf-prefix", meta.icon);

      var icon = document.createElement("span");
      icon.className = "material-symbols-outlined uf-input-prefix";
      icon.setAttribute("aria-hidden", "true");
      icon.textContent = meta.icon;

      el.parentNode.insertBefore(wrap, el);
      wrap.appendChild(icon);
      wrap.appendChild(el);

      // Inline fallback: Unfold CSS loads after ours and clears input borders.
      wrap.style.setProperty("border", "1px solid #d0d7e2", "important");
      wrap.style.setProperty("border-radius", "0.9rem", "important");
      wrap.style.setProperty("background", "#f8fafc", "important");
      el.style.setProperty("border", "0", "important");
      el.style.setProperty("box-shadow", "none", "important");
      el.style.setProperty("outline", "none", "important");
      el.style.setProperty("background", "transparent", "important");

      if (meta.placeholder && !el.getAttribute("placeholder")) {
        el.setAttribute("placeholder", meta.placeholder);
      }
      el.classList.add("uf-has-prefix");
    });
  }

  function onReady() {
    decorate();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", onReady);
  } else {
    onReady();
  }
  document.addEventListener("twoos:spa-ready", onReady);
})();
