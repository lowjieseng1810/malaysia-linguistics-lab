document.addEventListener("DOMContentLoaded", function () {

   /* =========================================
   HERO LOADING STATE
   ========================================= */

let heroLoaded = false;

const loadingOverlay =
    document.createElement("div");

loadingOverlay.id =
    "hero-loading-overlay";

loadingOverlay.style.position =
    "absolute";

loadingOverlay.style.inset =
    "0";

loadingOverlay.style.display =
    "flex";

loadingOverlay.style.flexDirection =
    "column";

loadingOverlay.style.alignItems =
    "center";

loadingOverlay.style.justifyContent =
    "center";

loadingOverlay.style.background =
    "rgba(5,12,18,0.96)";

loadingOverlay.style.zIndex =
    "999";

loadingOverlay.style.transition =
    "opacity 1.2s ease";

const loadingText =
    document.createElement("div");

loadingText.textContent =
    "Loading Earth...";

loadingText.style.color =
    "#ffffff";

loadingText.style.fontSize =
    "18px";

loadingText.style.letterSpacing =
    "2px";

loadingText.style.marginBottom =
    "16px";

const loadingPercent =
    document.createElement("div");

loadingPercent.textContent =
    "0%";

loadingPercent.style.color =
    "#d9b44a";

loadingPercent.style.fontSize =
    "28px";

loadingPercent.style.fontWeight =
    "700";

loadingOverlay.appendChild(
    loadingText
);

loadingOverlay.appendChild(
    loadingPercent
);

globeStage.appendChild(
    loadingOverlay
);

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

    globeContainer.style.touchAction =
        "none";

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

    const textureLoader =
    new THREE.TextureLoader();

const earthDayTexture =
    textureLoader.load(
        "/static/images/earth/earth_day_8k.jpg"
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
    textureLoader.load(
        "/static/images/earth/earth_normal.jpg"
    );

const earthSpecularTexture =
    textureLoader.load(
        "/static/images/earth/earth_specular.jpg"
    );

const earthCloudTexture =
    textureLoader.load(
        "/static/images/earth/earth_clouds.png"
    );
    
      const earthNightTexture =
    textureLoader.load(
        "/static/images/earth/earth_night.png"
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
            }

        },

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


                vec3 cityLights =
    cityColor *
    cityMask *
    3.8 *
    nightAmount;


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


                gl_FragColor =
                    vec4(
                        finalColor,
                        1.0
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
        "/static/images/earth/moon_8k.jpg"
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
            0.82,

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

    let arrivalEventSent = false;

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

let heroLoadingProgress =
    0;

let heroLoadingFinished =
    false;
   
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
           
           This is the visual target.
           We can fine-tune the exact
           longitude after you test it.
        */

        earthSystem.rotation.y =
            THREE.MathUtils.lerp(
                earthSystem.rotation.y,
                -1.78,
                0.035
            );

        earthSystem.rotation.x =
            THREE.MathUtils.lerp(
                earthSystem.rotation.x,
                0.20,
                0.035
            );

        earthSystem.rotation.z =
            THREE.MathUtils.lerp(
                earthSystem.rotation.z,
                -0.08,
                0.035
            );


        /*
           PHASE 4:
           Fly closer.
        */

        camera.position.z =
            THREE.MathUtils.lerp(
                startCameraPosition.z,
                2.15,
                progress
            );

        camera.position.x =
            THREE.MathUtils.lerp(
                startCameraPosition.x,
                0,
                progress
            );

        camera.position.y =
            THREE.MathUtils.lerp(
                startCameraPosition.y,
                0.75,
                progress
            );

camera.lookAt(
    earthSystem.position
);
       
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


        if (rawProgress >= 1) {

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
    opacity
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
                0xffffff,

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
       
   
   
    /* =========================================
       ANIMATION
       ========================================= */

    function animate(
        time
    ) {


      
        requestAnimationFrame(
            animate
        );

/* =========================================
   HERO LOADING
   ========================================= */

if (!heroLoaded) {

    loadingValue += 1.2;

    if (loadingValue > 100) {
        loadingValue = 100;
    }

    loadingPercent.textContent =
        Math.floor(
            loadingValue
        ) + "%";

    if (loadingValue >= 100) {

        heroLoaded = true;

        loadingOverlay.style.opacity =
            "0";

        setTimeout(() => {

            loadingOverlay.remove();

        }, 1200);

    }

}
       
        /* USER VIEW ROTATION */

        if (!flightActive) {

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
       
            /* SLOW SPACE MOTION */

        stars.rotation.y +=
            0.000035;

       distantStars.rotation.y +=
    0.000015;

brightStars.rotation.y +=
    0.000008;
       
       
       
       
       
        
    


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

