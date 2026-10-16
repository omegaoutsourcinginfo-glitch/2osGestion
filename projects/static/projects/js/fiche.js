(function () {
  var sections = document.querySelectorAll(".fiche-section");
  var tocLinks = document.querySelectorAll(".fiche-toc a");
  if (tocLinks.length && sections.length && "IntersectionObserver" in window) {
    var activeMap = {};
    var spy = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          activeMap[entry.target.id] = entry.isIntersecting;
        });
        var current = null;
        sections.forEach(function (section) {
          if (activeMap[section.id]) {
            current = section.id;
          }
        });
        tocLinks.forEach(function (link) {
          var href = link.getAttribute("href") || "";
          var id = href.charAt(0) === "#" ? href.slice(1) : "";
          link.classList.toggle("is-active", Boolean(current && id === current));
        });
      },
      { threshold: 0.25, rootMargin: "-15% 0px -55% 0px" }
    );
    sections.forEach(function (section) {
      spy.observe(section);
    });
  }

  var frame = document.getElementById("doc-frame");
  var image = document.getElementById("doc-image");
  var fallback = document.getElementById("doc-fallback");
  var title = document.getElementById("doc-title");
  var openLink = document.getElementById("doc-open");
  var items = document.querySelectorAll(".doc-item");

  function showDoc(button) {
    if (!button) {
      return;
    }
    var url = button.getAttribute("data-url") || "";
    var kind = button.getAttribute("data-kind") || "file";
    var label = button.getAttribute("data-label") || "Document";
    var previewable = button.getAttribute("data-previewable") === "1";

    items.forEach(function (item) {
      item.classList.toggle("is-active", item === button);
    });

    if (title) {
      title.textContent = label;
    }
    if (openLink) {
      openLink.href = url;
    }

    if (frame) {
      if (kind === "pdf") {
        frame.src = url;
        frame.classList.remove("hidden");
      } else {
        frame.removeAttribute("src");
        frame.classList.add("hidden");
      }
    }

    if (image) {
      if (kind === "image") {
        image.src = url;
        image.classList.remove("hidden");
      } else {
        image.removeAttribute("src");
        image.classList.add("hidden");
      }
    }

    if (fallback) {
      fallback.classList.toggle("hidden", previewable);
    }
  }

  items.forEach(function (item) {
    item.addEventListener("click", function () {
      showDoc(item);
    });
  });

  document.querySelectorAll(".doc-jump").forEach(function (link) {
    link.addEventListener("click", function () {
      var url = link.getAttribute("data-url");
      var match = null;
      items.forEach(function (item) {
        if (item.getAttribute("data-url") === url) {
          match = item;
        }
      });
      if (match) {
        showDoc(match);
      }
    });
  });
})();
