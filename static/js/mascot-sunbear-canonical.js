/* Canonical Malayan sun bear — single source of truth (navbar head, floating full, AI Tutor head). */
(function (global) {
  "use strict";

  var PALETTE = {
    fur: "#1A1A1C",
    furSoft: "#2C2C30",
    furRim: "#3D342C",
    muzzle: "#F7EFE2",
    muzzleShade: "#EDE3D2",
    /* Warm cream fur pigmentation — natural sun-bear chest, not cloth white */
    chest: "#E8D7A8",
    chestDeep: "#D4C089",
    chestSoft: "#EFD9A3",
    earInner: "#E8B84A",
    earInnerDeep: "#D4A43A",
    pawPad: "#F2E6D4",
    nose: "#0E0E10",
    eye: "#121214",
    blush: "#F0A090",
    collar: "#1F5C44",
    gold: "#E8C56A",
    cream: "#FFF6E8",
    tongue: "#E88878",
    shadow: "#050808"
  };

  /** Shared face — species cues: compact snout, small rounded ears, calm eyes. */
  function headMarkup() {
    return (
      '<g class="mascot-head-group">' +

      /* Compact rounded bear head with slight forehead mass */
      '<ellipse class="mascot-head" cx="50" cy="49" rx="31" ry="30.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse cx="50" cy="49" rx="31" ry="30.5" fill="none" stroke="' + PALETTE.furRim + '" stroke-width="1.8" opacity="0.75"/>' +

      /* Small rounded sun-bear ears — organic, attached, not mouse circles */
      '<ellipse class="mascot-ear mascot-ear--left" cx="23" cy="21" rx="9" ry="10.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-ear mascot-ear--right" cx="77" cy="21" rx="9" ry="10.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse cx="23" cy="21" rx="9" ry="10.5" fill="none" stroke="' + PALETTE.furRim + '" stroke-width="1.2" opacity="0.7"/>' +
      '<ellipse cx="77" cy="21" rx="9" ry="10.5" fill="none" stroke="' + PALETTE.furRim + '" stroke-width="1.2" opacity="0.7"/>' +
      '<ellipse class="mascot-ear-inner mascot-ear-inner--left" cx="23.2" cy="22" rx="4.2" ry="5" fill="' + PALETTE.earInner + '"/>' +
      '<ellipse class="mascot-ear-inner mascot-ear-inner--right" cx="76.8" cy="22" rx="4.2" ry="5" fill="' + PALETTE.earInner + '"/>' +
      '<ellipse cx="23.2" cy="23" rx="1.8" ry="2.1" fill="' + PALETTE.earInnerDeep + '" opacity="0.4"/>' +
      '<ellipse cx="76.8" cy="23" rx="1.8" ry="2.1" fill="' + PALETTE.earInnerDeep + '" opacity="0.4"/>' +

      /*
       * Broad compact cream snout — species muzzle, not a panda mask.
       * Softly irregular silhouette so it reads as fur, not a sticker.
       */
      '<path class="mascot-muzzle" d="' +
      "M36.5 54.5" +
      "c1.4-3.2 6.2-5.4 13.5-5.4" +
      "c7.4 0 12.2 2.2 13.6 5.4" +
      "c1.2 2.8.2 6.8-2.4 9.6" +
      "c-2.8 3-7.2 4.6-11.2 4.5" +
      "c-4.2-.1-8.4-1.8-11-4.8" +
      "c-2.4-2.7-3.2-6.6-2.5-9.3" +
      'z" fill="' + PALETTE.muzzle + '"/>' +
      '<ellipse cx="50" cy="60" rx="8" ry="3.2" fill="' + PALETTE.muzzleShade + '" opacity="0.35"/>' +

      /* Quiet brows — expression emphasis without anime eyes */
      '<path class="mascot-brow mascot-brow--left" d="M32.5 36.5c1.6-0.55 4.8-0.55 6.4 0" fill="none" stroke="#0A0A0C" stroke-width="1.25" stroke-linecap="round" opacity="0.2"/>' +
      '<path class="mascot-brow mascot-brow--right" d="M61.1 36.5c1.6-0.55 4.8-0.55 6.4 0" fill="none" stroke="#0A0A0C" stroke-width="1.25" stroke-linecap="round" opacity="0.2"/>' +

      /*
       * Natural friendly eyes — moderate soft-oval, small highlight.
       * Surrounding dark fur keeps them from dominating the face.
       */
      '<g class="mascot-eyes">' +
      /* Gaze groups: tiny translate only — no extra pupil overpaint */
      '<g class="mascot-gaze mascot-gaze--left">' +
      '<ellipse class="mascot-eye mascot-eye--left" cx="37.5" cy="42" rx="4.3" ry="4.7" fill="' + PALETTE.eye + '"/>' +
      '<circle class="mascot-shine mascot-shine--a" cx="36.2" cy="40.8" r="1" fill="#FFFFFF"/>' +
      "</g>" +
      '<g class="mascot-gaze mascot-gaze--right">' +
      '<ellipse class="mascot-eye mascot-eye--right" cx="62.5" cy="42" rx="4.3" ry="4.7" fill="' + PALETTE.eye + '"/>' +
      '<circle class="mascot-shine mascot-shine--b" cx="61.2" cy="40.8" r="1" fill="#FFFFFF"/>' +
      "</g>" +
      '<path class="mascot-eye-closed mascot-eye-closed--left" d="M33.2 43c2 2 6.2 2 8.2 0" fill="none" stroke="#0A0A0C" stroke-width="2" stroke-linecap="round" opacity="0"/>' +
      '<path class="mascot-eye-closed mascot-eye-closed--right" d="M58.2 43c2 2 6.2 2 8.2 0" fill="none" stroke="#0A0A0C" stroke-width="2" stroke-linecap="round" opacity="0"/>' +
      '<path class="mascot-eye-proud mascot-eye-proud--left" d="M33.5 43.5c1.8 1.4 5.4 1.4 7.2 0" fill="none" stroke="#0A0A0C" stroke-width="1.8" stroke-linecap="round" opacity="0"/>' +
      '<path class="mascot-eye-proud mascot-eye-proud--right" d="M58.5 43.5c1.8 1.4 5.4 1.4 7.2 0" fill="none" stroke="#0A0A0C" stroke-width="1.8" stroke-linecap="round" opacity="0"/>' +
      '<g class="mascot-stars" opacity="0">' +
      '<path d="M37.5 37.2l.85 2.1 2.2.1-1.7 1.35.5 2.1-1.85-1.1-1.85 1.1.5-2.1-1.7-1.35 2.2-.1z" fill="' + PALETTE.gold + '"/>' +
      '<path d="M62.5 37.2l.85 2.1 2.2.1-1.7 1.35.5 2.1-1.85-1.1-1.85 1.1.5-2.1-1.7-1.35 2.2-.1z" fill="' + PALETTE.gold + '"/>' +
      "</g>" +
      '<ellipse class="mascot-sleepy-lid mascot-sleepy-lid--left" cx="37.5" cy="40" rx="4.5" ry="2.8" fill="' + PALETTE.fur + '" opacity="0"/>' +
      '<ellipse class="mascot-sleepy-lid mascot-sleepy-lid--right" cx="62.5" cy="40" rx="4.5" ry="2.8" fill="' + PALETTE.fur + '" opacity="0"/>' +
      '<rect class="mascot-lid mascot-lid--left" x="33" y="37.2" width="9" height="0" rx="3" fill="' + PALETTE.fur + '"/>' +
      '<rect class="mascot-lid mascot-lid--right" x="58" y="37.2" width="9" height="0" rx="3" fill="' + PALETTE.fur + '"/>' +
      "</g>" +

      /* Compact rounded nose on upper snout */
      '<ellipse class="mascot-nose" cx="50" cy="55.2" rx="3.5" ry="2.6" fill="' + PALETTE.nose + '"/>' +
      '<ellipse cx="48.9" cy="54.5" rx="0.7" ry="0.5" fill="#FFFFFF" opacity="0.32"/>' +

      /* Soft bear mouths */
      '<path class="mascot-mouth mascot-mouth--neutral" d="M46 62.5c1.4.85 4.6.85 6 0" fill="none" stroke="#1A1210" stroke-width="1.75" stroke-linecap="round"/>' +
      '<path class="mascot-mouth mascot-mouth--smile" d="M44.2 61.5c2.2 2.8 9.4 2.8 11.6 0" fill="none" stroke="#1A1210" stroke-width="2" stroke-linecap="round" opacity="0"/>' +
      '<path class="mascot-mouth mascot-mouth--grin" d="M43.2 61c2.4 3.8 11.2 3.8 13.6 0" fill="none" stroke="#1A1210" stroke-width="2.1" stroke-linecap="round" opacity="0"/>' +
      '<ellipse class="mascot-mouth mascot-mouth--wow" cx="50" cy="63.2" rx="2.6" ry="2.8" fill="#1A1210" opacity="0"/>' +
      '<ellipse class="mascot-mouth mascot-mouth--yawn" cx="50" cy="63.6" rx="3.6" ry="3.8" fill="#1A1210" opacity="0"/>' +
      '<ellipse class="mascot-tongue" cx="50" cy="65.4" rx="2" ry="1.35" fill="' + PALETTE.tongue + '" opacity="0"/>' +

      /* Soft blush on dark cheeks beside snout */
      '<ellipse class="mascot-blush mascot-blush--left" cx="30" cy="55.5" rx="3.8" ry="2.4" fill="' + PALETTE.blush + '" opacity="0.45"/>' +
      '<ellipse class="mascot-blush mascot-blush--right" cx="70" cy="55.5" rx="3.8" ry="2.4" fill="' + PALETTE.blush + '" opacity="0.45"/>' +
      "</g>"
    );
  }

  /**
   * Natural Malayan sun-bear chest fur patch (solid, organic).
   * Broad upper chest, soft irregular edges, slight lower point —
   * NOT a U/horseshoe, hole, bib, or badge.
   */
  function chestMarkup() {
    return (
      /* Solid organic chest patch — fur pigmentation under the collar */
      '<path class="mascot-chest" d="' +
      "M34.2 83.6" +
      "C29.5 84.8 27.2 89.2 28.6 94.2" +
      "C30.1 99.6 34.8 104.2 41.2 106.8" +
      "C44.6 108.2 47.8 109.4 50.2 109.6" +
      "C53.4 109.8 56.8 108.4 60.6 105.8" +
      "C66.8 101.6 71.2 96.2 71.8 91.2" +
      "C72.4 86.6 69.2 83.2 64.4 82.8" +
      "C60.8 82.5 57.6 84.2 55.4 86.4" +
      "C53.6 84.2 51.2 82.8 48.4 82.6" +
      "C44.6 82.4 39.8 82.6 34.2 83.6" +
      'Z" fill="' + PALETTE.chest + '"/>' +
      /* Soft asymmetric shade — reads as fur depth, not a cloth fold */
      '<path class="mascot-chest-shade" d="' +
      "M36.5 88" +
      "c-1.8 2.2-2.2 5.4-.4 7.8" +
      "c1.6 2.2 4.6 3.6 7.6 3.2" +
      "c-2.2-1.8-3.4-4.6-3-7.2" +
      "c.2-1.4.8-2.8 1.6-3.8" +
      "c-2.2-.2-4.2-.2-5.8 0" +
      'z" fill="' + PALETTE.chestDeep + '" opacity="0.28"/>' +
      '<path class="mascot-chest-lobe" d="' +
      "M58.5 87.5" +
      "c1.6 1.4 2.6 3.8 2.2 6.2" +
      "c-.4 2.4-2.2 4.4-4.6 5.2" +
      "c1.8-1.6 2.6-4 2.4-6.2" +
      "c-.1-1.2-.5-2.4-1.2-3.4" +
      "c.4-.4.8-.8 1.2-1.8" +
      'z" fill="' + PALETTE.chestSoft + '" opacity="0.4"/>' +

      /* Thin collar + pendant sit on top of the fur patch */
      '<ellipse class="mascot-collar" cx="50" cy="81.2" rx="10" ry="1.45" fill="' + PALETTE.collar + '"/>' +
      '<circle class="mascot-pendant" cx="50" cy="88.8" r="2.1" fill="' + PALETTE.gold + '"/>' +
      '<circle cx="50" cy="88.5" r="1.25" fill="' + PALETTE.cream + '"/>' +
      '<circle cx="49.25" cy="88.15" r="0.32" fill="' + PALETTE.fur + '"/>' +
      '<circle cx="50.75" cy="88.15" r="0.32" fill="' + PALETTE.fur + '"/>' +
      '<ellipse cx="50" cy="89" rx="0.58" ry="0.4" fill="' + PALETTE.fur + '"/>'
    );
  }

  function bodyMarkup() {
    return (
      '<ellipse class="mascot-shadow" cx="50" cy="118" rx="24" ry="5" fill="' + PALETTE.shadow + '" opacity="0.3"/>' +

      /* Short rounded animal legs — visible, not human shoes */
      '<g class="mascot-legs">' +
      '<ellipse class="mascot-leg mascot-leg--left" cx="38" cy="107" rx="10" ry="7.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-leg mascot-leg--right" cx="62" cy="107" rx="10" ry="7.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-pad mascot-pad--foot-left" cx="38" cy="111.5" rx="5" ry="2.6" fill="' + PALETTE.pawPad + '" opacity="0.55"/>' +
      '<ellipse class="mascot-pad mascot-pad--foot-right" cx="62" cy="111.5" rx="5" ry="2.6" fill="' + PALETTE.pawPad + '" opacity="0.55"/>' +
      "</g>" +

      /* Torso first so arms can join at the shoulders without a gap */
      '<ellipse class="mascot-body" cx="50" cy="93.5" rx="24" ry="16.5" fill="' + PALETTE.fur + '"/>' +
      '<ellipse cx="50" cy="93.5" rx="24" ry="16.5" fill="none" stroke="' + PALETTE.furRim + '" stroke-width="1.3" opacity="0.5"/>' +

      /*
       * Continuous stubby arms: shoulder mass sits ON the torso (cx≈30/70),
       * then forearm + paw extend outward as one connected limb.
       * Pivot for pose transforms is the inner/shoulder edge (CSS).
       */
      '<g class="mascot-arms">' +
      '<g class="mascot-arm mascot-arm--left">' +
      '<ellipse class="mascot-shoulder mascot-shoulder--left" cx="30.5" cy="88.5" rx="9.2" ry="8.2" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-forearm mascot-forearm--left" cx="21.5" cy="93.5" rx="8.2" ry="8.8" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-pad mascot-pad--left" cx="15.8" cy="98.2" rx="4.5" ry="3.4" fill="' + PALETTE.pawPad + '"/>' +
      "</g>" +
      '<g class="mascot-arm mascot-arm--right">' +
      '<ellipse class="mascot-shoulder mascot-shoulder--right" cx="69.5" cy="88.5" rx="9.2" ry="8.2" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-forearm mascot-forearm--right" cx="78.5" cy="93.5" rx="8.2" ry="8.8" fill="' + PALETTE.fur + '"/>' +
      '<ellipse class="mascot-pad mascot-pad--right" cx="84.2" cy="98.2" rx="4.5" ry="3.4" fill="' + PALETTE.pawPad + '"/>' +
      "</g>" +
      "</g>" +

      '<ellipse class="mascot-tail" cx="50" cy="108" rx="3.2" ry="2.3" fill="' + PALETTE.furSoft + '" opacity="0"/>' +

      headMarkup() +
      chestMarkup() +

      '<g class="mascot-prop mascot-prop--heart" opacity="0">' +
      '<path d="M50 98c-7.5-7.5-17-2-17 5.5 0 9.5 17 17 17 17s17-7.5 17-17c0-7.5-9.5-13-17-5.5z" fill="#E85A5A"/>' +
      "</g>" +
      '<g class="mascot-fx mascot-fx--confetti" opacity="0">' +
      '<circle cx="16" cy="22" r="2.2" fill="' + PALETTE.gold + '"/>' +
      '<circle cx="86" cy="26" r="2" fill="#E85A5A"/>' +
      '<rect x="20" y="50" width="4" height="4" rx="1" fill="#5BB8E8" transform="rotate(20 22 52)"/>' +
      '<rect x="78" y="54" width="4" height="4" rx="1" fill="#7BC96F" transform="rotate(-15 80 56)"/>' +
      '<circle cx="12" cy="72" r="1.8" fill="#E8A0D0"/>' +
      '<circle cx="90" cy="70" r="1.8" fill="' + PALETTE.gold + '"/>' +
      "</g>" +
      '<g class="mascot-fx mascot-fx--zzz" opacity="0">' +
      '<text x="80" y="24" fill="#6AA8E8" font-size="10" font-family="Georgia, serif" font-weight="700">Z</text>' +
      '<text x="88" y="16" fill="#6AA8E8" font-size="8" font-family="Georgia, serif" font-weight="700">z</text>' +
      '<text x="94" y="10" fill="#6AA8E8" font-size="6" font-family="Georgia, serif" font-weight="700">z</text>' +
      "</g>" +
      '<g class="mascot-fx mascot-fx--query" opacity="0">' +
      '<text x="82" y="22" fill="#C9A24A" font-size="16" font-family="Georgia, serif" font-weight="700">?</text>' +
      "</g>" +
      '<g class="mascot-fx mascot-fx--bang" opacity="0">' +
      '<text x="84" y="22" fill="#C9A24A" font-size="16" font-family="Georgia, serif" font-weight="700">!</text>' +
      "</g>" +
      '<g class="mascot-fx mascot-fx--sparkle" opacity="0">' +
      '<path d="M14 38l1.1 2.7 2.7.12-2.1 1.7.6 2.7L14 44l-2.4 1.3.6-2.7-2.1-1.7 2.7-.12z" fill="' + PALETTE.gold + '"/>' +
      '<path d="M86 36l.9 2.2 2.2.12-1.7 1.4.5 2.2L86 40.8l-2.1 1.1.5-2.2-1.7-1.4 2.2-.12z" fill="' + PALETTE.gold + '"/>' +
      "</g>"
    );
  }

  function renderInline(options) {
    options = options || {};
    var width = options.width || 96;
    var height = options.height || 112;
    var klass = options.className || "mascot-svg";
    return (
      '<svg class="' + klass + '" viewBox="0 0 100 124" width="' + width + '" height="' + height + '" ' +
      'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">' +
      bodyMarkup() +
      "</svg>"
    );
  }

  function renderHeadOnly(options) {
    options = options || {};
    var width = options.width || 64;
    var height = options.height || 64;
    var klass = options.className || "mascot-svg mascot-svg--head";
    return (
      '<svg class="' + klass + '" viewBox="12 4 76 78" width="' + width + '" height="' + height + '" ' +
      'xmlns="http://www.w3.org/2000/svg" aria-hidden="true" focusable="false">' +
      headMarkup() +
      "</svg>"
    );
  }

  function renderDocument(options) {
    options = options || {};
    var viewBox = options.viewBox || "0 0 100 124";
    var label = options.label || "Malayan sun bear companion";
    var markup = options.headOnly ? headMarkup() : bodyMarkup();
    return (
      '<svg xmlns="http://www.w3.org/2000/svg" viewBox="' + viewBox + '" role="img" aria-label="' + label + '">' +
      markup +
      "</svg>\n"
    );
  }

  function renderHeadDocument(options) {
    options = options || {};
    return renderDocument({
      viewBox: options.viewBox || "12 4 76 78",
      label: options.label || "Malayan sun bear",
      headOnly: true
    });
  }

  global.MMLEMascot = {
    palette: PALETTE,
    renderInline: renderInline,
    renderHeadOnly: renderHeadOnly,
    renderDocument: renderDocument,
    renderHeadDocument: renderHeadDocument,
    bodyMarkup: bodyMarkup,
    headMarkup: headMarkup,
    chestMarkup: chestMarkup,
    version: "sun-bear-final-v3c"
  };
})(typeof window !== "undefined" ? window : globalThis);
