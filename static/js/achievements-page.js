(function () {
  "use strict";
  const backdrop = document.getElementById("achievement-detail-backdrop");
  const closeBtn = document.getElementById("achievement-detail-close");
  const titleEl = document.getElementById("achievement-detail-title");
  const descEl = document.getElementById("achievement-detail-description");
  const stateEl = document.getElementById("achievement-detail-state");
  const dateEl = document.getElementById("achievement-detail-date");
  const stampHost = document.getElementById("achievement-detail-stamp-host");
  const categoryEl = document.getElementById("achievement-detail-category");

  function formatEarnedDate(ts) {
    const n = Number(ts);
    if (!n) return "";
    const date = new Date(n * 1000);
    if (Number.isNaN(date.getTime())) return "";
    try {
      return date
        .toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" })
        .toUpperCase();
    } catch (err) {
      return date.toLocaleDateString();
    }
  }

  function stampMarkup(card) {
    const unlocked = card.dataset.unlocked === "true";
    const cat = card.dataset.categoryKey || "learning";
    const icon = card.dataset.icon || "seal";
    const face = card.dataset.faceValue || "10";
    const year = card.dataset.issueYear || "2026";
    const title = card.dataset.title || "";
    const rarity = (card.dataset.rarity || "common").toLowerCase();
    const rarityLabel = rarity.replace(/_/g, " ").toUpperCase();
    const earned = unlocked ? formatEarnedDate(card.dataset.unlockedAt) : "";
    const meta = unlocked && earned
      ? '<span class="postage-stamp-meta"><span class="postage-stamp-status">Earned</span><span class="postage-stamp-earned">' +
        earned +
        "</span></span>"
      : '<span class="postage-stamp-meta"><span class="postage-stamp-status">' +
        (unlocked ? "Earned" : "To unlock") +
        "</span></span>";
    return (
      '<div class="postage-stamp postage-stamp--compact postage-stamp--' +
      cat +
      " postage-stamp--rarity-" +
      rarity +
      " " +
      (unlocked ? "is-unlocked" : "is-locked") +
      '" aria-hidden="true">' +
      '<span class="postage-stamp-body"></span>' +
      '<span class="postage-stamp-frame"></span>' +
      '<span class="postage-stamp-foil"></span>' +
      '<span class="postage-stamp-postmark"></span>' +
      '<span class="postage-stamp-face">' +
      '<span class="postage-stamp-value">' +
      face +
      "</span>" +
      '<span class="postage-stamp-emblem">' +
      '<span class="achievement-icon achievement-icon--' +
      icon +
      '"></span></span>' +
      '<strong class="postage-stamp-title">' +
      title +
      "</strong>" +
      '<span class="postage-stamp-rarity">' +
      rarityLabel +
      "</span>" +
      meta +
      '<span class="postage-stamp-year">Series ' +
      year +
      "</span>" +
      "</span></div>"
    );
  }

  function openDetail(card) {
    if (!backdrop || !card) return;
    titleEl.textContent = card.dataset.title || "";
    descEl.textContent = card.dataset.description || "";
    if (categoryEl) categoryEl.textContent = card.dataset.category || "";
    const unlocked = card.dataset.unlocked === "true";
    stateEl.textContent = unlocked ? "Collected" : "Locked — keep exploring";
    if (stampHost) stampHost.innerHTML = stampMarkup(card);
    if (unlocked && card.dataset.unlockedAt) {
      const date = new Date(Number(card.dataset.unlockedAt) * 1000);
      dateEl.hidden = false;
      dateEl.textContent = "Collected " + date.toLocaleDateString();
    } else {
      dateEl.hidden = true;
      dateEl.textContent = "";
    }
    backdrop.hidden = false;
    closeBtn && closeBtn.focus();
  }

  function closeDetail() {
    if (backdrop) backdrop.hidden = true;
  }

  function openFromHash() {
    const key = (window.location.hash || "").replace(/^#/, "");
    if (!key) return;
    const card =
      document.getElementById("stamp-" + key) ||
      document.querySelector('.achievement-stamp[data-key="' + key + '"]');
    if (card) {
      card.scrollIntoView({ behavior: "smooth", block: "center" });
      openDetail(card);
    }
  }

  document.querySelectorAll(".achievements-progress-fill[data-progress-pct]").forEach(function (el) {
    var pct = Number(el.getAttribute("data-progress-pct") || "0");
    if (!isFinite(pct)) pct = 0;
    pct = Math.max(0, Math.min(100, pct));
    el.style.width = pct + "%";
  });

  document.querySelectorAll(".achievement-stamp").forEach(function (card) {
    card.addEventListener("click", function () {
      openDetail(card);
    });
    card.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        openDetail(card);
      }
    });
  });
  if (closeBtn) closeBtn.addEventListener("click", closeDetail);
  if (backdrop) {
    backdrop.addEventListener("click", function (event) {
      if (event.target === backdrop) closeDetail();
    });
  }
  document.addEventListener("keydown", function (event) {
    if (event.key === "Escape") closeDetail();
  });
  openFromHash();
  window.addEventListener("hashchange", openFromHash);
})();
