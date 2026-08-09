/* Non-AI global mascot companion — independent from AI Tutor. */
(function () {
  "use strict";

  let prefs = {
    enabled: true,
    reactions_enabled: true,
    achievement_reactions_enabled: true,
    facts_enabled: true,
    thoughts_enabled: true,
    voice_enabled: false,
    frequency: "normal"
  };

  let root = null;
  let speechEl = null;
  let thoughtEl = null;
  let lastEventAt = 0;
  let lastClickAt = 0;
  let thoughtTimer = null;
  let blinkTimer = null;
  let priorityUntil = 0;
  let gazeRaf = null;
  let gazeIdleTimer = null;
  let gazeX = 0;
  let gazeY = 0;
  let gazeTargetX = 0;
  let gazeTargetY = 0;
  let gazeBound = false;
  const CLICK_COOLDOWN_MS = 4800;
  const GAZE_IDLE_MS = 2200;
  const GAZE_MAX_X = 1.55;
  const GAZE_MAX_Y = 1.15;
  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const MAJOR_VOICE = {
    achievement_unlocked: true,
    language_discovered: true,
    streak_milestone: true,
    passport_complete: true,
    course_complete: true
  };

  /* First meaningful page entry this session (sessionStorage). */
  const PAGE_INTROS = {
    dashboard: {
      text: "Hi! I'm your little Malayan sun bear guide. Let's explore Malaysia's living languages together!",
      expression: "happy",
      pose: "wave"
    },
    explorer: {
      text: "Come on — let's find where these living languages call home.",
      expression: "curious",
      pose: "point"
    },
    passport: {
      text: "Your heritage passport is ready!",
      expression: "proud",
      pose: "idle"
    },
    achievements: {
      text: "Let's see what you've collected!",
      expression: "excited",
      pose: "clap"
    },
    dictionary: {
      text: "Let's discover a new word.",
      expression: "curious",
      pose: "idle"
    },
    quiz: {
      text: "Ready? I'll be cheering for you!",
      expression: "encouraging",
      pose: "wave"
    },
    settings: {
      text: "You can decide how often you'd like me around.",
      expression: "happy",
      pose: "sit"
    },
    profile: {
      text: "Here's your journey so far — look how far you've come!",
      expression: "proud",
      pose: "idle"
    },
    lesson: {
      text: "One more step — I'm right here with you.",
      expression: "encouraging",
      pose: "wave"
    },
    default: {
      text: "Welcome! I'm your Malayan sun bear companion.",
      expression: "happy",
      pose: "wave"
    }
  };

  const PAGE_THOUGHTS = {
    achievements: "That stamp would look good in your collection.",
    settings: "I can quiet down whenever you like.",
    dictionary: "Did you find a new word?",
    quiz: "A short quiz keeps the languages alive.",
    passport: "Your heritage collection is growing!",
    explorer: "Which language should we discover next?",
    lesson: "There's more to explore.",
    profile: "You've already come a long way.",
    default: "Malaysia has so many stories hiding in its languages."
  };

  /* Click reactions: rotating self-intros + light contextual lines. */
  const CLICK_INTROS = [
    { text: "Hi! I'm your Malayan sun bear companion.", expression: "happy", pose: "wave" },
    { text: "I'm your little Malayan sun bear guide.", expression: "curious", pose: "idle" },
    { text: "That's me — your Malayan sun bear!", expression: "proud", pose: "idle" },
    { text: "I'm here to explore with you.", expression: "encouraging", pose: "point" },
    { text: "Nice to see you again!", expression: "happy", pose: "wave" }
  ];

  const CLICK_CONTEXT = {
    achievements: [
      { text: "You've collected quite a few stamps!", expression: "proud" },
      { text: "Let's see what we can discover next.", expression: "curious" }
    ],
    explorer: [
      { text: "Where should we explore next?", expression: "curious" },
      { text: "There's more to explore.", expression: "excited" }
    ],
    dictionary: [
      { text: "Did you find a new word?", expression: "curious" },
      { text: "Another word for your collection!", expression: "happy" }
    ],
    quiz: [
      { text: "That was a good one — keep going!", expression: "encouraging" },
      { text: "Ready when you are.", expression: "happy" }
    ],
    passport: [
      { text: "Your heritage collection is growing!", expression: "proud" }
    ],
    settings: [
      { text: "Tweak me anytime.", expression: "happy" }
    ],
    profile: [
      { text: "You've already come a long way.", expression: "proud" }
    ],
    lesson: [
      { text: "One more step!", expression: "encouraging" }
    ],
    default: []
  };

  let clickIntroIndex = 0;

  /* Lightweight local short-term context — session only, no AI / no PII. */
  const CTX_KEY = "mmle_mascot_context_v1";
  const CTX_COOLDOWN_KEY = "mmle_mascot_ctx_line_at";
  const CONTEXT_PRIORITY = {
    achievement_unlocked: 1,
    streak_milestone: 2,
    language_discovered: 3,
    passport_complete: 3,
    lesson_completed: 4,
    quiz_completed: 5,
    word_saved: 6,
    page_intro: 7,
    click: 8
  };

  function readContext() {
    try {
      const raw = sessionStorage.getItem(CTX_KEY);
      return raw ? JSON.parse(raw) : {};
    } catch (err) {
      return {};
    }
  }

  function writeContext(patch) {
    const next = Object.assign(readContext(), patch || {}, { updated_at: Date.now() });
    /* Bound recent discoveries */
    if (Array.isArray(next.recent_discoveries) && next.recent_discoveries.length > 6) {
      next.recent_discoveries = next.recent_discoveries.slice(-6);
    }
    try {
      sessionStorage.setItem(CTX_KEY, JSON.stringify(next));
    } catch (err) {
      /* ignore quota */
    }
    return next;
  }

  function rememberAction(type, detail) {
    const d = detail || {};
    const patch = {
      last_action: type,
      last_page: pageKind()
    };
    if (d.language || d.lang_key) {
      patch.last_language = d.language || d.lang_key;
      const ctx = readContext();
      const list = Array.isArray(ctx.recent_discoveries) ? ctx.recent_discoveries.slice() : [];
      const label = d.language || d.lang_key;
      if (label && list[list.length - 1] !== label) list.push(label);
      patch.recent_discoveries = list;
    }
    if (d.title || d.key) {
      patch.last_achievement = d.title || d.key;
      patch.last_achievement_rarity = d.rarity || "";
    }
    if (type === "lesson_completed") patch.last_lesson = d.lang_key || d.language || pageKind();
    if (type === "quiz_completed") patch.last_quiz = d.lang_key || d.language || "quiz";
    if (type === "word_saved") patch.last_word = d.word || "word";
    if (d.days != null) patch.streak = d.days;
    return writeContext(patch);
  }

  function contextualLine(type, detail) {
    const d = detail || {};
    const ctx = readContext();
    if (type === "language_discovered") {
      return "Another language discovered" + (d.language ? ": " + d.language + "!" : "!");
    }
    if (type === "word_saved") {
      return "Nice one! That's going into your collection.";
    }
    if (type === "lesson_completed") {
      return "Great work. One more step on your journey.";
    }
    if (type === "quiz_completed") {
      return "Well done — your knowledge is growing.";
    }
    if (type === "streak_milestone") {
      return d.days ? "Your streak is growing — " + d.days + " days!" : "Your streak is growing!";
    }
    if (type === "achievement_unlocked") {
      const rarity = (d.rarity || "").toLowerCase();
      if (d.earned === 1) return "Your first stamp!";
      if (rarity === "legendary") return "A legendary stamp — look what you earned!";
      if (rarity === "epic") return "An epic find for your collection!";
      if (rarity === "rare") return "Look what you earned — a rare stamp!";
      return "Look what you earned!";
    }
    if (type === "login" || type === "welcome_back") {
      if (ctx.last_language) return "Welcome back! Ready to keep exploring " + ctx.last_language + "?";
      return "Welcome back! Ready to keep exploring?";
    }
    return null;
  }

  function canSpeakContext() {
    try {
      const last = Number(sessionStorage.getItem(CTX_COOLDOWN_KEY) || 0);
      return Date.now() - last > 6500;
    } catch (err) {
      return true;
    }
  }

  function markContextSpoken() {
    try {
      sessionStorage.setItem(CTX_COOLDOWN_KEY, String(Date.now()));
    } catch (err) {
      /* ignore */
    }
  }

  function rarityExpression(rarity) {
    const r = (rarity || "common").toLowerCase();
    if (r === "legendary" || r === "epic") return "celebrating";
    if (r === "rare") return "proud";
    if (r === "uncommon") return "excited";
    return "happy";
  }

  function frequencyGap() {
    if (prefs.frequency === "frequent") return 7000;
    if (prefs.frequency === "occasional") return 22000;
    return 12000;
  }

  function mascotSvg() {
    if (window.MMLEMascot && typeof window.MMLEMascot.renderInline === "function") {
      return window.MMLEMascot.renderInline({ width: 96, height: 112, className: "mascot-svg" });
    }
    /* final-v3 fallback if canonical JS missing */
    return (
      '<svg class="mascot-svg" viewBox="0 0 100 124" width="96" height="112" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">' +
      '<ellipse cx="50" cy="49" rx="31" ry="30.5" fill="#1A1A1C"/>' +
      '<ellipse cx="23" cy="21" rx="9" ry="10.5" fill="#1A1A1C"/><ellipse cx="77" cy="21" rx="9" ry="10.5" fill="#1A1A1C"/>' +
      '<ellipse cx="23.2" cy="22" rx="4.2" ry="5" fill="#E8B84A"/><ellipse cx="76.8" cy="22" rx="4.2" ry="5" fill="#E8B84A"/>' +
      '<path d="M36.5 54.5c1.4-3.2 6.2-5.4 13.5-5.4c7.4 0 12.2 2.2 13.6 5.4c1.2 2.8.2 6.8-2.4 9.6c-2.8 3-7.2 4.6-11.2 4.5c-4.2-.1-8.4-1.8-11-4.8c-2.4-2.7-3.2-6.6-2.5-9.3z" fill="#F7EFE2"/>' +
      '<ellipse cx="37.5" cy="42" rx="4.3" ry="4.7" fill="#121214"/><ellipse cx="62.5" cy="42" rx="4.3" ry="4.7" fill="#121214"/>' +
      '<circle cx="36.2" cy="40.8" r="1" fill="#FFFFFF"/><circle cx="61.2" cy="40.8" r="1" fill="#FFFFFF"/>' +
      '<ellipse cx="50" cy="93.5" rx="24" ry="16.5" fill="#1A1A1C"/>' +
      '<ellipse cx="38" cy="107" rx="10" ry="7.5" fill="#1A1A1C"/><ellipse cx="62" cy="107" rx="10" ry="7.5" fill="#1A1A1C"/>' +
      '<g class="mascot-arm mascot-arm--left">' +
      '<ellipse class="mascot-shoulder" cx="30.5" cy="88.5" rx="9.2" ry="8.2" fill="#1A1A1C"/>' +
      '<ellipse cx="21.5" cy="93.5" rx="8.2" ry="8.8" fill="#1A1A1C"/>' +
      '<ellipse cx="15.8" cy="98.2" rx="4.5" ry="3.4" fill="#F2E6D4"/>' +
      "</g>" +
      '<g class="mascot-arm mascot-arm--right">' +
      '<ellipse class="mascot-shoulder" cx="69.5" cy="88.5" rx="9.2" ry="8.2" fill="#1A1A1C"/>' +
      '<ellipse cx="78.5" cy="93.5" rx="8.2" ry="8.8" fill="#1A1A1C"/>' +
      '<ellipse cx="84.2" cy="98.2" rx="4.5" ry="3.4" fill="#F2E6D4"/>' +
      "</g>" +
      '<path class="mascot-chest" d="M34.2 83.6C29.5 84.8 27.2 89.2 28.6 94.2C30.1 99.6 34.8 104.2 41.2 106.8C44.6 108.2 47.8 109.4 50.2 109.6C53.4 109.8 56.8 108.4 60.6 105.8C66.8 101.6 71.2 96.2 71.8 91.2C72.4 86.6 69.2 83.2 64.4 82.8C60.8 82.5 57.6 84.2 55.4 86.4C53.6 84.2 51.2 82.8 48.4 82.6C44.6 82.4 39.8 82.6 34.2 83.6Z" fill="#E8D7A8"/>' +
      "</svg>"
    );
  }

  const EXPR_POSES = {
    happy: "wave",
    excited: "clap",
    celebrating: "clap",
    thinking: "idle",
    curious: "idle",
    proud: "idle",
    encouraging: "wave",
    surprised: "idle",
    sleepy: "sit",
    idle: "idle"
  };

  function setPose(name) {
    if (!root) return;
    const pose = name || "idle";
    root.setAttribute("data-pose", pose);
  }

  function applyGazeTransform() {
    if (!root) return;
    const left = root.querySelector(".mascot-gaze--left");
    const right = root.querySelector(".mascot-gaze--right");
    /* Percent of each eye's fill-box — stays subtle across SVG scales */
    const tx = ((gazeX / GAZE_MAX_X) * 16).toFixed(2);
    const ty = ((gazeY / GAZE_MAX_Y) * 12).toFixed(2);
    const t = "translate(" + tx + "%, " + ty + "%)";
    if (left) left.style.transform = t;
    if (right) right.style.transform = t;
  }

  function tickGaze() {
    gazeRaf = null;
    if (!root || root.classList.contains("is-hidden")) return;
    gazeX += (gazeTargetX - gazeX) * 0.14;
    gazeY += (gazeTargetY - gazeY) * 0.14;
    if (Math.abs(gazeX) < 0.02 && Math.abs(gazeTargetX) < 0.02) gazeX = 0;
    if (Math.abs(gazeY) < 0.02 && Math.abs(gazeTargetY) < 0.02) gazeY = 0;
    applyGazeTransform();
    if (
      Math.abs(gazeX - gazeTargetX) > 0.03 ||
      Math.abs(gazeY - gazeTargetY) > 0.03 ||
      Math.abs(gazeX) > 0.02 ||
      Math.abs(gazeY) > 0.02
    ) {
      gazeRaf = window.requestAnimationFrame(tickGaze);
    }
  }

  function requestGazeTick() {
    if (gazeRaf || reduced) return;
    gazeRaf = window.requestAnimationFrame(tickGaze);
  }

  function relaxGaze() {
    gazeTargetX = 0;
    gazeTargetY = 0;
    requestGazeTick();
  }

  function onGazePointerMove(event) {
    /* Touch/mobile: keep neutral eyes; only mouse/pen track. */
    if (event.pointerType === "touch") return;
    if (reduced || !root || root.classList.contains("is-hidden")) return;
    if (root.classList.contains("is-blinking") || root.classList.contains("is-sleepy")) return;
    if (document.body.classList.contains("mascot-is-dragging")) return;
    const figure = root.querySelector(".mascot-companion-figure") || root;
    const rect = figure.getBoundingClientRect();
    const cx = rect.left + rect.width * 0.5;
    const cy = rect.top + rect.height * 0.38;
    const nx = (event.clientX - cx) / Math.max(140, window.innerWidth * 0.28);
    const ny = (event.clientY - cy) / Math.max(140, window.innerHeight * 0.28);
    gazeTargetX = Math.max(-1, Math.min(1, nx)) * GAZE_MAX_X;
    gazeTargetY = Math.max(-1, Math.min(1, ny)) * GAZE_MAX_Y;
    if (gazeIdleTimer) window.clearTimeout(gazeIdleTimer);
    gazeIdleTimer = window.setTimeout(relaxGaze, GAZE_IDLE_MS);
    requestGazeTick();
  }

  function bindGazeTracking() {
    if (gazeBound || reduced) return;
    gazeBound = true;
    window.addEventListener("pointermove", onGazePointerMove, { passive: true });
  }

  function scheduleBlink() {
    if (!root || reduced || blinkTimer) return;
    /* Natural cadence: about every 3–5s with jitter */
    const delay = 3000 + Math.random() * 2000;
    blinkTimer = window.setTimeout(function () {
      blinkTimer = null;
      if (!root || root.classList.contains("is-hidden")) {
        scheduleBlink();
        return;
      }
      if (
        root.classList.contains("is-celebrating") ||
        root.classList.contains("is-sleepy")
      ) {
        scheduleBlink();
        return;
      }
      root.classList.add("is-blinking");
      window.setTimeout(function () {
        root && root.classList.remove("is-blinking");
        if (Math.random() < 0.22) {
          window.setTimeout(function () {
            if (!root) return;
            root.classList.add("is-blinking");
            window.setTimeout(function () {
              root && root.classList.remove("is-blinking");
              scheduleBlink();
            }, 120);
          }, 140);
        } else {
          scheduleBlink();
        }
      }, 130);
    }, delay);
  }

  function ensure() {
    if (root) return root;
    root = document.createElement("aside");
    root.className = "mascot-companion is-hidden is-idle";
    root.setAttribute("aria-label", "Malayan sun bear companion");
    root.setAttribute("data-safe-zone", "1");
    root.setAttribute("data-expression", "idle");
    root.setAttribute("data-pose", "idle");
    root.innerHTML =
      '<div class="mascot-speech" id="mascot-speech"></div>' +
      '<div class="mascot-thought" id="mascot-thought">' +
      '<span class="mascot-thought-eyebrow">Do you know?</span>' +
      '<span class="mascot-thought-text"></span>' +
      "</div>" +
      '<div class="mascot-bubbles" aria-hidden="true">' +
      '<span class="mascot-bubble"></span><span class="mascot-bubble"></span><span class="mascot-bubble"></span>' +
      "</div>" +
      '<button type="button" class="mascot-companion-figure" aria-label="Talk to your exploration companion">' +
      mascotSvg() +
      "</button>";
    document.body.appendChild(root);
    speechEl = root.querySelector("#mascot-speech");
    thoughtEl = root.querySelector("#mascot-thought");
    const figure = root.querySelector(".mascot-companion-figure");
    figure.setAttribute("aria-label", "Drag or tap your exploration companion");
    figure.style.touchAction = "none";
    bindDragHandlers(figure);
    bindGazeTracking();
    placeSafe();
    scheduleBlink();
    return root;
  }

  function pageKind() {
    if (document.querySelector(".achievements-page")) return "achievements";
    if (document.querySelector(".settings-page")) return "settings";
    if (document.querySelector(".level-page") || document.getElementById("lesson-content")) {
      return "lesson";
    }
    if (document.getElementById("dict-results") || document.getElementById("dict-search")) {
      return "dictionary";
    }
    if (document.getElementById("quiz-setup-card") || document.getElementById("quiz-play-card")) {
      return "quiz";
    }
    if (/\/profile\b/i.test(location.pathname)) return "profile";
    if (document.querySelector(".dash-sidebar") || document.querySelector(".dash-shell")) {
      const hash = (location.hash || "").toLowerCase();
      if (hash.indexOf("world-explorer") >= 0) return "explorer";
      if (hash.indexOf("heritage-passport") >= 0) return "passport";
      return "dashboard";
    }
    if (document.getElementById("world-explorer-card")) return "explorer";
    if (document.getElementById("heritage-passport")) return "passport";
    return "default";
  }

  let lastDock = null;
  let lastTutorOpen = null;
  let userPinned = false;
  let dragActive = false;
  let suppressClick = false;
  const DRAG_THRESHOLD_PX = 8;
  const POS_STORAGE_KEY = "mmle_mascot_pos_v1";
  const DRAG_HINT_KEY = "mmle_mascot_drag_hint_v1";
  const DRAG_DONE_KEY = "mmle_mascot_drag_done_v1";
  let dragPtr = null;

  function reservedZones() {
    const zones = [];
    const vw = window.innerWidth;
    const vh = window.innerHeight;

    function pushRect(el, pad) {
      if (!el) return;
      const style = window.getComputedStyle(el);
      if (style.display === "none" || style.visibility === "hidden") return;
      if (Number(style.opacity) === 0) return;
      const r = el.getBoundingClientRect();
      if (r.width < 8 || r.height < 8) return;
      // Ignore off-screen or fully clipped elements.
      if (r.bottom < 0 || r.top > vh || r.right < 0 || r.left > vw) return;
      const p = pad || 8;
      zones.push({
        left: r.left - p,
        top: r.top - p,
        right: r.right + p,
        bottom: r.bottom + p,
        label: el.id || el.className || "zone"
      });
    }

    function pushBox(box, pad) {
      if (!box) return;
      const p = pad || 8;
      zones.push({
        left: box.left - p,
        top: box.top - p,
        right: box.right + p,
        bottom: box.bottom + p,
        label: box.label || "box"
      });
    }

    // Reserve only the sidebar's horizontal strip (not its full sticky height as a
    // reason to vanish) — left docks must clear this gutter.
    const sidebar = document.querySelector(".dash-sidebar");
    if (sidebar) {
      const style = window.getComputedStyle(sidebar);
      if (style.display !== "none" && style.visibility !== "hidden") {
        const r = sidebar.getBoundingClientRect();
        if (r.width > 8) {
          pushBox(
            { left: 0, top: 0, right: Math.min(vw * 0.42, r.right + 8), bottom: vh, label: "sidebar-gutter" },
            0
          );
        }
      }
    }

    // Tutor FAB + open panel (live geometry)
    pushRect(document.getElementById("ai-tutor-toggle-button"), 18);
    const tutorPanel = document.getElementById("ai-tutor-panel");
    if (tutorPanel && tutorPanel.classList.contains("is-open")) {
      pushRect(tutorPanel, 18);
    }

    // Dashboard status must stay readable
    pushRect(document.getElementById("globe-status"), 14);

    // Keep mascot off the Earth canvas on stacked mobile hero layouts
    const earthHost = document.getElementById("three-earth-container");
    if (earthHost && vw < 900) {
      const card = document.getElementById("world-explorer-card");
      if (card && !card.classList.contains("is-malaysia-view")) {
        pushRect(earthHost, 12);
      }
    }

    // Malaysia map beacons + labels
    document.querySelectorAll(".exploration-beacon.is-geo-placed").forEach(function (beacon) {
      pushRect(beacon, 6);
      const label = beacon.querySelector(".beacon-label");
      pushRect(label, 4);
    });

    // Edge controls / dialogs (open ones only)
    [
      ".level-nav",
      ".lesson-controls",
      "#dict-search",
      ".quiz-actions",
      ".passport-controls",
      ".pagination",
      ".modal.is-open",
      "[role='dialog'][aria-modal='true']",
      ".heritage-plaque",
      ".achievement-plaque"
    ].forEach(function (sel) {
      document.querySelectorAll(sel).forEach(function (el) {
        pushRect(el, 10);
      });
    });

    // Language cards only when they occupy the lower dock band
    document.querySelectorAll(".language-card, .lang-card, .dash-feature-card").forEach(function (el) {
      const r = el.getBoundingClientRect();
      if (r.bottom > vh - 160 && r.top < vh - 40) pushRect(el, 8);
    });

    return zones;
  }

  function rectsOverlap(a, b) {
    return !(a.right <= b.left || a.left >= b.right || a.bottom <= b.top || a.top >= b.bottom);
  }

  function overlapArea(a, b) {
    const w = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const h = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    if (w <= 0 || h <= 0) return 0;
    return w * h;
  }

  function candidatePenalty(candidate, zones) {
    let penalty = 0;
    for (let i = 0; i < zones.length; i += 1) {
      const area = overlapArea(candidate, zones[i]);
      if (area > 0) {
        penalty += area;
      }
    }
    return penalty;
  }

  function getFootprint() {
    const mobile = window.innerWidth < 720;
    return {
      w: mobile ? 78 : 108,
      h: mobile ? 90 : 124
    };
  }

  function loadUserPosition() {
    try {
      const raw = window.localStorage.getItem(POS_STORAGE_KEY);
      if (!raw) return null;
      const parsed = JSON.parse(raw);
      if (!parsed || typeof parsed.left !== "number" || typeof parsed.top !== "number") {
        return null;
      }
      return parsed;
    } catch (err) {
      return null;
    }
  }

  function saveUserPosition(left, top) {
    try {
      window.localStorage.setItem(
        POS_STORAGE_KEY,
        JSON.stringify({
          left: Math.round(left),
          top: Math.round(top),
          vw: window.innerWidth,
          vh: window.innerHeight,
          pinned: true
        })
      );
      userPinned = true;
      if (root) root.dataset.userPinned = "1";
    } catch (err) {
      /* ignore quota / private mode */
    }
  }

  function renormalizeUserPosition(saved) {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const fp = getFootprint();
    const srcW = saved.vw || vw;
    const srcH = saved.vh || vh;
    let left = saved.left * (vw / Math.max(1, srcW));
    let top = saved.top * (vh / Math.max(1, srcH));
    left = Math.max(4, Math.min(left, vw - fp.w - 4));
    top = Math.max(64, Math.min(top, vh - fp.h - 4));
    return { left: left, top: top };
  }

  function applyLeftTop(left, top, settling) {
    if (!root) return;
    const vw = window.innerWidth;
    root.classList.toggle("is-settling", !!settling);
    // Avoid animating from dock coords during live drag / instant moves.
    if (!settling) {
      root.style.transition = "none";
    } else {
      root.style.transition = "";
    }
    root.style.left = Math.round(left) + "px";
    root.style.top = Math.round(top) + "px";
    root.style.right = "auto";
    root.style.bottom = "auto";
    root.dataset.side = left < vw * 0.5 ? "left" : "right";
    root.dataset.safeDock = "user:" + Math.round(left) + "," + Math.round(top);
    if (!settling) {
      // Force style flush, then restore stylesheet transitions for later snaps.
      void root.offsetWidth;
      window.requestAnimationFrame(function () {
        if (root && !dragActive && !root.classList.contains("is-settling")) {
          root.style.transition = "";
        }
      });
    } else {
      window.setTimeout(function () {
        if (root) {
          root.classList.remove("is-settling");
          root.style.transition = "";
        }
      }, 420);
    }
  }

  function applyDockPosition(best) {
    if (!root || !best) return;
    root.style.top = "auto";
    root.dataset.side = best.side;
    root.dataset.safeDock = best.side + ":" + best.bottom;
    root.style.bottom = best.bottom + "px";
    if (best.side === "left") {
      root.style.left = best.inset + "px";
      root.style.right = "auto";
    } else {
      root.style.right = best.inset + "px";
      root.style.left = "auto";
    }
  }

  function buildDockOptions() {
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const mobile = vw < 720;
    const wide = vw >= 1100;
    const kind = pageKind();
    const tutorPanel = document.getElementById("ai-tutor-panel");
    const tutorOpen = !!(tutorPanel && tutorPanel.classList.contains("is-open"));
    const tutorBtn = document.getElementById("ai-tutor-toggle-button");
    const sidebar = document.querySelector(".dash-sidebar");
    const sidebarOpen = !!(sidebar && window.getComputedStyle(sidebar).display !== "none");
    const footprint = getFootprint();

    let tutorClearBottom = mobile ? 108 : 120;
    if (tutorBtn) {
      const tr = tutorBtn.getBoundingClientRect();
      if (tr.width > 4 && tr.height > 4) {
        tutorClearBottom = Math.max(
          tutorClearBottom,
          Math.ceil(vh - tr.top + 18)
        );
      }
    }

    let sidebarInset = 16;
    if (sidebarOpen && sidebar) {
      const sr = sidebar.getBoundingClientRect();
      sidebarInset = Math.max(16, Math.min(280, Math.ceil(sr.right + 12)));
    }

    const docks = [];
    function addDock(side, bottom, inset, score) {
      docks.push({ side: side, bottom: bottom, inset: inset, score: score });
    }

    addDock("left", tutorClearBottom, sidebarOpen ? sidebarInset : 18, 20);
    addDock("left", tutorClearBottom + 24, sidebarOpen ? sidebarInset : 16, 16);
    addDock("right", tutorClearBottom, tutorOpen ? Math.min(500, Math.floor(vw * 0.46)) : 18, 12);
    addDock("left", Math.min(Math.floor(vh * 0.34), 260), sidebarOpen ? sidebarInset : 16, 10);
    addDock("right", Math.min(Math.floor(vh * 0.34), 260), 16, 8);

    if (mobile && tutorOpen && tutorPanel) {
      const pr = tutorPanel.getBoundingClientRect();
      if (pr.height > 8) {
        const underBottom = Math.floor(vh - pr.bottom - footprint.h - 8);
        if (underBottom >= 8) {
          addDock("left", Math.min(underBottom, tutorClearBottom), 10, 50);
          addDock("left", Math.max(8, underBottom - 12), 10, 46);
        }
      }
    }

    if (kind === "explorer" || kind === "dashboard") {
      addDock("left", tutorClearBottom, wide ? Math.max(sidebarInset, 24) : 14, 24);
    }
    if (kind === "lesson" || kind === "dictionary" || kind === "quiz") {
      addDock("left", tutorClearBottom + 8, sidebarOpen ? sidebarInset : 14, 18);
      addDock("right", tutorClearBottom + 8, tutorOpen ? 460 : 14, 11);
    }
    if (kind === "achievements" || kind === "passport" || kind === "settings") {
      addDock("right", tutorClearBottom, tutorOpen ? 420 : 16, 15);
      addDock("left", tutorClearBottom, sidebarOpen ? sidebarInset : 16, 14);
    }

    const zones = reservedZones();
    const ranked = [];
    docks.forEach(function (dock) {
      const left = dock.side === "left" ? dock.inset : vw - dock.inset - footprint.w;
      const top = vh - dock.bottom - footprint.h;
      const candidate = {
        left: left,
        top: top,
        right: left + footprint.w,
        bottom: top + footprint.h
      };
      if (candidate.left < 4 || candidate.right > vw - 4 || candidate.top < 72) {
        return;
      }
      const penalty = candidatePenalty(candidate, zones);
      let score = dock.score * 1000 - penalty;
      if (tutorOpen && dock.side === "left") score += 800;
      if (sidebarOpen && dock.side === "right") score += 400;
      if (
        lastDock &&
        penalty < footprint.w * footprint.h * 0.08 &&
        lastDock.side === dock.side &&
        Math.abs(lastDock.bottom - dock.bottom) < 28 &&
        Math.abs(lastDock.inset - dock.inset) < 28
      ) {
        score += 1200;
      }
      ranked.push({
        side: dock.side,
        bottom: Math.round(dock.bottom),
        inset: Math.round(dock.inset),
        score: score,
        penalty: penalty,
        left: left,
        top: top,
        candidate: candidate
      });
    });

    ranked.sort(function (a, b) { return b.score - a.score; });
    return {
      ranked: ranked,
      zones: zones,
      footprint: footprint,
      tutorOpen: tutorOpen,
      sidebarOpen: sidebarOpen,
      sidebarInset: sidebarInset,
      tutorClearBottom: tutorClearBottom,
      kind: kind
    };
  }

  function isPositionSafe(left, top, zones, footprint) {
    const candidate = {
      left: left,
      top: top,
      right: left + footprint.w,
      bottom: top + footprint.h
    };
    const penalty = candidatePenalty(candidate, zones || reservedZones());
    return penalty <= footprint.w * footprint.h * 0.12;
  }

  function nearestSafePosition(fromLeft, fromTop) {
    const built = buildDockOptions();
    const fp = built.footprint;
    const threshold = fp.w * fp.h * 0.12;
    const cx = fromLeft + fp.w / 2;
    const cy = fromTop + fp.h / 2;
    let best = null;
    // Prefer clear docks; fall back to lowest-penalty dock nearest the drop.
    built.ranked.forEach(function (dock) {
      const dx = dock.left + fp.w / 2 - cx;
      const dy = dock.top + fp.h / 2 - cy;
      const dist = Math.sqrt(dx * dx + dy * dy);
      const clear = dock.penalty <= threshold;
      const rank = (clear ? 0 : 100000) + dock.penalty + dist * 10 - dock.score;
      if (!best || rank < best.rank) {
        best = { left: dock.left, top: dock.top, rank: rank, dock: dock };
      }
    });
    if (!best) {
      return { left: 16, top: Math.max(72, window.innerHeight - fp.h - 120) };
    }
    return { left: best.left, top: best.top, dock: best.dock };
  }

  function placeSafe() {
    if (!root || dragActive) return;
    const vw = window.innerWidth;
    const vh = window.innerHeight;
    const mobile = vw < 720;
    const tutorPanel = document.getElementById("ai-tutor-panel");
    const tutorOpen = !!(tutorPanel && tutorPanel.classList.contains("is-open"));
    root.classList.toggle("is-compact", mobile);

    if (lastTutorOpen !== null && lastTutorOpen !== tutorOpen) {
      lastDock = null;
    }
    lastTutorOpen = tutorOpen;

    root.classList.remove("is-safe-hidden");
    root.removeAttribute("aria-hidden");

    const built = buildDockOptions();
    const fp = built.footprint;

    // Prefer persisted user position when still safe.
    const saved = loadUserPosition();
    if (saved && saved.pinned !== false) {
      userPinned = true;
      const norm = renormalizeUserPosition(saved);
      if (isPositionSafe(norm.left, norm.top, built.zones, fp)) {
        applyLeftTop(norm.left, norm.top, false);
        lastDock = null;
        return;
      }
      // Viewport/UI changed — snap to nearest safe, keep pinned.
      const snapped = nearestSafePosition(norm.left, norm.top);
      applyLeftTop(snapped.left, snapped.top, true);
      saveUserPosition(snapped.left, snapped.top);
      if (snapped.dock) {
        lastDock = {
          side: snapped.dock.side,
          bottom: snapped.dock.bottom,
          inset: snapped.dock.inset
        };
      }
      return;
    }

    let best = built.ranked[0] || null;
    if (!best) {
      const fallbackSide =
        tutorOpen || built.kind === "explorer" || built.kind === "dashboard" ? "left" : "right";
      best = {
        side: fallbackSide,
        bottom: built.tutorClearBottom,
        inset: fallbackSide === "left" ? (built.sidebarOpen ? built.sidebarInset : 14) : 14,
        score: 0,
        penalty: Infinity,
        candidate: null
      };
    }

    lastDock = { side: best.side, bottom: best.bottom, inset: best.inset };
    applyDockPosition(best);
  }

  function finalizeUserDrop() {
    if (!root) return;
    const rect = root.getBoundingClientRect();
    const fp = getFootprint();
    const zones = reservedZones();
    const safe = isPositionSafe(rect.left, rect.top, zones, fp);
    if (safe) {
      applyLeftTop(rect.left, rect.top, false);
      saveUserPosition(rect.left, rect.top);
      root.classList.add("is-settling");
      window.setTimeout(function () {
        if (root) root.classList.remove("is-settling");
      }, 420);
    } else {
      const snapped = nearestSafePosition(rect.left, rect.top);
      // Instant move out of protected UI, then play a short settle on the figure.
      applyLeftTop(snapped.left, snapped.top, false);
      saveUserPosition(snapped.left, snapped.top);
      root.classList.add("is-settling");
      window.setTimeout(function () {
        if (root) root.classList.remove("is-settling");
      }, 420);
    }
    maybeDragSuccessSpeech();
  }

  function bindDragHandlers(figure) {
    if (!figure || figure.dataset.dragBound === "1") return;
    figure.dataset.dragBound = "1";

    let startX = 0;
    let startY = 0;
    let originLeft = 0;
    let originTop = 0;
    let offsetX = 0;
    let offsetY = 0;
    let moved = false;

    figure.addEventListener("pointerdown", function (event) {
      if (!prefs.enabled) return;
      if (event.button != null && event.button !== 0) return;
      ensure();
      const rect = root.getBoundingClientRect();
      // Lock current visual position into left/top without jumping.
      applyLeftTop(rect.left, rect.top, false);
      dragPtr = event.pointerId;
      startX = event.clientX;
      startY = event.clientY;
      originLeft = rect.left;
      originTop = rect.top;
      offsetX = event.clientX - rect.left;
      offsetY = event.clientY - rect.top;
      moved = false;
      try {
        figure.setPointerCapture(event.pointerId);
      } catch (err) {
        /* ignore */
      }
    });

    figure.addEventListener("pointermove", function (event) {
      if (dragPtr == null || event.pointerId !== dragPtr) return;
      const dx = event.clientX - startX;
      const dy = event.clientY - startY;
      if (!moved && Math.hypot(dx, dy) < DRAG_THRESHOLD_PX) {
        return;
      }
      if (!moved) {
        moved = true;
        dragActive = true;
        suppressClick = true;
        root.classList.add("is-dragging");
        document.body.classList.add("mascot-is-dragging");
      }
      event.preventDefault();
      const vw = window.innerWidth;
      const vh = window.innerHeight;
      const fp = getFootprint();
      let left = event.clientX - offsetX;
      let top = event.clientY - offsetY;
      left = Math.max(4, Math.min(left, vw - fp.w - 4));
      top = Math.max(64, Math.min(top, vh - fp.h - 4));
      applyLeftTop(left, top, false);
    });

    function endPointer(event) {
      if (dragPtr == null || event.pointerId !== dragPtr) return;
      try {
        figure.releasePointerCapture(dragPtr);
      } catch (err) {
        /* ignore */
      }
      dragPtr = null;
      root.classList.remove("is-dragging");
      document.body.classList.remove("mascot-is-dragging");
      dragActive = false;
      if (moved) {
        finalizeUserDrop();
        window.setTimeout(function () {
          suppressClick = false;
        }, 50);
      } else {
        suppressClick = false;
        onMascotClick(event);
      }
      moved = false;
    }

    figure.addEventListener("pointerup", endPointer);
    figure.addEventListener("pointercancel", endPointer);

    // Prevent native click after a drag; click path is handled in pointerup.
    figure.addEventListener("click", function (event) {
      event.preventDefault();
      event.stopPropagation();
    });
  }

  function maybeDragSuccessSpeech() {
    try {
      if (window.localStorage.getItem(DRAG_DONE_KEY) === "1") return;
      window.localStorage.setItem(DRAG_DONE_KEY, "1");
    } catch (err) {
      return;
    }
    window.setTimeout(function () {
      if (Date.now() < priorityUntil) return;
      showSpeech("Nice! You can move me whenever you want.", "happy", 3600, {
        pose: "wave",
        fromDragHint: true
      });
    }, 280);
  }

  function maybeDragTutorial() {
    try {
      if (window.localStorage.getItem(DRAG_HINT_KEY) === "1") return;
    } catch (err) {
      return;
    }
    function tryHint() {
      try {
        if (window.localStorage.getItem(DRAG_HINT_KEY) === "1") return;
      } catch (err) {
        return;
      }
      if (Date.now() < priorityUntil) {
        window.setTimeout(tryHint, 500);
        return;
      }
      try {
        window.localStorage.setItem(DRAG_HINT_KEY, "1");
      } catch (err) {
        /* ignore */
      }
      showSpeech("Try dragging me around! I'll stay out of your way.", "curious", 4800, {
        pose: "wave",
        fromDragHint: true
      });
    }
    // After first-entry intros; lower priority than celebrations via priorityUntil gate.
    window.setTimeout(tryHint, 7200);
  }

  function setExpression(name, pose) {
    if (!root) return;
    const states = [
      "is-idle",
      "is-happy",
      "is-celebrating",
      "is-thinking",
      "is-curious",
      "is-proud",
      "is-encouraging",
      "is-excited",
      "is-surprised",
      "is-sleepy"
    ];
    const next = name && name !== "idle" ? name : "idle";
    root.classList.remove.apply(root.classList, states);
    root.classList.add(next === "idle" ? "is-idle" : "is-" + next);
    root.setAttribute("data-expression", next);
    setPose(pose || EXPR_POSES[next] || "idle");
  }

  function speak(text, forceMajor) {
    if (!prefs.voice_enabled || !text) return;
    if (!forceMajor) return;
    if (!window.speechSynthesis || typeof window.SpeechSynthesisUtterance !== "function") {
      return;
    }
    try {
      window.speechSynthesis.cancel();
      const utter = new SpeechSynthesisUtterance(String(text).slice(0, 80));
      utter.rate = 1.05;
      utter.pitch = 1.12;
      utter.volume = 0.62;
      const voices = window.speechSynthesis.getVoices && window.speechSynthesis.getVoices();
      if (voices && voices.length) {
        const soft =
          voices.find(function (v) {
            return /google uk english female|samantha|zira|female/i.test(v.name);
          }) || voices.find(function (v) {
            return /^en/i.test(v.lang);
          });
        if (soft) utter.voice = soft;
      }
      root && root.setAttribute("data-voice-speaking", "1");
      utter.onend = function () {
        root && root.removeAttribute("data-voice-speaking");
      };
      utter.onerror = function () {
        root && root.removeAttribute("data-voice-speaking");
      };
      window.speechSynthesis.speak(utter);
    } catch (err) {
      root && root.removeAttribute("data-voice-speaking");
    }
  }

  function showSpeech(text, expression, holdMs, opts) {
    ensure();
    if (!prefs.enabled || !prefs.reactions_enabled) return;
    const options = opts || {};
    const now = Date.now();
    const isPriority = !!(options.priority || expression === "celebrating");
    if (!isPriority && now < priorityUntil) {
      return;
    }
    if (now - lastEventAt < frequencyGap() && !isPriority && !options.fromClick) {
      return;
    }
    lastEventAt = now;
    const hold = holdMs || 4200;
    if (isPriority) {
      priorityUntil = now + hold + 200;
      if (thoughtTimer) {
        window.clearTimeout(thoughtTimer);
        thoughtTimer = null;
      }
    }
    if (!dragActive) {
      placeSafe();
    }
    root.classList.remove("is-hidden");
    setExpression(expression || "happy", options.pose);
    speechEl.textContent = text;
    speechEl.classList.add("is-open");
    thoughtEl.classList.remove("is-open", "is-staging", "is-text-in");
    if (options.fromClick) {
      root.classList.add("is-clicked");
      window.setTimeout(function () {
        root && root.classList.remove("is-clicked");
      }, 700);
    }
    window.setTimeout(function () {
      speechEl.classList.remove("is-open");
      if (Date.now() >= priorityUntil - 50) {
        setExpression("idle");
      }
    }, hold);
  }

  function showThought(message, eyebrow) {
    ensure();
    if (!prefs.enabled || !prefs.thoughts_enabled) return;
    if (Date.now() < priorityUntil) return;
    placeSafe();
    root.classList.remove("is-hidden");
    setExpression("thinking");
    thoughtEl.querySelector(".mascot-thought-eyebrow").textContent = eyebrow || "Hmm…";
    thoughtEl.querySelector(".mascot-thought-text").textContent = message;
    thoughtEl.classList.remove("is-open", "is-text-in");
    thoughtEl.classList.add("is-staging");
    if (thoughtTimer) window.clearTimeout(thoughtTimer);
    window.setTimeout(function () {
      thoughtEl.classList.add("is-open");
    }, reduced ? 0 : 920);
    window.setTimeout(function () {
      thoughtEl.classList.add("is-text-in");
    }, reduced ? 0 : 1180);
    thoughtTimer = window.setTimeout(function () {
      thoughtEl.classList.remove("is-open", "is-staging", "is-text-in");
      if (Date.now() >= priorityUntil) {
        setExpression("curious");
      }
    }, 6800);
  }

  function onMascotClick(event) {
    if (event && typeof event.preventDefault === "function") {
      event.preventDefault();
      event.stopPropagation();
    }
    if (suppressClick || dragActive) return;
    ensure();
    if (!prefs.enabled || !prefs.reactions_enabled) return;
    const now = Date.now();
    if (now - lastClickAt < CLICK_COOLDOWN_MS) return;
    if (now < priorityUntil) return;
    lastClickAt = now;
    const kind = pageKind();
    const context = CLICK_CONTEXT[kind] || [];
    let pick;
    if (context.length && Math.random() < 0.35) {
      pick = context[Math.floor(Math.random() * context.length)];
    } else {
      pick = CLICK_INTROS[clickIntroIndex % CLICK_INTROS.length];
      clickIntroIndex += 1;
    }
    showSpeech(pick.text, pick.expression || "happy", 3800, {
      fromClick: true,
      priority: true,
      pose: pick.pose
    });
    if (prefs.voice_enabled) {
      speak(pick.text, true);
    }
  }

  async function maybeFact() {
    if (!prefs.enabled || !prefs.facts_enabled || !prefs.thoughts_enabled) return;
    if (Math.random() > (prefs.frequency === "frequent" ? 0.32 : 0.16)) return;
    try {
      const response = await fetch("/api/mascot/fact", { credentials: "same-origin" });
      const data = await response.json();
      if (!data || !data.ok || !data.fact) return;
      showThought(data.fact.fact, "Do you know?");
    } catch (err) {
      /* ignore */
    }
  }

  function pageGreeting() {
    if (!prefs.enabled || !prefs.reactions_enabled) return;
    const kind = pageKind();
    writeContext({ last_page: kind });
    const key = "mmle_page_intro_" + kind + "_" + (location.pathname || "/");
    if (sessionStorage.getItem(key)) return;
    sessionStorage.setItem(key, "1");
    const intro = PAGE_INTROS[kind] || PAGE_INTROS.default;
    function tryIntro() {
      if (Date.now() < priorityUntil) {
        /* Do not overwrite achievement celebrations; retry shortly after. */
        window.setTimeout(tryIntro, Math.max(250, priorityUntil - Date.now() + 80));
        return;
      }
      showSpeech(intro.text, intro.expression || "happy", 5200, {
        priority: true,
        pose: intro.pose
      });
      if (prefs.voice_enabled) {
        speak(intro.text, true);
      }
    }
    window.setTimeout(tryIntro, 700);
  }

  async function loadPrefs() {
    try {
      const response = await fetch("/api/mascot/preferences", { credentials: "same-origin" });
      if (!response.ok) return;
      const data = await response.json();
      prefs = Object.assign(prefs, data || {});
      ensure();
      if (prefs.enabled) {
        root.classList.remove("is-hidden");
        placeSafe();
        setExpression("idle");
        scheduleBlink();
      } else {
        root.classList.add("is-hidden");
      }
    } catch (err) {
      /* ignore */
    }
  }

  const eventMessages = {
    achievement_unlocked: function (detail) {
      if (!prefs.achievement_reactions_enabled) return;
      rememberAction("achievement_unlocked", detail);
      const line = contextualLine("achievement_unlocked", detail) || "Look what you earned!";
      const expr = rarityExpression(detail.rarity);
      const hold = (detail.rarity === "legendary" || detail.rarity === "epic") ? 6200 : 5600;
      showSpeech(line, expr, hold, {
        priority: true,
        pose: expr === "celebrating" ? "clap" : expr === "proud" ? "idle" : "wave"
      });
      speak(line, MAJOR_VOICE.achievement_unlocked);
      markContextSpoken();
    },
    language_discovered: function (detail) {
      rememberAction("language_discovered", detail);
      const line = contextualLine("language_discovered", detail) ||
        ("You discovered " + (detail.language || "a living language") + "!");
      showSpeech(line, "excited", 4500, { priority: true });
      speak(line, true);
      markContextSpoken();
      window.setTimeout(function () {
        setExpression("happy");
      }, 1600);
    },
    passport_complete: function () {
      rememberAction("passport_complete", {});
      showSpeech("Four languages. Your passport is complete!", "celebrating", 5600, {
        priority: true,
        pose: "hug"
      });
      speak("Four languages. Your passport is complete!", true);
      markContextSpoken();
    },
    lesson_completed: function (detail) {
      rememberAction("lesson_completed", detail);
      if (!canSpeakContext()) return;
      const line = contextualLine("lesson_completed", detail);
      showSpeech(line, "proud", 4200, { priority: true });
      markContextSpoken();
    },
    quiz_completed: function (detail) {
      rememberAction("quiz_completed", detail);
      if (!canSpeakContext()) return;
      const line = contextualLine("quiz_completed", detail);
      showSpeech(line, "encouraging", 4200, { priority: true });
      markContextSpoken();
    },
    word_saved: function (detail) {
      rememberAction("word_saved", detail);
      if (!canSpeakContext()) return;
      const line = contextualLine("word_saved", detail);
      showSpeech(line, "happy", 3800, { priority: true });
      markContextSpoken();
    },
    malaysia_arrived: function () {
      rememberAction("malaysia_arrived", {});
      showSpeech("Welcome to Malaysia. Find a glowing language beacon.", "curious", 4800, {
        priority: true
      });
    },
    login: function () {
      rememberAction("login", {});
      const line = contextualLine("login", {}) || "Welcome back! Ready to explore?";
      showSpeech(line, "happy", 4200, { priority: true });
      markContextSpoken();
    },
    streak_milestone: function (detail) {
      rememberAction("streak_milestone", detail);
      const line = contextualLine("streak_milestone", detail) || "Your streak is growing!";
      showSpeech(line, "excited", 5200, { priority: true });
      speak(line, true);
      markContextSpoken();
    }
  };

  window.addEventListener("mascotCompanionEvent", function (event) {
    const detail = event.detail || {};
    const handler = eventMessages[detail.type];
    if (!handler) return;
    /* Soft priority gate: ignore low-priority spam while a high-priority line is active */
    const rank = CONTEXT_PRIORITY[detail.type] || 9;
    if (rank > 3 && Date.now() < priorityUntil && detail.type !== "achievement_unlocked") {
      rememberAction(detail.type, detail);
      return;
    }
    handler(detail);
  });

  window.MMLEMascotContext = {
    read: readContext,
    write: writeContext,
    remember: rememberAction
  };

  // Layout helpers for safe companion docking (no API / no Tutor chat).
  window.MMLEMascotLayout = {
    placeSafe: placeSafe,
    ensure: ensure,
    reservedZones: reservedZones,
    nearestSafePosition: nearestSafePosition,
    isPositionSafe: isPositionSafe,
    saveUserPosition: saveUserPosition,
    loadUserPosition: loadUserPosition,
    getFootprint: getFootprint,
    applyLeftTop: applyLeftTop,
    finalizeUserDrop: finalizeUserDrop,
    DRAG_THRESHOLD_PX: DRAG_THRESHOLD_PX,
    POS_STORAGE_KEY: POS_STORAGE_KEY,
    DRAG_HINT_KEY: DRAG_HINT_KEY,
    DRAG_DONE_KEY: DRAG_DONE_KEY
  };

  window.addEventListener("mascotPreferencesUpdated", function (event) {
    prefs = Object.assign(prefs, event.detail || {});
    ensure();
    root.classList.toggle("is-hidden", !prefs.enabled);
    placeSafe();
  });

  window.addEventListener("heritagePassportUpdated", function (event) {
    const detail = event.detail || {};
    if (detail.newly_discovered) {
      const card = (detail.cards || []).find(function (c) { return c.key === detail.language; });
      window.dispatchEvent(
        new CustomEvent("mascotCompanionEvent", {
          detail: {
            type: "language_discovered",
            language: card ? card.display_name : detail.language
          }
        })
      );
      if (detail.complete) {
        window.dispatchEvent(
          new CustomEvent("mascotCompanionEvent", { detail: { type: "passport_complete" } })
        );
      }
    }
    if (window.reportNewAchievements && detail.new_achievements) {
      window.reportNewAchievements(detail.new_achievements);
    }
  });

  document.addEventListener("DOMContentLoaded", function () {
    const bodyObserver = new MutationObserver(function () {
      placeSafe();
    });
    bodyObserver.observe(document.body, { attributes: true, attributeFilter: ["class"] });

    window.addEventListener("mmleLayoutChanged", placeSafe);

    const tutorPanelEl = document.getElementById("ai-tutor-panel");
    if (tutorPanelEl) {
      const tutorObserver = new MutationObserver(function () {
        placeSafe();
      });
      tutorObserver.observe(tutorPanelEl, {
        attributes: true,
        attributeFilter: ["class"]
      });
    }

    loadPrefs().then(function () {
      const saved = loadUserPosition();
      if (saved) userPinned = true;
      pageGreeting();
      maybeDragTutorial();
      maybeFact();
      if (document.getElementById("world-explorer-card")) {
        const key = "mmle_world_explorer_visit";
        if (!sessionStorage.getItem(key)) {
          sessionStorage.setItem(key, "1");
          fetch("/api/achievements/evaluate", {
            method: "POST",
            credentials: "same-origin",
            headers: {
              "Content-Type": "application/json",
              "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || ""
            },
            body: JSON.stringify({ milestone: "world_explorer_visit" })
          })
            .then(function (r) { return r.json(); })
            .then(function (data) {
              if (data && data.new_achievements) {
                window.reportNewAchievements(data.new_achievements);
              }
            })
            .catch(function () {});
        }
      }
    });
    window.addEventListener("resize", placeSafe);
    window.addEventListener("earthMalaysiaFlightComplete", function () {
      fetch("/api/achievements/evaluate", {
        method: "POST",
        credentials: "same-origin",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": (document.querySelector('meta[name="csrf-token"]') || {}).content || ""
        },
        body: JSON.stringify({ milestone: "malaysia_arrived" })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.new_achievements) {
            window.reportNewAchievements(data.new_achievements);
          }
          window.dispatchEvent(
            new CustomEvent("mascotCompanionEvent", { detail: { type: "malaysia_arrived" } })
          );
        })
        .catch(function () {});
    });
  });
})();
