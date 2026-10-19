/* Fake News Detection — home page behavior.
 *
 * All dynamic content is inserted with safe DOM APIs (textContent / createElement);
 * no innerHTML is used with server or model data.
 */
(function () {
  "use strict";

  var form = document.getElementById("news-form");
  var textarea = document.getElementById("news_input");
  var counter = document.getElementById("char-count");
  var submit = document.getElementById("submit-btn");
  var submitLabel = document.getElementById("submit-label");
  var spinner = document.getElementById("spinner");
  var exampleBtn = document.getElementById("example-btn");
  var formStatus = document.getElementById("form-status");

  var resultCard = document.getElementById("result-card");
  var verdictIcon = document.getElementById("verdict-icon");
  var resultHeading = document.getElementById("result-heading");
  var verdictCaption = document.getElementById("verdict-caption");
  var confidenceBlock = document.getElementById("confidence-block");
  var confidenceValue = document.getElementById("confidence-value");
  var confidenceMeter = document.getElementById("confidence-meter");
  var confidenceFill = document.getElementById("confidence-fill");
  var lowConfidenceNote = document.getElementById("low-confidence-note");
  var probabilitiesBlock = document.getElementById("probabilities");
  var probRows = document.getElementById("prob-rows");
  var explanation = document.getElementById("explanation");
  var expSupporting = document.getElementById("exp-supporting");
  var expOpposing = document.getElementById("exp-opposing");
  var expNote = document.getElementById("exp-note");
  var feedback = document.getElementById("feedback");
  var feedbackStatus = document.getElementById("feedback-status");

  var minChars = counter ? parseInt(counter.getAttribute("data-min"), 10) || 50 : 50;
  var maxChars = counter ? parseInt(counter.getAttribute("data-max"), 10) || 50000 : 50000;
  var lastPredictionId = null;

  var EXAMPLE_TEXT =
    "The Reserve Bank of India announced that the repo rate will remain unchanged " +
    "after the latest Monetary Policy Committee meeting, citing stable inflation and " +
    "steady growth in the services sector.";

  /* ---------- small DOM helpers (safe by construction) ---------- */
  function el(tag, className, text) {
    var node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function clear(node) {
    while (node && node.firstChild) node.removeChild(node.firstChild);
  }

  function setHidden(node, hidden) {
    if (node) node.hidden = !!hidden;
  }

  function announce(message) {
    if (formStatus) formStatus.textContent = message;
  }

  function isValidProbability(value) {
    return typeof value === "number" && isFinite(value) && value >= 0 && value <= 1;
  }

  function isValidConfidence(value) {
    return typeof value === "number" && isFinite(value) && value > 0 && value <= 1;
  }

  /* ---------- character counter ---------- */
  function updateCounter() {
    if (!textarea || !counter) return;
    var len = textarea.value.trim().length;
    counter.textContent = len.toLocaleString() + " / " + maxChars.toLocaleString() + " characters";
    counter.classList.toggle("warn", len > 0 && len < minChars);
    counter.classList.toggle("ok", len >= minChars && len <= maxChars);
  }

  /* ---------- form state ---------- */
  function setLoading(on) {
    if (submit) {
      submit.disabled = on;
      submit.setAttribute("aria-disabled", on ? "true" : "false");
    }
    if (spinner) spinner.classList.toggle("hidden", !on);
    if (submitLabel) submitLabel.textContent = on ? "Checking…" : "Check news";
    if (form) form.setAttribute("aria-busy", on ? "true" : "false");
  }

  function showError(message) {
    showResultCard();
    resultCard.classList.remove("is-real", "is-fake");
    resultCard.classList.add("is-unknown");
    if (verdictIcon) verdictIcon.textContent = "!";
    if (resultHeading) resultHeading.textContent = "Prediction unavailable";
    if (verdictCaption) verdictCaption.textContent = message || "Please try again.";
    setHidden(confidenceBlock, true);
    setHidden(probabilitiesBlock, true);
    setHidden(explanation, true);
    setHidden(lowConfidenceNote, true);
    setHidden(feedback, true);
  }

  function showResultCard() {
    if (!resultCard) return;
    resultCard.hidden = false;
    var fallback = document.getElementById("result-fallback");
    setHidden(fallback, true);
  }

  /* ---------- result rendering ---------- */
  function renderConfidence(confidence) {
    if (!confidenceBlock) return;
    if (!isValidConfidence(confidence)) {
      setHidden(confidenceBlock, true);
      return;
    }
    var pct = Math.round(confidence * 1000) / 10; // one decimal
    setHidden(confidenceBlock, false);
    if (confidenceValue) confidenceValue.textContent = pct + "%";
    if (confidenceFill) confidenceFill.style.setProperty("--value", Math.max(0, Math.min(100, pct)) + "%");
    if (confidenceMeter) confidenceMeter.setAttribute("aria-label", "Model confidence: " + pct + "%");
  }

  /* Probability display: uses the label -> value mapping returned by the API,
   * never positional order, so class order in the model cannot be misread. */
  function renderProbabilities(probabilities) {
    if (!probRows || !probabilitiesBlock) return;
    clear(probRows);

    var labels = ["Real News", "Fake News"];
    var values = [];
    var sum = 0;
    for (var i = 0; i < labels.length; i++) {
      var v = probabilities[labels[i]];
      if (!isValidProbability(v)) {
        setHidden(probabilitiesBlock, true);
        return;
      }
      values.push(v);
      sum += v;
    }
    var extraKeys = Object.keys(probabilities).filter(function (k) {
      return labels.indexOf(k) === -1;
    });
    if (extraKeys.length > 0) {
      setHidden(probabilitiesBlock, true);
      return;
    }
    // Require the two class probabilities to be consistent (sum ~ 1).
    if (Math.abs(sum - 1) > 0.02) {
      setHidden(probabilitiesBlock, true);
      return;
    }

    for (var j = 0; j < labels.length; j++) {
      var isReal = labels[j] === "Real News";
      var row = el("div", "class-prob-row " + (isReal ? "is-real" : "is-fake"));
      row.appendChild(el("span", "class-prob-row__name", labels[j]));

      var meter = el("div", "meter");
      meter.setAttribute("role", "img");
      var pct = Math.round(values[j] * 1000) / 10;
      meter.setAttribute("aria-label", labels[j] + ": " + pct + "%");
      var fill = el("div", "meter__fill");
      fill.style.setProperty("--value", pct + "%");
      meter.appendChild(fill);
      row.appendChild(meter);

      row.appendChild(el("span", "class-prob-row__value", pct + "%"));
      probRows.appendChild(row);
    }
    setHidden(probabilitiesBlock, false);
  }

  /* Feature contribution chips.
   *
   * Bar widths are normalized against the largest absolute contribution among
   * the displayed features (both directions combined), so bars are comparable
   * within one result. Contributions are TF-IDF x model weight; the printed
   * value keeps its sign but is not a percentage, so no % label is used.
   */
  function renderExplanation(exp) {
    if (!explanation || !expSupporting || !expOpposing || !expNote) return;
    clear(expSupporting);
    clear(expOpposing);

    var all = [];
    ["supporting", "opposing"].forEach(function (key) {
      var items = exp && exp[key];
      if (Array.isArray(items)) {
        items.forEach(function (it) {
          if (it && typeof it.contribution === "number" && isFinite(it.contribution)) {
            all.push(Math.abs(it.contribution));
          }
        });
      }
    });
    var maxAbs = all.length ? Math.max.apply(null, all) : 0;

    function fill(listNode, items) {
      if (!Array.isArray(items) || items.length === 0) {
        listNode.appendChild(el("li", "chip muted small", "No strong word signals in this direction."));
        return;
      }
      items.forEach(function (it) {
        var li = el("li", "chip");
        li.appendChild(el("span", "chip__word", String(it.feature)));

        var bar = el("span", "chip__bar");
        var fillEl = el("span", "chip__bar-fill");
        var width = maxAbs > 0 ? (Math.abs(it.contribution) / maxAbs) * 100 : 0;
        fillEl.style.setProperty("--value", Math.max(1, width).toFixed(1) + "%");
        fillEl.style.width = Math.max(1, width).toFixed(1) + "%";
        bar.appendChild(fillEl);
        li.appendChild(bar);

        var value = typeof it.contribution === "number" ? it.contribution : 0;
        li.appendChild(el("span", "chip__value", (value >= 0 ? "+" : "") + value.toFixed(4)));
        listNode.appendChild(li);
      });
    }

    if (!exp) {
      setHidden(explanation, true);
      return;
    }
    fill(expSupporting, exp.supporting);
    fill(expOpposing, exp.opposing);
    expNote.textContent = exp.note || "";
    // Show the section whenever explanation data arrived; empty directions
    // render an explicit "no strong signals" message instead of blank space.
    setHidden(explanation, false);
  }

  function renderFeedback(predictionId) {
    lastPredictionId = predictionId;
    if (!feedback) return;
    var available = typeof predictionId === "number" && isFinite(predictionId);
    setHidden(feedback, !available);
    if (feedbackStatus) feedbackStatus.textContent = "";
    var buttons = feedback.querySelectorAll("button[data-feedback]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].disabled = false;
    }
  }

  function showSuccess(data) {
    showResultCard();
    var isReal = data.prediction === "Real News";
    resultCard.classList.remove("is-unknown");
    resultCard.classList.toggle("is-real", isReal);
    resultCard.classList.toggle("is-fake", !isReal);

    if (verdictIcon) verdictIcon.textContent = isReal ? "✓" : "✕";
    if (resultHeading) resultHeading.textContent = data.prediction;
    if (verdictCaption) {
      verdictCaption.textContent = isReal
        ? "The model classifies this article as real news."
        : "The model classifies this article as fake news.";
    }

    renderConfidence(typeof data.confidence === "number" ? data.confidence : null);
    renderProbabilities(data.probabilities || null);
    renderExplanation(data.explanation || null);
    renderFeedback(data.prediction_id);
    setHidden(lowConfidenceNote, !data.low_confidence);

    announce("Prediction: " + data.prediction + (isValidConfidence(data.confidence)
      ? ", model confidence " + Math.round(data.confidence * 100) + "%"
      : ""));
    if (resultHeading) {
      resultHeading.focus({ preventScroll: false });
    }
  }

  /* ---------- submission ---------- */
  function submitPrediction() {
    var text = textarea.value.trim();
    if (text.length < minChars) {
      announce("Please enter at least " + minChars + " characters.");
      showError("Please enter at least " + minChars + " characters before checking.");
      return;
    }
    if (text.length > maxChars) {
      announce("Text is too long. Please enter at most " + maxChars.toLocaleString() + " characters.");
      showError("Text is too long. Please enter at most " + maxChars.toLocaleString() + " characters.");
      return;
    }

    setLoading(true);
    announce("Analyzing the article…");

    fetch("/api/predict", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ text: text }),
    })
      .then(function (res) {
        return res.json().then(function (d) { return { status: res.status, data: d }; });
      })
      .then(function (r) {
        setLoading(false);
        if (!r.data || !r.data.success) {
          announce("Prediction failed.");
          showError((r.data && r.data.error) || "Prediction failed. Please try again.");
          return;
        }
        showSuccess(r.data);
      })
      .catch(function () {
        setLoading(false);
        announce("Network error.");
        showError("Network error. Please check your connection and try again.");
      });
  }

  /* ---------- feedback ---------- */
  function csrfToken() {
    var input = form ? form.querySelector('input[name="csrf_token"]') : null;
    return input ? input.value : null;
  }

  function submitFeedback(value) {
    if (typeof lastPredictionId !== "number") return;
    var buttons = feedback.querySelectorAll("button[data-feedback]");
    for (var i = 0; i < buttons.length; i++) {
      buttons[i].disabled = true;
    }
    if (feedbackStatus) {
      feedbackStatus.textContent = "Sending feedback…";
      feedbackStatus.className = "feedback__status";
    }

    var headers = { "Content-Type": "application/json" };
    var token = csrfToken();
    if (token) headers["X-CSRF-Token"] = token;

    fetch("/api/feedback", {
      method: "POST",
      headers: headers,
      body: JSON.stringify({ prediction_id: lastPredictionId, feedback: value }),
    })
      .then(function (res) { return res.json().then(function (d) { return { status: res.status, data: d }; }); })
      .then(function (r) {
        if (r.data && r.data.success) {
          if (feedbackStatus) {
            feedbackStatus.textContent = r.data.already_recorded
              ? "Feedback was already recorded for this prediction."
              : "Thanks! Your feedback was recorded.";
            feedbackStatus.className = "feedback__status is-ok";
          }
          // Keep buttons disabled: the first feedback is final (documented policy).
        } else {
          if (feedbackStatus) {
            feedbackStatus.textContent = (r.data && r.data.error) || "Could not save feedback. Please try again.";
            feedbackStatus.className = "feedback__status is-error";
          }
          for (var i = 0; i < buttons.length; i++) {
            buttons[i].disabled = false;
          }
        }
      })
      .catch(function () {
        if (feedbackStatus) {
          feedbackStatus.textContent = "Network error. Please try again.";
          feedbackStatus.className = "feedback__status is-error";
        }
        for (var i = 0; i < buttons.length; i++) {
          buttons[i].disabled = false;
        }
      });
  }

  /* ---------- wiring ---------- */
  if (textarea) {
    textarea.addEventListener("input", updateCounter);
    textarea.addEventListener("keydown", function (e) {
      // Ctrl+Enter (or Cmd+Enter) submits without interfering with normal typing.
      if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
        e.preventDefault();
        if (form) {
          if (typeof form.requestSubmit === "function") {
            form.requestSubmit();
          } else {
            submitPrediction();
          }
        }
      }
    });
    updateCounter();
  }

  if (exampleBtn) {
    exampleBtn.addEventListener("click", function () {
      if (!textarea) return;
      textarea.value = EXAMPLE_TEXT;
      updateCounter();
      textarea.focus();
      announce("Example article inserted. You can edit it before checking.");
    });
  }

  if (form) {
    form.addEventListener("submit", function (e) {
      e.preventDefault();
      if (submit && submit.disabled) return; // duplicate submission guard
      submitPrediction();
    });
  }

  if (feedback) {
    feedback.addEventListener("click", function (e) {
      var btn = e.target.closest ? e.target.closest("button[data-feedback]") : null;
      if (!btn || btn.disabled) return;
      submitFeedback(btn.getAttribute("data-feedback"), btn);
    });
  }
})();
