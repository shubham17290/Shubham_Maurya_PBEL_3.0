/* History pages: relative timestamps, auto-applied filters, and the
 * clear-history confirmation dialog (progressive enhancement — all features
 * have working no-JS fallbacks; the server requires an explicit confirm field).
 */
(function () {
  "use strict";

  /* ---------- relative timestamps ---------- */
  function relativeTime(date) {
    var seconds = Math.round((Date.now() - date.getTime()) / 1000);
    var future = seconds < 0;
    var abs = Math.abs(seconds);
    var text;
    if (abs < 45) text = "just now";
    else if (abs < 90) text = "1 minute ago";
    else if (abs < 3600) text = Math.round(abs / 60) + " minutes ago";
    else if (abs < 5400) text = "1 hour ago";
    else if (abs < 86400) text = Math.round(abs / 3600) + " hours ago";
    else if (abs < 129600) text = "yesterday";
    else if (abs < 2592000) text = Math.round(abs / 86400) + " days ago";
    else if (abs < 5184000) text = "1 month ago";
    else if (abs < 31536000) text = Math.round(abs / 2592000) + " months ago";
    else text = Math.round(abs / 31536000) + " years ago";
    return future ? "in " + text : text;
  }

  var times = document.querySelectorAll("time.js-relative");
  for (var i = 0; i < times.length; i++) {
    var node = times[i];
    var iso = node.getAttribute("datetime");
    if (!iso) continue;
    var parsed = new Date(iso);
    if (isNaN(parsed.getTime())) continue; // keep server-rendered fallback text
    var exact = parsed.toLocaleString();
    node.textContent = relativeTime(parsed);
    node.title = exact;
  }

  /* ---------- auto-apply label filter (single change event per selection) ---------- */
  var autoSelect = document.querySelector("select[data-auto-submit='true']");
  var filterForm = document.getElementById("history-filter");
  if (autoSelect && filterForm) {
    autoSelect.addEventListener("change", function () {
      filterForm.submit();
    });
  }

  /* ---------- clear-history confirmation dialog ---------- */
  var clearBtn = document.getElementById("clear-btn");
  var dialog = document.getElementById("clear-dialog");
  var confirmInput = document.getElementById("clear-confirm");
  var clearForm = document.getElementById("clear-form");

  if (clearBtn && dialog && clearForm && confirmInput && typeof dialog.showModal === "function") {
    clearBtn.addEventListener("click", function (e) {
      e.preventDefault();
      dialog.showModal();
    });

    var cancelBtn = document.getElementById("clear-cancel");
    if (cancelBtn) {
      cancelBtn.addEventListener("click", function () {
        dialog.close(); // cancel: nothing is submitted or deleted
      });
    }

    var confirmBtn = document.getElementById("clear-confirm-btn");
    if (confirmBtn) {
      confirmBtn.addEventListener("click", function () {
        confirmInput.value = "1";
        dialog.close();
        if (typeof clearForm.requestSubmit === "function") {
          clearForm.requestSubmit();
        } else {
          clearForm.submit();
        }
      });
    }

    // Escape closes the dialog with no deletion (native <dialog> behavior).
  }
})();
