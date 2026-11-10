# H3 prompt spec and the multi-shot method

## The official structure

MiniMax publishes an official prompt-writing skill for H3 (`h3-prompt-writing`).
For text-to-video (T2VA base mode), a complete prompt is built from:

1. An instruction and subject definition: who and what is in the scene, stated
once, precisely (appearance, clothing, props, environment).
2. An integrated multimodal description: the visual narrative in order,
including camera movement and subject action over time.
3. `overall_soundscape`: the ambient and foley sound of the scene.
4. `non_diegetic_music`: the score the audience hears but the characters do
not.

For reference-based modes (Ref2VA), the official structure expands to six
sections: subject definitions, summary, retention analysis, a detailed
description made of timed shot blocks, overall soundscape, and non-diegetic
music. Dialogue is written with speaker labels and `<d>` tags, for example
`<d>[Mandarin] line here</d>`.

When the app in this skill generates a draft, it mirrors the base structure
with labeled blocks a human can read and edit:

```text
<subject and scene definition paragraph>
<shot block>
<shot block>
<ambience line>
<score line>
```

## The core fact about H3 generation

One H3 generation is one continuous take. The model does not cut between
shots inside a clip, does not change location mid-clip, and does not plan a
shot sequence. Hosted director-style video tools do plan shot sequences internally, which is
why a single hosted clip can contain several cuts. With H3, the director work
happens outside the model:

- You write the shot list.
- You generate one clip per shot.
- You stitch the clips.

## The multi-shot method (verified)

1. Split the story into shots with classic coverage: an establishing wide,
a subject close-up, detail or reaction shots, a climax cutaway, and a
closing wide when the story needs one. Three shots at 5 seconds each
already reads as a directed sequence.
2. Fix one character description and reuse it word for word in every shot
prompt. Change only the shot-specific parts (framing, action, camera).
Example anchor reused across three shots: "the same investigator in a
dark trench coat and fedora raises his brass lantern".
3. Repeat the palette and atmosphere words in every shot ("eerie teal-green
glow", "fog", "cinematic"). Color language is the cheapest continuity
glue between independent generations.
4. Use one fixed seed for all shots of the video. Combined with the repeated
descriptions, the same costume, props and grade show up across shots.
5. End each shot prompt with the shot type as a leading label in the text
itself: "Wide establishing shot:", "Close-up shot:", "Cutaway wide
shot:". H3 follows explicit camera language at the start of the prompt.
6. Generate all shots in one Colab session, download in order, stitch with
hard cuts. Do not add transitions by default: hard cuts at shot
boundaries are what make it feel edited.

## Worked example (real prompts from a verified run)

Story: a Lovecraft investigator before a tentacled gate. Seed 424242,
1376×768, 5 seconds per shot.

Shot 1, wide establishing:
"Wide establishing shot: a lone investigator in a dark trench coat and
fedora, holding a brass lantern, stands before a colossal ancient stone
gate carved with tentacles on a foggy cliff above a black ocean at night,
Lovecraftian cosmic horror, eerie teal-green glow, cinematic"

Shot 2, close-up:
"Close-up shot: the same investigator in a dark trench coat and fedora
raises his brass lantern, his face lit by eerie teal-green light, glowing
runes carved into the ancient stone gate behind him, fog drifting past,
expression of awe and dread, Lovecraftian cosmic horror, cinematic"

Shot 3, cutaway climax:
"Cutaway wide shot: a gigantic tentacled shadow rises from the black ocean
below a foggy cliff at night, massive tentacles curling against the sky,
the tiny silhouette of an investigator holding a lantern visible on the
cliff edge above, Lovecraftian cosmic horror, eerie teal-green glow,
cinematic"

Result: costume, lantern and grade matched across all three shots, and the
stitched 15-second sequence read as one directed scene.

## Honest trade-offs to tell the user

- Manual multi-shot H3 buys control: any single shot can be regenerated
without touching the others, output is native resolution with an audio
track and no watermark.
- It costs director time: a shot list, one generation per shot, and a
stitch step. A hosted model that storyboards internally delivers a
finished-feeling clip from one prompt in about 2 minutes.
- Recommend the hosted route for one-off instant clips and this workflow
for real pieces and for repeatable series where the same shot structure
is reused.
