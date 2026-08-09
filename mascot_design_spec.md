# Malaysian Linguistics Lab Mascot Design Spec

## Project Intent

This mascot is not an icon and not an illustration study. It is a software-brand character intended to sit in the same emotional category as Duolingo, GitHub, Discord, Slack, and other product mascots that are memorable at very small sizes and still feel premium at larger sizes.

The character should read as:

- kind
- curious
- encouraging
- playful
- safe for children
- confident without being loud

The mascot should feel like a guide into language discovery, not like a wildlife drawing and not like educational clipart.

## Core Character Idea

The character is a baby rhinoceros hornbill reduced to its most lovable brand traits:

- oversized round face
- large attentive eyes
- tiny toy-like beak
- tiny body hidden behind the head
- soft upward energy in the pose

The hornbill identity comes from the casque and beak shape, but the emotional identity must come from the face. If the beak is hidden, the mascot should still look like a lovable app character rather than a generic bird.

## Silhouette Strategy

The silhouette should be built around a near-circular head with a small forward bump for the beak and a small top bump for the casque. The body should be visually subordinate and mostly tucked behind the head.

Why:

- A rounded silhouette reads as plush, premium, and approachable.
- A small beak keeps the character from looking aggressive or wildlife-realistic.
- A compact silhouette survives 24px better than a long projecting beak.

## View Angle

Use a soft 3/4 view, approximately 10 to 15 degrees off-center.

Why:

- Both eyes remain visible, which is essential for personality.
- The face stays dominant instead of collapsing into a profile beak shape.
- The hornbill species cue remains visible through the casque and beak placement.

## Proportions

- Head: about 85% of total visual mass
- Face patch: about 70% of head area
- Eyes together: about 30% of face area
- Beak plus casque together: about 15% of total icon area
- Body: about 15% of total visual mass
- Wings and feet: accent shapes only

Why:

- Premium mascots are remembered through face proportions first.
- Large face area creates immediate emotional legibility at small sizes.
- Reducing beak dominance prevents the mascot from reading as a stock hornbill drawing.

## Head Shape

The head should be a soft rounded egg leaning slightly toward a circle. The lower cheeks should be full and plush. The top feather cap should form a clean curved helmet shape rather than pointy feathers.

Why:

- Circular forms are easier to anthropomorphize.
- A softer head shape shifts the character from bird illustration to mascot design.
- The feather cap gives species identity without needing texture.

## Face Patch

The cream face patch should be large, centered, and almost circular, with a slight taper near the small beak attachment point. Cheeks should be subtly fuller in the lower half.

Why:

- A large face patch creates a clean stage for the eyes.
- A centered face patch helps the character feel stable and friendly.
- Fuller cheeks create baby proportions and warmth.

## Eye Design

The eyes are the primary emotional engine.

- Large rounded vertical ovals
- Near eye slightly larger than far eye
- Pupils oversized and low enough to feel focused, but gaze angled slightly upward for curiosity
- Minimal visible sclera
- One strong round highlight and one smaller secondary highlight per eye
- Upper eyelids gently lowered into a friendly smile shape

Why:

- Large pupils increase cuteness and approachability.
- Asymmetry reinforces the 3/4 view and avoids an emoji look.
- A slight upward gaze makes the character feel hopeful and attentive.
- Lid shape adds softness without needing detailed lashes or realistic anatomy.

## Eyebrows / Brow Expression

Use soft dark-green brow arcs above both eyes. They should be short, rounded, and slightly lifted in the center.

Why:

- Brows add intelligence and expression immediately.
- Lifted inner brows make the character look curious and kind.
- Rounded brows avoid any stern or angry read.

## Smile

Use a very small smile centered low on the face patch, almost hidden. It should be a short shallow curve, not an open mouth.

Why:

- A tiny smile feels premium and subtle.
- It supports the eyes instead of competing with them.
- A small mouth keeps the face readable at 24px.

## Cheeks

Use soft cheek puffs or slightly warmer cream side shapes under the eyes. Do not add blush circles.

Why:

- Cheek volume makes the face feel plush and baby-like.
- Warm cheek shaping adds friendliness without introducing extra colors.
- Avoiding blush keeps the mascot modern rather than sticker-like.

## Beak Design

The beak is a small accessory, not the hero.

- Length reduced to about half the previous approach
- Height reduced to about two-thirds of a typical hornbill beak
- Rounded capsule-like top and bottom forms
- Soft forward point with no sharp tip
- Gently curved downward, but very restrained

Why:

- The mascot must remain cute if the beak is visually ignored.
- Smaller beak keeps the eyes and face as the first read.
- Rounded geometry makes it feel like a toy instead of a bird specimen.

## Casque Design

The casque should be a small floating accent over the beak, visually distinct but simplified into one soft rounded cap.

Why:

- This preserves the hornbill cue without overpowering the face.
- A separate casque keeps the species identity readable at small sizes.
- Simplifying it to one accent shape keeps the design premium and minimal.

## Body Design

The body should be tiny, pear-like, and mostly hidden behind the head. Only a small chest, one waving wing, and tiny feet should be visible.

Why:

- Hiding most of the body keeps attention on the face.
- A tiny body enhances the baby proportion.
- One raised wing adds action and greeting behavior.

## Wing Pose

The visible wing should be lifted slightly outward as if the mascot is saying hello.

Why:

- This creates friendly motion even in a static mark.
- A small waving gesture makes the mascot feel interactive.
- It adds character without needing facial exaggeration alone.

## Color Palette

Use flat colors only. No gradients. No outlines.

- Forest green: primary feather/body color
- Deep green: cap, brows, and shadow shapes
- Warm cream: face patch
- Golden yellow: beak base and casque
- Warm orange: beak tip and feet
- White: eye highlights only
- Black: pupils only

Why:

- Flat fills feel modern and product-grade.
- Limited palette improves brand consistency and small-size readability.
- Outline-free construction avoids the clipart look.

## Shape Language

All forms should be built from:

- circles
- ovals
- rounded capsules
- broad soft wedges

Avoid:

- feather texture
- anatomical layering
- pointy hooks
- realistic nostril details
- harsh corners

Why:

- Premium mascots rely on clear big shapes.
- Geometric softness creates instant friendliness.
- Reducing detail protects legibility at 24px.

## Small-Size Readability Rules

At 24px, the viewer should still read:

1. big friendly eyes
2. round baby face
3. small hornbill beak cue
4. compact cute silhouette

At 48px, the viewer should additionally read:

1. 3/4 face angle
2. brow expression
3. tiny smile
4. waving pose

Why:

- Software mascots must perform as tiny UI assets first.
- Secondary details should emerge only at medium sizes.

## Grayscale and Silhouette Rules

In grayscale, the face/eye balance must still feel expressive.

In silhouette, the character should still feel like a rounded mascot with a subtle beak-and-casque bump rather than a generic blob.

Why:

- Product branding appears in many visual states.
- The mascot should remain identifiable even when color information is lost.

## Implementation Constraints For SVG

When translating this spec into SVG:

- draw the head and face first
- place the eyes second
- add brows and smile third
- add body and wing fourth
- attach beak and casque last
- use only flat fills
- use no strokes
- use no gradients
- use no texture

This order is mandatory because the face is the character and the beak is only a species cue.