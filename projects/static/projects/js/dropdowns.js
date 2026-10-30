/**
 * Final Select2 pass for all admin dropdowns.
 * Loaded last (after Django form.media jquery/select2/autocomplete).
 */
(function () {
  function run(force) {
    try {
      if (window.TwoosSpa && typeof window.TwoosSpa.reinitDjangoAutocomplete === "function") {
        window.TwoosSpa.reinitDjangoAutocomplete(document, force !== false);
        return;
      }
    } catch (err) {
      // fall through
    }
    // Minimal fallback if spa_nav is missing
    try {
      if (!window.django || !django.jQuery || !django.jQuery.fn.select2) {
        return;
      }
      var $ = django.jQuery;
      $("select")
        .not(".admin-autocomplete")
        .not("[name*=__prefix__]")
        .not("[multiple]")
        .each(function () {
          var $el = $(this);
          if (this.closest && this.closest(".empty-form")) {
            return;
          }
          if ($el.data("select2")) {
            try {
              $el.select2("destroy");
            } catch (e1) {
              // ignore
            }
            $el.next(".select2-container").remove();
          }
          $el.select2({
            width: "100%",
            theme: "admin-autocomplete",
            minimumResultsForSearch: 0,
            allowClear: false,
            placeholder: this.getAttribute("data-placeholder") || "Rechercher…",
            dropdownParent: $(document.body),
          });
          this.style.setProperty("display", "none", "important");
        });
    } catch (err2) {
      // ignore
    }
  }

  function schedule() {
    run(true);
    window.setTimeout(function () {
      run(true);
    }, 50);
    window.setTimeout(function () {
      run(true);
    }, 250);
    window.setTimeout(function () {
      run(true);
    }, 800);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", schedule);
  } else {
    schedule();
  }
  window.addEventListener("load", function () {
    schedule();
  });
  document.addEventListener("formset:added", function (event) {
    window.setTimeout(function () {
      if (window.TwoosSpa && window.TwoosSpa.reinitDjangoAutocomplete) {
        window.TwoosSpa.reinitDjangoAutocomplete(event.target || document, true);
      } else {
        run(true);
      }
    }, 30);
  });
})();
