document.addEventListener("DOMContentLoaded", function () {

   /* =========================================
   HERO LOADING STATE
   ========================================= */

let heroLoaded = false;
let heroLoadingProgress = 0;
let heroLoadingFinished = false;
let loadCompleteTime = 0;
let loadingStateIndex = 0;

const loadingStates = [
    "Loading Earth...",
    "Loading Atmosphere...",
    "Loading Languages...",
    "Preparing Experience...",
    "Finalizing..."
];

let loadingValue = 0;

    const globeStage =
        document.getElementById("globe-stage");

    const exploreButton =
        document.getElementById("explore-world-button");

    if (!globeStage) {
        console.error("Three.js globe stage not found.");
        return;
    }

    if (typeof THREE === "undefined") {
        console.error("Three.js did not load.");
        return;
    }

const loadingOverlay =
    document.createElement("div");

const styleSheet =
    document.createElement("style");

styleSheet.textContent = `
@keyframes hero-logo-rotate {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes hero-logo-pulse {
    0%, 100% { transform: scale(1); opacity: 0.65; }
    50% { transform: scale(1.18); opacity: 1; }
}
`;

document.head.appendChild(
    styleSheet
);

loadingOverlay.id =
    "hero-loading-overlay";

loadingOverlay.style.position =
    "fixed";

loadingOverlay.style.inset =
    "0";

loadingOverlay.style.width =
    "100vw";

loadingOverlay.style.height =
    "100vh";

loadingOverlay.style.display =
    "flex";

loadingOverlay.style.flexDirection =
    "column";

loadingOverlay.style.alignItems =
    "center";

loadingOverlay.style.justifyContent =
    "center";

loadingOverlay.style.background =
    "radial-gradient(circle at center, rgba(10,18,29,0.96), rgba(2,6,12,1))";

loadingOverlay.style.zIndex =
    "9999";

loadingOverlay.style.transition =
    "opacity 0.9s ease";

loadingOverlay.style.pointerEvents =
    "all";

const loadingLogo =
    document.createElement("div");

loadingLogo.style.width =
    "68px";

loadingLogo.style.height =
    "68px";

loadingLogo.style.display =
    "flex";

loadingLogo.style.alignItems =
    "center";

loadingLogo.style.justifyContent =
    "center";

loadingLogo.style.marginBottom =
    "20px";

loadingLogo.style.position =
    "relative";

loadingLogo.style.animation =
    "hero-logo-rotate 14s linear infinite";

const loadingLogoRing =
    document.createElement("div");

loadingLogoRing.style.width =
    "100%";

loadingLogoRing.style.height =
    "100%";

loadingLogoRing.style.border =
    "2px solid rgba(217,180,74,0.8)";

loadingLogoRing.style.borderRadius =
    "50%";

loadingLogoRing.style.boxShadow =
    "0 0 18px rgba(217,180,74,0.18)";

const loadingLogoCore =
    document.createElement("div");

loadingLogoCore.style.width =
    "18px";

loadingLogoCore.style.height =
    "18px";

loadingLogoCore.style.borderRadius =
    "50%";

loadingLogoCore.style.background =
    "rgba(217,180,74,0.92)";

loadingLogoCore.style.boxShadow =
    "0 0 18px rgba(217,180,74,0.45)";

loadingLogoCore.style.animation =
    "hero-logo-pulse 1.8s ease-in-out infinite";

loadingLogo.appendChild(
    loadingLogoRing
);

loadingLogo.appendChild(
    loadingLogoCore
);

const loadingBrand =
    document.createElement("div");

loadingBrand.textContent =
    "Malaysia Linguistics Lab";

loadingBrand.style.color =
    "#ffffff";

loadingBrand.style.fontSize =
    "22px";

loadingBrand.style.fontWeight =
    "300";

loadingBrand.style.letterSpacing =
    "0.16em";

loadingBrand.style.textAlign =
    "center";

loadingBrand.style.marginBottom =
    "10px";

const loadingSubtitle =
    document.createElement("div");

loadingSubtitle.textContent =
    "Discover • Preserve • Learn";

loadingSubtitle.style.color =
    "#a5b8cf";

loadingSubtitle.style.fontSize =
    "14px";

loadingSubtitle.style.letterSpacing =
    "0.24em";

loadingSubtitle.style.textAlign =
    "center";

loadingSubtitle.style.marginBottom =
    "32px";

const loadingText =
    document.createElement("div");

loadingText.textContent =
    loadingStates[0];

loadingText.style.color =
    "#c8d4e0";

loadingText.style.fontSize =
    "16px";

loadingText.style.letterSpacing =
    "0.12em";

loadingText.style.marginBottom =
    "18px";

const loadingPercent =
    document.createElement("div");

loadingPercent.textContent =
    "0%";

loadingPercent.style.color =
    "#d9b44a";

loadingPercent.style.fontSize =
    "34px";

loadingPercent.style.fontWeight =
    "700";

loadingPercent.style.marginBottom =
    "10px";

const loadingStatus =
    document.createElement("div");

loadingStatus.textContent =
    loadingStates[0];

loadingStatus.style.color =
    "#9fb8d6";

loadingStatus.style.fontSize =
    "14px";

loadingStatus.style.letterSpacing =
    "0.22em";

loadingStatus.style.marginBottom =
    "22px";

const loadingBarBackground =
    document.createElement("div");

loadingBarBackground.style.width =
    "280px";

loadingBarBackground.style.height =
    "4px";

loadingBarBackground.style.background =
    "rgba(255,255,255,0.08)";

loadingBarBackground.style.borderRadius =
    "999px";

loadingBarBackground.style.overflow =
    "hidden";

const loadingBar =
    document.createElement("div");

loadingBar.style.width =
    "0%";

loadingBar.style.height =
    "100%";

loadingBar.style.background =
    "linear-gradient(90deg, #f6e27c, #deba5f)";

loadingBar.style.borderRadius =
    "999px";

loadingBar.style.transition =
    "width 0.35s ease";

loadingOverlay.appendChild(
    loadingBrand
);

loadingOverlay.appendChild(
    loadingSubtitle
);

loadingOverlay.appendChild(
    loadingText
);

loadingOverlay.appendChild(
    loadingPercent
);

loadingOverlay.appendChild(
    loadingStatus
);

loadingOverlay.appendChild(
    loadingBarBackground
);

loadingBarBackground.appendChild(
    loadingBar
);

document.body.appendChild(
    loadingOverlay
);

const loadingAudio = {
    start: () => {},
    progress: () => {},
    complete: () => {}
};

const loadingManager =
    new THREE.LoadingManager();

loadingManager.onStart =
    function (url, itemsLoaded, itemsTotal) {
        loadingAudio.start();
    };

loadingManager.onProgress =
    function (url, itemsLoaded, itemsTotal) {
        const nextValue =
            Math.round(
                (itemsLoaded /
                    itemsTotal) *
                    100
            );

        loadingValue =
            nextValue;

        loadingPercent.textContent =
            nextValue + "%";

        loadingBar.style.width =
            nextValue + "%";

        const stateIndex =
            Math.min(
                loadingStates.length - 1,
                Math.floor(
                    nextValue /
                        (100 /
                            loadingStates.length)
                )
            );

        if (
            stateIndex !==
            loadingStateIndex
        ) {
            loadingStateIndex =
                stateIndex;

            loadingStatus.textContent =
                loadingStates[
                    loadingStateIndex
                ];
        }

        if (
            nextValue === 100 &&
            !heroLoaded
        ) {
            heroLoaded = true;
            loadCompleteTime =
                performance.now();
            loadingAudio.complete();
        }

        loadingAudio.progress();
    };

loadingManager.onLoad =
    function () {
        if (!heroLoaded) {
            heroLoaded = true;
            loadCompleteTime =
                performance.now();
            loadingAudio.complete();
        }
    };

loadingManager.onError =
    function (url) {
        console.warn(
            "Loading failed:",
            url
        );
    };


    /* =========================================
       REMOVE OLD THREE CONTAINER
       ========================================= */

    const oldContainer =
        document.getElementById(
            "three-earth-container"
        );

    if (oldContainer) {
        oldContainer.remove();
    }


    /* =========================================
       CREATE THREE.JS CONTAINER
       ========================================= */

    const globeContainer =
        document.createElement("div");

    globeContainer.id =
        "three-earth-container";

    globeContainer.style.position =
        "absolute";

  globeContainer.style.left =
    "0";

globeContainer.style.right =
    "0";

globeContainer.style.top =
    "-40px";

globeContainer.style.bottom =
    "0";
   
        globeContainer.style.zIndex =
        "4";

    globeContainer.style.overflow =
        "hidden";

    globeContainer.style.cursor =
        "grab";

const vignetteOverlay =
    document.createElement("div");

vignetteOverlay.style.position =
    "absolute";

vignetteOverlay.style.inset =
    "0";

vignetteOverlay.style.pointerEvents =
    "none";

vignetteOverlay.style.zIndex =
    "5";

vignetteOverlay.style.background =
    "radial-gradient(circle at center, transparent 45%, rgba(0,0,0,0.18) 100%)";

vignetteOverlay.style.mixBlendMode =
    "multiply";

    globeStage.appendChild(
        vignetteOverlay
    );

    globeStage.appendChild(
        globeContainer
    );


    /* =========================================
       SCENE
       ========================================= */

    const scene =
        new THREE.Scene();


    /* =========================================
       CAMERA
       ========================================= */

const camera =
    new THREE.PerspectiveCamera(
        34,
        1,
        0.1,
        300
    );

 camera.position.set(
    0,
    0,
    6.1
);

camera.position.set(
    0,
    0,
    6.1
);
    
/* =========================================
       RENDERER
       ========================================= */

    const renderer =
        new THREE.WebGLRenderer({
            antialias: true,
            alpha: true
        });

    renderer.setPixelRatio(
    Math.min(
        window.devicePixelRatio,
        2
    )
);




/* =========================================
   CINEMATIC OUTPUT
   ========================================= */

renderer.outputColorSpace =
    THREE.SRGBColorSpace;


/*
ACES Filmic
Solar Smash 风格最重要的一步
*/

renderer.toneMapping =
    THREE.ACESFilmicToneMapping;

renderer.toneMappingExposure =
    1.05;


/*
真实光照
*/

renderer.physicallyCorrectLights =
    true;


/*
阴影
*/

renderer.shadowMap.enabled =
    true;

renderer.shadowMap.type =
    THREE.PCFSoftShadowMap;


renderer.setClearColor(
    0x000000,
    0
);


globeContainer.appendChild(
    renderer.domElement
);

    /* =========================================
       SPACE WORLD
       ========================================= */

    const spaceWorld =
        new THREE.Group();

    scene.add(
        spaceWorld
    );


    /* =========================================
       STAR FIELD
       ========================================= */

    const starCount =
        2200;

    const starPositions =
        new Float32Array(
            starCount * 3
        );

    for (
        let i = 0;
        i < starCount;
        i++
    ) {

        const radius =
            35 +
            Math.random() * 90;

        const theta =
            Math.random() *
            Math.PI *
            2;

        const phi =
            Math.acos(
                2 * Math.random() - 1
            );

        starPositions[
            i * 3
        ] =
            radius *
            Math.sin(phi) *
            Math.cos(theta);

        starPositions[
            i * 3 + 1
        ] =
            radius *
            Math.cos(phi);

        starPositions[
            i * 3 + 2
        ] =
            radius *
            Math.sin(phi) *
            Math.sin(theta);
    }

    const starGeometry =
        new THREE.BufferGeometry();

    starGeometry.setAttribute(
        "position",
        new THREE.BufferAttribute(
            starPositions,
            3
        )
    );

    const starMaterial =
        new THREE.PointsMaterial({
            color: 0xffffff,
            size: 0.055,
            sizeAttenuation: true,
            transparent: true,
            opacity: 0.9
        });

    const stars =
        new THREE.Points(
            starGeometry,
            starMaterial
        );

    spaceWorld.add(
        stars
    );


    /* =========================================
       EARTH SYSTEM
       ========================================= */

    const earthSystem =
        new THREE.Group();

    spaceWorld.add(
        earthSystem
    );


    /* =========================================
       EARTH
       ========================================= */

    const globeScriptUrl =
        (() => {
            if (
                document.currentScript &&
                document.currentScript.src
            ) {
                return document.currentScript.src;
            }

            for (
                let i = 0;
                i < document.scripts.length;
                i += 1
            ) {
                const script =
                    document.scripts[i];

                if (
                    script.src &&
                    script.src.includes(
                        "earth-globe.js"
                    )
                ) {
                    return script.src;
                }
            }

            return window.location.href;
        })();

    const globeAssetBaseUrl =
        new URL(
            "../images/earth/",
            globeScriptUrl
        );

    const resolveGlobeAssetUrl =
        function (filename) {
            return new URL(
                filename,
                globeAssetBaseUrl
            ).href;
        };

    const textureLoader =
    new THREE.TextureLoader(
        loadingManager
    );

    const loadTextureWithLogging =
        function (
            filename,
            label
        ) {
            return textureLoader.load(
                resolveGlobeAssetUrl(
                    filename
                ),
                function (loadedTexture) {
                    console.log(
                        "[earth-globe]",
                        label,
                        "loaded",
                        {
                            src:
                                loadedTexture.image?.currentSrc ||
                                loadedTexture.image?.src ||
                                null,
                            width:
                                loadedTexture.image?.width ||
                                null,
                            height:
                                loadedTexture.image?.height ||
                                null
                        }
                    );
                },
                undefined,
                function (error) {
                    console.error(
                        "[earth-globe]",
                        label,
                        "failed",
                        error
                    );
                }
            );
        };

const earthDayTexture =
    loadTextureWithLogging(
        "earth_day_8k.jpg",
        "earth_day_8k.jpg"
    );

earthDayTexture.colorSpace =
    THREE.SRGBColorSpace;

earthDayTexture.anisotropy =
    renderer.capabilities.getMaxAnisotropy();

earthDayTexture.minFilter =
    THREE.LinearMipmapLinearFilter;

earthDayTexture.magFilter =
    THREE.LinearFilter;

earthDayTexture.generateMipmaps =
    true;


    const earthNormalTexture =
    loadTextureWithLogging(
        "earth_normal.jpg",
        "earth_normal.jpg"
    );

const earthSpecularTexture =
    loadTextureWithLogging(
        "earth_specular.jpg",
        "earth_specular.jpg"
    );

const earthCloudTexture =
    loadTextureWithLogging(
        "earth_clouds.png",
        "earth_clouds.png"
    );
    
      const earthNightTexture =
    loadTextureWithLogging(
        "earth_night.png",
        "earth_night.png"
    );
    
    const earthGeometry =
        new THREE.SphereGeometry(
            1,
            96,
            96
        );

/* =========================================
   CINEMATIC EARTH MATERIAL
   ========================================= */

const earthMaterial =
    new THREE.ShaderMaterial({

        uniforms: {

            dayTexture: {
                value: earthDayTexture
            },

            nightTexture: {
                value: earthNightTexture
            },

            sunWorldPosition: {
                value: new THREE.Vector3()
            },

            cameraWorldPosition: {
                value: new THREE.Vector3()
            },

            revealOpacity: {
                value: 0.0
            }

        },

        transparent: false,
        depthWrite: true,
      
        vertexShader: `

            varying vec2 vUv;
            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;

            void main() {

                vUv = uv;

                vec4 worldPosition =
                    modelMatrix *
                    vec4(
                        position,
                        1.0
                    );

                vWorldPosition =
                    worldPosition.xyz;

                vWorldNormal =
                    normalize(
                        mat3(modelMatrix) *
                        normal
                    );

                gl_Position =
                    projectionMatrix *
                    viewMatrix *
                    worldPosition;
            }

        `,

        fragmentShader: `

            uniform sampler2D dayTexture;
            uniform sampler2D nightTexture;

            uniform vec3 sunWorldPosition;
            uniform vec3 cameraWorldPosition;

            uniform float revealOpacity;

            varying vec2 vUv;
            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;


            void main() {

                vec3 normal =
                    normalize(
                        vWorldNormal
                    );

                vec3 sunDirection =
                    normalize(
                        sunWorldPosition -
                        vWorldPosition
                    );

                vec3 viewDirection =
                    normalize(
                        cameraWorldPosition -
                        vWorldPosition
                    );


                float NdotL =
                    dot(
                        normal,
                        sunDirection
                    );


                /* =================================
                   DAY / NIGHT TRANSITION
                   ================================= */

                float dayAmount =
                    smoothstep(
                        -0.10,
                        0.20,
                        NdotL
                    );

                float nightAmount =
                    1.0 -
                    smoothstep(
                        -0.16,
                        0.07,
                        NdotL
                    );


                /* =================================
                   RAW DAY TEXTURE
                   ================================= */

                vec3 rawDay =
                    texture2D(
                        dayTexture,
                        vUv
                    ).rgb;


                /* =================================
                   OCEAN DETECTION
                   ================================= */

                float blueDominance =
                    rawDay.b -
                    max(
                        rawDay.r,
                        rawDay.g
                    );

                float oceanMask =
                    smoothstep(
                        0.015,
                        0.18,
                        blueDominance
                    );


                /* =================================
                   CINEMATIC LAND
                   ================================= */

                vec3 land =
                    rawDay;


                float landLuminance =
                    dot(
                        land,
                        vec3(
                            0.2126,
                            0.7152,
                            0.0722
                        )
                    );


                /*
                   Reduce artificial map saturation
                */

                land =
                    mix(
                        vec3(
                            landLuminance
                        ),
                        land,
                        0.76
                    );


                /*
                   Natural Earth colour grading
                */

                land.r *= 1.03;
                land.g *= 0.95;
                land.b *= 0.83;


                /*
                   Stronger terrain definition
                */

                land =
                    (
                        land -
                        0.5
                    ) *
                    1.18 +
                    0.5;


                land =
                    max(
                        land,
                        vec3(0.0)
                    );


                /* =================================
                   DEEP CINEMATIC OCEAN
                   ================================= */

                float oceanBrightness =
                    dot(
                        rawDay,
                        vec3(
                            0.2126,
                            0.7152,
                            0.0722
                        )
                    );


                vec3 deepOcean =
                    vec3(
                        0.008,
                        0.045,
                        0.105
                    );


                vec3 midOcean =
                    vec3(
                        0.012,
                        0.095,
                        0.205
                    );


                vec3 shallowOcean =
                    vec3(
                        0.035,
                        0.20,
                        0.34
                    );


                vec3 ocean =
                    mix(
                        deepOcean,
                        midOcean,
                        smoothstep(
                            0.05,
                            0.28,
                            oceanBrightness
                        )
                    );


                ocean =
                    mix(
                        ocean,
                        shallowOcean,
                        smoothstep(
                            0.28,
                            0.58,
                            oceanBrightness
                        )
                    );


                /*
                   Preserve real texture detail
                */

                ocean +=
                    rawDay *
                    0.11;


                /* =================================
                   OCEAN SUN REFLECTION
                   ================================= */

                vec3 halfDirection =
                    normalize(
                        sunDirection +
                        viewDirection
                    );


                float sharpSpecular =
                    pow(
                        max(
                            dot(
                                normal,
                                halfDirection
                            ),
                            0.0
                        ),
                        110.0
                    );


                float broadSpecular =
                    pow(
                        max(
                            dot(
                                normal,
                                halfDirection
                            ),
                            0.0
                        ),
                        22.0
                    );


                vec3 oceanReflection =
    vec3(
        0.62,
        0.78,
        0.92
    ) *
    (
        sharpSpecular *
        0.92 +

        broadSpecular *
        0.10
    ) *
    oceanMask *
    max(
        NdotL,
        0.0
    );


                /* =================================
                   LAND + OCEAN
                   ================================= */

                vec3 dayColor =
                    mix(
                        land,
                        ocean,
                        oceanMask
                    );


                /* =================================
                   SPHERICAL SUNLIGHT
                   ================================= */

                float diffuse =
                    max(
                        NdotL,
                        0.0
                    );


                float softDiffuse =
                    pow(
                        diffuse,
                        0.72
                    );


                /*
                   Warm light near terminator,
                   neutral white at full daylight
                */

                vec3 sunlightColor =
                    mix(
                        vec3(
                            1.0,
                            0.68,
                            0.40
                        ),

                        vec3(
                            1.0,
                            0.97,
                            0.88
                        ),

                        smoothstep(
                            0.0,
                            0.52,
                            diffuse
                        )
                    );


                dayColor *=
    0.095 +
    softDiffuse *
    1.04;


                dayColor *=
                    sunlightColor;


                dayColor +=
                    oceanReflection;


                /* =================================
                   SUBTLE SURFACE ATMOSPHERIC HAZE
                   ================================= */

                float fresnel =
                    pow(
                        1.0 -
                        max(
                            dot(
                                normal,
                                viewDirection
                            ),
                            0.0
                        ),
                        3.4
                    );


              vec3 surfaceHaze =
    vec3(
        0.16,
        0.38,
        0.62
    ) *
    fresnel *
    dayAmount *
    0.075;

                dayColor +=
                    surfaceHaze;


                /* =================================
                   TRUE DARK SIDE
                   ================================= */

                vec3 darkEarth =
                    rawDay *
                    vec3(
                        0.004,
                        0.007,
                        0.012
                    );


                darkEarth +=
                    vec3(
                        0.0008,
                        0.002,
                        0.005
                    );


                /* =================================
                   CITY LIGHTS
                   ================================= */

                vec3 nightSample =
                    texture2D(
                        nightTexture,
                        vUv
                    ).rgb;


                float cityBrightness =
                    max(
                        nightSample.r,
                        max(
                            nightSample.g,
                            nightSample.b
                        )
                    );


                /*
                   Remove purple / blue background
                   from night texture
                */

              float cityMask =
    smoothstep(
        0.105,
        0.54,
        cityBrightness
    );

                vec3 warmCity =
                    vec3(
                        1.0,
                        0.55,
                        0.20
                    );


                vec3 whiteCity =
                    vec3(
                        1.0,
                        0.91,
                        0.68
                    );


                vec3 cityColor =
                    mix(
                        warmCity,
                        whiteCity,
                        cityBrightness
                    );


                /* City / night-light layer disabled (keep day/night shading). */
                vec3 cityLights = vec3(0.0);


                /* =================================
                   TERMINATOR SUNSET
                   ================================= */

                float terminator =
                    1.0 -
                    smoothstep(
                        0.0,
                        0.12,
                        abs(
                            NdotL
                        )
                    );


                vec3 terminatorGlow =
                    vec3(
                        0.30,
                        0.055,
                        0.008
                    ) *
                    terminator *
                    0.15;


                /* =================================
                   FINAL COMBINATION
                   ================================= */

                vec3 finalColor =
                    mix(
                        darkEarth,
                        dayColor,
                        dayAmount
                    );


                finalColor +=
                    cityLights;


                finalColor +=
                    terminatorGlow;


                /* =================================
                   FILMIC CONTRAST
                   ================================= */

                finalColor =
                    finalColor *
                    (
                        1.0 +
                        finalColor *
                        0.11
                    );

                finalColor =
                    pow(
                        max(
                            finalColor,
                            vec3(0.0)
                        ),
                        vec3(0.95)
                    );

                float opacity =
                    smoothstep(
                        0.0,
                        1.0,
                        revealOpacity
                    );

                gl_FragColor =
                    vec4(
                        finalColor,
                        opacity
                    );
            }

        `
    });


/* =========================================
   EARTH MESH
   ========================================= */

const earth =
    new THREE.Mesh(
        earthGeometry,
        earthMaterial
    );


earthSystem.add(
    earth
);

let revealProgress = 0.0;
let cloudsRevealProgress = 0.0;


/* =========================================
   CINEMATIC ATMOSPHERE
   ========================================= */

/* =========================================
   CINEMATIC DOUBLE-LAYER ATMOSPHERE
   ========================================= */


/* =========================================
   INNER ATMOSPHERE
   Thin bright edge close to Earth
   ========================================= */

const atmosphereGeometry =
    new THREE.SphereGeometry(
        1.028,
        128,
        128
    );


const atmosphereMaterial =
    new THREE.ShaderMaterial({

        uniforms: {

            sunWorldPosition: {
                value: new THREE.Vector3()
            },

            cameraWorldPosition: {
                value: new THREE.Vector3()
            }

        },

        vertexShader: `

            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;

            void main() {

                vec4 worldPosition =
                    modelMatrix *
                    vec4(
                        position,
                        1.0
                    );

                vWorldPosition =
                    worldPosition.xyz;

                vWorldNormal =
                    normalize(
                        mat3(modelMatrix) *
                        normal
                    );

                gl_Position =
                    projectionMatrix *
                    viewMatrix *
                    worldPosition;
            }

        `,

        fragmentShader: `

            uniform vec3 sunWorldPosition;
            uniform vec3 cameraWorldPosition;

            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;

            void main() {

                vec3 normal =
                    normalize(
                        vWorldNormal
                    );

                vec3 viewDirection =
                    normalize(
                        cameraWorldPosition -
                        vWorldPosition
                    );

                vec3 sunDirection =
                    normalize(
                        sunWorldPosition -
                        vWorldPosition
                    );

                float viewDot =
                    max(
                        dot(
                            normal,
                            viewDirection
                        ),
                        0.0
                    );

                float sunDot =
                    dot(
                        normal,
                        sunDirection
                    );


                /* STRONGER VISIBLE RIM */

float rim =
    pow(
        1.0 -
        viewDot,
        2.55
    );


                /* DAY / NIGHT CONTROL */

                float daylight =
                    smoothstep(
                        -0.30,
                        0.28,
                        sunDot
                    );


                /* BRIGHT BLUE DAY EDGE */

             vec3 dayColor =
vec3(
1.0,
0.995,
0.985
);

                /* VERY DARK NIGHT EDGE */

                vec3 nightColor =
                    vec3(
                        0.003,
                        0.018,
                        0.055
                    );


                vec3 atmosphereColor =
                    mix(
                        nightColor,
                        dayColor,
                        daylight
                    );


                /* SUNSET TERMINATOR */

                float sunsetBand =
                    1.0 -
                    smoothstep(
                        0.0,
                        0.11,
                        abs(
                            sunDot
                        )
                    );


                vec3 sunsetColor =
                    vec3(
                        1.0,
                        0.20,
                        0.025
                    );


                atmosphereColor =
                    mix(
                        atmosphereColor,
                        sunsetColor,
                        sunsetBand * 0.52
                    );


                float alpha =
                    rim *
                    (
                     0.010 +
daylight * 0.18
                    );


alpha +=
    rim *
    sunsetBand * 0.10;

gl_FragColor =
    vec4(
        atmosphereColor,
        alpha
    );
            }

        `,

        transparent: true,

        blending:
            THREE.AdditiveBlending,

        side:
            THREE.BackSide,

        depthWrite: false
    });


const atmosphere =
    new THREE.Mesh(
        atmosphereGeometry,
        atmosphereMaterial
    );


earthSystem.add(
    atmosphere
);


/* =========================================
   OUTER ATMOSPHERE GLOW
   Large soft cinematic halo
   ========================================= */

const outerAtmosphereGeometry =
    new THREE.SphereGeometry(
    1.055,
    128,
    128
);


const outerAtmosphereMaterial =
    new THREE.ShaderMaterial({

        uniforms: {

            sunWorldPosition: {
                value: new THREE.Vector3()
            },

            cameraWorldPosition: {
                value: new THREE.Vector3()
            }

        },

        vertexShader: `

            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;

            void main() {

                vec4 worldPosition =
                    modelMatrix *
                    vec4(
                        position,
                        1.0
                    );

                vWorldPosition =
                    worldPosition.xyz;

                vWorldNormal =
                    normalize(
                        mat3(modelMatrix) *
                        normal
                    );

                gl_Position =
                    projectionMatrix *
                    viewMatrix *
                    worldPosition;
            }

        `,

        fragmentShader: `

            uniform vec3 sunWorldPosition;
            uniform vec3 cameraWorldPosition;

            varying vec3 vWorldPosition;
            varying vec3 vWorldNormal;

            void main() {

                vec3 normal =
                    normalize(
                        vWorldNormal
                    );

                vec3 viewDirection =
                    normalize(
                        cameraWorldPosition -
                        vWorldPosition
                    );

                vec3 sunDirection =
                    normalize(
                        sunWorldPosition -
                        vWorldPosition
                    );

                float viewDot =
                    max(
                        dot(
                            normal,
                            viewDirection
                        ),
                        0.0
                    );

                float sunDot =
                    dot(
                        normal,
                        sunDirection
                    );

float outerRim =
    pow(
        1.0 -
        viewDot,
        3.65
    );
              
               
                    float daylight =
                    smoothstep(
                        -0.35,
                        0.25,
                        sunDot
                    );


                vec3 glowColor =
                    mix(
                        vec3(
                            0.005,
                            0.025,
                            0.07
                        ),

                       vec3(
   0.90,
0.93,
0.98
),

                        daylight
                    );


                float alpha =
                    outerRim *
                    (
                       0.004 +
daylight * 0.08
                    );


                gl_FragColor =
                    vec4(
                        glowColor,
                        alpha
                    );
            }

        `,

        transparent: true,

        blending:
            THREE.AdditiveBlending,

        side:
            THREE.BackSide,

        depthWrite: false
    });


const outerAtmosphere =
    new THREE.Mesh(
        outerAtmosphereGeometry,
        outerAtmosphereMaterial
    );


earthSystem.add(
    outerAtmosphere
);
    
   
   /* =========================================
       MOON
       ========================================= */

    const moonGeometry =
        new THREE.SphereGeometry(
            0.23,
            48,
            48
        );

    const moonTexture =
    textureLoader.load(
        resolveGlobeAssetUrl(
            "moon_8k.jpg"
        )
    );

moonTexture.colorSpace =
    THREE.SRGBColorSpace;

const moonMaterial =
    new THREE.MeshStandardMaterial({

        map: moonTexture,

        roughness: 1,

        metalness: 0

    });

    const moon =
        new THREE.Mesh(
            moonGeometry,
            moonMaterial
        );

    moon.position.set(
        3.3,
        0.55,
        -2.2
    );
   
        spaceWorld.add(
        moon
    );

/* =========================================
   CINEMATIC CLOUD LAYER
   ========================================= */

earthCloudTexture.colorSpace =
    THREE.SRGBColorSpace;

earthCloudTexture.anisotropy =
    renderer.capabilities.getMaxAnisotropy();

earthCloudTexture.minFilter =
    THREE.LinearMipmapLinearFilter;

earthCloudTexture.magFilter =
    THREE.LinearFilter;


const cloudGeometry =
    new THREE.SphereGeometry(
        1.018,
        128,
        128
    );


const cloudMaterial =
    new THREE.MeshPhongMaterial({

        map:
            earthCloudTexture,

        transparent:
            true,

        opacity:
            0.0,

        depthWrite:
            false,

        side:
            THREE.DoubleSide,

        blending:
            THREE.NormalBlending,

        shininess:
            3,

        color:
            0xffffff

    });


const clouds =
    new THREE.Mesh(
        cloudGeometry,
        cloudMaterial
    );


earth.add(
    clouds
);
  
    /* =========================================
   SUN
   ========================================= */

const sunGeometry =
    new THREE.SphereGeometry(
        0.72,
        64,
        64
    );

const sunMaterial =
    new THREE.MeshBasicMaterial({

        color: 0xffffff

    });

    const sun =
    new THREE.Mesh(
        sunGeometry,
        sunMaterial
    );

sun.position.set(
      -11,
    5.6,
    -12
);

spaceWorld.add(
    sun
);


/* =========================================
   SUN GLOW
   ========================================= */

const sunGlowGeometry =
    new THREE.SphereGeometry(
        1.75,
        64,
        64
    );

const sunGlowMaterial =
    new THREE.MeshBasicMaterial({

        color: 0xfff4dd,

        transparent: true,

        opacity: 0.18,

        side: THREE.BackSide

    });

const sunGlow =
    new THREE.Mesh(
        sunGlowGeometry,
        sunGlowMaterial
    );

sun.add(
    sunGlow
);


/* =========================================
   REAL SUN WORLD POSITION
   ========================================= */

const realSunWorldPosition =
    new THREE.Vector3();



/* =========================================
   LIGHTS
   ========================================= */

/* =========================================
   LIGHTS
   ========================================= */

const ambientLight =
    new THREE.AmbientLight(
        0x8eb9ad,
        0.12
    );

scene.add(
    ambientLight
);


const sunLight =
    new THREE.DirectionalLight(
        0xfff1cf,
        5.2
    );

sunLight.position.copy(
    sun.position
);

scene.add(
    sunLight
);


const earthFillLight =
    new THREE.DirectionalLight(
        0x4a9b87,
        0.18
    );

earthFillLight.position.set(
    4,
    -2,
    3
);

scene.add(
    earthFillLight
);
    
/* =========================================
       INITIAL WORLD COMPOSITION
       ========================================= */

  earthSystem.position.set(
    1.45,
    -0.99,
    0
);

earthSystem.scale.setScalar(
    0.92
);
    
earthSystem.rotation.x =
    0.13;

earthSystem.rotation.y =
    -0.08;

earthSystem.rotation.z =
    -0.08;


    /* =========================================
       VIEW ROTATION
       ========================================= */

    let viewYaw = 0;
    let viewPitch = 0;

    let targetYaw = 0;
    let targetPitch = 0;

    let dragging = false;

    let previousPointerX = 0;
    let previousPointerY = 0;


    globeContainer.addEventListener(
        "pointerdown",
        function (event) {

            if (flightActive) {
                return;
            }

            dragging = true;

            previousPointerX =
                event.clientX;

            previousPointerY =
                event.clientY;

            globeContainer.style.cursor =
                "grabbing";

            globeContainer.setPointerCapture(
                event.pointerId
            );
        }
    );


    globeContainer.addEventListener(
        "pointermove",
        function (event) {

            if (
                !dragging ||
                flightActive
            ) {
                return;
            }

            const deltaX =
                event.clientX -
                previousPointerX;

            const deltaY =
                event.clientY -
                previousPointerY;

          targetYaw -=
    deltaX * 0.0026;

targetPitch +=
    deltaY * 0.0020;
            
                targetPitch =
                Math.max(
                    -0.60,
                    Math.min(
                        0.60,
                        targetPitch
                    )
                );

            previousPointerX =
                event.clientX;

            previousPointerY =
                event.clientY;
        }
    );


    function stopDragging(
        event
    ) {

        dragging = false;

        globeContainer.style.cursor =
            flightActive
                ? "default"
                : "grab";

        if (
            event &&
            globeContainer.hasPointerCapture(
                event.pointerId
            )
        ) {
            globeContainer.releasePointerCapture(
                event.pointerId
            );
        }
    }


    globeContainer.addEventListener(
        "pointerup",
        stopDragging
    );

    globeContainer.addEventListener(
        "pointercancel",
        stopDragging
    );


    /* =========================================
       MALAYSIA FLIGHT
       ========================================= */

    let flightActive = false;

    let flightStartTime = 0;

    const flightDuration =
        5200;

    const startCameraPosition =
        new THREE.Vector3();

    const startEarthPosition =
        new THREE.Vector3();

    /*
       Peninsular Malaysia target
       (matches the marker's lat/lon
       so the flight lands where the
       marker actually is instead of
       a hand-picked magic rotation).
    */

    const MALAYSIA_FLIGHT_LAT =
        THREE.MathUtils.degToRad(
            4.21
        );

    const MALAYSIA_FLIGHT_LON =
        THREE.MathUtils.degToRad(
            101.976
        );

    const malaysiaFlightLocalDirection =
        new THREE.Vector3(
            Math.cos(MALAYSIA_FLIGHT_LAT) *
                Math.cos(MALAYSIA_FLIGHT_LON),
            Math.sin(MALAYSIA_FLIGHT_LAT),
            -Math.cos(MALAYSIA_FLIGHT_LAT) *
                Math.sin(MALAYSIA_FLIGHT_LON)
        );

    /*
       Yaw (earthSystem.rotation.y) that
       brings the Malaysia direction to
       face the camera, assuming zero
       accumulated spin on the earth mesh.

       Phase 3 also drives earthSystem's X
       tilt to 0.20 and Z tilt to -0.08 at
       the same time as this yaw (Three.js
       Euler 'XYZ' composes them together),
       so the yaw can't be solved from a plain
       atan2 on the untilted direction - that
       ignores the tilt and centres the wrong
       point (e.g. Asia instead of Malaysia).

       Instead of hand-deriving the coupled
       X/Y/Z matrix, this delegates the actual
       rotation math to THREE.Vector3.applyEuler
       itself (the same function Phase 3's
       result will actually be rendered with),
       so it is guaranteed to match. The
       horizontal offset x'(yaw) of the rotated
       direction is a pure sinusoid in yaw, so
       sampling it at yaw = 0 and yaw = PI/2
       fully determines its amplitude/phase and
       therefore both roots where x' = 0; the
       root whose rotated z' is positive is the
       one that faces the camera.
    */

    const MALAYSIA_TILT_X = 0.20;
    const MALAYSIA_TILT_Z = -0.08;

    const MALAYSIA_FRONT_YAW =
        (function () {

            const probeVector =
                new THREE.Vector3();
            const probeEuler =
                new THREE.Euler(
                    MALAYSIA_TILT_X,
                    0,
                    MALAYSIA_TILT_Z,
                    "XYZ"
                );

            function rotatedAt(yaw) {
                probeEuler.y = yaw;
                return probeVector
                    .copy(
                        malaysiaFlightLocalDirection
                    )
                    .applyEuler(
                        probeEuler
                    );
            }

            const xAtZero =
                rotatedAt(0).x;
            const xAtQuarter =
                rotatedAt(
                    Math.PI / 2
                ).x;

            const phase =
                Math.atan2(
                    xAtQuarter,
                    xAtZero
                );

            const candidateOne =
                phase + Math.PI / 2;
            const candidateTwo =
                phase - Math.PI / 2;

            const zOne =
                rotatedAt(
                    candidateOne
                ).z;
            const zTwo =
                rotatedAt(
                    candidateTwo
                ).z;

            return zOne >= zTwo
                ? candidateOne
                : candidateTwo;

        })();

    console.log(
    "MALAYSIA_FRONT_YAW =",
    MALAYSIA_FRONT_YAW
);
    
        /*
       earth.rotation.y (the mesh's own idle
       auto-spin) and earthSystem.rotation.y
       (the flight's yaw) both rotate around
       the same axis and both end up baked
       into Earth's final on-screen orientation
       at once. Subtracting the spin out of the
       earthSystem target only cancels it
       correctly when earthSystem has no X/Z
       tilt - once the tilt is non-zero the two
       rotations no longer commute, so the
       subtraction leaves a leftover error that
       grows with however long the globe had
       been idling, and Malaysia lands off
       centre. Freezing the mesh's own spin to
       0 for the flight (and forever after,
       since it never resumes once the flight
       finishes) removes that second rotation
       source, so earthSystem.rotation is the
       only thing controlling Earth's final
       orientation.
    */

    let flightEarthSpinAtLaunch = 0;

    /*
       Starting orientation of earthSystem
       at the moment the flight begins, used
       to ease the rotation directly toward
       Malaysia (see updateMalaysiaFlight)
       instead of an unbounded per-frame
       decay, so the sweep always finishes
       early while still zoomed out instead
       of drifting across other countries
       while the camera is already close.
    */

    let flightStartRotationY = 0;
    let flightStartRotationX = 0;
    let flightStartRotationZ = 0;

    let arrivalEventSent = false;
    let malaysiaMarkerCreated = false;
    let malaysiaMarkerGroup = null;
    const malaysiaMarkerBasePosition = new THREE.Vector3();
    const malaysiaMarkerDirection = new THREE.Vector3();
    const malaysiaMarkerTempOffset = new THREE.Vector3();
    let malaysiaMarkerFadeStartTime = 0;
    let malaysiaMarkerVisible = false;
    let malaysiaMarkerRing = null;
    let malaysiaMarkerCore = null;
    let malaysiaMarkerGlow = null;

    function createMalaysiaMarker() {
        if (malaysiaMarkerCreated) {
            return;
        }

        malaysiaMarkerCreated = true;

        const malaysiaLat =
            THREE.MathUtils.degToRad(
                4.21
            );

      const malaysiaLon =
    THREE.MathUtils.degToRad(
        108
    );

        const markerDir =
            new THREE.Vector3(
                Math.cos(malaysiaLat) * Math.cos(malaysiaLon),
                Math.sin(malaysiaLat),
                -Math.cos(malaysiaLat) * Math.sin(malaysiaLon)
            ).normalize();

        const markerPosition =
            markerDir.clone().multiplyScalar(
                1.02
            );

        malaysiaMarkerBasePosition.copy(
            markerPosition
        );

        malaysiaMarkerDirection.copy(
            markerDir
        );

        malaysiaMarkerGroup =
            new THREE.Group();

        malaysiaMarkerGroup.position.copy(
            markerPosition
        );

        const orientation =
            new THREE.Quaternion().setFromUnitVectors(
                new THREE.Vector3(0, 1, 0),
                markerDir
            );

malaysiaMarkerRing =
    new THREE.Mesh(

        new THREE.TorusGeometry(
            0.38,
            0.004,
            24,
            128
        ),

        new THREE.MeshStandardMaterial({
            color: 0xffd77a,
            metalness: 0.78,
            roughness: 0.22,
            emissive: 0x191100,
            emissiveIntensity: 0.08,
            transparent: true,
            opacity: 0,
            depthWrite: false
        })

    );
     
            malaysiaMarkerRing.quaternion.copy(
            orientation
        );

        malaysiaMarkerRing.rotation.x +=
            Math.PI * 0.5;

        malaysiaMarkerGroup.add(
            malaysiaMarkerRing
        );

        malaysiaMarkerCore =
            new THREE.Mesh(
                new THREE.SphereGeometry(
                    0.028,
                    18,
                    18
                ),
                new THREE.MeshStandardMaterial({
                    color: 0xfff3c0,
                    metalness: 0.18,
                    roughness: 0.45,
                    emissive: 0x0b0500,
                    emissiveIntensity: 0.12,
                    transparent: true,
                    opacity: 0,
                    depthWrite: false
                })
            );

        malaysiaMarkerGroup.add(
            malaysiaMarkerCore
        );

        malaysiaMarkerGlow =
            new THREE.Mesh(
                new THREE.TorusGeometry(
                    0.18,
                    0.01,
                    16,
                    128
                ),
                new THREE.MeshBasicMaterial({
                    color: 0xffe5a4,
                    transparent: true,
                    opacity: 0,
                    blending: THREE.AdditiveBlending,
                    depthWrite: false,
                    side: THREE.DoubleSide
                })
            );

        malaysiaMarkerGlow.quaternion.copy(
            orientation
        );

        malaysiaMarkerGlow.rotation.x +=
            Math.PI * 0.5;

        malaysiaMarkerGroup.add(
            malaysiaMarkerGlow
        );

        malaysiaMarkerGroup.visible = false;

        earth.add(
            malaysiaMarkerGroup
        );
    }

    function revealMalaysiaMarker() {
        createMalaysiaMarker();

        if (
            malaysiaMarkerGroup &&
            !malaysiaMarkerVisible
        ) {
            malaysiaMarkerGroup.visible =
                true;
            malaysiaMarkerVisible =
                true;
            malaysiaMarkerFadeStartTime =
                performance.now();
        }
    }

    window.addEventListener(
        "earthMalaysiaFlightComplete",
        function () {
            revealMalaysiaMarker();
        }
    );

/* =========================================
   HERO STATES
   ========================================= */

const HERO_STATE = {

    LOADING: 0,

    IDLE: 1,

    PREPARING: 2,

    FLYING: 3,

    REVEAL: 4,

    COMPLETE: 5

};

let heroState =
    HERO_STATE.LOADING;

   
    function easeInOutCubic(
        value
    ) {

        return value < 0.5
            ? 4 *
              value *
              value *
              value
            : 1 -
              Math.pow(
                  -2 * value + 2,
                  3
              ) / 2;
    }


    function startMalaysiaFlight() {

        if (flightActive) {
            return;
        }

      heroState =
    HERO_STATE.PREPARING;
      
        flightActive = true;

       heroState =
    HERO_STATE.FLYING;
       
        arrivalEventSent = false;

        /*
           Zero out the mesh's own spin instead
           of trying to subtract it back out
           later, so earthSystem.rotation.y is
           the single rotation that determines
           where Earth ends up facing.
        */
        earth.rotation.y = 0;

        flightEarthSpinAtLaunch = 0;

        flightStartRotationY =
            earthSystem.rotation.y;

        flightStartRotationX =
            earthSystem.rotation.x;

        flightStartRotationZ =
            earthSystem.rotation.z;

        flightStartTime =
            performance.now();

        startCameraPosition.copy(
            camera.position
        );

        startEarthPosition.copy(
            earthSystem.position
        );

        targetYaw = 0;
        targetPitch = 0;

        globeContainer.style.cursor =
            "default";

        window.dispatchEvent(
            new CustomEvent(
                "earthMalaysiaFlightStarted"
            )
        );
    }


    if (exploreButton) {

        exploreButton.addEventListener(
            "click",
            startMalaysiaFlight
        );
    }


    /* =========================================
       UPDATE MALAYSIA FLIGHT
       ========================================= */

    function updateMalaysiaFlight(
        time
    ) {

        if (!flightActive) {
            return;
        }

        const rawProgress =
            Math.min(
                (
                    time -
                    flightStartTime
                ) /
                flightDuration,
                1
            );

        const progress =
            easeInOutCubic(
                rawProgress
            );


        /*
           PHASE 1:
           Pull the world back toward
           a centred Earth view.
        */

        viewYaw +=
            (
                0 -
                viewYaw
            ) * 0.045;

        viewPitch +=
            (
                0 -
                viewPitch
            ) * 0.045;


        /*
           PHASE 2:
           Move Earth to the centre.
        */

        earthSystem.position.x =
            THREE.MathUtils.lerp(
                startEarthPosition.x,
                0,
                progress
            );

        earthSystem.position.y =
            THREE.MathUtils.lerp(
                startEarthPosition.y,
                0,
                progress
            );


        /*
           PHASE 3:
           Rotate Earth toward
           Southeast Asia / Malaysia.
           
           The target yaw is derived from
           Malaysia's actual lat/lon (see
           MALAYSIA_FRONT_YAW above) and
           compensated for whatever auto-spin
           the earth mesh had already
           accumulated when the flight
           started, so it always lands on
           Malaysia instead of drifting to a
           random ocean spot depending on
           timing.

           The rotation is eased directly from
           its starting angle to the target
           using a curve that finishes early
           (by ~45% of the flight), while the
           camera is still zoomed out. This
           keeps Malaysia centred throughout
           the approach instead of sweeping
           past other countries (e.g. China or
           India) while already zoomed in.
        */

        const rotationEase =
            easeInOutCubic(
                Math.min(
                    rawProgress / 0.45,
                    1
                )
            );

earthSystem.rotation.y =
    THREE.MathUtils.lerp(
        flightStartRotationY,
        MALAYSIA_FRONT_YAW,
        rotationEase
    );
            
            earthSystem.rotation.x =
            THREE.MathUtils.lerp(
                flightStartRotationX,
                0.20,
                rotationEase
            );

        earthSystem.rotation.z =
            THREE.MathUtils.lerp(
                flightStartRotationZ,
                -0.08,
                rotationEase
            );


        /*
           PHASE 4:
           Fly closer.

           (The actual position/lookAt values
           are applied once below, using
           cameraEase, so the flight always
           ends at that single, exact camera
           position - never an intermediate
           estimate.)
        */

        if (
            rawProgress >= 0.65
        ) {
            revealMalaysiaMarker();
        }
       
            /*
           SIGNAL DASHBOARD.JS
           BEFORE THE EARTH COMPLETELY
           FILLS THE SCREEN.
        */

        if (
            rawProgress >= 0.82 &&
            !arrivalEventSent
        ) {

            arrivalEventSent = true;

            window.dispatchEvent(
                new CustomEvent(
                    "earthMalaysiaArrivalReady"
                )
            );
        }

        const cameraEase =
            easeInOutCubic(
                progress
            );

        /*
           Cinematic cloud reveal during the
           approach: the cloud layer (already
           dispersed from the initial page-load
           reveal) gradually fades back in and
           wraps around the Earth as the camera
           closes in on Malaysia.
        */

        clouds.material.opacity =
            progress * 0.7;

        camera.position.z =
            THREE.MathUtils.lerp(
                startCameraPosition.z,
                3.0,
                cameraEase
            );

        camera.position.x =
            THREE.MathUtils.lerp(
                startCameraPosition.x,
                0,
                cameraEase * 0.98
            );

        camera.position.y =
            THREE.MathUtils.lerp(
                startCameraPosition.y,
                0.55,
                cameraEase
            );

        if (progress > 0.35) {
            camera.position.x +=
                Math.sin(
                    progress * Math.PI * 1.6
                ) * 0.035;
        }

        /*
           Aim slightly above the earth's
           centre so Peninsular Malaysia
           settles a little lower in the
           frame instead of dead-centre.
        */

const malaysiaWorldPosition =
    malaysiaMarkerBasePosition
        .clone();

earth.localToWorld(
    malaysiaWorldPosition
);

camera.lookAt(
    malaysiaWorldPosition
);

        if (rawProgress >= 1) {

       console.log("=== Flight Complete ===");

console.log(
    "camera",
    camera.position.x,
    camera.position.y,
    camera.position.z
);

console.log(
    "earthSystem.rotation",
    earthSystem.rotation.x,
    earthSystem.rotation.y,
    earthSystem.rotation.z
);

console.log(
    "earth.rotation",
    earth.rotation.x,
    earth.rotation.y,
    earth.rotation.z
);

const malaysiaWorld =
    malaysiaFlightLocalDirection
        .clone()
        .applyQuaternion(
            earth.getWorldQuaternion(
                new THREE.Quaternion()
            )
        );

console.log(
    "Malaysia world",
    malaysiaWorld.x,
    malaysiaWorld.y,
    malaysiaWorld.z
);

console.log(
    "MALAYSIA_FRONT_YAW",
    MALAYSIA_FRONT_YAW
);
           
            heroState =
    HERO_STATE.REVEAL;


    flightActive = false;

            window.dispatchEvent(
                new CustomEvent(
                    "earthMalaysiaFlightComplete"
                )
            );
        }
    }


    /* =========================================
       RESIZE
       ========================================= */

    function resizeEarth() {

        const width =
            globeStage.clientWidth;

        const height =
            globeStage.clientHeight;

        if (!width || !height) {
            return;
        }

        camera.aspect =
            width / height;

        camera.updateProjectionMatrix();

        renderer.setSize(
            width,
            height,
            false
        );
    }


    resizeEarth();

    window.addEventListener(
        "resize",
        resizeEarth
    );

/* =========================================
   CINEMATIC STAR FIELD
   ========================================= */

function createStarLayer(
    count,
    radiusMin,
    radiusMax,
    size,
    opacity,
    color = 0xffffff
) {

    const positions =
        new Float32Array(
            count * 3
        );

    for (
        let i = 0;
        i < count;
        i++
    ) {

        const radius =
            THREE.MathUtils.randFloat(
                radiusMin,
                radiusMax
            );


        const theta =
            Math.random()
            * Math.PI
            * 2;


        const phi =
            Math.acos(
                THREE.MathUtils.randFloatSpread(
                    2
                )
            );


        positions[
            i * 3
        ] =
            radius
            * Math.sin(phi)
            * Math.cos(theta);


        positions[
            i * 3 + 1
        ] =
            radius
            * Math.cos(phi);


        positions[
            i * 3 + 2
        ] =
            radius
            * Math.sin(phi)
            * Math.sin(theta);

    }


    const geometry =
        new THREE.BufferGeometry();


    geometry.setAttribute(

        "position",

        new THREE.BufferAttribute(
            positions,
            3
        )

    );


    const material =
        new THREE.PointsMaterial({

            color:
                color,

            size:
                size,

            transparent:
                true,

            opacity:
                opacity,

            sizeAttenuation:
                true,

            depthWrite:
                false

        });


    return new THREE.Points(
        geometry,
        material
    );

}


/* 大量细小远星 */

const distantStars =
    createStarLayer(
        3200,
        35,
        75,
        0.055,
        0.72
    );


scene.add(
    distantStars
);


/* 少量较亮星星 */

const brightStars =
    createStarLayer(
        420,
        30,
        65,
        0.105,
        0.92
    );


scene.add(
    brightStars
);

const spaceDust =
    createStarLayer(
        1800,
        26,
        85,
        0.02,
        0.18,
        0xc8dbe8
    );

scene.add(
    spaceDust
);

const nebulaGeometry =
    new THREE.SphereGeometry(
        42,
        32,
        32
    );

const nebulaMaterial =
    new THREE.MeshBasicMaterial({
        color: 0x1a3247,
        transparent: true,
        opacity: 0.045,
        side: THREE.BackSide,
        depthWrite: false
    });

const nebula =
    new THREE.Mesh(
        nebulaGeometry,
        nebulaMaterial
    );

scene.add(
    nebula
);
       
   
   
    /* =========================================
       ANIMATION
       ========================================= */

    function animate(
        time
    ) {


      
        requestAnimationFrame(
            animate
        );

        if (
            !heroLoaded &&
            performance.now() -
                loadCompleteTime >
                1400
        ) {
            heroLoaded = true;
            loadCompleteTime =
                performance.now();
            loadingValue = 100;
            loadingPercent.textContent =
                "100%";
            loadingBar.style.width =
                "100%";
            loadingStatus.textContent =
                "Finalizing...";
        }

/* =========================================
   HERO LOADING
   ========================================= */

if (!heroLoaded) {
            // keep the overlay visible while assets load
            loadingPercent.textContent =
                loadingValue + "%";
            loadingBar.style.width =
                loadingValue + "%";
            loadingStatus.textContent =
                loadingStates[
                    loadingStateIndex
                ];
        }

if (heroLoaded) {
            const elapsed =
                (performance.now() -
                    loadCompleteTime) /
                1000;

            if (elapsed >= 0.8) {
                const fade =
                    Math.min(
                        (elapsed - 0.8) /
                            0.9,
                        1
                    );

                loadingOverlay.style.opacity =
                    String(1 - fade);

                if (fade >= 1) {
                    if (
                        loadingOverlay.parentNode
                    ) {
                        loadingOverlay.remove();
                    }
                }
            }

            revealProgress +=
                0.0045;

            cloudsRevealProgress +=
                0.0025;

            earthMaterial.uniforms
                .revealOpacity
                .value =
                Math.min(
                    1,
                    revealProgress
                );

clouds.material.opacity =
    (flightActive ||
        heroState === HERO_STATE.REVEAL)
        ? clouds.material.opacity
        : Math.max(
            0,
            0.85 -
                cloudsRevealProgress
        );
        }


        if (
            !flightActive &&
            heroState !== HERO_STATE.REVEAL
        ) {

            targetYaw +=
                Math.sin(
                    time * 0.00012
                ) * 0.00012;

            targetPitch +=
                Math.cos(
                    time * 0.00009
                ) * 0.00006;

            targetPitch =
                Math.max(
                    -0.60,
                    Math.min(
                        0.60,
                        targetPitch
                    )
                );

            viewYaw +=
                (
                    targetYaw -
                    viewYaw
                ) * 0.06;

            viewPitch +=
                (
                    targetPitch -
                    viewPitch
                ) * 0.06;

            earth.rotation.y +=
                0.0018;
       
       clouds.rotation.y +=
    0.00022;
       
            }


        const orbitRadius = 6.1;

/*
   Once the Malaysia flight has finished
   (heroState REVEAL), leave the camera
   exactly where updateMalaysiaFlight put
   it. Otherwise this unconditional orbit
   formula runs every frame and immediately
   snaps the camera back out to the wide
   idle orbit, undoing the "finish centered
   on Malaysia" result right after arrival.
*/

if (
    heroState !==
    HERO_STATE.REVEAL
) {

camera.position.x =
    earthSystem.position.x +
    Math.sin(viewYaw) *
    Math.cos(viewPitch) *
    orbitRadius;

camera.position.y =
    earthSystem.position.y +
    Math.sin(viewPitch) *
    orbitRadius;

camera.position.z =
    earthSystem.position.z +
    Math.cos(viewYaw) *
    Math.cos(viewPitch) *
    orbitRadius;

camera.lookAt(
    earthSystem.position.x,
    earthSystem.position.y + 0.2,
    earthSystem.position.z
);

}
       
            /* SLOW SPACE MOTION */

        stars.rotation.y +=
            0.000035;

       distantStars.rotation.y +=
    0.000015;

brightStars.rotation.y +=
    0.000008;

spaceDust.rotation.y +=
    0.000022;

nebula.rotation.y +=
    0.000006;

brightStars.material.opacity =
    0.86 +
    Math.sin(time * 0.002) *
    0.05;



        if (
            malaysiaMarkerVisible &&
            malaysiaMarkerGroup
        ) {
            const markerFade =
                Math.min(
                    Math.max(
                        (time -
                            malaysiaMarkerFadeStartTime) /
                            1000,
                        0
                    ),
                    1
                );

            const pulse =
                1 +
                Math.sin(
                    time * 0.0027
                ) *
                0.022;

            const floatDistance =
                0.008 +
                Math.sin(
                    time * 0.0019
                ) *
                0.006;

            malaysiaMarkerTempOffset
                .copy(
                    malaysiaMarkerDirection
                )
                .multiplyScalar(
                    floatDistance
                );

            malaysiaMarkerGroup.position
                .copy(
                    malaysiaMarkerBasePosition
                )
                .add(
                    malaysiaMarkerTempOffset
                );

            malaysiaMarkerGroup.scale
                .setScalar(
                    pulse
                );

            if (
                malaysiaMarkerRing &&
                malaysiaMarkerCore &&
                malaysiaMarkerGlow
            ) {
                malaysiaMarkerRing.material.opacity =
                    0.85 * markerFade;

                malaysiaMarkerCore.material.opacity =
                    0.65 * markerFade;

                malaysiaMarkerGlow.material.opacity =
                    0.35 * markerFade *
                    (0.84 +
                        Math.sin(
                            time * 0.0033
                        ) *
                        0.16);
            }
        }
       
       
       
       
       
        
    


        /* MOON ORBIT */

        const moonTime =
            time * 0.00012;

        moon.position.x =
            Math.cos(
                moonTime
            ) * 2.8;

        moon.position.z =
            Math.sin(
                moonTime
            ) * 2.8 -
            0.8;

        moon.position.y =
            0.7 +
            Math.sin(
                moonTime * 0.7
            ) * 0.35;


        /* =========================================
           MALAYSIA FLIGHT
           ========================================= */

        updateMalaysiaFlight(
            time
        );


        /* =========================================
           UPDATE REAL SUN POSITION FOR EARTH SHADER
           ========================================= */

       /* =========================================
   UPDATE REAL SUN POSITION
   ========================================= */

sun.getWorldPosition(
    realSunWorldPosition
);


/* =========================================
   UPDATE EARTH SHADER
   ========================================= */

earthMaterial.uniforms
    .sunWorldPosition
    .value
    .copy(
        realSunWorldPosition
    );


camera.getWorldPosition(
    earthMaterial.uniforms
        .cameraWorldPosition
        .value
);


/* =========================================
   UPDATE BOTH ATMOSPHERE SHADERS
   ========================================= */

atmosphereMaterial.uniforms
    .sunWorldPosition
    .value
    .copy(
        realSunWorldPosition
    );

camera.getWorldPosition(
    atmosphereMaterial.uniforms
        .cameraWorldPosition
        .value
);


/* OUTER ATMOSPHERE */

outerAtmosphereMaterial.uniforms
    .sunWorldPosition
    .value
    .copy(
        realSunWorldPosition
    );

camera.getWorldPosition(
    outerAtmosphereMaterial.uniforms
        .cameraWorldPosition
        .value
);

/* =========================================
   RENDER SCENE
   ========================================= */

/* =========================================
   HERO LOADING TIMER
   ========================================= */

if (
    heroState ===
    HERO_STATE.LOADING
) {

    heroLoadingProgress +=
        0.55;

    if (
        heroLoadingProgress >= 100
    ) {

        heroLoadingProgress = 100;

        heroLoadingFinished =
            true;

        heroState =
            HERO_STATE.IDLE;

    }

}

   renderer.render(
    scene,
    camera
);

    }


    /* =========================================
       START ANIMATION
       ========================================= */

    animate(
        performance.now()
    );

});

