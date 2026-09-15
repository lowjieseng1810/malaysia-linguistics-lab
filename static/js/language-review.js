(function () {
  var tabs = document.querySelectorAll(".review-tab");
  var panels = {
    overview: document.getElementById("panel-overview"),
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

  function applyFilters() {
    var query = ((q && q.value) || "").trim().toLowerCase();
    var mode = (filt && filt.value) || "all";
    return rows.filter(function (row) {
      if (mode === "technical_issues" && !row.has_technical) return false;
      if (mode === "needs_verification") {
        var pending = [
          "needs_verification",
          "needs_revision",
          "academic_review_pending",
          "community_review_pending"
        ];
        if (pending.indexOf(row.review_status) === -1 && row.bucket !== "technical" && row.bucket !== "suspicious") {
          return false;
        }
      }
      if (mode === "reviewed" && row.review_status !== "reviewed") return false;
      if (mode === "newly_added" && !row.is_newly_added) return false;
      if (mode === "source_derived" && !row.source_derived) return false;
      if (!query) return true;
      var blob = [
        row.word,
        row.meaning_en,
        row.meaning_ms,
        row.source_ref,
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
      return (
        "<tr>" +
        "<td>" + escapeHtml(row.word) + "</td>" +
        "<td>" + escapeHtml(row.meaning_ms) + "</td>" +
        "<td>" + escapeHtml(row.meaning_en) + "</td>" +
        "<td>" + escapeHtml(row.source_ref) + "</td>" +
        "<td>" + escapeHtml(row.review_status_label) + "</td>" +
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
