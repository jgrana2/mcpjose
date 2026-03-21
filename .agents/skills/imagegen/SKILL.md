---
name: "imagegen"
description: "Use when the user asks to generate or edit images (for example: generate image, edit/inpaint/mask, background removal or replacement, transparent background, product shots, concept art, covers, or batch variants). Use the `mcpjose_generate_image` tool to perform the generation."
---


# Image Generation Skill

Generates or edits images for the current project (e.g., website assets, game assets, UI mockups, product mockups, wireframes, logo design, photorealistic images, infographics). Uses the `mcpjose_generate_image` tool, which leverages Gemini.

## When to use
- Generate a new image (concept art, product shot, cover, website hero)
- Edit an existing image (inpainting, masked edits, transformations, background replacement)

## Decision tree (generate vs edit)
- If the user provides an input image (or says “edit/retouch/inpaint/mask/translate/localize/change only X”) → **edit** (pass `image_path` to the tool)
- Else → **generate** (use only `prompt` and `output_path`)

## Workflow
1. Decide intent: generate vs edit (see decision tree above).
2. Collect inputs up front: prompt(s), exact text (verbatim), constraints/avoid list, and any input image(s). 
3. Augment prompt into a short labeled spec (structure + constraints) without inventing new creative requirements.
4. Call the `mcpjose_generate_image` tool with the appropriate `prompt`, and optionally `output_path` and `image_path`.
5. For complex edits/generations, inspect outputs and validate: subject, style, composition, text accuracy, and invariants/avoid items.
6. Iterate: make a single targeted change (prompt or input image), re-run, re-check.
7. Save/return final outputs and note the final prompt used.

## Temp and output conventions
- Use `tmp/imagegen/` for intermediate files.
- Write final artifacts under `output/imagegen/` when working in this repo.
- Use the `output_path` parameter to control output paths; keep filenames stable and descriptive.

## Defaults & rules
- Assume the user wants a new image unless they explicitly ask for an edit.
- Use the `mcpjose_generate_image` tool for all generations and edits.
- If the result isn’t clearly relevant or doesn’t satisfy constraints, iterate with small targeted prompt changes; only ask a question if a missing detail blocks success.

## Prompt augmentation
Reformat user prompts into a structured, production-oriented spec. Only make implicit details explicit; do not invent new requirements.

## Use-case taxonomy (exact slugs)
Classify each request into one of these buckets and keep the slug consistent across prompts.

Generate:
- photorealistic-natural — candid/editorial lifestyle scenes with real texture and natural lighting.
- product-mockup — product/packaging shots, catalog imagery, merch concepts.
- ui-mockup — app/web interface mockups that look shippable.
- infographic-diagram — diagrams/infographics with structured layout and text.
- logo-brand — logo/mark exploration, vector-friendly.
- illustration-story — comics, children’s book art, narrative scenes.
- stylized-concept — style-driven concept art, 3D/stylized renders.
- historical-scene — period-accurate/world-knowledge scenes.

Edit:
- text-localization — translate/replace in-image text, preserve layout.
- identity-preserve — try-on, person-in-scene; lock face/body/pose.
- precise-object-edit — remove/replace a specific element (incl. interior swaps).
- lighting-weather — time-of-day/season/atmosphere changes only.
- background-extraction — transparent background / clean cutout.
- style-transfer — apply reference style while changing subject/scene.
- compositing — multi-image insert/merge with matched lighting/perspective.
- sketch-to-render — drawing/line art to photoreal render.

Template (include only relevant lines):
```
Use case: <taxonomy slug>
Asset type: <where the asset will be used>
Primary request: <user's main prompt>
Scene/background: <environment>
Subject: <main subject>
Style/medium: <photo/illustration/3D/etc>
Composition/framing: <wide/close/top-down; placement>
Lighting/mood: <lighting + mood>
Color palette: <palette notes>
Materials/textures: <surface details>
Quality: <low/medium/high/auto>
Input fidelity (edits): <low/high>
Text (verbatim): "<exact text>"
Constraints: <must keep/must avoid>
Avoid: <negative constraints>
```

Augmentation rules:
- Keep it short; add only details the user already implied or provided elsewhere.
- Always classify the request into a taxonomy slug above and tailor constraints/composition/quality to that bucket. 
- If the user gives a broad request (e.g., "Generate images for this website"), use judgment to propose tasteful, context-appropriate assets and map each to a taxonomy slug.
- For edits, explicitly list invariants ("change only X; keep Y unchanged").
- If any critical detail is missing and blocks success, ask a question; otherwise proceed.

## Prompting best practices (short list)
- Structure prompt as scene -> subject -> details -> constraints.
- Include intended use (ad, UI mock, infographic) to set the mode and polish level.
- Use camera/composition language for photorealism.
- Quote exact text and specify typography + placement.
- For tricky words, spell them letter-by-letter and require verbatim rendering.
- For multi-image inputs, reference images by index and describe how to combine them.
- For edits, repeat invariants every iteration to reduce drift.
- Iterate with single-change follow-ups.
- If results feel “tacky”, add a brief “Avoid:” line (stock-photo vibe; cheesy lens flare; oversaturated neon; harsh bloom; oversharpening; clutter) and specify restraint (“editorial”, “premium”, “subtle”).
