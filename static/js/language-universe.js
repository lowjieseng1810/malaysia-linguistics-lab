/* =========================================
   Malaysian Language Universe
   Overlay on the existing Three.js Earth.
   Uses only LANGUAGE_EXPLORER_META (verified data).
   ========================================= */

(function () {
    "use strict";

    /* Approximate community locations (geography only — not invented linguistics). */
    const LANGUAGE_COORDS = {
        iban: { lat: 2.3, lon: 113.0 },
        "kadazan-dusun": { lat: 5.9, lon: 116.2 },
        bidayuh: { lat: 1.35, lon: 110.35 },
        "mah-meri": { lat: 2.86, lon: 101.35 }
    };

    const meta = window.LANGUAGE_EXPLORER_META || {};
    const languages = Object.keys(meta);

    if (!languages.length) {
        return;
    }

    const globeStage = document.getElementById("globe-stage");
    const explorerCard = document.getElementById("world-explorer-card");
    if (!globeStage || !explorerCard) {
        return;
    }

    let selectedKey = null;
    let markersVisible = false;
    let rafId = 0;
    let discoverIndex = 0;

    const root = document.createElement("div");
    root.id = "language-universe";
    root.className = "language-universe";
    root.setAttribute("aria-live", "polite");

    const markersLayer = document.createElement("div");
    markersLayer.className = "universe-markers";
    markersLayer.setAttribute("role", "list");
    markersLayer.setAttribute("aria-label", "Living languages of Malaysia");
    /* Critical: layer must NOT capture Earth drag events. */
    markersLayer.style.pointerEvents = "none";

    const panel = document.createElement("aside");
    panel.className = "universe-profile";
    panel.id = "universe-profile";
    panel.hidden = true;
    panel.setAttribute("aria-hidden", "true");

    const discoverBar = document.createElement("div");
    discoverBar.className = "universe-discover-bar";
    discoverBar.innerHTML = `
        <button type="button" class="universe-discover-btn" id="universe-discover-lang">
            Discover a language
        </button>
        <button type="button" class="universe-discover-btn universe-discover-btn--ghost" id="universe-discover-word">
            Discover a word
        </button>
    `;

    const wordToast = document.createElement("div");
    wordToast.className = "universe-word-toast";
    wordToast.id = "universe-word-toast";
    wordToast.hidden = true;
    wordToast.setAttribute("role", "status");

    root.appendChild(markersLayer);
    root.appendChild(panel);
    root.appendChild(discoverBar);
    root.appendChild(wordToast);
    globeStage.appendChild(root);

    const markerEls = {};

    languages.forEach(function (key) {
        const info = meta[key] || {};
        const coords = LANGUAGE_COORDS[key];
        if (!coords) {
            return;
        }

        const btn = document.createElement("button");
        btn.type = "button";
        btn.className = "universe-marker";
        btn.setAttribute("role", "listitem");
        btn.setAttribute(
            "aria-label",
            (info.display_name || key) +
                (info.region ? ", " + info.region : "")
        );
        btn.dataset.lang = key;
        btn.innerHTML = `
            <span class="universe-marker-pulse" aria-hidden="true"></span>
            <span class="universe-marker-halo" aria-hidden="true"></span>
            <span class="universe-marker-core" aria-hidden="true"></span>
            <span class="universe-marker-label">
                <strong>${escapeHtml(info.display_name || key)}</strong>
                ${info.region ? `<span>${escapeHtml(shortRegion(info.region))}</span>` : ""}
            </span>
        `;

        btn.addEventListener("pointerdown", function (event) {
            event.stopPropagation();
        });

        btn.addEventListener("click", function (event) {
            event.stopPropagation();
            selectLanguage(key, true);
        });

        btn.addEventListener("keydown", function (event) {
            if (event.key === "Enter" || event.key === " ") {
                event.preventDefault();
                selectLanguage(key, true);
            }
        });

        markersLayer.appendChild(btn);
        markerEls[key] = btn;
    });

    function escapeHtml(value) {
        return String(value || "")
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;");
    }

    function shortRegion(region) {
        return String(region || "").split(",")[0].trim();
    }

    function buildWordLink(dictionaryUrl, word) {
        const base = String(dictionaryUrl || "");
        const sep = base.indexOf("?") >= 0 ? "&" : "?";
        return base + sep + "q=" + encodeURIComponent(word || "");
    }

    function formatCount(n) {
        if (n == null || n === "") {
            return null;
        }
        return String(n);
    }

    function selectLanguage(key, openPanel) {
        selectedKey = key;
        Object.keys(markerEls).forEach(function (k) {
            markerEls[k].classList.toggle("is-selected", k === key);
            markerEls[k].classList.toggle("is-dimmed", k !== key);
        });
        explorerCard.classList.toggle("universe-language-focused", !!key);
        if (openPanel) {
            renderProfile(key);
            markPassportDiscovery(key);
        }
    }

    function csrfToken() {
        const meta = document.querySelector('meta[name="csrf-token"]');
        return meta ? meta.getAttribute("content") || "" : "";
    }

    function markPassportDiscovery(langKey) {
        if (!langKey) {
            return;
        }
        fetch("/api/passport/discover", {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                "X-CSRFToken": csrfToken()
            },
            credentials: "same-origin",
            body: JSON.stringify({ language: langKey })
        })
            .then(function (response) {
                return response.json().then(function (data) {
                    return { ok: response.ok, data: data };
                });
            })
            .then(function (result) {
                if (!result.ok || !result.data || !result.data.success) {
                    return;
                }
                window.dispatchEvent(
                    new CustomEvent("heritagePassportUpdated", {
                        detail: result.data
                    })
                );
            })
            .catch(function () {
                /* Passport is optional — never block exploration. */
            });
    }

    function clearSelection() {
        selectedKey = null;
        Object.keys(markerEls).forEach(function (k) {
            markerEls[k].classList.remove("is-selected", "is-dimmed");
        });
        explorerCard.classList.remove("universe-language-focused");
        panel.hidden = true;
        panel.setAttribute("aria-hidden", "true");
        panel.classList.remove("is-open");
    }

    function renderProfile(key) {
        const info = meta[key];
        if (!info) {
            return;
        }

        const stats = [];
        const vocab = formatCount(info.vocab_count);
        const lessons = formatCount(info.lesson_count);
        const quizzes = formatCount(info.quiz_count);

        if (vocab != null) {
            stats.push(`<div><span>Vocabulary</span><strong>${vocab}</strong></div>`);
        }
        if (lessons != null) {
            stats.push(`<div><span>Lessons</span><strong>${lessons}</strong></div>`);
        }
        if (quizzes != null && Number(info.quiz_count) > 0) {
            stats.push(`<div><span>Quiz items</span><strong>${quizzes}</strong></div>`);
        }

        panel.innerHTML = `
            <button type="button" class="universe-profile-close" aria-label="Close language profile">×</button>
            <p class="universe-profile-eyebrow">Living language</p>
            <h3>${escapeHtml(info.display_name || key)}</h3>
            ${info.region ? `<p class="universe-profile-region">${escapeHtml(info.region)}</p>` : ""}
            <p class="universe-profile-blurb">${escapeHtml(info.blurb || "A living language of Malaysia")}</p>
            ${stats.length ? `<div class="universe-profile-stats">${stats.join("")}</div>` : ""}
            <div class="universe-profile-actions">
                ${info.dictionary_url ? `<a class="universe-action" href="${escapeHtml(info.dictionary_url)}">Explore Dictionary</a>` : ""}
                ${info.learn_url ? `<a class="universe-action universe-action--primary" href="${escapeHtml(info.learn_url)}">Learn</a>` : ""}
                ${info.compare_url ? `<a class="universe-action" href="${escapeHtml(info.compare_url)}">Compare</a>` : ""}
                ${info.quiz_url ? `<a class="universe-action" href="${escapeHtml(info.quiz_url)}">Quiz</a>` : ""}
            </div>
        `;

        const closeBtn = panel.querySelector(".universe-profile-close");
        if (closeBtn) {
            closeBtn.addEventListener("click", clearSelection);
        }

        panel.hidden = false;
        panel.setAttribute("aria-hidden", "false");
        panel.classList.add("is-open");
    }

    function showMarkers(show) {
        markersVisible = !!show;
        root.classList.toggle("markers-visible", markersVisible);
        if (markersVisible) {
            startMarkerLoop();
        }
    }

    function updateMarkerPositions() {
        if (!markersVisible || !window.EarthExplorer || !window.EarthExplorer.projectLatLon) {
            return;
        }

        Object.keys(markerEls).forEach(function (key) {
            const coords = LANGUAGE_COORDS[key];
            const el = markerEls[key];
            if (!coords || !el) {
                return;
            }
            const projected = window.EarthExplorer.projectLatLon(coords.lat, coords.lon);
            if (!projected || !projected.visible) {
                el.classList.add("is-occluded");
                el.style.opacity = "0";
                el.style.pointerEvents = "none";
                el.setAttribute("aria-hidden", "true");
                el.tabIndex = -1;
                return;
            }

            const facing = typeof projected.facing === "number" ? projected.facing : 1;
            const fade = Math.max(0.35, Math.min(1, (facing - 0.08) / 0.55));

            el.classList.remove("is-occluded");
            el.style.opacity = String(fade);
            el.style.pointerEvents = "auto";
            el.setAttribute("aria-hidden", "false");
            el.tabIndex = 0;
            el.style.transform =
                "translate3d(" +
                projected.x +
                "px, " +
                projected.y +
                "px, 0) translate(-50%, -50%)";
        });
    }

    function startMarkerLoop() {
        if (rafId) {
            return;
        }
        function tick() {
            updateMarkerPositions();
            rafId = window.requestAnimationFrame(tick);
        }
        rafId = window.requestAnimationFrame(tick);
    }

    function discoverLanguage() {
        if (!languages.length) {
            return;
        }
        const key = languages[discoverIndex % languages.length];
        discoverIndex += 1;
        showMarkers(true);
        selectLanguage(key, true);
        const el = markerEls[key];
        if (el) {
            el.classList.add("is-discovered");
            window.setTimeout(function () {
                el.classList.remove("is-discovered");
            }, 1600);
            try {
                el.focus({ preventScroll: true });
            } catch (focusError) {
                /* ignore */
            }
        }
    }

    function discoverWord() {
        const withWords = languages.filter(function (key) {
            return meta[key] && meta[key].sample_word && meta[key].sample_word.word;
        });
        if (!withWords.length) {
            wordToast.hidden = false;
            wordToast.innerHTML =
                "<p>No vocabulary samples are available yet.</p>";
            return;
        }
        const key = withWords[Math.floor(Math.random() * withWords.length)];
        const info = meta[key];
        const sample = info.sample_word;
        showMarkers(true);
        selectLanguage(key, true);
        wordToast.hidden = false;
        wordToast.innerHTML = `
            <p class="universe-word-eyebrow">A word from ${escapeHtml(info.display_name || key)}</p>
            <p class="universe-word-term">${escapeHtml(sample.word)}</p>
            ${sample.meaning ? `<p class="universe-word-meaning">${escapeHtml(sample.meaning)}</p>` : ""}
            ${info.dictionary_url ? `<a href="${escapeHtml(buildWordLink(info.dictionary_url, sample.word))}">Learn this word</a>` : ""}
        `;
    }

    const discoverLangBtn = document.getElementById("universe-discover-lang");
    const discoverWordBtn = document.getElementById("universe-discover-word");
    if (discoverLangBtn) {
        discoverLangBtn.addEventListener("click", discoverLanguage);
    }
    if (discoverWordBtn) {
        discoverWordBtn.addEventListener("click", discoverWord);
    }

    /*
     * Yellow language beacons stay visible from the initial WORLD view and remain
     * lat/lon-projected onto the Three.js globe (they move with rotation).
     */
    function enableInitialBeacons() {
        showMarkers(true);
    }

    if (window.EarthExplorer && window.EarthExplorer.projectLatLon) {
        enableInitialBeacons();
    } else {
        window.addEventListener("earthExplorerReady", enableInitialBeacons, { once: true });
    }

    window.addEventListener("earthMalaysiaArrivalReady", function () {
        showMarkers(true);
        root.classList.add("is-malaysia-focus");
    });

    window.addEventListener("earthMalaysiaFlightComplete", function () {
        showMarkers(true);
        root.classList.add("is-malaysia-focus");
    });

    window.addEventListener("earthMalaysiaFlightStarted", function () {
        root.classList.add("is-journeying");
    });

    document.addEventListener("visibilitychange", function () {
        if (document.hidden && rafId) {
            window.cancelAnimationFrame(rafId);
            rafId = 0;
        } else if (!document.hidden && markersVisible && !rafId) {
            startMarkerLoop();
        }
    });

    window.addEventListener("earthGlobeLayout", function () {
        if (markersVisible) {
            updateMarkerPositions();
        }
    });

    discoverBar.style.pointerEvents = "auto";
    panel.style.pointerEvents = "auto";
    wordToast.style.pointerEvents = "auto";
})();
