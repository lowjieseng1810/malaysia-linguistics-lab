/* =========================================
   Malaysia Linguistics Lab
   Dashboard — Living Malaysia Explorer
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const exploreButton =
        document.getElementById("explore-world-button");

    const explorerCard =
        document.getElementById("world-explorer-card");

    const globeStage =
        document.getElementById("globe-stage");


    if (explorerCard) {
        explorerCard.dataset.explorerState = "world";
    }

    if (!exploreButton || !explorerCard || !globeStage) {

        console.error(
            "World Explorer elements could not be found."
        );

        return;
    }


    let transitionRunning = false;

    let malaysiaStageCreated = false;

    /* =========================================
       LIVE USER LOCATION ON EARTH
       ========================================= */

    function initialiseUserLocation() {

        const interactiveGlobe =
            document.getElementById(
                "interactive-globe"
            );


        const globeStatus =
            globeStage.querySelector(
                ".globe-status"
            );


        if (!interactiveGlobe || !globeStatus) {
            return;
        }


        const statusText =
            globeStatus.querySelector(
                "span:last-child"
            );


        const userMarker =
            document.createElement("div");


        userMarker.className =
            "user-globe-marker";


        userMarker.setAttribute(
            "aria-hidden",
            "true"
        );


        userMarker.innerHTML = `

            <span class="user-marker-ring">
            </span>

            <span class="user-marker-core">
            </span>

            <span class="user-marker-label">
                You are here
            </span>

        `;


        interactiveGlobe.appendChild(
            userMarker
        );


        if (!navigator.geolocation) {

            if (statusText) {

                statusText.textContent =
                    "Location unavailable · Malaysia awaits";

            }


            return;
        }


        if (statusText) {

            statusText.textContent =
                "Finding your place in the world";

        }


        navigator.geolocation.getCurrentPosition(

            function (position) {

                const latitude =
                    position.coords.latitude;


                const longitude =
                    position.coords.longitude;


                /*
                   Convert real latitude and longitude
                   into a stable visual position on the
                   front-facing CSS globe.

                   This is a visual globe projection,
                   not a GIS map projection.
                */

                const horizontalPosition =
                    50 + (longitude / 180) * 34;


                const verticalPosition =
                    50 - (latitude / 90) * 34;


                const safeLeft =
                    Math.max(
                        18,
                        Math.min(
                            82,
                            horizontalPosition
                        )
                    );


                const safeTop =
                    Math.max(
                        18,
                        Math.min(
                            82,
                            verticalPosition
                        )
                    );


                userMarker.style.left =
                    safeLeft + "%";


                userMarker.style.top =
                    safeTop + "%";


                window.requestAnimationFrame(
                    function () {

                        userMarker.classList.add(
                            "is-visible"
                        );

                    }
                );


                globeStatus.classList.add(
                    "has-location"
                );


                if (statusText) {

                    statusText.textContent =
                        "Your place found · Malaysia awaits";

                }

            },


            function () {

                if (statusText) {

                    statusText.textContent =
                        "Your world · Malaysia awaits";

                }

            },


            {
                enableHighAccuracy: false,

                timeout: 8000,

                maximumAge: 300000
            }

        );
    }


    initialiseUserLocation();
    
    /* =========================================
       CREATE LIVING MALAYSIA STAGE
       ========================================= */

    function createMalaysiaStage() {

        if (malaysiaStageCreated) {
            return;
        }


        malaysiaStageCreated = true;


        const malaysiaStage =
            document.createElement("div");


        malaysiaStage.className =
            "living-malaysia-stage";


        malaysiaStage.id =
            "living-malaysia-stage";


        malaysiaStage.innerHTML = `

            <div class="malaysia-ambient-world"
                 aria-hidden="true">

                <div class="malaysia-sky-glow">
                </div>

                <div class="malaysia-mist mist-one">
                </div>

                <div class="malaysia-mist mist-two">
                </div>

                <div class="malaysia-mist mist-three">
                </div>

            </div>


            <div class="miniature-ocean"
                 aria-hidden="true">

                <span class="ocean-current current-one">
                </span>

                <span class="ocean-current current-two">
                </span>

                <span class="ocean-current current-three">
                </span>

                <span class="ocean-current current-four">
                </span>

            </div>


            <div class="malaysia-stage-header">

                <span class="malaysia-stage-eyebrow">
                    Living Malaysia
                </span>

                <h3>
                    Choose a place.
                    Discover a living language.
                </h3>

                <p>
                    Follow the glowing signals across Malaysia
                    and discover the communities behind each language.
                </p>

            </div>


            <div class="malaysia-experience-layout">


                <div class="miniature-map-scene"
                     id="miniature-map-scene">


                    <div class="map-compass"
                         aria-hidden="true">

                        <span class="compass-letter">
                            N
                        </span>

                        <span class="compass-line">
                        </span>

                    </div>


                    <div class="real-malaysia-map-wrap">

                        <object
                            class="real-malaysia-map"
                            id="real-malaysia-map"
                            type="image/svg+xml"
                            data="/static/images/malaysia_map.svg"
                            aria-label="Map of Malaysia">
                        </object>

                        <!--
                          All state beacons live inside the map wrap so SVG/geo
                          placement stays attached when the map scales or floats.
                        -->
                        <button
                            class="exploration-beacon selangor-beacon"
                            type="button"
                            data-region="selangor"
                            aria-label="Explore Mah Meri in Selangor">

                            <span class="beacon-outer-ring"></span>
                            <span class="beacon-middle-ring"></span>
                            <span class="beacon-core"></span>
                            <span class="beacon-label">
                                <strong>Selangor</strong>
                                <small>1 living language</small>
                            </span>
                            <span class="beacon-connector" aria-hidden="true"></span>
                        </button>

                        <button
                            class="exploration-beacon sarawak-beacon"
                            type="button"
                            data-region="sarawak"
                            aria-label="Explore languages in Sarawak">

                            <span class="beacon-outer-ring"></span>
                            <span class="beacon-middle-ring"></span>
                            <span class="beacon-core"></span>
                            <span class="beacon-label">
                                <strong>Sarawak</strong>
                                <small>2 living languages</small>
                            </span>
                            <span class="beacon-connector" aria-hidden="true"></span>
                        </button>

                        <button
                            class="exploration-beacon sabah-beacon"
                            type="button"
                            data-region="sabah"
                            aria-label="Explore languages in Sabah">

                            <span class="beacon-outer-ring"></span>
                            <span class="beacon-middle-ring"></span>
                            <span class="beacon-core"></span>
                            <span class="beacon-label">
                                <strong>Sabah</strong>
                                <small>1 living language</small>
                            </span>
                            <span class="beacon-connector" aria-hidden="true"></span>
                        </button>

                    </div>


                    <div class="map-stage-instruction">

                        <span class="instruction-signal"
                              aria-hidden="true">
                        </span>

                        Select a glowing signal

                    </div>

                </div>


                <aside
                    class="region-discovery-panel"
                    id="region-discovery-panel"
                    aria-live="polite">

                    ${getEmptyDiscoveryHTML()}

                </aside>


            </div>


            <div class="malaysia-stage-footer">

                <span>
                    01
                </span>

                <p>
                    Every signal marks a place where language,
                    community, and living heritage meet.
                </p>

            </div>

        `;


        explorerCard.appendChild(
            malaysiaStage
        );


        activateExplorationBeacons();
        /* Geo placement runs after is-malaysia-view layout — see onFlightComplete. */

        /* Bring the Malaysia map into view — avoids looking like an empty green void. */
        window.requestAnimationFrame(function () {
            try {
                malaysiaStage.scrollIntoView({
                    behavior: "smooth",
                    block: "start"
                });
            } catch (err) {
                malaysiaStage.scrollIntoView(true);
            }
        });
    }


    /*
     * Place the Selangor beacon from real lat/lon (Mah Meri / Carey Island),
     * calibrated against Sabah + Sarawak SVG land paths already in malaysia_map.svg
     * using the same community coordinates as language-universe.js.
     */
    function getSelangorGeo() {
        const fromMah =
            window.MAH_MERI_DATA &&
            window.MAH_MERI_DATA.language
                ? window.MAH_MERI_DATA.language
                : null;
        if (
            fromMah &&
            typeof fromMah.lat === "number" &&
            typeof fromMah.lon === "number"
        ) {
            return { lat: fromMah.lat, lon: fromMah.lon, source: "MAH_MERI_DATA" };
        }
        /* Fallback identical to LANGUAGE_COORDS["mah-meri"]. */
        return { lat: 2.86, lon: 101.35, source: "LANGUAGE_COORDS.mah-meri" };
    }


    let cachedMalaysiaSvgDoc = null;
    let malaysiaSvgPrefetchPromise = null;

    function resolveMalaysiaSvgDoc(mapObject) {
        if (!mapObject) {
            return null;
        }
        const live = mapObject.contentDocument;
        if (live && live.documentElement) {
            cachedMalaysiaSvgDoc = live;
            return live;
        }
        return cachedMalaysiaSvgDoc;
    }

    function prefetchMalaysiaSvg(mapObject) {
        if (cachedMalaysiaSvgDoc) {
            return Promise.resolve(cachedMalaysiaSvgDoc);
        }
        if (malaysiaSvgPrefetchPromise) {
            return malaysiaSvgPrefetchPromise;
        }
        if (!mapObject) {
            return Promise.resolve(null);
        }
        const url =
            mapObject.getAttribute("data") ||
            "/static/images/malaysia_map.svg";
        malaysiaSvgPrefetchPromise = fetch(url, { credentials: "same-origin" })
            .then(function (resp) {
                return resp.text();
            })
            .then(function (text) {
                const parser = new DOMParser();
                cachedMalaysiaSvgDoc = parser.parseFromString(
                    text,
                    "image/svg+xml"
                );
                return cachedMalaysiaSvgDoc;
            })
            .catch(function () {
                return null;
            });
        return malaysiaSvgPrefetchPromise;
    }


    function placeBeaconAtSvg(beacon, mapObject, wrap, svgX, svgY, meta) {
        const svgDoc = resolveMalaysiaSvgDoc(mapObject);
        if (!svgDoc || !beacon || !wrap) {
            return false;
        }
        const svgRoot = svgDoc.documentElement;
        const vb = (svgRoot.getAttribute("viewBox") || "0 0 915 400")
            .trim()
            .split(/[\s,]+/)
            .map(Number);
        const vbX = vb[0] || 0;
        const vbY = vb[1] || 0;
        const vbW = vb[2] || 915;
        const vbH = vb[3] || 400;
        const u = (svgX - vbX) / vbW;
        const v = (svgY - vbY) / vbH;
        const mapRect = mapObject.getBoundingClientRect();
        const wrapRect = wrap.getBoundingClientRect();
        if (wrapRect.width < 8) {
            return false;
        }
        /* Object may report 0×0 while SVG is still painting — map fills the wrap. */
        const refRect =
            mapRect.width >= 8 && mapRect.height >= 8 ? mapRect : wrapRect;
        const pageX = refRect.left + u * refRect.width;
        const pageY = refRect.top + v * refRect.height;
        const leftPct = ((pageX - wrapRect.left) / wrapRect.width) * 100;
        const topPct = ((pageY - wrapRect.top) / wrapRect.height) * 100;
        const safeLeft = Math.max(2, Math.min(98, leftPct));
        const safeTop = Math.max(2, Math.min(98, topPct));
        beacon.style.setProperty("left", safeLeft.toFixed(2) + "%", "important");
        beacon.style.setProperty("top", safeTop.toFixed(2) + "%", "important");
        beacon.style.setProperty("right", "auto", "important");
        beacon.style.setProperty("bottom", "auto", "important");
        beacon.style.setProperty("transform", "translate(-50%, -50%)", "important");
        beacon.classList.add("is-geo-placed");
        beacon.dataset.geoLeftPct = safeLeft.toFixed(2);
        beacon.dataset.geoTopPct = safeTop.toFixed(2);
        beacon.dataset.geoSvgX = svgX.toFixed(1);
        beacon.dataset.geoSvgY = svgY.toFixed(1);
        if (meta) {
            Object.keys(meta).forEach(function (key) {
                beacon.dataset[key] = String(meta[key]);
            });
        }
        return true;
    }


    /** All filled land shapes in the Malaysia SVG (peninsula pieces + Borneo). */
    function collectSvgLandElements(svgDoc) {
        if (!svgDoc) {
            return [];
        }
        const nodes = svgDoc.querySelectorAll("path, polygon");
        const out = [];
        for (let i = 0; i < nodes.length; i += 1) {
            const el = nodes[i];
            let box;
            try {
                box = el.getBBox();
            } catch (err) {
                continue;
            }
            if (box.width >= 2 && box.height >= 2) {
                out.push(el);
            }
        }
        return out;
    }

    function pageXYToSvgPoint(refRect, vb, pageX, pageY) {
        const u = (pageX - refRect.left) / refRect.width;
        const v = (pageY - refRect.top) / refRect.height;
        return { x: vb.x + u * vb.w, y: vb.y + v * vb.h };
    }

    /*
     * True if any sample point of `rect` (page coords) falls on a filled
     * land shape. Uses a dense 7x7 grid (49 points, including the edges) —
     * a coarse 3x3 (corners+midpoints) grid can miss a land shape that only
     * intrudes along part of one edge (e.g. the left third of the bottom
     * edge), which is exactly the kind of partial overlap that reads as
     * "the card is sitting on the map" in a screenshot even though its
     * corners and edge-midpoints are clear.
     */
    function rectOverlapsLand(ctx, rect) {
        if (!ctx || !ctx.landEls.length) {
            return false;
        }
        let pt;
        try {
            pt = ctx.svgDoc.documentElement.createSVGPoint();
        } catch (err) {
            return false;
        }
        const steps = 6;
        for (let xi = 0; xi <= steps; xi += 1) {
            const x = rect.left + ((rect.right - rect.left) * xi) / steps;
            for (let yi = 0; yi <= steps; yi += 1) {
                const y = rect.top + ((rect.bottom - rect.top) * yi) / steps;
                const sp = pageXYToSvgPoint(ctx.refRect, ctx.vb, x, y);
                pt.x = sp.x;
                pt.y = sp.y;
                for (let i = 0; i < ctx.landEls.length; i += 1) {
                    try {
                        if (ctx.landEls[i].isPointInFill(pt)) {
                            return true;
                        }
                    } catch (err2) {
                        /* ignore */
                    }
                }
            }
        }
        return false;
    }

    function isPagePointOnLand(ctx, pageX, pageY) {
        if (!ctx || !ctx.landEls.length) {
            return false;
        }
        let pt;
        try {
            pt = ctx.svgDoc.documentElement.createSVGPoint();
        } catch (err) {
            return false;
        }
        const sp = pageXYToSvgPoint(ctx.refRect, ctx.vb, pageX, pageY);
        pt.x = sp.x;
        pt.y = sp.y;
        for (let i = 0; i < ctx.landEls.length; i += 1) {
            try {
                if (ctx.landEls[i].isPointInFill(pt)) {
                    return true;
                }
            } catch (err2) {
                /* ignore */
            }
        }
        return false;
    }

    /* Westernmost land x (page px) that intrudes beside/at this rect's band. */
    function minWestLandEdgeAtRect(ctx, rect) {
        let minEdge = null;
        for (let y = rect.top; y <= rect.bottom; y += 2) {
            for (let x = Math.ceil(rect.left); x <= rect.right + 72; x += 1) {
                if (isPagePointOnLand(ctx, x, y)) {
                    minEdge = minEdge === null ? x : Math.min(minEdge, x);
                    break;
                }
            }
        }
        return minEdge;
    }

    function hasWestLandClearance(ctx, rect, gapPx) {
        const edge = minWestLandEdgeAtRect(ctx, rect);
        if (edge === null) {
            return true;
        }
        return rect.right <= edge - gapPx;
    }

    function rectOverlapArea(a, b) {
        const ox = Math.max(0, Math.min(a.right, b.right) - Math.max(a.left, b.left));
        const oy = Math.max(0, Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top));
        return ox * oy;
    }

    /*
     * Angle-ordered preference so the search tends to land on natural-looking
     * placements before falling back to less usual directions — purely a
     * tie-breaker/style choice, correctness comes from the land test. Builds
     * a full 360° sweep ordered by angular distance from `centerDeg`, so the
     * search tries "the direction we actually want" first (e.g. straight
     * down for Sarawak) and only drifts away from it if that side is blocked
     * by land/other labels.
     *
     * Angle convention here: 0° = right, 90° = down, 180° = left, 270° = up
     * (screen space, y grows downward — matches Math.cos/sin usage below).
     */
    function buildAngleOrder(centerDeg) {
        const order = [centerDeg];
        for (let step = 15; step <= 180; step += 15) {
            order.push((centerDeg + step + 360) % 360);
            if (step !== 180) {
                order.push((centerDeg - step + 360) % 360);
            }
        }
        return order;
    }

    const LABEL_SEARCH_ANGLES_DEG = buildAngleOrder(200);
    /* Sarawak must read as "below the state region" — bias hard toward straight down. */
    const SARAWAK_ANGLES_DEG = buildAngleOrder(90);
    /* Selangor sits on the west coast — prefer a short leader just outside the
       coast (down / down-left), never onto peninsula land or mid-ocean. */
    const SELANGOR_ANGLES_DEG = buildAngleOrder(125);
    /* Desktop Selangor: keep the card near the beacon (below / slightly left),
       not parked at the map's far-west ocean edge. */
    const SELANGOR_DESKTOP_ANGLES_DEG = buildAngleOrder(115);
    /* Max leader length so the card stays visually attached to Selangor. */
    const DESKTOP_SELANGOR_MAX_DIST_PX = 118;

    function clampRectToWrap(rect, wrapRect, pad) {
        const w = rect.right - rect.left;
        const h = rect.bottom - rect.top;
        const minLeft = wrapRect.left + pad;
        const maxLeft = wrapRect.right - pad - w;
        const minTop = wrapRect.top + pad;
        const maxTop = wrapRect.bottom - pad - h;
        const left = maxLeft >= minLeft ? Math.max(minLeft, Math.min(maxLeft, rect.left)) : rect.left;
        const top = maxTop >= minTop ? Math.max(minTop, Math.min(maxTop, rect.top)) : rect.top;
        return { left: left, top: top, right: left + w, bottom: top + h };
    }

    /* Desktop Selangor: keep a clear margin inside the map wrap/stage edge. */
    function clampSelangorDesktopRect(rect, wrapRect, pad) {
        const w = rect.right - rect.left;
        const h = rect.bottom - rect.top;
        const edgePad = Math.max(pad, 24);
        const minLeft = wrapRect.left + edgePad;
        const maxLeft = wrapRect.right - edgePad - w;
        const minTop = wrapRect.top + edgePad;
        const maxTop = wrapRect.bottom - edgePad - h;
        const left = maxLeft >= minLeft ? Math.max(minLeft, Math.min(maxLeft, rect.left)) : rect.left;
        const top = maxTop >= minTop ? Math.max(minTop, Math.min(maxTop, rect.top)) : rect.top;
        return { left: left, top: top, right: left + w, bottom: top + h };
    }

    /**
     * Search real map-relative geometry (SVG land fills, wrap bounds, sibling
     * labels, instruction text) for a label placement that never covers a
     * Malaysia land shape. Every candidate is clamped into the wrap so the
     * result is always fully on-screen/on-map; land/obstacle avoidance then
     * ranks which clamped position looks best. Returns the winning page-space
     * rect for the label.
     */
    function findClearLabelRect(ctx, beaconRect, w, h, obstacles, angleOrder, minRadiusFrac) {
        const cx = beaconRect.left + beaconRect.width * 0.5;
        const cy = beaconRect.top + beaconRect.height * 0.5;
        const angles = angleOrder || LABEL_SEARCH_ANGLES_DEG;
        const placementRect = ctx.placementRect || ctx.wrapRect;
        /*
         * Radii scale with the actual wrap footprint (not a fixed 880px
         * reference) so the search can still reach genuinely clear corners
         * of a cramped landscape wrap instead of giving up early and
         * clamping onto land.
         */
        const maxSpan = Math.max(ctx.wrapRect.width, ctx.wrapRect.height);
        const radiusFracs = [
            0.04, 0.06, 0.08, 0.1, 0.13, 0.17, 0.22, 0.28, 0.35, 0.44, 0.55, 0.7, 0.85
        ].filter(function (f) {
            return f >= (minRadiusFrac || 0);
        });
        const radii = (radiusFracs.length ? radiusFracs : [minRadiusFrac || 0.09]).map(
            function (f) {
                return Math.max(36, f * maxSpan);
            }
        );

        /*
         * Obstacles may be plain rects (hard: other labels — never worth
         * overlapping just to face the preferred direction) or
         * { rect, soft: true } (soft: instruction text — avoided when
         * possible, but a direction-preferred spot with a little overlap
         * there beats a "perfect" spot facing the wrong way entirely).
         */
        const hardObstacles = [];
        const softObstacles = [];
        for (let oi = 0; oi < obstacles.length; oi += 1) {
            const o = obstacles[oi];
            if (!o) {
                continue;
            }
            if (o.soft && o.rect) {
                softObstacles.push(o.rect);
            } else {
                /* Inflate hard (label-vs-label) obstacles by a small margin
                   so cards get real breathing room instead of just barely
                   missing each other by a sub-pixel sliver. */
                const r = o.rect || o;
                hardObstacles.push({
                    left: r.left - 10,
                    top: r.top - 10,
                    right: r.right + 10,
                    bottom: r.bottom + 10
                });
            }
        }

        function candidateAt(radius, angleDeg) {
            const rad = (angleDeg * Math.PI) / 180;
            const pcx = cx + radius * Math.cos(rad);
            const pcy = cy + radius * Math.sin(rad);
            const raw = {
                left: pcx - w / 2,
                top: pcy - h / 2,
                right: pcx + w / 2,
                bottom: pcy + h / 2
            };
            /* Always clamp into the wrap first — visibility is a hard
               requirement — then judge land/obstacle clearance on the
               clamped (i.e. truly final) rect, not the pre-clamp guess. */
            const rect = clampRectToWrap(raw, placementRect, 4);
            const onLand = rectOverlapsLand(ctx, rect);
            let hardOverlap = 0;
            for (let oi = 0; oi < hardObstacles.length; oi += 1) {
                hardOverlap += rectOverlapArea(rect, hardObstacles[oi]);
            }
            let softOverlap = 0;
            for (let oi = 0; oi < softObstacles.length; oi += 1) {
                softOverlap += rectOverlapArea(rect, softObstacles[oi]);
            }
            return { rect: rect, onLand: onLand, hardOverlap: hardOverlap, softOverlap: softOverlap };
        }

        /*
         * "As close as possible, never on land" is a distance-first search:
         * walk radii from smallest to largest (closest to the beacon first)
         * and, at the FIRST radius that has any valid (land-free,
         * label-free) candidate at all, take the best one there and stop —
         * a larger radius is never preferred once a valid smaller one
         * exists. Within a given radius, `angles` (already sorted by
         * closeness to the preferred direction, e.g. straight down for
         * Sarawak) breaks ties so the closest-possible spot also leans the
         * right way when several equally-close options exist.
         */
        function searchClosest(angleList, allowSoftOverlap) {
            for (let ri = 0; ri < radii.length; ri += 1) {
                let best = null;
                let bestScore = Infinity;
                for (let ai = 0; ai < angleList.length; ai += 1) {
                    const c = candidateAt(radii[ri], angleList[ai]);
                    if (c.onLand || c.hardOverlap > 200) {
                        continue;
                    }
                    if (!allowSoftOverlap && c.softOverlap > 200) {
                        continue;
                    }
                    const score = ai * 5 + c.hardOverlap * 2 + c.softOverlap * 0.5;
                    if (score < bestScore) {
                        bestScore = score;
                        best = c.rect;
                    }
                }
                if (best) {
                    return best;
                }
            }
            return null;
        }

        /*
         * Tiered cone widening: try a tight ±45° cone around the preferred
         * direction first (genuinely "below" for Sarawak, not just
         * "same level, technically closer"), then widen only if nothing at
         * all is available there. Without this, "closest valid radius wins"
         * can lock onto a smaller-radius candidate at the very edge of a
         * wide cone (e.g. due east/west — same height as the beacon, not
         * actually below it) purely because it appears at an earlier radius
         * than a true below-the-marker spot.
         */
        const cone45 = angles.slice(0, Math.min(angles.length, 7));
        const cone90 = angles.slice(0, Math.min(angles.length, 13));
        let result =
            searchClosest(cone45, false) ||
            searchClosest(cone45, true) ||
            searchClosest(cone90, false) ||
            searchClosest(cone90, true) ||
            searchClosest(angles, false) ||
            searchClosest(angles, true);
        if (result) {
            return result;
        }

        /* Last resort: no fully land/label-clear spot exists anywhere in the
           grid — pick whichever candidate minimizes land+overlap, closest
           radius first, rather than leaving the label undefined. */
        for (let ri = 0; ri < radii.length; ri += 1) {
            let best = null;
            let bestScore = Infinity;
            for (let ai = 0; ai < angles.length; ai += 1) {
                const c = candidateAt(radii[ri], angles[ai]);
                const score =
                    (c.onLand ? 1e7 : 0) + c.hardOverlap * 20 + c.softOverlap * 2 + ai * 2;
                if (score < bestScore) {
                    bestScore = score;
                    best = c.rect;
                }
            }
            if (best && bestScore < 1e7) {
                return best;
            }
            if (ri === radii.length - 1 && best) {
                return best;
            }
        }
        return clampRectToWrap(
            { left: cx - w / 2, top: cy - h / 2, right: cx + w / 2, bottom: cy + h / 2 },
            placementRect,
            4
        );
    }

    /*
     * Desktop Selangor only: card slightly left / lower-left of the beacon,
     * completely off peninsula land, with ≥24px clearance from the map wrap
     * edge and a short diagonal gold leader (same connector as Sabah/Sarawak).
     */
    function findDesktopSelangorOffMapRect(ctx, beaconRect, w, h, obstacles) {
        const bcx = beaconRect.left + beaconRect.width * 0.5;
        const bcy = beaconRect.top + beaconRect.height * 0.5;
        const wrapBound = ctx.wrapRect;
        const edgePad = 16;
        const maxDist = Math.min(
            DESKTOP_SELANGOR_MAX_DIST_PX,
            Math.max(72, wrapBound.width * 0.2)
        );
        /* Search only near the beacon — never park the card in open sea. */
        const minLeft = Math.ceil(Math.max(wrapBound.left + edgePad, bcx - maxDist - w * 0.35));
        const maxLeft = Math.min(bcx + 28, wrapBound.right - edgePad - w);
        const minTop = Math.ceil(Math.max(wrapBound.top + edgePad, bcy - 24));
        const maxTop = Math.floor(Math.min(wrapBound.bottom - edgePad - h, bcy + maxDist));

        function blockedByObstacles(cand, allowSoft) {
            for (let oi = 0; oi < obstacles.length; oi += 1) {
                const o = obstacles[oi];
                if (!o) {
                    continue;
                }
                if (o.soft && o.rect) {
                    if (!allowSoft && rectOverlapArea(cand, o.rect) > 200) {
                        return true;
                    }
                } else {
                    const r = o.rect || o;
                    const hard = {
                        left: r.left - 10,
                        top: r.top - 10,
                        right: r.right + 10,
                        bottom: r.bottom + 10
                    };
                    if (rectOverlapArea(cand, hard) > 200) {
                        return true;
                    }
                }
            }
            return false;
        }

        function isValid(cand, allowSoft) {
            if (cand.left < wrapBound.left + edgePad - 0.5 || cand.top < wrapBound.top + edgePad - 0.5) {
                return false;
            }
            if (cand.right > wrapBound.right - edgePad + 0.5) {
                return false;
            }
            if (cand.bottom > wrapBound.bottom - edgePad + 0.5) {
                return false;
            }
            const ccx = (cand.left + cand.right) / 2;
            const ccy = (cand.top + cand.bottom) / 2;
            if (Math.hypot(ccx - bcx, ccy - bcy) > maxDist + 8) {
                return false;
            }
            /* Inflate slightly so anti-aliased coast tips cannot nick the card. */
            if (
                rectOverlapsLand(ctx, {
                    left: cand.left - 2,
                    top: cand.top - 4,
                    right: cand.right + 6,
                    bottom: cand.bottom + 2
                })
            ) {
                return false;
            }
            if (blockedByObstacles(cand, allowSoft)) {
                return false;
            }
            return true;
        }

        let best = null;
        let bestScore = Infinity;
        if (minLeft <= maxLeft && minTop <= maxTop) {
            for (let left = minLeft; left <= maxLeft; left += 2) {
                for (let top = minTop; top <= maxTop; top += 2) {
                    const cand = {
                        left: left,
                        top: top,
                        right: left + w,
                        bottom: top + h
                    };
                    if (!isValid(cand, false) && !isValid(cand, true)) {
                        continue;
                    }
                    const dist = Math.hypot(
                        (cand.left + cand.right) / 2 - bcx,
                        (cand.top + cand.bottom) / 2 - bcy
                    );
                    /* Prefer slightly below the beacon (short diagonal gold leader). */
                    const belowBias = top + h * 0.5 >= bcy - 2 ? 0 : 18;
                    const score = dist + belowBias;
                    if (score < bestScore) {
                        bestScore = score;
                        best = cand;
                    }
                }
            }
        }
        if (best) {
            return best;
        }

        const fallback = clampSelangorDesktopRect(
            {
                left: bcx - w * 0.35,
                top: bcy + 28,
                right: bcx - w * 0.35 + w,
                bottom: bcy + 28 + h
            },
            wrapBound,
            edgePad
        );
        if (isValid(fallback, true)) {
            return fallback;
        }
        return findClearLabelRect(
            ctx,
            beaconRect,
            w,
            h,
            obstacles,
            SELANGOR_DESKTOP_ANGLES_DEG,
            0
        );
    }

    /*
     * Connector geometry from the ACTUAL rendered label box and the CSS
     * .beacon-connector pivot (left: 11px; top: 11px; transform-origin: left center).
     * Pivot Y = 11 + connectorHeight/2 (Selangor height 2px → 12; others 1px → 11.5).
     */
    function updateConnector(btn, label) {
        if (!btn || !label) {
            return;
        }
        void label.offsetWidth;
        const br = btn.getBoundingClientRect();
        const lr = label.getBoundingClientRect();
        if (br.width < 1 || lr.width < 1) {
            return;
        }

        const labelLocalX = lr.left - br.left;
        const labelLocalY = lr.top - br.top;
        const labelW = lr.width;
        const labelH = lr.height;

        const isSelangor = btn.classList.contains("selangor-beacon");
        const connectorHeight = isSelangor ? 2 : 1;
        const pivotX = 11;
        const pivotY = 11 + connectorHeight / 2;

        let targetX;
        let targetY;
        if (isSelangor) {
            /* Top-center of the painted Selangor card. */
            targetX = labelLocalX + labelW / 2;
            targetY = labelLocalY;
        } else {
            /* Sabah / Sarawak: aim at the painted card interior. */
            targetX = labelLocalX + labelW / 2;
            targetY = labelLocalY + labelH * 0.42;
        }

        const dx = targetX - pivotX;
        const dy = targetY - pivotY;
        const len = Math.max(1, Math.hypot(dx, dy));
        const ang = (Math.atan2(dy, dx) * 180) / Math.PI;
        btn.style.setProperty("--conn-len", len.toFixed(1) + "px");
        btn.style.setProperty("--conn-ang", ang.toFixed(2) + "deg");
    }

    /**
     * Responsive label + leader-line layout from geo-placed beacon positions.
     * Sabah keeps its exact original preset/behavior untouched. Selangor and
     * Sarawak are placed by searching real map geometry (SVG land fills, wrap
     * bounds, sibling labels, instruction text) so the label card never covers
     * the peninsula/Borneo landmass, on any viewport.
     */
    function layoutBeaconLabelsAndConnectors() {
        const scene = document.getElementById("miniature-map-scene");
        if (!scene) {
            return false;
        }
        const wrap = scene.querySelector(".real-malaysia-map-wrap");
        if (!wrap) {
            return false;
        }
        const wrapRect = wrap.getBoundingClientRect();
        if (wrapRect.width < 40) {
            return false;
        }
        const scale = Math.max(0.68, Math.min(1.14, wrapRect.width / 880));
        const instruction = scene.querySelector(".map-stage-instruction");
        const instrRect =
            instruction && instruction.offsetParent
                ? instruction.getBoundingClientRect()
                : null;

        /* --- Sabah: unchanged — exact original preset + nudge behavior. --- */
        const sabahBtn = scene.querySelector(".exploration-beacon.sabah-beacon.is-geo-placed");
        let sabahLabelRect = null;
        if (sabahBtn) {
            const sabahPreset = { lx: -132, ly: -90 };
            let lx = sabahPreset.lx * scale;
            let ly = sabahPreset.ly * scale;
            sabahBtn.style.setProperty("--label-x", lx.toFixed(1) + "px");
            sabahBtn.style.setProperty("--label-y", ly.toFixed(1) + "px");

            const sabahLabel = sabahBtn.querySelector(".beacon-label");
            if (sabahLabel && instrRect) {
                for (let n = 0; n < 8; n += 1) {
                    const lr = sabahLabel.getBoundingClientRect();
                    const ox = Math.max(
                        0,
                        Math.min(lr.right, instrRect.right) -
                            Math.max(lr.left, instrRect.left)
                    );
                    const oy = Math.max(
                        0,
                        Math.min(lr.bottom, instrRect.bottom) -
                            Math.max(lr.top, instrRect.top)
                    );
                    if (ox * oy <= 4) {
                        break;
                    }
                    ly -= 10;
                    lx -= 8;
                    sabahBtn.style.setProperty("--label-y", ly.toFixed(1) + "px");
                    sabahBtn.style.setProperty("--label-x", lx.toFixed(1) + "px");
                }
            }
            if (sabahLabel) {
                updateConnector(sabahBtn, sabahLabel);
                sabahLabelRect = sabahLabel.getBoundingClientRect();
            }
        }

        /* --- Selangor + Sarawak: land-aware responsive placement. --- */
        const mapObject = document.getElementById("real-malaysia-map");
        const svgDoc = resolveMalaysiaSvgDoc(mapObject);
        let ctx = null;
        if (svgDoc) {
            const svgRoot = svgDoc.documentElement;
            const vbArr = (svgRoot.getAttribute("viewBox") || "0 0 915 400")
                .trim()
                .split(/[\s,]+/)
                .map(Number);
            const vb = {
                x: vbArr[0] || 0,
                y: vbArr[1] || 0,
                w: vbArr[2] || 915,
                h: vbArr[3] || 400
            };
            const mapRect = mapObject.getBoundingClientRect();
            const refRect =
                mapRect.width >= 8 && mapRect.height >= 8 ? mapRect : wrapRect;
            /*
             * On short/cramped wraps (mobile portrait), the drawn land can
             * run almost to the wrap's bottom edge, leaving no room at all
             * for a "below the state" label inside the wrap. There is
             * genuinely empty space (no land is ever drawn there) between
             * the wrap's bottom and the instruction line below the map
             * card — extend the allowed placement area (not the land
             * geometry, which still only comes from the real SVG) a little
             * into that space so "below" placements have somewhere to go.
             */
            let placementRect = wrapRect;
            if (instrRect && instrRect.top > wrapRect.bottom) {
                const extendedBottom = Math.min(
                    wrapRect.bottom + 56,
                    instrRect.top - 6
                );
                if (extendedBottom > wrapRect.bottom) {
                    placementRect = {
                        left: wrapRect.left,
                        top: wrapRect.top,
                        right: wrapRect.right,
                        bottom: extendedBottom,
                        width: wrapRect.width,
                        height: extendedBottom - wrapRect.top
                    };
                }
            }
            ctx = {
                svgDoc: svgDoc,
                landEls: collectSvgLandElements(svgDoc),
                refRect: refRect,
                vb: vb,
                wrapRect: wrapRect,
                placementRect: placementRect,
                scale: scale
            };
            /*
             * Incomplete SVG land (common for the first 1–2s after <object>
             * load) makes rectOverlapsLand() under-detect coast, so the
             * first "clear" spot can sit on land — then a later pass with
             * full land pushes Selangor into open sea. Wait until enough
             * land shapes exist before land-aware placement.
             */
            if (ctx.landEls.length < 8) {
                ctx = null;
            }
        }

        const obstacles = [];
        if (instrRect) {
            obstacles.push({ rect: instrRect, soft: true });
        }
        if (sabahLabelRect) {
            obstacles.push(sabahLabelRect);
        }

        /* Desktop-only: wrapRect.width ~728-880px on desktop vs. ~310px
           (portrait) / ~403px (landscape) — a wide margin below "scale"'s
           own 880px reference keeps this strictly desktop. */
        const isDesktopWide = wrapRect.width > 500;

        /*
         * Sarawak is placed first (with a hard "below the state" bias and a
         * larger minimum separation) so its stronger placement requirement
         * wins the best spot; Selangor is placed second and treats Sarawak's
         * chosen rect as an obstacle to avoid.
         */
        ["sarawak", "selangor"].forEach(function (region) {
            const btn = scene.querySelector(
                ".exploration-beacon." + region + "-beacon.is-geo-placed"
            );
            const label = btn ? btn.querySelector(".beacon-label") : null;
            if (!btn || !label) {
                return;
            }
            const beaconRect = btn.getBoundingClientRect();
            const size = label.getBoundingClientRect();
            const w = Math.max(size.width, 96);
            const h = Math.max(size.height, 40);

            let lx;
            let ly;
            if (ctx) {
                let rect;
                if (region === "selangor" && isDesktopWide) {
                    rect = findDesktopSelangorOffMapRect(ctx, beaconRect, w, h, obstacles);
                } else {
                    const angleOrder =
                        region === "sarawak" ? SARAWAK_ANGLES_DEG : SELANGOR_ANGLES_DEG;
                    /* No minimum separation — the label should sit as close to
                       its state as land/obstacle avoidance allows. */
                    const minRadiusFrac = 0;
                    rect = findClearLabelRect(
                        ctx,
                        beaconRect,
                        w,
                        h,
                        obstacles,
                        angleOrder,
                        minRadiusFrac
                    );
                }

                if (region === "sarawak" && isDesktopWide) {
                    const placeBound = ctx.placementRect || ctx.wrapRect;
                    const bcx =
                        beaconRect.left + beaconRect.width * 0.5;
                    const bcy =
                        beaconRect.top + beaconRect.height * 0.5;
                    /*
                     * Desktop-only: local search for a slightly closer
                     * below-beacon ocean spot. Prefer a small upward move
                     * when clear; otherwise a short west/east slide that
                     * still sits under the state and never on Borneo land.
                     */
                    let bestRect = rect;
                    let bestDist = Math.hypot(
                        (rect.left + rect.right) / 2 - bcx,
                        (rect.top + rect.bottom) / 2 - bcy
                    );
                    for (let ox = -28; ox <= 28; ox += 2) {
                        for (let oy = -18; oy <= 4; oy += 2) {
                            const cand = clampRectToWrap(
                                {
                                    left: rect.left + ox,
                                    right: rect.right + ox,
                                    top: rect.top + oy,
                                    bottom: rect.bottom + oy
                                },
                                placeBound,
                                4
                            );
                            if (
                                (cand.top + cand.bottom) / 2 <
                                bcy + 10
                            ) {
                                continue;
                            }
                            if (rectOverlapsLand(ctx, cand)) {
                                continue;
                            }
                            let blocked = false;
                            for (
                                let oi = 0;
                                oi < obstacles.length;
                                oi += 1
                            ) {
                                const o =
                                    obstacles[oi].rect || obstacles[oi];
                                if (rectOverlapArea(cand, o) > 200) {
                                    blocked = true;
                                    break;
                                }
                            }
                            if (blocked) {
                                continue;
                            }
                            const dist = Math.hypot(
                                (cand.left + cand.right) / 2 - bcx,
                                (cand.top + cand.bottom) / 2 - bcy
                            );
                            if (dist + 0.25 < bestDist) {
                                bestDist = dist;
                                bestRect = cand;
                            }
                        }
                    }
                    rect = bestRect;
                }

                lx = rect.left - beaconRect.left;
                ly = rect.top - beaconRect.top;
            } else {
                /*
                 * SVG land not ready — keep interim placement near the final
                 * bias so a later land-aware pass does not jump above→below
                 * (which previously froze a stale connector aimed upward).
                 */
                if (region === "selangor") {
                    lx = 8 * scale;
                    ly = 28 * scale;
                } else {
                    lx = -w - 18 * scale;
                    ly = 40 * scale;
                }
            }

            btn.style.setProperty("--label-x", lx.toFixed(1) + "px");
            btn.style.setProperty("--label-y", ly.toFixed(1) + "px");
            /* Layout first, then connector from the painted label box. */
            updateConnector(btn, label);
            obstacles.push(label.getBoundingClientRect());
        });

        return true;
    }


    let beaconGeoListenersBound = false;
    let beaconGeoPlacementStable = false;
    let beaconGeoStableWrapWidth = 0;

    function positionExplorationBeaconsFromGeo() {
        const scene = document.getElementById("miniature-map-scene");
        const mapObject = document.getElementById("real-malaysia-map");
        const wrap = scene
            ? scene.querySelector(".real-malaysia-map-wrap")
            : null;
        const selangor = scene
            ? scene.querySelector(".selangor-beacon")
            : null;
        const sabah = scene ? scene.querySelector(".sabah-beacon") : null;
        const sarawak = scene
            ? scene.querySelector(".sarawak-beacon")
            : null;

        if (!scene || !mapObject || !wrap || !selangor || !sabah || !sarawak) {
            return;
        }

        /* Ensure beacons are map-attached children of the wrap. */
        [selangor, sabah, sarawak].forEach(function (btn) {
            if (btn.parentElement !== wrap) {
                wrap.appendChild(btn);
            }
        });

        const geo = getSelangorGeo();
        selangor.dataset.geoLat = String(geo.lat);
        selangor.dataset.geoLon = String(geo.lon);
        selangor.dataset.geoSource = geo.source;

        function applyPlacement(forceRelayout) {
            const svgDoc = resolveMalaysiaSvgDoc(mapObject);
            if (!svgDoc) {
                return false;
            }

            const sabahEl = svgDoc.getElementById("sabah");
            const sarawakEl = svgDoc.getElementById("sarawak");
            if (!sabahEl || !sarawakEl || !sabahEl.getBBox || !sarawakEl.getBBox) {
                return false;
            }

            let sabahBox;
            let sarawakBox;
            try {
                sabahBox = sabahEl.getBBox();
                sarawakBox = sarawakEl.getBBox();
            } catch (err) {
                return false;
            }

            const PEN_GEO = {
                lonMin: 99.65,
                lonMax: 104.55,
                latMin: 1.15,
                latMax: 6.85
            };

            let penMinX = Infinity;
            let penMinY = Infinity;
            let penMaxX = -Infinity;
            let penMaxY = -Infinity;
            const landNodes = svgDoc.querySelectorAll("path, polygon");
            let penLandCount = 0;
            for (let i = 0; i < landNodes.length; i += 1) {
                const el = landNodes[i];
                if (el.id === "sabah" || el.id === "sarawak") {
                    continue;
                }
                let box;
                try {
                    box = el.getBBox();
                } catch (err2) {
                    continue;
                }
                if (box.width < 2 || box.height < 2) {
                    continue;
                }
                if (box.x > Math.min(sarawakBox.x, sabahBox.x) - 20) {
                    continue;
                }
                penLandCount += 1;
                penMinX = Math.min(penMinX, box.x);
                penMinY = Math.min(penMinY, box.y);
                penMaxX = Math.max(penMaxX, box.x + box.width);
                penMaxY = Math.max(penMaxY, box.y + box.height);
            }

            if (!isFinite(penMinX) || penMaxX - penMinX < 40 || penLandCount < 4) {
                return false;
            }

            const wrapWidth = wrap.getBoundingClientRect().width;
            if (
                beaconGeoPlacementStable &&
                !forceRelayout &&
                Math.abs(wrapWidth - beaconGeoStableWrapWidth) < 2
            ) {
                layoutBeaconLabelsAndConnectors();
                return true;
            }

            const uLon =
                (geo.lon - PEN_GEO.lonMin) /
                (PEN_GEO.lonMax - PEN_GEO.lonMin);
            const vLat =
                (PEN_GEO.latMax - geo.lat) /
                (PEN_GEO.latMax - PEN_GEO.latMin);
            const selSvgX = penMinX + uLon * (penMaxX - penMinX);
            const selSvgY = penMinY + vLat * (penMaxY - penMinY);

            const sabahCx = sabahBox.x + sabahBox.width * 0.5;
            const sabahCy = sabahBox.y + sabahBox.height * 0.5;
            const sarawakCx = sarawakBox.x + sarawakBox.width * 0.5;
            const sarawakCy = sarawakBox.y + sarawakBox.height * 0.5;

            const okSel = placeBeaconAtSvg(
                selangor,
                mapObject,
                wrap,
                selSvgX,
                selSvgY,
                { geoFrame: "peninsula-bbox+MAH_MERI_DATA" }
            );
            const okSabah = placeBeaconAtSvg(
                sabah,
                mapObject,
                wrap,
                sabahCx,
                sabahCy,
                {
                    geoFrame: "svg#sabah-bbox",
                    geoLat: "5.9",
                    geoLon: "116.2",
                    geoSource: "LANGUAGE_COORDS.kadazan-dusun"
                }
            );
            const okSarawak = placeBeaconAtSvg(
                sarawak,
                mapObject,
                wrap,
                sarawakCx,
                sarawakCy,
                {
                    geoFrame: "svg#sarawak-bbox",
                    geoLat: "2.3",
                    geoLon: "113.0",
                    geoSource: "LANGUAGE_COORDS.iban"
                }
            );
            if (okSel && okSabah && okSarawak) {
                layoutBeaconLabelsAndConnectors();
                const landReady = collectSvgLandElements(svgDoc).length >= 8;
                if (!landReady) {
                    /* Beacons are placed, but label land-tests are not trustworthy
                       yet — keep retrying so we do not freeze a mid-ocean drift. */
                    return false;
                }
                beaconGeoPlacementStable = true;
                beaconGeoStableWrapWidth = wrapWidth;
                return true;
            }
            return false;
        }

        function tryPlace(attempt) {
            prefetchMalaysiaSvg(mapObject).then(function () {
                if (applyPlacement(false)) {
                    return;
                }
                if (attempt < 72) {
                    window.setTimeout(function () {
                        tryPlace(attempt + 1);
                    }, 180);
                }
            });
        }

        prefetchMalaysiaSvg(mapObject);

        function schedulePlacement() {
            window.requestAnimationFrame(function () {
                window.requestAnimationFrame(function () {
                    tryPlace(0);
                });
            });
        }

        if (mapObject.contentDocument && mapObject.contentDocument.readyState === "complete") {
            cachedMalaysiaSvgDoc = mapObject.contentDocument;
        }

        if (!beaconGeoListenersBound) {
            mapObject.addEventListener(
                "load",
                function () {
                    cachedMalaysiaSvgDoc = mapObject.contentDocument;
                    beaconGeoPlacementStable = false;
                    schedulePlacement();
                },
                { once: true }
            );
        }

        if (!beaconGeoPlacementStable) {
            schedulePlacement();
        } else {
            applyPlacement(false);
        }

        if (beaconGeoListenersBound) {
            return;
        }
        beaconGeoListenersBound = true;

        window.addEventListener(
            "resize",
            function () {
                beaconGeoPlacementStable = false;
                if (applyPlacement(true)) {
                    layoutBeaconLabelsAndConnectors();
                }
            },
            { passive: true }
        );
        window.addEventListener(
            "orientationchange",
            function () {
                window.setTimeout(function () {
                    beaconGeoPlacementStable = false;
                    if (applyPlacement(true)) {
                        layoutBeaconLabelsAndConnectors();
                    }
                }, 280);
            },
            { passive: true }
        );
    }


    /* =========================================
       EMPTY DISCOVERY STATE
       ========================================= */

    function getEmptyDiscoveryHTML() {

        return `

            <div class="discovery-empty-state">

                <span class="discovery-empty-symbol"
                      aria-hidden="true">
                    ✦
                </span>

                <span class="discovery-empty-eyebrow">
                    Waiting to Discover
                </span>

                <h4>
                    The map is yours to explore.
                </h4>

                <p>
                    Choose Selangor, Sabah, or Sarawak to reveal
                    the living languages connected to that place.
                </p>

            </div>

        `;
    }


    /* =========================================
       ACTIVATE MAP BEACONS
       ========================================= */

    function activateExplorationBeacons() {

        const beaconButtons =
            explorerCard.querySelectorAll(
                ".exploration-beacon"
            );


        beaconButtons.forEach(
            function (button) {

                button.addEventListener(
                    "click",
                    function () {

                        const selectedRegion =
                            button.dataset.region;


                        beaconButtons.forEach(
                            function (beacon) {

                                beacon.classList.remove(
                                    "is-selected"
                                );

                            }
                        );


                        button.classList.add(
                            "is-selected"
                        );


                        focusMapRegion(
                            selectedRegion
                        );


                        showRegionDiscovery(
                            selectedRegion
                        );

                    }
                );

            }
        );
    }


    /* =========================================
       FOCUS SELECTED REGION
       ========================================= */

    function focusMapRegion(region) {

        const mapScene =
            document.getElementById(
                "miniature-map-scene"
            );


        if (!mapScene) {
            return;
        }


        mapScene.classList.remove(
            "focus-sabah",
            "focus-sarawak",
            "focus-selangor"
        );


        void mapScene.offsetWidth;


        mapScene.classList.add(
            "focus-" + region
        );


        explorerCard.classList.add(
            "region-selected"
        );
    }


    /* =========================================
       READ LANGUAGE PROGRESS
       ========================================= */

    function getLanguageProgress(selector) {

        const originalCard =
            document.querySelector(selector);


        if (!originalCard) {
            return 0;
        }

        // Prefer explicit data-progress on language cards (dashboard cards no
        // longer render a .progress-fill control).
        if (originalCard.dataset && originalCard.dataset.progress != null) {
            const fromData = Number(originalCard.dataset.progress);
            if (!Number.isNaN(fromData)) {
                return fromData;
            }
        }

        const progressElement =
            originalCard.querySelector(
                ".progress-fill"
            );


        if (!progressElement) {
            return 0;
        }


        const progressValue =
            Number(
                progressElement.value != null
                    ? progressElement.value
                    : progressElement.getAttribute("data-progress")
            );


        if (Number.isNaN(progressValue)) {
            return 0;
        }


        return progressValue;
    }


    /* =========================================
       READ LANGUAGE LINK
       ========================================= */

    function getLanguageLink(selector) {

        const originalCard =
            document.querySelector(selector);


        if (!originalCard) {
            return "#";
        }


        return originalCard.getAttribute(
            "href"
        ) || "#";
    }


    /* =========================================
       LANGUAGE PATH CARD
       ========================================= */

    function getLanguageExplorerMeta(langKey) {
        return (window.LANGUAGE_EXPLORER_META || {})[langKey] || null;
    }

    function createLanguagePathHTML(options) {

        const progress =
            getLanguageProgress(
                options.selector
            );


        const link =
            getLanguageLink(
                options.selector
            );


        let actionText =
            "Begin the journey";


        if (progress > 0) {

            actionText =
                "Continue the journey";

        }

        const meta = options.langKey
            ? getLanguageExplorerMeta(options.langKey)
            : null;

        const vocabCountText = meta && typeof meta.vocab_count === "number"
            ? `${meta.vocab_count} words in the course dictionary`
            : "";

        const deepLinks = meta
            ? `
                <div class="discovery-language-path-links">
                    <a href="${meta.dictionary_url}" class="discovery-language-deep-link">Browse dictionary →</a>
                    <a href="${meta.compare_url}" class="discovery-language-deep-link">Compare languages →</a>
                </div>
            `
            : "";

        return `

            <a
                class="discovery-language-path"
                href="${link}"
                aria-label="Explore ${options.name}">

                <div class="discovery-language-path-top">

                    <span class="discovery-language-number">
                        ${options.number}
                    </span>

                    <span class="discovery-language-origin">
                        ${options.origin}
                    </span>

                </div>


                <div class="discovery-language-path-main">

                    <div>

                        <h5>
                            ${options.name}
                        </h5>

                        <p>
                            ${options.description}
                        </p>

                        ${vocabCountText ? `<p class="discovery-language-vocab-count">${vocabCountText}</p>` : ""}

                    </div>

                    <span
                        class="discovery-language-arrow"
                        aria-hidden="true">
                        →
                    </span>

                </div>


                <div class="discovery-language-path-footer">

                    <span>
                        ${actionText}
                    </span>

                    <span class="discovery-path-progress">
                        ${progress}% explored
                    </span>

                </div>

            </a>

            ${deepLinks}

        `;
    }


    /* =========================================
       ENSERA CULTURAL OBJECT
       SARAWAK
       ========================================= */

    function getEnseraCulturalObjectHTML() {

        return `

            <section
                class="featured-cultural-object"
                aria-labelledby="ensera-object-title">


                <div class="cultural-object-heading">

                    <div>

                        <span class="cultural-object-eyebrow">
                            Within Iban Oral Tradition
                        </span>

                        <h5 id="ensera-object-title">
                            Ensera
                        </h5>

                        <p class="cultural-object-subtitle">
                            One form within a wider oral world
                        </p>

                    </div>


                    <span
                        class="cultural-object-mark"
                        aria-hidden="true">
                        ✦
                    </span>

                </div>


                <p class="cultural-object-introduction">
                    Ensera belongs within the wider tradition
                    of Iban leka main — a cultural world that
                    includes multiple forms of oral expression.
                </p>


                <button
                    class="cultural-object-trigger"
                    id="ensera-object-trigger"
                    type="button"
                    aria-expanded="false"
                    aria-controls="ensera-object-experience">

                    <span>
                        See Ensera in its wider tradition
                    </span>

                    <span
                        class="cultural-object-trigger-arrow"
                        aria-hidden="true">
                        →
                    </span>

                </button>


                <div
                    class="cultural-object-experience"
                    id="ensera-object-experience"
                    hidden>


                    <div class="cultural-object-context">

                        <span class="cultural-context-eyebrow">
                            One Form, A Wider Tradition
                        </span>

                        <p>
                            Ensera is not presented here as the whole
                            of Iban oral tradition. It is one form
                            situated within the wider world of
                            leka main.
                        </p>

                    </div>


                    <div class="cultural-object-sources">

                        <span class="cultural-sources-heading">
                            Source &amp; Context
                        </span>

                        <ul>

                            <li>
                                Chemaline Anak Osup —
                                Leka Main: Puisi Rakyat Iban —
                                Satu Analisis Bentuk dan Fungsi,
                                Universiti Sains Malaysia, 2006
                            </li>

                        </ul>

                    </div>


                </div>

            </section>

        `;
    }


    /* =========================================
       INAIT CULTURAL OBJECT
       SABAH — MEMORY ECHO EXPERIENCE
       ========================================= */

    function getInaitCulturalObjectHTML() {

        return `

            <section
                class="featured-cultural-object"
                aria-labelledby="inait-object-title">


                <div class="cultural-object-heading">

                    <div>

                        <span class="cultural-object-eyebrow">
                            From the Magavau Ritual
                        </span>

                        <h5 id="inait-object-title">
                            Inait
                        </h5>

                        <p class="cultural-object-subtitle">
                            A long ritual poem carried by memory and voice
                        </p>

                    </div>


                    <span
                        class="cultural-object-mark"
                        aria-hidden="true">
                        ✦
                    </span>

                </div>


                <p class="cultural-object-introduction">
                    In the Penampang Kadazan Magavau ritual context,
                    Inait is a long ritual poem memorised by a bobohizan.
                    It may take hours to recite: some parts are chanted,
                    while others are delivered in a normal speaking voice.
                </p>


                <div
                    class="inait-language-reveal"
                    aria-label="One meaning through two forms of language">

                    <div class="inait-language-reveal-heading">

                        <span>
                            One Meaning
                        </span>

                        <strong>
                            Two forms of language
                        </strong>

                    </div>


                    <div class="inait-language-reveal-core">

                        <span
                            class="inait-meaning-point"
                            aria-hidden="true">
                        </span>

                        <span class="inait-meaning-label">
                            Corresponding meaning
                        </span>

                    </div>


                    <div class="inait-language-forms">

                        <div class="inait-language-form">

                            <span>
                                Common
                            </span>

                            <strong>
                                Everyday language
                            </strong>

                        </div>


                        <span
                            class="inait-language-relation"
                            aria-hidden="true">
                            ↔
                        </span>


                        <div class="inait-language-form">

                            <span>
                                Ritual
                            </span>

                            <strong>
                                Ritual language
                            </strong>

                        </div>

                    </div>


                    <p class="inait-language-reveal-note">
                        Research describes paired lines in which
                        the same or corresponding meaning appears
                        through common and ritual forms of language.
                    </p>

                </div>


                <button
                    class="cultural-object-trigger"
                    id="inait-object-trigger"
                    type="button"
                    aria-expanded="false"
                    aria-controls="inait-object-experience">

                    <span>
                        Follow how knowledge is remembered
                    </span>

                    <span
                        class="cultural-object-trigger-arrow"
                        aria-hidden="true">
                        →
                    </span>

                </button>


                <div
                    class="cultural-object-experience"
                    id="inait-object-experience"
                    hidden>


                    <div class="inait-memory-echo">


                        <div class="memory-echo-introduction">

                            <span>
                                A Memory Echo
                            </span>

                            <p>
                                Knowledge continues only when
                                someone hears, holds, and carries it.
                            </p>

                        </div>


                        <div
                            class="memory-echo-moment"
                            data-memory-stage="hear">

                            <span
                                class="memory-echo-symbol"
                                aria-hidden="true">
                                Hear
                            </span>

                            <div class="memory-echo-copy">

                                <strong>
                                    A voice enters memory
                                </strong>

                                <p>
                                    Knowledge is first encountered
                                    through spoken recitation and listening.
                                </p>

                            </div>

                        </div>


                        <span
                            class="memory-echo-connection"
                            aria-hidden="true">
                        </span>


                        <div
                            class="memory-echo-moment"
                            data-memory-stage="hold">

                            <span
                                class="memory-echo-symbol"
                                aria-hidden="true">
                                Hold
                            </span>

                            <div class="memory-echo-copy">

                                <strong>
                                    Memory becomes the archive
                                </strong>

                                <p>
                                    What has been heard is remembered,
                                    recalled, and kept without a written page.
                                </p>

                            </div>

                        </div>


                        <span
                            class="memory-echo-connection"
                            aria-hidden="true">
                        </span>


                        <div
                            class="memory-echo-moment"
                            data-memory-stage="carry">

                            <span
                                class="memory-echo-symbol"
                                aria-hidden="true">
                                Carry
                            </span>

                            <div class="memory-echo-copy">

                                <strong>
                                    Another generation receives it
                                </strong>

                                <p>
                                    Remembered knowledge can continue
                                    when another person hears and carries it onward.
                                </p>

                            </div>

                        </div>


                        <div class="memory-echo-question">

                            <span>
                                The fragile point
                            </span>

                            <p>
                                If fewer people hear the recitation,
                                who will remain to hold and carry
                                the knowledge forward?
                            </p>

                        </div>


                    </div>


                    <div class="cultural-object-sources">

                        <span class="cultural-sources-heading">
                            Sources &amp; Context
                        </span>

                        <ul>

                            <li>
                                Elvin Dainal,
                                <em>
                                    Re-Imagining the Inait of the Magavau
                                    Ritual in Intercultural Music
                                    Compositional Process
                                </em>,
                                Idealogy Journal, Vol. 9, No. 2, 2024.
                                DOI: 10.24191/idealogy.v9i2.431
                            </li>

                        </ul>

                    </div>


                </div>

            </section>

        `;
    }


    /* =========================================
       MAH MERI LANGUAGE OBJECT
       SELANGOR — VOICE REGISTER CONTRAST
       ========================================= */

    function getMahMeriLanguageObjectHTML() {

        const data =
            window.MAH_MERI_DATA;


        if (!data) {

            console.error(
                "Mah Meri data could not be found."
            );

            return "";
        }


        const registers =
            data.voiceRegisters;


        return `

            <section
                class="featured-cultural-object mahmeri-language-object"
                aria-labelledby="mahmeri-object-title">


                <div class="cultural-object-heading">

                    <div>

                        <span class="cultural-object-eyebrow">
                            ${registers.eyebrow}
                        </span>

                        <h5 id="mahmeri-object-title">
                            ${registers.title}
                        </h5>

                        <p class="cultural-object-subtitle">
                            ${registers.subtitle}
                        </p>

                    </div>


                    <span
                        class="cultural-object-mark"
                        aria-hidden="true">
                        ◌
                    </span>

                </div>


                <p class="cultural-object-introduction">
                    ${registers.introduction}
                </p>


                <div
                    class="mahmeri-register-contrast"
                    aria-label="Comparison of two Mah Meri voice registers">


                    <div class="mahmeri-register-card">

                        <span class="mahmeri-register-label">
                            ${registers.firstRegister.label}
                        </span>

                        <ul>

                            ${registers.firstRegister.characteristics
                                .map(
                                    function (item) {

                                        return `
                                            <li>
                                                ${item}
                                            </li>
                                        `;

                                    }
                                )
                                .join("")}

                        </ul>

                    </div>


                    <div
    class="mahmeri-register-relation"
    aria-hidden="true">
    
</div>
                  

<div class="mahmeri-register-card">

                        <span class="mahmeri-register-label">
                            ${registers.secondRegister.label}
                        </span>

                        <ul>

                            ${registers.secondRegister.characteristics
                                .map(
                                    function (item) {

                                        return `
                                            <li>
                                                ${item}
                                            </li>
                                        `;

                                    }
                                )
                                .join("")}

                        </ul>

                    </div>


                </div>


                <div class="mahmeri-register-key-idea">

                    <span>
                        What changes?
                    </span>

                    <p>
                        ${registers.keyIdea}
                    </p>

                </div>


                <div class="cultural-object-sources">

                    <span class="cultural-sources-heading">
                        Source &amp; Context
                    </span>

                    <ul>

                        <li>
                            ${data.source.authors},
                            <em>
                                ${data.source.title}
                            </em>,
                            ${data.source.journal},
                            ${data.source.year}.
                            DOI: ${data.source.doi}
                        </li>

                    </ul>

                </div>


            </section>

        `;
    }


    /* =========================================
       ACTIVATE ONE CULTURAL OBJECT
       ========================================= */

    function activateCulturalObject(options) {

        const trigger =
            document.getElementById(
                options.triggerId
            );


        const experience =
            document.getElementById(
                options.experienceId
            );


        if (!trigger || !experience) {
            return;
        }


        const triggerText =
            trigger.querySelector(
                "span:first-child"
            );


        trigger.addEventListener(
            "click",
            function () {

                const isExpanded =
                    trigger.getAttribute(
                        "aria-expanded"
                    ) === "true";


                if (isExpanded) {

                    trigger.setAttribute(
                        "aria-expanded",
                        "false"
                    );


                    experience.hidden = true;


                    if (triggerText) {

                        triggerText.textContent =
                            options.openText;

                    }


                    return;
                }


                trigger.setAttribute(
                    "aria-expanded",
                    "true"
                );


                experience.hidden = false;


                if (triggerText) {

                    triggerText.textContent =
                        options.closeText;

                }

            }
        );
    }


    /* =========================================
       ACTIVATE ENSERA
       ========================================= */

    function activateEnseraCulturalObject() {

        activateCulturalObject(
            {
                triggerId:
                    "ensera-object-trigger",

                experienceId:
                    "ensera-object-experience",

                openText:
                    "See Ensera in its wider tradition",

                closeText:
                    "Close the cultural context"
            }
        );
    }


    /* =========================================
       ACTIVATE INAIT
       ========================================= */

    function activateInaitCulturalObject() {

        activateCulturalObject(
            {
                triggerId:
                    "inait-object-trigger",

                experienceId:
                    "inait-object-experience",

                openText:
                    "Follow how knowledge is remembered",

                closeText:
                    "Close the memory echo"
            }
        );
    }


    /* =========================================
       SARAWAK DISCOVERY
       ========================================= */

    function getSarawakDiscoveryHTML() {

        const ibanPath =
            createLanguagePathHTML(
                {
                    selector:
                        ".iban-card",

                    langKey:
                        "iban",

                    number:
                        "01",

                    name:
                        "Iban",

                    origin:
                        "Sarawak",

                    description:
                        "Enter a living language shaped by community, memory, and generations of everyday use."
                }
            );


        const bidayuhPath =
            createLanguagePathHTML(
                {
                    selector:
                        ".bidayuh-card",

                    langKey:
                        "bidayuh",

                    number:
                        "02",

                    name:
                        "Bidayuh",

                    origin:
                        "Sarawak",

                    description:
                        "Discover another distinct language tradition rooted in the communities of Sarawak."
                }
            );


        const enseraObject =
            getEnseraCulturalObjectHTML();


        return `

            <div class="region-discovery-content">


                <button
                    class="close-region-discovery"
                    type="button"
                    aria-label="Return to the full Malaysia map">

                    <span aria-hidden="true">
                        ←
                    </span>

                    Back to Malaysia

                </button>


                <div class="discovery-place-identity">

                    <span class="region-discovery-eyebrow">
                        Sarawak Discovered
                    </span>

                    <div class="discovery-place-title-row">

                        <h4>
                            A place where languages
                            carry living heritage.
                        </h4>

                        <span
                            class="discovery-place-mark"
                            aria-hidden="true">
                            02
                        </span>

                    </div>

                </div>


                <div class="discovery-place-story">

                    <span class="discovery-story-line"
                          aria-hidden="true">
                    </span>

                    <p>
                        Across Sarawak, language lives through
                        communities, stories, memory, and the
                        knowledge passed between generations.
                    </p>

                </div>


                ${enseraObject}


                <div class="discovery-paths-header">

                    <span>
                        Two paths into Sarawak
                    </span>

                    <p>
                        Choose a language to continue the journey.
                    </p>

                </div>


                <div class="discovery-language-paths">

                    ${ibanPath}

                    ${bidayuhPath}

                </div>

            </div>

        `;
    }


    /* =========================================
       SABAH DISCOVERY
       ========================================= */

    function getSabahDiscoveryHTML() {

        const kadazanPath =
            createLanguagePathHTML(
                {
                    selector:
                        ".kadazan-card",

                    langKey:
                        "kadazan-dusun",

                    number:
                        "01",

                    name:
                        "Kadazan-Dusun",

                    origin:
                        "Sabah",

                    description:
                        "Enter a living language tradition connected to community, place, and cultural memory."
                }
            );


        const inaitObject =
            getInaitCulturalObjectHTML();


        return `

            <div class="region-discovery-content">


                <button
                    class="close-region-discovery"
                    type="button"
                    aria-label="Return to the full Malaysia map">

                    <span aria-hidden="true">
                        ←
                    </span>

                    Back to Malaysia

                </button>


                <div class="discovery-place-identity">

                    <span class="region-discovery-eyebrow">
                        Sabah Discovered
                    </span>

                    <div class="discovery-place-title-row">

                        <h4>
                            A living language shaped
                            by place and community.
                        </h4>

                        <span
                            class="discovery-place-mark"
                            aria-hidden="true">
                            01
                        </span>

                    </div>

                </div>


                <div class="discovery-place-story">

                    <span class="discovery-story-line"
                          aria-hidden="true">
                    </span>

                    <p>
                        In Sabah, language carries relationships
                        between people, landscape, tradition,
                        and generations of shared knowledge.
                    </p>

                </div>


                ${inaitObject}


                <div class="discovery-paths-header">

                    <span>
                        A path into Sabah
                    </span>

                    <p>
                        Follow the language into its living story.
                    </p>

                </div>


                <div class="discovery-language-paths">

                    ${kadazanPath}

                </div>

            </div>

        `;
    }


    /* =========================================
       SELANGOR DISCOVERY
       MAH MERI
       ========================================= */

    function getSelangorDiscoveryHTML() {

        const data =
            window.MAH_MERI_DATA;


        if (!data) {

            return `

                <div class="region-discovery-content">

                    <button
                        class="close-region-discovery"
                        type="button"
                        aria-label="Return to the full Malaysia map">

                        <span aria-hidden="true">
                            ←
                        </span>

                        Back to Malaysia

                    </button>


                    <div class="discovery-empty-state">

                        <span class="discovery-empty-eyebrow">
                            Content unavailable
                        </span>

                        <h4>
                            Mah Meri discovery data could not be loaded.
                        </h4>

                    </div>

                </div>

            `;
        }


        const discovery =
            data.discovery;


        const mahMeriObject =
            getMahMeriLanguageObjectHTML();


        return `

            <div class="region-discovery-content">


                <button
                    class="close-region-discovery"
                    type="button"
                    aria-label="Return to the full Malaysia map">

                    <span aria-hidden="true">
                        ←
                    </span>

                    Back to Malaysia

                </button>


                <div class="discovery-place-identity">

                    <span class="region-discovery-eyebrow">
                        ${discovery.placeEyebrow}
                    </span>

                    <div class="discovery-place-title-row">

                        <h4>
                            ${discovery.placeTitle}
                        </h4>

                        <span
                            class="discovery-place-mark"
                            aria-hidden="true">
                            01
                        </span>

                    </div>

                </div>


                <div class="discovery-place-story">

                    <span
                        class="discovery-story-line"
                        aria-hidden="true">
                    </span>

                    <p>
                        ${discovery.placeStory}
                    </p>

                </div>


                ${mahMeriObject}


                <div class="discovery-paths-header">

                    <span>
                        ${discovery.pathHeading}
                    </span>

                    <p>
                        ${discovery.pathIntroduction}
                    </p>

                </div>


                ${createLanguagePathHTML({
                    selector: ".mah-meri-card",
                    langKey: "mah-meri",
                    number: "01",
                    name: data.language.name,
                    origin: data.language.region,
                    description: discovery.languageDescription
                })}
        `;
    }


    /* =========================================
       SHOW REGION DISCOVERY
       ========================================= */

    function showRegionDiscovery(region) {

        const discoveryPanel =
            document.getElementById(
                "region-discovery-panel"
            );


        if (!discoveryPanel) {
            return;
        }


        discoveryPanel.classList.remove(
            "is-revealing"
        );


        if (region === "sarawak") {

            discoveryPanel.innerHTML =
                getSarawakDiscoveryHTML();

        }


        if (region === "sabah") {

            discoveryPanel.innerHTML =
                getSabahDiscoveryHTML();

        }


        if (region === "selangor") {

            discoveryPanel.innerHTML =
                getSelangorDiscoveryHTML();

        }


        const closeButton =
            discoveryPanel.querySelector(
                ".close-region-discovery"
            );


        if (closeButton) {

            closeButton.addEventListener(
                "click",
                resetRegionDiscovery
            );

        }


        if (region === "sarawak") {

            activateEnseraCulturalObject();

        }


        if (region === "sabah") {

            activateInaitCulturalObject();

        }


        discoveryPanel.scrollTop = 0;

        /* On narrow / short viewports, keep the selected state's panel in frame. */
        if (window.matchMedia("(max-width: 900px), (max-height: 560px)").matches) {
            window.requestAnimationFrame(function () {
                try {
                    discoveryPanel.scrollIntoView({
                        behavior: "smooth",
                        block: "nearest"
                    });
                } catch (err) {
                    discoveryPanel.scrollIntoView(true);
                }
            });
        }


        window.requestAnimationFrame(
            function () {

                window.requestAnimationFrame(
                    function () {

                        discoveryPanel.classList.add(
                            "is-revealing"
                        );

                    }
                );

            }
        );
    }


    /* =========================================
       RESET REGION DISCOVERY
       ========================================= */

    function resetRegionDiscovery() {

        const mapScene =
            document.getElementById(
                "miniature-map-scene"
            );


        const discoveryPanel =
            document.getElementById(
                "region-discovery-panel"
            );


        const beaconButtons =
            explorerCard.querySelectorAll(
                ".exploration-beacon"
            );


        if (mapScene) {

            mapScene.classList.remove(
                "focus-sabah",
                "focus-sarawak",
                "focus-selangor"
            );

        }


        beaconButtons.forEach(
            function (beacon) {

                beacon.classList.remove(
                    "is-selected"
                );

            }
        );


        explorerCard.classList.remove(
            "region-selected"
        );


        if (discoveryPanel) {

            discoveryPanel.classList.remove(
                "is-revealing"
            );


            discoveryPanel.innerHTML =
                getEmptyDiscoveryHTML();

        }
    }


    /* =========================================
       BEGIN JOURNEY
       ========================================= */

    exploreButton.addEventListener(
        "click",
        function () {

            if (
                transitionRunning ||
                explorerCard.classList.contains(
                    "has-arrived"
                )
            ) {
                return;
            }


            transitionRunning = true;


            exploreButton.disabled = true;


            exploreButton.innerHTML =

                "Travelling to Malaysia" +

                '<span aria-hidden="true">' +
                "→" +
                "</span>";


            explorerCard.classList.add(
                "is-travelling"
            );


            /*
               STATE MACHINE:
               WORLD → ENTERING → MALAYSIA
               Earth is the opening hero; Malaysia map
               is the destination explorer surface.
            */

            function onArrivalReady() {
                window.removeEventListener(
                    "earthMalaysiaArrivalReady",
                    onArrivalReady
                );
                explorerCard.classList.add(
                    "is-cloud-covered"
                );
                explorerCard.dataset.explorerState =
                    "entering";
            }

            window.addEventListener(
                "earthMalaysiaArrivalReady",
                onArrivalReady
            );

            function onFlightComplete() {

                if (
                    explorerCard.classList.contains("has-arrived") ||
                    explorerCard.dataset.flightCompleteHandled === "1"
                ) {
                    return;
                }
                explorerCard.dataset.flightCompleteHandled = "1";

                window.removeEventListener(
                    "earthMalaysiaFlightComplete",
                    onFlightComplete
                );

                explorerCard.dataset.explorerState =
                    "entering";

                window.setTimeout(function () {
                    createMalaysiaStage();

                    explorerCard.classList.add(
                        "is-malaysia-view"
                    );
                    explorerCard.classList.add(
                        "has-arrived"
                    );
                    explorerCard.classList.remove(
                        "is-travelling"
                    );
                    explorerCard.classList.remove(
                        "is-cloud-covered"
                    );
                    explorerCard.dataset.explorerState =
                        "malaysia";

                    const journeyItems =
                        document.querySelectorAll(
                            ".universe-journey-steps li"
                        );
                    journeyItems.forEach(function (item, index) {
                        item.classList.toggle(
                            "is-active",
                            index >= 1
                        );
                    });

                    window.requestAnimationFrame(function () {
                        window.requestAnimationFrame(function () {
                            positionExplorationBeaconsFromGeo();
                        });
                    });

                    transitionRunning = false;
                }, 900);

            }

            window.addEventListener(
                "earthMalaysiaFlightComplete",
                onFlightComplete
            );

            // If the Earth flight never finishes (WebGL stall / missing event),
            // still open Malaysia so the CTA is not permanently disabled.
            window.setTimeout(function () {
                if (
                    !explorerCard.classList.contains("has-arrived") &&
                    transitionRunning
                ) {
                    console.warn(
                        "[dashboard] Malaysia flight timed out; forcing arrival."
                    );
                    onFlightComplete();
                }
            }, 12000);

            explorerCard.dataset.explorerState =
                "entering";

        }
    );


    /* =========================================
       RANDOM WORD CARD
       ========================================= */

    const randomWordBtn =
        document.getElementById("random-word-btn");
    const randomWordTerm =
        document.getElementById("random-word-term");
    const randomWordMeta =
        document.getElementById("random-word-meta");
    const randomWordDictLink =
        document.getElementById("random-word-dict-link");
    const randomWordLearnLink =
        document.getElementById("random-word-learn-link");
    const randomWordLang =
        document.getElementById("random-word-lang");

    if (randomWordBtn && randomWordTerm && randomWordMeta) {
        randomWordBtn.addEventListener("click", function () {
            randomWordBtn.disabled = true;
            randomWordBtn.textContent = "Discovering…";

            const recentKey = "mmle_recent_random_ids";
            let recent = [];
            try {
                recent = JSON.parse(sessionStorage.getItem(recentKey) || "[]") || [];
            } catch (e) {
                recent = [];
            }
            recent = recent.filter(function (id) { return typeof id === "number"; }).slice(-8);
            const excludeQuery = recent.length ? ("?exclude=" + recent.join(",")) : "";

            fetch("/api/dictionary/random" + excludeQuery)
                .then(function (response) {
                    return response.json();
                })
                .then(function (data) {
                    randomWordBtn.disabled = false;
                    randomWordBtn.textContent = "Next random word";

                    if (!data || !data.ok || !data.word) {
                        randomWordMeta.textContent =
                            (data && data.message) ||
                            "No vocabulary is available yet.";
                        return;
                    }

                    const word = data.word;
                    if (word.id) {
                        recent.push(Number(word.id));
                        try {
                            sessionStorage.setItem(recentKey, JSON.stringify(recent.slice(-8)));
                        } catch (e) {}
                    }
                    randomWordTerm.textContent = word.word || "Word";
                    if (randomWordLang) {
                        if (word.language_display) {
                            randomWordLang.hidden = false;
                            randomWordLang.textContent = word.language_display;
                        } else {
                            randomWordLang.hidden = true;
                        }
                    }
                    const bits = [];
                    if (word.meaning_en) {
                        bits.push(word.meaning_en);
                    }
                    if (word.part_of_speech) {
                        bits.push(word.part_of_speech);
                    }
                    if (word.difficulty) {
                        bits.push(word.difficulty);
                    }
                    if (word.ipa) {
                        bits.push("/" + word.ipa + "/");
                    }
                    randomWordMeta.textContent = bits.join(" · ") || "Meaning unavailable";

                    if (randomWordDictLink && word.dictionary_url) {
                        randomWordDictLink.href = word.dictionary_url;
                        randomWordDictLink.textContent = "Open dictionary";
                    }
                    if (randomWordLearnLink) {
                        randomWordLearnLink.hidden = false;
                        randomWordLearnLink.href = word.learn_url || word.dictionary_url || "/dictionary";
                    }
                })
                .catch(function () {
                    randomWordBtn.disabled = false;
                    randomWordBtn.textContent = "Discover a Word";
                    randomWordMeta.textContent =
                        "Could not load a word right now.";
                });
        });
    }

    window.MalaysiaMapBeacons = {
        reposition: positionExplorationBeaconsFromGeo
    };

});