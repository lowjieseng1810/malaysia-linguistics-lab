(function () {
  var tabs = document.querySelectorAll(".review-tab");
  var panels = {
    overview: document.getElementById("panel-overview"),
    queue: document.getElementById("panel-queue"),
    recent: document.getElementById("panel-recent"),
    vocabulary: document.getElementById("panel-vocabulary"),
    issues: document.getElementById("panel-issues"),
    sources: document.getElementById("panel-sources"),
    academic: document.getElementById("panel-academic"),
    collaboration: document.getElementById("panel-collaboration")
  };

  function showTab(id) {
    Object.keys(panels).forEach(function (key) {
      if (!panels[key]) return;
      panels[key].hidden = key !== id;
    });
    tabs.forEach(function (tab) {
      tab.setAttribute("aria-selected", tab.getAttribute("data-tab") === id ? "true" : "false");
    });
    if (history.replaceState) {
      history.replaceState(null, "", "#" + id);
    }
  }

  tabs.forEach(function (tab) {
    tab.addEventListener("click", function () {
      showTab(tab.getAttribute("data-tab"));
    });
  });

  var hash = (location.hash || "#overview").replace("#", "");
  if (panels[hash]) showTab(hash);

  function closeAllSelects(except) {
    document.querySelectorAll(".review-select.is-open").forEach(function (widget) {
      if (widget === except) return;
      var menu = widget.querySelector(".review-select-menu");
      var trigger = widget.querySelector(".review-select-trigger");
      widget.classList.remove("is-open");
      if (menu) menu.hidden = true;
      if (trigger) trigger.setAttribute("aria-expanded", "false");
    });
  }

  function positionMenu(widget) {
    var trigger = widget.querySelector(".review-select-trigger");
    var menu = widget.querySelector(".review-select-menu");
    if (!trigger || !menu) return;
    var rect = trigger.getBoundingClientRect();
    var width = Math.max(rect.width, 280);
    menu.style.position = "fixed";
    menu.style.left = Math.max(8, rect.left) + "px";
    menu.style.width = width + "px";
    menu.style.minWidth = width + "px";
    var below = rect.bottom + 6;
    menu.hidden = false;
    var menuHeight = menu.offsetHeight || 240;
    if (below + menuHeight > window.innerHeight - 8 && rect.top > menuHeight + 12) {
      menu.style.top = Math.max(8, rect.top - menuHeight - 6) + "px";
    } else {
      menu.style.top = below + "px";
    }
  }

  function bindSelect(widget) {
    var trigger = widget.querySelector(".review-select-trigger");
    var menu = widget.querySelector(".review-select-menu");
    var hidden = widget.querySelector("input[type='hidden']");
    var valueEl = widget.querySelector(".review-select-value");
    if (!trigger || !menu || !hidden) return;

    function options() {
      return Array.prototype.slice.call(menu.querySelectorAll("[role='option']"));
    }

    function setValue(option, submit) {
      options().forEach(function (item) {
        item.setAttribute("aria-selected", item === option ? "true" : "false");
      });
      hidden.value = option.getAttribute("data-value") || "";
      if (valueEl) valueEl.textContent = option.textContent;
      closeAllSelects();
      if (submit && widget.classList.contains("review-select--autosubmit")) {
        var form = widget.closest("form");
        if (form) form.submit();
      }
    }

    trigger.addEventListener("click", function (event) {
      event.preventDefault();
      var open = widget.classList.contains("is-open");
      closeAllSelects();
      if (open) return;
      widget.classList.add("is-open");
      trigger.setAttribute("aria-expanded", "true");
      positionMenu(widget);
      var selected = menu.querySelector("[aria-selected='true']") || options()[0];
      if (selected) selected.focus();
    });

    options().forEach(function (option) {
      option.setAttribute("tabindex", "-1");
      option.addEventListener("click", function () {
        setValue(option, true);
      });
    });

    trigger.addEventListener("keydown", function (event) {
      if (event.key === "ArrowDown" || event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        trigger.click();
      }
    });

    menu.addEventListener("keydown", function (event) {
      var items = options();
      var index = items.indexOf(document.activeElement);
      if (event.key === "Escape") {
        event.preventDefault();
        closeAllSelects();
        trigger.focus();
      } else if (event.key === "ArrowDown") {
        event.preventDefault();
        items[Math.min(items.length - 1, index + 1)].focus();
      } else if (event.key === "ArrowUp") {
        event.preventDefault();
        items[Math.max(0, index - 1)].focus();
      } else if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        if (document.activeElement && document.activeElement.getAttribute("role") === "option") {
          setValue(document.activeElement, true);
        }
      }
    });
  }

  document.querySelectorAll(".review-select").forEach(bindSelect);

  document.querySelectorAll(".review-again").forEach(function (btn) {
    btn.addEventListener("click", function () {
      var card = btn.closest(".review-recent-item");
      if (!card) return;
      var form = card.querySelector(".review-form-recent");
      if (!form) return;
      form.hidden = !form.hidden;
      if (!form.hidden) {
        var trigger = form.querySelector(".review-select-trigger");
        if (trigger) trigger.focus();
      }
    });
  });

  var pageRoot = document.querySelector(".review-page");
  var canEdit = pageRoot && pageRoot.getAttribute("data-can-edit") === "1";
  var vocabPost = (pageRoot && pageRoot.getAttribute("data-vocab-post")) || "";
  var csrfMeta = document.querySelector('meta[name="csrf-token"]');
  var csrf = csrfMeta ? csrfMeta.getAttribute("content") : "";
  var choiceNode = document.getElementById("review-status-choices");
  var statusChoices = [];
  try {
    statusChoices = JSON.parse((choiceNode && choiceNode.textContent) || "[]");
  } catch (err) {
    statusChoices = [];
  }

  function issueContext(row) {
    if (!row.issue_context) return "";
    return (
      '<div class="review-issue-context" aria-readonly="true">' +
      '<span class="review-issue-context-label">Issue context</span>' +
      "<p>" + escapeHtml(row.issue_context) + "</p></div>"
    );
  }

  function statusEditor(row) {
    if (!canEdit || !vocabPost) return "";
    var current = row.review_status === "reviewed" ? "academically_reviewed" : (row.review_status || "needs_verification");
    var options = statusChoices.map(function (choice) {
      var selected = choice.id === current ? " selected" : "";
      return '<option value="' + escapeHtml(choice.id) + '"' + selected + ">" + escapeHtml(choice.label) + "</option>";
    }).join("");
    var humanNote = row.reviewer_note || "";
    return (
      '<form class="review-form review-vocab-inline" method="post" action="' + escapeHtml(vocabPost) + '">' +
      '<input type="hidden" name="csrf_token" value="' + escapeHtml(csrf) + '">' +
      '<input type="hidden" name="vocab_id" value="' + escapeHtml(row.id) + '">' +
      '<label>Review status<select name="status" class="review-native-select">' + options + "</select></label>" +
      '<label>Reviewer notes<textarea name="note" maxlength="2000" placeholder="Add your review comments here…">' +
      escapeHtml(humanNote) + "</textarea></label>" +
      '<button type="submit">Save review</button></form>'
    );
  }
  document.addEventListener("click", function (event) {
    if (!event.target.closest(".review-select")) closeAllSelects();
  });
  window.addEventListener("resize", function () {
    document.querySelectorAll(".review-select.is-open").forEach(positionMenu);
  });
  window.addEventListener("scroll", function () {
    document.querySelectorAll(".review-select.is-open").forEach(positionMenu);
  }, true);

  var dataNode = document.getElementById("review-vocab-data");
  if (!dataNode) return;
  var rows = [];
  try {
    rows = JSON.parse(dataNode.textContent || "[]");
  } catch (err) {
    rows = [];
  }

  var q = document.getElementById("vocab-q");
  var filt = document.getElementById("vocab-filter");
  var body = document.getElementById("vocab-body");
  var count = document.getElementById("vocab-count");
  var pageLabel = document.getElementById("vocab-page");
  var prev = document.getElementById("vocab-prev");
  var next = document.getElementById("vocab-next");
  var page = 0;
  var pageSize = 40;
  var doneStatuses = ["reviewed", "academically_reviewed"];
  var pending = [
    "needs_verification",
    "needs_revision",
    "academic_review_pending",
    "community_review_pending"
  ];

  function applyFilters() {
    var query = ((q && q.value) || "").trim().toLowerCase();
    var mode = (filt && filt.value) || "all";
    return rows.filter(function (row) {
      if (mode === "technical_issues" && !row.has_technical) return false;
      if (mode === "needs_verification") {
        if (!row.in_review_queue && pending.indexOf(row.review_status) === -1 && row.bucket !== "technical" && row.bucket !== "suspicious") {
          return false;
        }
        if (doneStatuses.indexOf(row.review_status) !== -1) return false;
        if (row.is_pedagogical_bridge || row.review_status === "pedagogical_bridge") return false;
      }
      if (mode === "reviewed" && doneStatuses.indexOf(row.review_status) === -1) return false;
      if (mode === "newly_added" && !row.is_newly_added) return false;
      if (mode === "source_derived" && !row.source_derived) return false;
      if (mode === "pedagogical_bridge" && !row.is_pedagogical_bridge && row.review_status !== "pedagogical_bridge") return false;
      if (!query) return true;
      var blob = [
        row.word,
        row.meaning_en,
        row.meaning_ms,
        row.source_ref,
        row.review_status_label,
        row.reviewed_by_username,
        row.issue_context,
        row.reviewer_note,
        (row.issue_labels || []).join(" ")
      ].join(" ").toLowerCase();
      return blob.indexOf(query) !== -1;
    });
  }

  function escapeHtml(value) {
    return String(value || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  function render() {
    if (!body) return;
    var filtered = applyFilters();
    var pages = Math.max(1, Math.ceil(filtered.length / pageSize));
    if (page > pages - 1) page = pages - 1;
    if (page < 0) page = 0;
    var slice = filtered.slice(page * pageSize, page * pageSize + pageSize);
    body.innerHTML = slice.map(function (row) {
      var issues = (row.issues || [])
        .map(function (issue) {
          var cls = issue.severity === "technical" ? "review-badge is-issue" : "review-badge";
          return '<span class="' + cls + '">' + escapeHtml(issue.label) + "</span>";
        })
        .join(" ");
      var reviewer = [
        row.reviewed_by_username || "",
        row.reviewed_by_role || "",
        row.reviewed_at || ""
      ].filter(Boolean).join(" · ");
      var history = (row.history || []).length
        ? '<div class="review-muted">' + escapeHtml((row.history || []).map(function (event) {
          return (event.created_at || "") + ": " + (event.previous_status || "—") + " → " + (event.new_status || "");
        }).join(" | ")) + "</div>"
        : "";
      return (
        "<tr>" +
        "<td>" + escapeHtml(row.word) + "</td>" +
        "<td>" + escapeHtml(row.meaning_ms) + "</td>" +
        "<td>" + escapeHtml(row.meaning_en) + "</td>" +
        "<td>" + escapeHtml(row.source_ref) + "</td>" +
        "<td>" + escapeHtml(row.review_status_label) + history + issueContext(row) + statusEditor(row) + "</td>" +
        "<td>" + escapeHtml(reviewer || "—") + "</td>" +
        "<td>" + (issues || "—") + "</td>" +
        '<td><button type="button" class="review-cite" data-cite="' +
        encodeURIComponent(row.citation || "") +
        '">Cite</button></td>' +
        "</tr>"
      );
    }).join("");
    if (count) {
      count.textContent = filtered.length + " shown of " + rows.length + " stored entries.";
    }
    if (pageLabel) pageLabel.textContent = "Page " + (page + 1) + " of " + pages;
    body.querySelectorAll(".review-cite").forEach(function (btn) {
      btn.addEventListener("click", function () {
        var text = decodeURIComponent(btn.getAttribute("data-cite") || "");
        if (navigator.clipboard && text) navigator.clipboard.writeText(text);
      });
    });
  }

  if (q) q.addEventListener("input", function () { page = 0; render(); });
  if (filt) filt.addEventListener("change", function () { page = 0; render(); });
  if (prev) prev.addEventListener("click", function () { page -= 1; render(); });
  if (next) next.addEventListener("click", function () { page += 1; render(); });
  render();
})();
