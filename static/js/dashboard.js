/* =========================================
   Malaysian Language Heritage Explorer
   Dashboard — Living Malaysia Explorer
   ========================================= */

document.addEventListener("DOMContentLoaded", function () {

    const exploreButton =
        document.getElementById("explore-world-button");

    const explorerCard =
        document.getElementById("world-explorer-card");

    const globeStage =
        document.getElementById("globe-stage");


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

                    </div>


                    <button
                        class="exploration-beacon sarawak-beacon"
                        type="button"
                        data-region="sarawak"
                        aria-label="Explore languages in Sarawak">

                        <span class="beacon-outer-ring">
                        </span>

                        <span class="beacon-middle-ring">
                        </span>

                        <span class="beacon-core">
                        </span>

                        <span class="beacon-label">

                            <strong>
                                Sarawak
                            </strong>

                            <small>
                                2 living languages
                            </small>

                        </span>

                    </button>


                    <button
                        class="exploration-beacon sabah-beacon"
                        type="button"
                        data-region="sabah"
                        aria-label="Explore languages in Sabah">

                        <span class="beacon-outer-ring">
                        </span>

                        <span class="beacon-middle-ring">
                        </span>

                        <span class="beacon-core">
                        </span>

                        <span class="beacon-label">

                            <strong>
                                Sabah
                            </strong>

                            <small>
                                1 living language
                            </small>

                        </span>

                    </button>


                    <button
                        class="exploration-beacon selangor-beacon"
                        type="button"
                        data-region="selangor"
                        aria-label="Explore Mah Meri in Selangor">

                        <span class="beacon-outer-ring">
                        </span>

                        <span class="beacon-middle-ring">
                        </span>

                        <span class="beacon-core">
                        </span>

                        <span class="beacon-label">

                            <strong>
                                Selangor
                            </strong>

                            <small>
                                1 living language
                            </small>

                        </span>

                    </button>


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


        const progressElement =
            originalCard.querySelector(
                ".progress-fill"
            );


        if (!progressElement) {
            return 0;
        }


        const progressValue =
            Number(progressElement.value);


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


                <div class="mahmeri-language-path-preview">

    <div class="discovery-language-path-top">

        <span class="discovery-language-number">
            01
        </span>

        <span class="discovery-language-origin">
            ${data.language.region}
        </span>

    </div>


    <div class="discovery-language-path-main">

        <div>

            <h5>
                ${data.language.name}
            </h5>

            <p>
                ${discovery.languageDescription}
            </p>

        </div>

    </div>

</div>
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
               Sync with the actual Three.js
               camera flight (earth-globe.js)
               instead of guessing with fixed
               timeouts, so the Malaysia map
               never swaps in before the
               camera has actually finished
               centering on Malaysia.
            */

            function onArrivalReady() {

                window.removeEventListener(
                    "earthMalaysiaArrivalReady",
                    onArrivalReady
                );

                explorerCard.classList.add(
                    "is-cloud-covered"
                );

            }

            window.addEventListener(
                "earthMalaysiaArrivalReady",
                onArrivalReady
            );


            function onFlightComplete() {

                window.removeEventListener(
                    "earthMalaysiaFlightComplete",
                    onFlightComplete
                );

                /*
                   Pause for about a second
                   after the camera has fully
                   arrived and centered on
                   Malaysia before switching
                   to the map page.
                */

                window.setTimeout(
                    function () {

                        createMalaysiaStage();


                        explorerCard.classList.add(
                            "is-malaysia-view"
                        );


                        window.setTimeout(
                            function () {

                                explorerCard.classList.remove(
                                    "is-cloud-covered"
                                );


                                explorerCard.classList.add(
                                    "has-arrived"
                                );


                                transitionRunning = false;

                            },
                            900
                        );

                    },
                    1000
                );

            }

            window.addEventListener(
                "earthMalaysiaFlightComplete",
                onFlightComplete
            );

        }
    );

});