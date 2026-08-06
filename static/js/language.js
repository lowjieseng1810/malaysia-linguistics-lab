/* =========================================
   LANGUAGE COMPARISON PAGE
   Lightweight, dependency-free interactivity
   for the /compare page. The page already
   works with a full form submission (no JS
   required); this script simply upgrades the
   experience so switching either dropdown
   updates the table instantly.
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const form = document.getElementById("compare-form");
    const selectA = document.getElementById("compare-select-a");
    const selectB = document.getElementById("compare-select-b");
    const table = document.getElementById("compare-table");

    if (!form || !selectA || !selectB || !table) {
        return;
    }

    const columnA = document.getElementById("compare-col-a");
    const columnB = document.getElementById("compare-col-b");

    function renderSimpleField(cell, value, fallback) {
        cell.textContent = value || fallback || "";
    }

    function renderStatusField(cell, value) {
        cell.innerHTML = "";

        const pill = document.createElement("span");
        pill.className = "compare-status-pill";
        pill.textContent = value || "Documentation pending";

        cell.appendChild(pill);
    }

    function renderWordField(cell, wordData, fallbackText) {
        cell.innerHTML = "";

        if (!wordData || !wordData.word) {
            cell.textContent = fallbackText;
            return;
        }

        const strong = document.createElement("strong");
        strong.textContent = wordData.word;

        const meaning = document.createElement("span");
        meaning.className = "compare-meaning";
        meaning.textContent = " — " + (wordData.meaning || "");

        cell.appendChild(strong);
        cell.appendChild(meaning);
    }

    function renderLevelsField(cell, levels) {
        cell.innerHTML = "";

        const list = document.createElement("ul");
        list.className = "compare-levels-list";

        (levels || []).forEach(function (level) {
            const item = document.createElement("li");
            item.textContent = level;
            list.appendChild(item);
        });

        cell.appendChild(list);
    }
    function renderVitalityCard(letter, data) {
        const nameEl = document.getElementById("vitality-name-" + letter);
        const meterEl = document.getElementById("vitality-meter-" + letter);
        const badgeEl = document.getElementById("vitality-badge-" + letter);
        const explanationEl = document.getElementById("vitality-explanation-" + letter);
        const speakersEl = document.getElementById("vitality-speakers-" + letter);

        if (!nameEl || !meterEl || !badgeEl || !explanationEl || !speakersEl) {
            return;
        }

        const meter = data.vitality_meter || {
            estimated: true,
            filled_segments: 5,
            total_segments: 10,
            css_class: "estimated",
            explanation: "Data currently under review."
        };

        nameEl.textContent = data.display_name;
        speakersEl.textContent = data.speakers_estimate;

        badgeEl.textContent = data.vitality_status;
        badgeEl.className = "vitality-badge " + meter.css_class;

        explanationEl.textContent = meter.explanation;

        let estimatedBadge = document.getElementById("vitality-estimated-" + letter);

        if (meter.estimated) {
            if (!estimatedBadge) {
                estimatedBadge = document.createElement("span");
                estimatedBadge.id = "vitality-estimated-" + letter;
                estimatedBadge.className = "vitality-estimated-badge";
                badgeEl.insertAdjacentElement("afterend", estimatedBadge);
            }
            estimatedBadge.textContent = "~ Estimated";
        } else if (estimatedBadge) {
            estimatedBadge.remove();
        }

        meterEl.innerHTML = "";

        for (let index = 1; index <= meter.total_segments; index += 1) {
            const segment = document.createElement("span");

            segment.className =
                "vitality-segment " +
                (index <= meter.filled_segments ? "filled " : "") +
                meter.css_class;

            meterEl.appendChild(segment);
        }
    }
    function updateDiffBadge(id, same) {
        const badge = document.getElementById(id);

        if (!badge) {
            return;
        }

        badge.classList.remove("same", "different");
        badge.classList.add(same ? "same" : "different");
        badge.textContent = same ? "✓ Same" : "✗ Different";
    }

    function updateSummary(summary) {
        if (!summary) {
            return;
        }

        const percentageEl = document.getElementById("compare-summary-percentage");

        if (percentageEl) {
            percentageEl.textContent = summary.percentage + "%";
        }

        const badgesContainer = document.getElementById("compare-summary-badges");

        if (badgesContainer) {
            badgesContainer.innerHTML = "";

            summary.attributes.forEach(function (attribute) {
                const badge = document.createElement("span");

                badge.className =
                    "diff-badge " +
                    (attribute.same ? "same" : "different");

                badge.textContent =
                    (attribute.same ? "✓ Same " : "✗ Different ") +
                    attribute.label;

                badgesContainer.appendChild(badge);
            });
        }

        updateDiffBadge("diff-badge-region", summary.by_key.region);
        updateDiffBadge("diff-badge-family", summary.by_key.family);
        updateDiffBadge("diff-badge-writing_system", summary.by_key.writing_system);
        updateDiffBadge("diff-badge-vitality_status", summary.by_key.vitality_status);
        updateDiffBadge("diff-badge-levels", summary.by_key.levels);
    }

    function updateColumn(letter, data) {
        if (!data) {
            return;
        }

        const heading = letter === "a" ? columnA : columnB;

        if (heading) {
            heading.textContent = data.display_name;
        }

        table.querySelectorAll(
            'td[data-field="display_name"]'
        )[letter === "a" ? 0 : 1].textContent = data.display_name;

        table.querySelectorAll(
            'td[data-field="region"]'
        )[letter === "a" ? 0 : 1].textContent = data.region;

        table.querySelectorAll(
            'td[data-field="family"]'
        )[letter === "a" ? 0 : 1].textContent = data.family;

        table.querySelectorAll(
            'td[data-field="speakers_estimate"]'
        )[letter === "a" ? 0 : 1].textContent = data.speakers_estimate;

        renderStatusField(
            table.querySelectorAll(
                'td[data-field="vitality_status"]'
            )[letter === "a" ? 0 : 1],
            data.vitality_status
        );

        renderSimpleField(
            table.querySelectorAll(
                'td[data-field="writing_system"]'
            )[letter === "a" ? 0 : 1],
            data.writing_system,
            "Documentation pending"
        );

        renderWordField(
            table.querySelectorAll(
                'td[data-field="greeting"]'
            )[letter === "a" ? 0 : 1],
            data.greeting,
            "Documentation pending"
        );

        renderWordField(
            table.querySelectorAll(
                'td[data-field="number_system"]'
            )[letter === "a" ? 0 : 1],
            data.number_system,
            "Not yet included in course content"
        );

        renderLevelsField(
            table.querySelectorAll(
                'td[data-field="levels"]'
            )[letter === "a" ? 0 : 1],
            data.levels
        );

        renderVitalityCard(letter, data);
    }

    function updateComparison() {
        const langA = selectA.value;
        const langB = selectB.value;

        fetch("/api/compare/" + langA + "/" + langB)
            .then(function (response) {
                if (!response.ok) {
                    throw new Error("Comparison request failed");
                }
                return response.json();
            })
            .then(function (payload) {
                updateColumn("a", payload.a);
                updateColumn("b", payload.b);
                updateSummary(payload.summary);

                if (window.history && window.history.replaceState) {
                    const url = new URL(window.location.href);
                    url.searchParams.set("a", langA);
                    url.searchParams.set("b", langB);
                    window.history.replaceState({}, "", url);
                }
            })
            .catch(function () {
                /* Fall back to a normal form submission if the
                   API request fails for any reason. */
                form.submit();
            });
    }

    selectA.addEventListener("change", updateComparison);
    selectB.addEventListener("change", updateComparison);
});
