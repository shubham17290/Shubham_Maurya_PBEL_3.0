(function () {
  "use strict";

  var form = document.getElementById("news-form");
  var textarea = document.getElementById("news_input");
  var counter = document.getElementById("char-count");
  var submit = document.getElementById("submit-btn");
  var spinner = document.getElementById("spinner");
  var result = document.getElementById("result");
  var minChars = 50;
  var maxChars = 50000;

  function updateCounter() {
    if (!textarea || !counter) return;
    var len = textarea.value.trim().length;
    counter.textContent = len + " / " + maxChars + " characters";
    counter.classList.toggle("warn", len > 0 && len < minChars);
    counter.classList.toggle("ok", len >= minChars);
  }

  if (textarea) {
    textarea.addEventListener("input", updateCounter);
    updateCounter();
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      var text = textarea.value.trim();
      if (text.length < minChars) {
        showResult("Please enter at least " + minChars + " characters.", "warning");
        return;
      }
      setLoading(true);
      fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: text }),
      })
        .then(function (res) { return res.json().then(function (d) { return { status: res.status, data: d }; }); })
        .then(function (r) {
          setLoading(false);
          if (!r.data.success) {
            showResult(r.data.error || "Prediction failed.", "danger");
            return;
          }
          var pct = Math.round(r.data.confidence * 100);
          var cls = r.data.prediction === "Real News" ? "real" : "fake";
          var msg = r.data.prediction + " (" + pct + "% confidence)";
          if (r.data.low_confidence) msg += " - low confidence";
          showResult(msg, cls);
        })
        .catch(function () {
          setLoading(false);
          showResult("Network error. Please try again.", "danger");
        });
    });
  }

  function setLoading(on) {
    if (submit) submit.disabled = on;
    if (spinner) spinner.classList.toggle("hidden", !on);
  }

  function showResult(message, kind) {
    if (!result) return;
    result.textContent = message;
    result.className = "result result-" + kind;
    result.setAttribute("aria-live", "polite");
  }
})();