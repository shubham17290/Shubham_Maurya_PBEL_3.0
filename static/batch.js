/* Batch prediction page: dropzone, client-side file checks, upload state,
 * and results-table filtering. No inline handlers; CSP-friendly.
 */
(function () {
  "use strict";

  /* ---------- upload page ---------- */
  var form = document.getElementById("batch-form");

  if (form) {
    var dropzone = document.getElementById("dropzone");
    var fileInput = document.getElementById("file");
    var summary = document.getElementById("file-summary");
    var fileName = document.getElementById("file-name");
    var removeBtn = document.getElementById("file-remove");
    var uploadError = document.getElementById("upload-error");
    var submitBtn = document.getElementById("batch-submit");
    var uploading = document.getElementById("uploading");
    var status = document.getElementById("batch-status");
    var maxBytes = parseInt(form.getAttribute("data-max-bytes"), 10) || 5 * 1024 * 1024;
    var allowedExtensions = [".csv", ".txt"];
    var submitting = false;

    function setError(message) {
      if (!uploadError) return;
      uploadError.textContent = message || "";
      uploadError.hidden = !message;
      if (dropzone) dropzone.classList.toggle("is-invalid", !!message);
      if (status && message) status.textContent = message;
    }

    function formatSize(bytes) {
      if (bytes >= 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + " MB";
      if (bytes >= 1024) return (bytes / 1024).toFixed(1) + " KB";
      return bytes + " bytes";
    }

    function extensionAllowed(name) {
      var lower = name.toLowerCase();
      return allowedExtensions.some(function (ext) {
        return lower.endsWith(ext);
      });
    }

    function showSelection(file) {
      if (!file) {
        if (summary) summary.hidden = true;
        return;
      }
      if (fileName) fileName.textContent = file.name + " (" + formatSize(file.size) + ")";
      if (summary) summary.hidden = false;
    }

    /* Validate before submission; the server repeats every check. */
    function validateFile(file) {
      if (!file) return "Please choose a CSV or TXT file.";
      if (!extensionAllowed(file.name)) return "Unsupported file type. Please upload a CSV or TXT file.";
      if (file.size === 0) return "The selected file is empty.";
      if (file.size > maxBytes) {
        return "File is too large. Maximum " + formatSize(maxBytes) + " allowed.";
      }
      return "";
    }

    if (fileInput) {
      fileInput.addEventListener("change", function () {
        var file = fileInput.files && fileInput.files[0];
        showSelection(file);
        setError(file ? validateFile(file) : "");
      });
    }

    if (dropzone) {
      ["dragenter", "dragover"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.add("is-dragover");
        });
      });
      ["dragleave", "drop"].forEach(function (evt) {
        dropzone.addEventListener(evt, function (e) {
          e.preventDefault();
          dropzone.classList.remove("is-dragover");
        });
      });
      dropzone.addEventListener("drop", function (e) {
        var dt = e.dataTransfer;
        if (!dt || !dt.files || !dt.files.length || !fileInput) return;
        // Assign the dropped file to the underlying input when the browser allows it.
        try {
          fileInput.files = dt.files;
        } catch (err) {
          setError("Could not attach the dropped file in this browser. Please use “click to browse” instead.");
          return;
        }
        var file = dt.files[0];
        showSelection(file);
        setError(validateFile(file));
      });
    }

    if (removeBtn) {
      removeBtn.addEventListener("click", function () {
        if (fileInput) fileInput.value = "";
        showSelection(null);
        setError("");
        if (fileInput) fileInput.focus();
        if (status) status.textContent = "File removed.";
      });
    }

    form.addEventListener("submit", function (e) {
      if (submitting) {
        e.preventDefault();
        return;
      }
      var file = fileInput && fileInput.files ? fileInput.files[0] : null;
      var problem = validateFile(file);
      if (problem) {
        e.preventDefault();
        setError(problem);
        if (fileInput) fileInput.focus();
        return;
      }
      setError("");
      submitting = true;
      // Do not disable the submit button synchronously here: Chromium aborts
      // the native form submission when its submitter is disabled mid-event.
      // A guarded flag blocks duplicates; the button is marked busy visually.
      if (submitBtn) {
        submitBtn.classList.add("is-busy");
        submitBtn.setAttribute("aria-disabled", "true");
      }
      form.setAttribute("aria-busy", "true");
      // Honest indeterminate progress: the server processes synchronously and
      // does not report real percentage progress.
      if (uploading) uploading.hidden = false;
      if (status) status.textContent = "Uploading and processing your file…";
    });
  }

  /* ---------- results page filter ---------- */
  var filterSelect = document.getElementById("result-filter");
  if (filterSelect) {
    var scope = document.querySelector(filterSelect.getAttribute("data-filter-scope") || "#batch-table");
    var filterStatus = document.getElementById("filter-status");

    function applyFilter() {
      if (!scope) return;
      var value = filterSelect.value;
      var rows = scope.querySelectorAll("tbody tr");
      var shown = 0;
      for (var i = 0; i < rows.length; i++) {
        var row = rows[i];
        var match = value === "all" || row.getAttribute("data-label") === value;
        row.classList.toggle("is-filtered-out", !match);
        if (match) shown++;
      }
      if (filterStatus) {
        filterStatus.textContent = value === "all"
          ? "Showing all " + shown + " previewed rows."
          : "Showing " + shown + " of " + rows.length + " previewed rows.";
      }
    }

    filterSelect.addEventListener("change", applyFilter);
    applyFilter();
  }
})();
