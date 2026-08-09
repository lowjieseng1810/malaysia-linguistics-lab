/* Heritage key (sidebar) + physically hanging board in dashboard content. */
(function () {
  "use strict";

  const STATE = {
    IDLE: "idle",
    ENTERING: "entering",
    DISPLAYING: "displaying",
    EXITING: "exiting",
    COOLDOWN: "cooldown"
  };

  const COOLDOWN_MS = 3000;
  const ATTENTION_MIN_MS = 16000;
  const ATTENTION_MAX_MS = 22000;
  const SPEECH_MIN_GAP_MS = 28000;
  const SPEECH_HOLD_MS = 2600;
  /* Physical timeline (ms) */
  const DESCENT_MS = 3000;
  const SETTLE_MS = 900;
  const RETRACT_MS = 4000; /* slower deliberate pull-up */
  const INITIAL_ROPE = 56;
  const ANCHOR_LEFT_FRAC = 0.22;
  const ANCHOR_RIGHT_FRAC = 0.78;

  const SPEECH_LINES = [
    "Click me!",
    "Come see what you found!",
    "There's something new!"
  ];

  const STREAK_KEYS = {
    first_streak: 3,
    on_a_roll: 7,
    heritage_habit: 14,
    dedicated_explorer: 30
  };

  const RARITY_LABELS = {
    common: "Common",
    uncommon: "Uncommon",
    rare: "Rare",
    epic: "Epic",
    legendary: "Legendary"
  };

  let root = null;
  let host = null;
  let state = STATE.IDLE;
  let queue = [];
  let lastShown = null;
  let cooldownTimer = null;
  let attentionTimer = null;
  let speechTimer = null;
  let lastSpeechAt = 0;
  let lastInteractionAt = 0;
  let animFrame = null;
  let draining = false;
  let triggerFetchBusy = false;
  let cooldownTickTimer = null;
  let cooldownStartedAt = 0;
  let keycapLabelDefault = "Heritage";

  /* Drag / pendulum state — only while DISPLAYING; never extends the hold timer. */
  let sessionAnchorY = 0;
  let sessionRestY = 0;
  let sessionFromY = 0;
  let sessionRestLen = 200;
  let sessionMaxAmp = 20;
  let sessionMaxX = 160;
  let swingTheta = 0; /* radians — angular pendulum state while displaying */
  let swingOmega = 0;
  let lastPose = { x: 0, y: 0, rot: 0, ropeL: 0, ropeR: 0, gapL: 0, gapR: 0 };
  let drag = {
    active: false,
    pointerId: null,
    startClientX: 0,
    startClientY: 0,
    x: 0,
    y: 0,
    vx: 0,
    vy: 0,
    lastClientX: 0,
    lastClientY: 0,
    lastT: 0
  };

  function contentWidth() {
    const main = document.getElementById("dash-main") || document.querySelector(".dash-main");
    const hostEl = contentHost();
    const w =
      (hostEl && hostEl.getBoundingClientRect().width) ||
      (main && main.getBoundingClientRect().width) ||
      (window.innerWidth || 1200) * 0.7;
    return Math.max(280, w);
  }

  function physicsLimits() {
    const narrow = (window.innerWidth || 1200) < 720;
    const cw = contentWidth();
    /* Large suspended arc: ~18–28% of content width (desktop), ~15–22% (mobile). */
    const maxX = Math.round(cw * (narrow ? 0.18 : 0.26));
    return {
      narrow: narrow,
      contentW: cw,
      maxX: maxX,
      /* Keep angles in a believable wooden-sign band; length carries the arc. */
      maxAmpDeg: narrow ? 22 : 28,
      maxDragYDown: narrow ? 40 : 56,
      maxDragYUp: narrow ? 28 : 40,
      /* Angular pendulum — heavy wooden sign (slow period, light damping). */
      gravity: narrow ? 8.6 : 6.8,
      damping: narrow ? 0.38 : 0.26
    };
  }

  function rotatePoint(px, py, cx, cy, deg) {
    const r = (deg * Math.PI) / 180;
    const cos = Math.cos(r);
    const sin = Math.sin(r);
    const dx = px - cx;
    const dy = py - cy;
    return { x: cx + dx * cos - dy * sin, y: cy + dx * sin + dy * cos };
  }

  const reduced = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  function rarityOf(item) {
    const r = (item && item.rarity ? String(item.rarity) : "common").toLowerCase();
    return RARITY_LABELS[r] ? r : "common";
  }

  function csrf() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") || "" : "";
  }

  function triggerEl() {
    return document.getElementById("heritage-trigger");
  }

  function speechEl() {
    return document.getElementById("heritage-trigger-speech");
  }

  function contentHost() {
    return (
      document.getElementById("heritage-plaque-host") ||
      document.getElementById("dash-main") ||
      document.querySelector(".dash-main")
    );
  }

  function setTriggerBusy() {
    const btn = triggerEl();
    if (!btn) return;
    const busy =
      state === STATE.ENTERING ||
      state === STATE.DISPLAYING ||
      state === STATE.EXITING ||
      state === STATE.COOLDOWN;
    btn.disabled = busy;
    btn.setAttribute(
      "aria-expanded",
      state === STATE.ENTERING || state === STATE.DISPLAYING || state === STATE.EXITING
        ? "true"
        : "false"
    );
    btn.classList.toggle("is-busy", state === STATE.ENTERING || state === STATE.DISPLAYING || state === STATE.EXITING);
    btn.classList.toggle("is-cooldown", state === STATE.COOLDOWN);
  }

  function canInteract() {
    return state === STATE.IDLE;
  }

  function buildStampHtml(item) {
    const cat = item.category || "getting_started";
    const icon = item.icon || "seal";
    const face = item.face_value != null ? item.face_value : 10;
    const year = item.issue_year || "2026";
    const title = item.title || "Achievement";
    const rarity = rarityOf(item);
    return (
      '<div class="postage-stamp postage-stamp--compact postage-stamp--' +
      cat +
      " postage-stamp--rarity-" +
      rarity +
      ' is-unlocked is-revealing" aria-hidden="true">' +
      '<span class="postage-stamp-body"></span>' +
      '<span class="postage-stamp-frame"></span>' +
      '<span class="postage-stamp-foil" aria-hidden="true"></span>' +
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
      RARITY_LABELS[rarity] +
      "</span>" +
      '<span class="postage-stamp-year">' +
      year +
      "</span>" +
      "</span></div>"
    );
  }

  function ensureRoot() {
    if (root && document.body.contains(root)) return root;
    host = contentHost();
    if (!host) {
      host = document.createElement("div");
      host.id = "heritage-plaque-host";
      host.className = "heritage-plaque-host";
      const main = document.querySelector(".dash-main");
      if (main) {
        main.insertBefore(host, main.firstChild);
      } else {
        document.body.appendChild(host);
      }
    }
    root = document.createElement("div");
    root.id = "heritage-plaque";
    root.className = "heritage-plaque";
    root.setAttribute("role", "dialog");
    root.setAttribute("aria-live", "polite");
    root.setAttribute("aria-modal", "false");
    root.innerHTML =
      '<span class="heritage-plaque-anchor heritage-plaque-anchor--left" aria-hidden="true"></span>' +
      '<span class="heritage-plaque-anchor heritage-plaque-anchor--right" aria-hidden="true"></span>' +
      '<span class="heritage-plaque-rope heritage-plaque-rope--left" aria-hidden="true"></span>' +
      '<span class="heritage-plaque-rope heritage-plaque-rope--right" aria-hidden="true"></span>' +
      '<div class="heritage-plaque-board">' +
      '<div class="heritage-plaque-stamp-slot"></div>' +
      '<div class="heritage-plaque-glints" aria-hidden="true"></div>' +
      '<div class="heritage-plaque-copy">' +
      '<p class="heritage-plaque-eyebrow">Achievement Unlocked</p>' +
      '<p class="heritage-plaque-rarity" hidden></p>' +
      '<h3 class="heritage-plaque-title"></h3>' +
      '<p class="heritage-plaque-desc"></p>' +
      '<p class="heritage-plaque-meta" hidden></p>' +
      '<a class="heritage-plaque-action" href="/achievements">View Achievements →</a>' +
      "</div></div>";
    host.appendChild(root);
    return root;
  }

  function layoutMetrics() {
    const vh = window.innerHeight || 800;
    const vw = window.innerWidth || 1200;
    const narrow = vw < 720;
    const hostEl = contentHost();
    if (hostEl) {
      void hostEl.offsetTop;
    }
    const hostTop = hostEl ? hostEl.getBoundingClientRect().top : 0;

    /*
     * Geometry is solved in VIEWPORT space first (navbar → visible landing),
     * then converted into host-local Y for absolute CSS. That keeps the plaque
     * on-screen when the dashboard is scrolled, without sticky pinning.
     */
    const navbar = document.querySelector(".navbar");
    const navBottom = navbar
      ? navbar.getBoundingClientRect().bottom
      : Math.min(72, vh * 0.1);

    const limits = physicsLimits();
    const anchorVp = navBottom - (narrow ? 2 : 4);
    const startVp = anchorVp + INITIAL_ROPE;
    /*
     * Rope length must support a large horizontal arc at a believable angle:
     *   maxX ≈ L * sin(θ)  →  L ≥ maxX / sin(θ)
     * Lower the rest point within the safe viewport band when needed.
     */
    const idealDeg = narrow ? 20 : 24;
    const needLen = Math.ceil(limits.maxX / Math.sin((idealDeg * Math.PI) / 180));
    const minTravelVp = Math.max(narrow ? 190 : 260, needLen - INITIAL_ROPE);
    /* Lower rest so L·sin(θ) can reach the viewport-% arc without forcing huge angles. */
    const maxRestVp = Math.min(vh * (narrow ? 0.58 : 0.6), vh - (narrow ? 140 : 140));
    const restVp = Math.min(
      Math.max(startVp + minTravelVp, vh * (narrow ? 0.36 : 0.4)),
      maxRestVp
    );

    const anchorY = Math.round(anchorVp - hostTop);
    const startY = Math.round(startVp - hostTop);
    const restY = Math.round(restVp - hostTop);
    const travel = Math.max(12, restY - startY);
    const restLen = Math.max(12, restY - anchorY);
    const ampRad = (limits.maxAmpDeg * Math.PI) / 180;
    /* Cap horizontal target to what this rope length can do at the amp band. */
    const geomMaxX = Math.floor(restLen * Math.sin(ampRad));
    return {
      travel: travel,
      restY: restY,
      startY: startY,
      anchorY: anchorY,
      maxX: Math.min(limits.maxX, geomMaxX),
      maxAmpDeg: limits.maxAmpDeg
    };
  }

  /** Smooth accelerate-then-decelerate lowering curve (heavy plaque). */
  function gravityLower(p) {
    const t = Math.max(0, Math.min(1, p));
    return t * t * (3 - 2 * t);
  }

  /**
   * Rigid board + two ropes. Eyelets MUST match CSS:
   *   transform: translate3d(board-x,0,0) rotate(rot)
   *   transform-origin: 50% 0
   * i.e. rotate around board top-center, THEN translate by board-x.
   * (Older math rotated around (center+x), which detached one rope when x ≠ 0.)
   */
  function boardEyelet(rootW, boardY, boardX, rotDeg, frac) {
    const ox = rootW * 0.5;
    const dx = rootW * frac - ox;
    const r = (rotDeg * Math.PI) / 180;
    const cos = Math.cos(r);
    const sin = Math.sin(r);
    return {
      x: ox + boardX + dx * cos,
      y: boardY + dx * sin
    };
  }

  function setPose(boardY, boardX, rotDeg, opacity, anchorY) {
    if (!root) return;
    const ay = anchorY != null ? anchorY : sessionAnchorY;
    const rot = rotDeg || 0;
    const x = boardX || 0;
    const rootW = root.offsetWidth || 400;

    const anchorL = { x: rootW * ANCHOR_LEFT_FRAC, y: ay };
    const anchorR = { x: rootW * ANCHOR_RIGHT_FRAC, y: ay };
    const attachL = boardEyelet(rootW, boardY, x, rot, ANCHOR_LEFT_FRAC);
    const attachR = boardEyelet(rootW, boardY, x, rot, ANCHOR_RIGHT_FRAC);

    function ropeSeg(a, t) {
      const dx = t.x - a.x;
      const dy = t.y - a.y;
      const len = Math.max(10, Math.sqrt(dx * dx + dy * dy));
      /*
       * The rope DOM element is a vertical bar rotated with CSS `rotate(deg)`
       * (clockwise-positive) around its own top-center (the anchor). Rotating
       * the "straight down" vector (0, len) by `ang` lands at
       * (-len·sin(ang), len·cos(ang)) — so to reach a target offset (dx, dy)
       * we need ang = atan2(-dx, dy), NOT atan2(dx, dy). The previous sign
       * mirrored the rope's lean whenever dx ≠ 0, which is exactly why the
       * rope visually swung away from the board eyelet during motion while
       * the (tautological) endX/endY bookkeeping still reported zero gap.
       */
      const ang = (Math.atan2(-dx, dy) * 180) / Math.PI;
      return { len: len, ang: ang, endX: a.x + dx, endY: a.y + dy };
    }

    const rL = ropeSeg(anchorL, attachL);
    const rR = ropeSeg(anchorR, attachR);
    const gapL = Math.hypot(rL.endX - attachL.x, rL.endY - attachL.y);
    const gapR = Math.hypot(rR.endX - attachR.x, rR.endY - attachR.y);

    root.style.setProperty("--anchor-y", ay + "px");
    root.style.setProperty("--plaque-y", boardY + "px");
    root.style.setProperty("--board-x", x + "px");
    root.style.setProperty("--plaque-rot", rot + "deg");
    root.style.setProperty("--rope-len", Math.max(rL.len, rR.len) + "px");
    root.style.setProperty("--rope-left-len", rL.len + "px");
    root.style.setProperty("--rope-right-len", rR.len + "px");
    root.style.setProperty("--rope-left-rot", rL.ang + "deg");
    root.style.setProperty("--rope-right-rot", rR.ang + "deg");
    if (opacity != null) {
      root.style.opacity = String(opacity);
    }

    lastPose = {
      x: x,
      y: boardY,
      rot: rot,
      ropeL: rL.len,
      ropeR: rR.len,
      gapL: gapL,
      gapR: gapR,
      attachL: attachL,
      attachR: attachR
    };
  }

  /**
   * Two-rope swing pose — never use single-point pendulum (ay + L·cos θ) which
   * lifts the board and detaches one rope visually at large |x|.
   */
  function setDualRopeSwingPose(thetaDeg, boardY, opacity, anchorY, nominalLen) {
    const ay = anchorY != null ? anchorY : sessionAnchorY;
    const L = Math.max(12, nominalLen != null ? nominalLen : sessionRestLen);
    const rad = (thetaDeg * Math.PI) / 180;
    const boardX = L * Math.sin(rad);
    const y = boardY != null ? boardY : sessionRestY;
    setPose(y, boardX, thetaDeg, opacity, ay);
    return { x: boardX, y: y, rot: thetaDeg };
  }

  function pulseGlints(rarity) {
    if (reduced) return;
    const glintsHost = root && root.querySelector(".heritage-plaque-glints");
    if (!glintsHost) return;
    glintsHost.innerHTML = "";
    const count = rarity === "legendary" ? 5 : rarity === "epic" ? 3 : rarity === "rare" ? 2 : 0;
    for (let i = 0; i < count; i += 1) {
      const spark = document.createElement("span");
      spark.className = "heritage-plaque-glint";
      spark.style.left = 42 + Math.random() * 48 + "%";
      spark.style.top = 18 + Math.random() * 55 + "%";
      spark.style.animationDelay = i * 90 + "ms";
      glintsHost.appendChild(spark);
    }
    window.setTimeout(function () {
      glintsHost.innerHTML = "";
    }, 1800);
  }

  function celebrateStreak(item) {
    const days = STREAK_KEYS[item.key];
    if (!days) return;
    document.querySelectorAll(".dash-stat--streak, .streak-flame").forEach(function (el) {
      el.classList.add("is-celebrating");
      window.setTimeout(function () {
        el.classList.remove("is-celebrating");
      }, 3200);
    });
    window.dispatchEvent(
      new CustomEvent("mascotCompanionEvent", {
        detail: { type: "streak_milestone", days: days, title: item.title }
      })
    );
  }

  function holdMsFor(rarity) {
    /* ~half of the previous 11–14s readable holds */
    if (reduced) return 2800;
    if (rarity === "legendary") return 7000;
    if (rarity === "epic") return 6500;
    if (rarity === "rare") return 6000;
    return 5500;
  }

  function restoreKeycap() {
    const btn = triggerEl();
    if (!btn) return;
    const label = btn.querySelector(".heritage-key-label");
    const icon = btn.querySelector(".heritage-key-icon");
    if (label) label.textContent = keycapLabelDefault;
    if (icon) icon.hidden = false;
    btn.classList.remove("is-counting");
    if (cooldownTickTimer) {
      window.clearTimeout(cooldownTickTimer);
      cooldownTickTimer = null;
    }
  }

  function tickCooldownKeycap() {
    const btn = triggerEl();
    if (!btn || state !== STATE.COOLDOWN) {
      restoreKeycap();
      return;
    }
    const remainingMs = Math.max(0, COOLDOWN_MS - (Date.now() - cooldownStartedAt));
    const secs = Math.max(1, Math.ceil(remainingMs / 1000));
    const label = btn.querySelector(".heritage-key-label");
    const icon = btn.querySelector(".heritage-key-icon");
    if (icon) icon.hidden = true;
    if (label) label.textContent = secs + "s";
    btn.classList.add("is-counting");
    if (remainingMs > 0) {
      cooldownTickTimer = window.setTimeout(tickCooldownKeycap, 120);
    }
  }

  function endDrag() {
    if (!drag.active) return;
    const board = root && root.querySelector(".heritage-plaque-board");
    if (board && drag.pointerId != null) {
      try {
        board.releasePointerCapture(drag.pointerId);
      } catch (err) {
        /* ignore */
      }
    }
    drag.active = false;
    drag.pointerId = null;
  }

  function maxSwingTheta() {
    const limits = physicsLimits();
    const L = Math.max(sessionRestLen, 48);
    const ampCap = ((sessionMaxAmp || limits.maxAmpDeg) * Math.PI) / 180;
    const geomCap = Math.asin(Math.min(0.95, (sessionMaxX || limits.maxX) / L));
    return Math.min(ampCap, geomCap);
  }

  /**
   * While dragging, drive the rigid board directly from pointer geometry.
   * setPose keeps both rope endpoints on the real eyelets (not a single-L pendulum
   * shortcut that could leave one rope visually detached at large |x|).
   */
  function applyDragPose(boardX, boardY) {
    const limits = physicsLimits();
    const maxTheta = maxSwingTheta();
    const L = Math.max(sessionRestLen, 48);
    const maxX = L * Math.sin(maxTheta);
    const x = Math.max(-maxX, Math.min(maxX, boardX));
    const minY = sessionAnchorY + L * 0.82;
    const maxY = sessionAnchorY + L + limits.maxDragYDown;
    const y = Math.max(minY, Math.min(maxY, boardY));
    const rot = Math.max(
      -limits.maxAmpDeg,
      Math.min(limits.maxAmpDeg, x * 0.12)
    );
    setPose(y, x, rot, 1, sessionAnchorY);
    swingTheta = Math.atan2(x, Math.max(24, y - sessionAnchorY));
  }

  function applySuspendedPose(boardY, boardX, forceRot) {
    const L = Math.max(sessionRestLen, 48);
    const maxTheta = maxSwingTheta();
    const maxX = L * Math.sin(maxTheta);
    const x = Math.max(-maxX, Math.min(maxX, boardX));
    let theta =
      forceRot != null
        ? (forceRot * Math.PI) / 180
        : Math.atan2(x, Math.max(24, boardY - sessionAnchorY));
    theta = Math.max(-maxTheta, Math.min(maxTheta, theta));
    setDualRopeSwingPose((theta * 180) / Math.PI, boardY, 1, sessionAnchorY, L);
    swingTheta = theta;
  }

  function stepAngularPendulum(dtSec, limits) {
    /* Map px rope length into a slow period (~2.5–4s), not a snappy UI spring. */
    const L = Math.max(0.55, sessionRestLen / 220);
    const g = limits.gravity;
    const damp = limits.damping;
    /* θ'' = -(g/L) sinθ - c θ' */
    const alpha = -(g / L) * Math.sin(swingTheta) - damp * swingOmega;
    swingOmega += alpha * dtSec;
    swingTheta += swingOmega * dtSec;
    const maxTheta = maxSwingTheta();
    if (swingTheta > maxTheta) {
      swingTheta = maxTheta;
      swingOmega *= -0.28;
    } else if (swingTheta < -maxTheta) {
      swingTheta = -maxTheta;
      swingOmega *= -0.28;
    }
    setDualRopeSwingPose(
      (swingTheta * 180) / Math.PI,
      sessionRestY,
      1,
      sessionAnchorY,
      sessionRestLen
    );
    drag.x = lastPose.x;
    drag.y = lastPose.y - sessionRestY;
  }

  function bindBoardDrag() {
    if (!root || root.dataset.dragBound === "1") return;
    const board = root.querySelector(".heritage-plaque-board");
    if (!board) return;
    root.dataset.dragBound = "1";

    board.addEventListener("pointerdown", function (event) {
      if (reduced) return;
      if (state !== STATE.DISPLAYING) return;
      if (event.button != null && event.button !== 0) return;
      /* Touch + mouse: capture so the suspended board can be dragged on all devices. */
      event.preventDefault();
      drag.active = true;
      drag.pointerId = event.pointerId;
      drag.startClientX = event.clientX - drag.x;
      drag.startClientY = event.clientY - drag.y;
      drag.lastClientX = event.clientX;
      drag.lastClientY = event.clientY;
      drag.lastT = performance.now();
      drag.vx = 0;
      drag.vy = 0;
      board.classList.add("is-dragging");
      board.style.touchAction = "none";
      try {
        board.setPointerCapture(event.pointerId);
      } catch (err) {
        /* ignore */
      }
    });

    board.addEventListener("pointermove", function (event) {
      if (!drag.active || event.pointerId !== drag.pointerId) return;
      if (state !== STATE.DISPLAYING) {
        endDrag();
        board.classList.remove("is-dragging");
        return;
      }
      const now = performance.now();
      const dt = Math.max(8, now - drag.lastT);
      const limits = physicsLimits();
      let nx = event.clientX - drag.startClientX;
      let ny = event.clientY - drag.startClientY;
      const maxTheta = maxSwingTheta();
      const maxX = Math.max(sessionRestLen, 48) * Math.sin(maxTheta);
      nx = Math.max(-maxX, Math.min(maxX, nx));
      ny = Math.max(-limits.maxDragYUp, Math.min(limits.maxDragYDown, ny));
      drag.vx = ((event.clientX - drag.lastClientX) / dt) * 16;
      drag.vy = ((event.clientY - drag.lastClientY) / dt) * 16;
      drag.lastClientX = event.clientX;
      drag.lastClientY = event.clientY;
      drag.lastT = now;
      drag.x = nx;
      drag.y = ny;
      applyDragPose(drag.x, sessionRestY + drag.y);
      swingOmega = drag.vx / 48;
    });

    function release(event) {
      if (!drag.active || (event && event.pointerId !== drag.pointerId)) return;
      endDrag();
      board.classList.remove("is-dragging");
      board.style.touchAction = "";
      /* Keep angular inertia — several progressively smaller swings. */
      drag.vx = Math.max(-36, Math.min(36, drag.vx));
      drag.vy = Math.max(-14, Math.min(14, drag.vy));
      /* Convert horizontal release velocity into a heavy angular kick. */
      swingOmega = Math.max(-2.4, Math.min(2.4, drag.vx / 48));
      if (Math.abs(swingOmega) < 0.35 && Math.abs(swingTheta) > 0.08) {
        /* Letting go near an extreme still returns with weight. */
        swingOmega += (swingTheta > 0 ? -0.55 : 0.55);
      }
    }
    board.addEventListener("pointerup", release);
    board.addEventListener("pointercancel", release);
  }

  function fillBoard(item) {
    const el = ensureRoot();
    const rarity = rarityOf(item);
    el.className = "heritage-plaque is-visible heritage-plaque--rarity-" + rarity;
    el.querySelector(".heritage-plaque-title").textContent = item.title || "Achievement";
    el.querySelector(".heritage-plaque-desc").textContent = item.description || "";
    const rarityEl = el.querySelector(".heritage-plaque-rarity");
    if (rarityEl) {
      rarityEl.hidden = false;
      rarityEl.textContent = RARITY_LABELS[rarity];
      rarityEl.className = "heritage-plaque-rarity heritage-plaque-rarity--" + rarity;
    }
    const stampSlot = el.querySelector(".heritage-plaque-stamp-slot");
    if (stampSlot) {
      stampSlot.innerHTML = buildStampHtml(item);
      const stamp = stampSlot.querySelector(".postage-stamp");
      if (stamp && !reduced) {
        window.requestAnimationFrame(function () {
          stamp.classList.add("is-pressed");
        });
        window.setTimeout(function () {
          stamp.classList.remove("is-revealing");
        }, 900);
      } else if (stamp) {
        stamp.classList.remove("is-revealing");
      }
    }
    pulseGlints(rarity);
    const meta = el.querySelector(".heritage-plaque-meta");
    if (meta) {
      const bits = [];
      if (item.earned_date_label) bits.push("Earned " + item.earned_date_label);
      if (item.earned != null && item.total != null) {
        bits.push(item.earned + " / " + item.total + " collected");
      }
      if (bits.length) {
        meta.hidden = false;
        meta.textContent = bits.join(" · ");
      } else {
        meta.hidden = true;
        meta.textContent = "";
      }
    }
    const link = el.querySelector(".heritage-plaque-action");
    link.href = "/achievements#" + encodeURIComponent(item.key || "");
    link.textContent = "View Achievements →";
    return rarity;
  }

  function enterCooldown() {
    state = STATE.COOLDOWN;
    setTriggerBusy();
    cooldownStartedAt = Date.now();
    tickCooldownKeycap();
    if (cooldownTimer) window.clearTimeout(cooldownTimer);
    cooldownTimer = window.setTimeout(function () {
      state = STATE.IDLE;
      restoreKeycap();
      setTriggerBusy();
      scheduleAttention();
      drain();
    }, COOLDOWN_MS);
  }

  function showOne(item) {
    return new Promise(function (resolve) {
      if (!item || !item.title) {
        resolve();
        return;
      }
      state = STATE.ENTERING;
      setTriggerBusy();
      hideSpeech();
      endDrag();
      drag.x = 0;
      drag.y = 0;
      drag.vx = 0;
      drag.vy = 0;

      const rarity = fillBoard(item);
      lastShown = item;
      document.body.classList.add("heritage-plaque-active");
      if (host) host.setAttribute("aria-hidden", "false");
      bindBoardDrag();

      window.dispatchEvent(
        new CustomEvent("mascotCompanionEvent", {
          detail: {
            type: "achievement_unlocked",
            title: item.title,
            description: item.description,
            key: item.key,
            rarity: rarity,
            earned: item.earned,
            total: item.total
          }
        })
      );
      celebrateStreak(item);

      const hold = holdMsFor(rarity);
      /* Immediate pose so the board never flashes at CSS defaults; refined after focus settles. */
      (function seedPose() {
        const layout = layoutMetrics();
        const limits = physicsLimits();
        sessionFromY = layout.startY;
        sessionRestY = layout.restY;
        sessionAnchorY = layout.anchorY;
        sessionRestLen = Math.max(12, layout.restY - layout.anchorY);
        sessionMaxAmp = layout.maxAmpDeg || limits.maxAmpDeg;
        sessionMaxX = layout.maxX || limits.maxX;
        /* Seed state must match the start of a straight vertical descent: level board, θ=0. */
        swingTheta = 0;
        swingOmega = 0;
        setDualRopeSwingPose(
          0,
          sessionFromY,
          1,
          layout.anchorY,
          INITIAL_ROPE
        );
      })();

      function beginMotion() {
        /* Re-measure once after click/focus so navbar anchors match the visible viewport. */
        const layout = layoutMetrics();
        const limits = physicsLimits();
        const fromY = layout.startY;
        const restY = layout.restY;
        const anchorY = layout.anchorY;
        const restLen = Math.max(12, restY - anchorY);
        const fromLen = INITIAL_ROPE;
        sessionFromY = fromY;
        sessionRestY = restY;
        sessionAnchorY = anchorY;
        sessionRestLen = restLen;
        sessionMaxAmp = layout.maxAmpDeg || limits.maxAmpDeg;
        sessionMaxX = layout.maxX || limits.maxX;
        /* Straight vertical descent starts level — θ=0, both ropes vertical/parallel. */
        swingTheta = 0;
        swingOmega = 0;
        setDualRopeSwingPose(0, fromY, 1, anchorY, fromLen);

        function finish() {
          if (animFrame) {
            window.cancelAnimationFrame(animFrame);
            animFrame = null;
          }
          endDrag();
          const board = root && root.querySelector(".heritage-plaque-board");
          if (board) board.classList.remove("is-dragging");
          setDualRopeSwingPose(0, anchorY + Math.max(8, fromLen * 0.4), 0, anchorY, fromLen);
          if (root) root.classList.remove("is-visible");
          document.body.classList.remove("heritage-plaque-active");
          if (host) host.setAttribute("aria-hidden", "true");
          enterCooldown();
          resolve();
        }

        if (reduced) {
          setDualRopeSwingPose(0, restY, 1, anchorY, restLen);
          state = STATE.DISPLAYING;
          window.setTimeout(function () {
            state = STATE.EXITING;
            setTriggerBusy();
            setDualRopeSwingPose(0, anchorY + fromLen, 0, anchorY, fromLen);
            window.setTimeout(finish, 220);
          }, hold);
          return;
        }

        let start = null;
        let lastFrameTs = null;
        const enterEnd = DESCENT_MS;
        const settleEnd = enterEnd + SETTLE_MS;
        const holdEnd = settleEnd + hold;
        const retractEnd = holdEnd + RETRACT_MS;
        let retractStartX = 0;
        let retractStartY = restY;
        let retractStartRot = 0;

        function frame(ts) {
          if (start == null) start = ts;
          const t = ts - start;
          const dtSec =
            lastFrameTs == null
              ? 0.016
              : Math.min(0.032, Math.max(0.008, (ts - lastFrameTs) / 1000));
          lastFrameTs = ts;

          if (t < enterEnd) {
            /*
             * Straight vertical descent: board stays perfectly level (θ=0, x=0)
             * and both ropes stay vertical/parallel — only the rope length (and
             * therefore board Y) changes. No diagonal ropes, no tilt, ever.
             */
            state = STATE.ENTERING;
            const p = t / enterEnd;
            const ease = gravityLower(p);
            const L = fromLen + (restLen - fromLen) * ease;
            setDualRopeSwingPose(0, anchorY + L, 1, anchorY, L);
            swingTheta = 0;
            swingOmega = 0;
            drag.x = 0;
            drag.y = lastPose.y - restY;
          } else if (t < settleEnd) {
            /*
             * Soft settle: still perfectly level/centered — only a small damped
             * vertical bounce on the rope length (heavy sign "landing" on taut
             * ropes). Real pendulum swinging only begins once this is done.
             */
            state = STATE.ENTERING;
            const p = (t - enterEnd) / (settleEnd - enterEnd);
            const damp = Math.exp(-4.4 * p);
            const bounce = Math.sin(p * Math.PI * 2.4) * damp;
            const L = restLen * (1 + 0.05 * bounce);
            setDualRopeSwingPose(0, anchorY + L, 1, anchorY, L);
            swingTheta = 0;
            swingOmega = 0;
            drag.x = 0;
            drag.y = lastPose.y - restY;
          } else if (t < holdEnd) {
            state = STATE.DISPLAYING;
            setTriggerBusy();
            if (drag.active) {
              /* Pose driven by pointermove; display timer still advances. */
            } else if (
              Math.abs(swingTheta) < 0.02 &&
              Math.abs(swingOmega) < 0.08 &&
              Math.abs(drag.vx) < 0.15 &&
              Math.abs(drag.x) < 2
            ) {
              /* Resting pose until the user drags. */
              swingTheta = 0;
              swingOmega = 0;
              drag.x = 0;
              drag.y = 0;
              setDualRopeSwingPose(0, restY, 1, anchorY, restLen);
            } else {
              /* Angular pendulum — several slowing swings after a strong release. */
              stepAngularPendulum(dtSec, limits);
              if (Math.abs(swingTheta) < 0.012 && Math.abs(swingOmega) < 0.04) {
                swingTheta = 0;
                swingOmega = 0;
                drag.x = 0;
                drag.y = 0;
                drag.vx = 0;
                drag.vy = 0;
                setDualRopeSwingPose(0, restY, 1, anchorY, restLen);
              }
            }
          } else if (t < retractEnd) {
            if (state !== STATE.EXITING) {
              endDrag();
              const board = root && root.querySelector(".heritage-plaque-board");
              if (board) board.classList.remove("is-dragging");
              retractStartX = lastPose.x;
              retractStartY = lastPose.y;
              retractStartRot = lastPose.rot;
              drag.x = 0;
              drag.y = 0;
              drag.vx = 0;
              drag.vy = 0;
            }
            state = STATE.EXITING;
            setTriggerBusy();
            const p = (t - holdEnd) / (retractEnd - holdEnd);
            /* Slow ease-in-out pull upward — ropes shorten continuously. */
            const ease = p * p * (3 - 2 * p);
            const targetLen = Math.max(10, fromLen * 0.55);
            const startLen = Math.max(targetLen, retractStartY - anchorY);
            const L = startLen + (targetLen - startLen) * ease;
            /*
             * Heavy-sign inertia wobble while rising: a decaying oscillation
             * layered on top of the base pull-up, fading to zero well before
             * the board disappears so it settles before it's gone. This only
             * ever changes the theta/boardX FED INTO setPose() below — the
             * rope endpoints are always re-derived from that real board
             * transform every frame, so no amount of wobble can detach a
             * rope; it just rides the same real two-point suspension.
             */
            const wobbleP = Math.min(p, 0.9) / 0.9;
            const wobbleEnvelope = Math.sin(wobbleP * Math.PI) * Math.exp(-2.2 * p);
            const wobbleAngleMax = Math.min(8, limits.maxAmpDeg * 0.4);
            const wobbleXMax = Math.min(12, limits.maxX * 0.18);
            const wobbleAngle =
                wobbleAngleMax * wobbleEnvelope * Math.sin(p * Math.PI * 2 * 2.4);
            const wobbleX =
                wobbleXMax * wobbleEnvelope * Math.sin(p * Math.PI * 2 * 2.4 + 0.6);
            /* Retract on the same suspension arc as descent/swing — both ropes shorten together. */
            const theta = retractStartRot * (1 - ease) * 0.85 + wobbleAngle;
            const boardX = retractStartX * (1 - ease) + wobbleX;
            setPose(anchorY + L, boardX, theta, 1, anchorY);
          } else {
            finish();
            return;
          }
          animFrame = window.requestAnimationFrame(frame);
        }
        animFrame = window.requestAnimationFrame(frame);
      }

      window.requestAnimationFrame(function () {
        window.requestAnimationFrame(beginMotion);
      });
    });
  }

  async function drain() {
    if (draining) return;
    if (!canInteract()) return;
    if (!queue.length) return;
    draining = true;
    try {
      while (queue.length) {
        if (state !== STATE.IDLE) break;
        const next = queue.shift();
        await showOne(next);
        if (queue.length) {
          await new Promise(function (r) {
            const wait = function () {
              if (state === STATE.IDLE) r();
              else window.setTimeout(wait, 120);
            };
            wait();
          });
        }
      }
    } finally {
      draining = false;
    }
  }

  function ackKeys(keys) {
    if (!keys.length) return;
    fetch("/api/achievements/ack", {
      method: "POST",
      credentials: "same-origin",
      headers: {
        "Content-Type": "application/json",
        "X-CSRFToken": csrf()
      },
      body: JSON.stringify({ keys: keys })
    }).catch(function () {});
  }

  function enqueue(items, opts) {
    const options = opts || {};
    const list = Array.isArray(items) ? items : items ? [items] : [];
    const accepted = [];
    list.forEach(function (item) {
      if (!item || !item.title) return;
      if (queue.some(function (q) { return q.key === item.key; })) return;
      if (lastShown && lastShown.key === item.key && options.skipDuplicateRecent) return;
      queue.push(item);
      accepted.push(item.key);
    });
    if (accepted.length && !options.skipAck) ackKeys(accepted);
    if (canInteract()) drain();
  }

  function hideSpeech() {
    const bubble = speechEl();
    if (!bubble) return;
    bubble.classList.remove("is-open");
    bubble.hidden = true;
    if (speechTimer) {
      window.clearTimeout(speechTimer);
      speechTimer = null;
    }
  }

  function showSpeech(text) {
    const bubble = speechEl();
    if (!bubble || !text) return;
    bubble.hidden = false;
    bubble.textContent = text;
    window.requestAnimationFrame(function () {
      bubble.classList.add("is-open");
    });
    lastSpeechAt = Date.now();
    if (speechTimer) window.clearTimeout(speechTimer);
    speechTimer = window.setTimeout(hideSpeech, SPEECH_HOLD_MS);
  }

  function scheduleAttention() {
    if (attentionTimer) {
      window.clearTimeout(attentionTimer);
      attentionTimer = null;
    }
    if (!triggerEl()) return;
    const delay = ATTENTION_MIN_MS + Math.random() * (ATTENTION_MAX_MS - ATTENTION_MIN_MS);
    attentionTimer = window.setTimeout(runAttention, delay);
  }

  function runAttention() {
    attentionTimer = null;
    if (!canInteract()) {
      scheduleAttention();
      return;
    }
    if (Date.now() - lastInteractionAt < COOLDOWN_MS) {
      scheduleAttention();
      return;
    }
    const active = document.activeElement;
    if (
      active &&
      active !== triggerEl() &&
      active.closest &&
      (active.closest(".ai-tutor-panel") ||
        active.closest("#ai-tutor-toggle-button") ||
        active.closest(".mascot-companion") ||
        active.tagName === "INPUT" ||
        active.tagName === "TEXTAREA" ||
        active.isContentEditable)
    ) {
      scheduleAttention();
      return;
    }

    const btn = triggerEl();
    if (!btn) return;

    if (!reduced) {
      btn.classList.remove("is-hopping");
      void btn.offsetWidth;
      btn.classList.add("is-hopping");
      window.setTimeout(function () {
        btn.classList.remove("is-hopping");
      }, 780);
    }

    if (Date.now() - lastSpeechAt >= SPEECH_MIN_GAP_MS && Math.random() < 0.5) {
      showSpeech(SPEECH_LINES[Math.floor(Math.random() * SPEECH_LINES.length)]);
    }

    scheduleAttention();
  }

  async function latestUnlocked() {
    try {
      const response = await fetch("/api/achievements", { credentials: "same-origin" });
      if (!response.ok) return null;
      const data = await response.json();
      const entries = data.entries || data.items || [];
      const unlocked = entries
        .filter(function (e) { return e && e.unlocked; })
        .sort(function (a, b) {
          return (b.unlocked_at || 0) - (a.unlocked_at || 0);
        });
      if (!unlocked.length) return null;
      const top = unlocked[0];
      return {
        key: top.key,
        title: top.title,
        description: top.description,
        category: top.category,
        icon: top.icon,
        face_value: top.face_value,
        issue_year: top.issue_year,
        rarity: top.rarity,
        unlocked_at: top.unlocked_at,
        earned_date_label: top.earned_date_label,
        earned: data.earned,
        total: data.total
      };
    } catch (err) {
      return null;
    }
  }

  async function onTriggerClick(event) {
    if (event) {
      event.preventDefault();
      event.stopPropagation();
    }
    lastInteractionAt = Date.now();
    hideSpeech();

    const btn = triggerEl();
    if (btn) {
      /* Keep the user's scroll context — do not jump the sidebar into view. */
      try {
        btn.focus({ preventScroll: true });
      } catch (focusErr) {
        /* ignore */
      }
      btn.classList.add("is-pressed");
      window.setTimeout(function () {
        btn.classList.remove("is-pressed");
      }, 140);
    }

    if (!canInteract() || draining || triggerFetchBusy) return;

    if (queue.length) {
      drain();
      return;
    }

    if (lastShown) {
      queue.push(lastShown);
      drain();
      return;
    }

    triggerFetchBusy = true;
    setTriggerBusy();
    try {
      const latest = await latestUnlocked();
      if (!latest) {
        showSpeech("Explore to earn stamps!");
        state = STATE.IDLE;
        setTriggerBusy();
        return;
      }
      lastShown = latest;
      queue.push(latest);
      drain();
    } finally {
      triggerFetchBusy = false;
      if (state === STATE.IDLE) setTriggerBusy();
    }
  }

  function bindTrigger() {
    const btn = triggerEl();
    if (!btn || btn.dataset.bound === "1") return;
    btn.dataset.bound = "1";
    const label = btn.querySelector(".heritage-key-label");
    if (label && label.textContent) keycapLabelDefault = label.textContent.trim() || "Heritage";
    btn.addEventListener("click", onTriggerClick);
    btn.addEventListener("keydown", function (event) {
      if (event.key === "Enter" || event.key === " ") {
        event.preventDefault();
        onTriggerClick(event);
      }
    });
    scheduleAttention();
  }

  async function pullPending() {
    try {
      const response = await fetch("/api/achievements/pending", {
        credentials: "same-origin"
      });
      if (!response.ok) return;
      const data = await response.json();
      if (data && data.pending && data.pending.length) {
        enqueue(data.pending, { skipAck: true });
      }
    } catch (err) {
      /* ignore */
    }
  }

  window.HeritageAchievements = {
    enqueue: enqueue,
    show: enqueue,
    getState: function () { return state; },
    _seedLastShown: function (item) {
      if (item && item.title) lastShown = item;
    },
    _timing: {
      DESCENT_MS: DESCENT_MS,
      SETTLE_MS: SETTLE_MS,
      RETRACT_MS: RETRACT_MS,
      COOLDOWN_MS: COOLDOWN_MS,
      holdMsFor: holdMsFor
    },
    _layoutMetrics: layoutMetrics,
    _debugPose: function () {
      if (!root) return null;
      return {
        y: parseFloat(root.style.getPropertyValue("--plaque-y")) || 0,
        anchorY: parseFloat(root.style.getPropertyValue("--anchor-y")) || 0,
        rope: parseFloat(root.style.getPropertyValue("--rope-len")) || 0,
        ropeL: lastPose.ropeL,
        ropeR: lastPose.ropeR,
        gapL: lastPose.gapL,
        gapR: lastPose.gapR,
        rot: parseFloat(root.style.getPropertyValue("--plaque-rot")) || 0,
        x: parseFloat(root.style.getPropertyValue("--board-x")) || 0,
        dragActive: drag.active,
        dragX: drag.x,
        dragY: drag.y,
        maxAmp: sessionMaxAmp,
        visible: root.classList.contains("is-visible"),
        state: state
      };
    }
  };

  window.reportNewAchievements = function (items) {
    enqueue(items);
  };

  document.addEventListener("DOMContentLoaded", function () {
    bindTrigger();
    pullPending();
  });

  window.addEventListener("heritageAchievementsUnlocked", function (event) {
    const detail = event.detail || {};
    enqueue(detail.achievements || detail.items || detail);
  });
})();
