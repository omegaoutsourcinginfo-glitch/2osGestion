/**
 * User form — icon prefixes + placeholders on profile fields.
 */
(function () {
  var MAP = {
    id_email: { icon: "mail", placeholder: "email@exemple.com" },
    id_phone: { icon: "call", placeholder: "+212 6 …" },
    id_first_name: { icon: "person", placeholder: "Prénom" },
    id_last_name: { icon: "badge", placeholder: "Nom" },
    id_kind: { icon: "shield_person", placeholder: "" },
  };

  function decorate() {
    if (!document.querySelector(".uf-shell")) return;

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
