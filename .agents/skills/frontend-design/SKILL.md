---
name: frontend-design
description: Create distinctive, production-grade frontend interfaces with high design quality. Use this skill when the user asks to build web components, pages, artifacts, posters, or applications (examples include websites, landing pages, dashboards, React components, HTML/CSS layouts, or when styling/beautifying any web UI). Generates creative, polished code and UI design that avoids generic AI aesthetics.
license: Complete terms in LICENSE.txt
---

This skill guides creation of distinctive, production-grade frontend interfaces that avoid generic "AI slop" aesthetics. Implement real working code with exceptional attention to aesthetic details and creative choices.

The user provides frontend requirements: a component, page, application, or interface to build. They may include context about the purpose, audience, or technical constraints.

## Design Thinking

Before coding, understand the context and commit to a BOLD aesthetic direction:
- **Purpose**: What problem does this interface solve? Who uses it?
- **Tone**: Pick an extreme: brutally minimal, maximalist chaos, retro-futuristic, organic/natural, luxury/refined, playful/toy-like, editorial/magazine, brutalist/raw, art deco/geometric, soft/pastel, industrial/utilitarian, etc. There are so many flavors to choose from. Use these for inspiration but design one that is true to the aesthetic direction.
- **Constraints**: Technical requirements (framework, performance, accessibility).
- **Differentiation**: What makes this UNFORGETTABLE? What's the one thing someone will remember?

**CRITICAL**: Choose a clear conceptual direction and execute it with precision. Bold maximalism and refined minimalism both work - the key is intentionality, not intensity.

Then implement working code (HTML/CSS/JS, React, Vue, etc.) that is:
- Production-grade and functional
- Visually striking and memorable
- Cohesive with a clear aesthetic point-of-view
- Meticulously refined in every detail

## Frontend Aesthetics Guidelines

When doing frontend design tasks, avoid generic, overbuilt layouts. Use these hard rules inspired by industry best practices to ensure high-quality design:

- **One composition**: The first viewport must read as one composition, not a dashboard (unless it's a dashboard).
- **Brand first**: On branded pages, the brand or product name must be a hero-level signal, not just nav text or an eyebrow. No headline should overpower the brand.
- **Brand test**: If the first viewport could belong to another brand after removing the nav, the branding is too weak.
- **Typography**: Use expressive, purposeful fonts and avoid default stacks (Inter, Roboto, Arial, system). Pair a distinctive display font with a refined body font.
- **Background**: Don't rely on flat, single-color backgrounds; use gradients, images, or subtle patterns to build atmosphere.
- **Full-bleed hero only**: On landing pages and promotional surfaces, the hero image should be a dominant edge-to-edge visual plane or background by default. Do not use inset hero images, side-panel hero images, rounded media cards, tiled collages, or floating image blocks unless the existing design system clearly requires it.
- **Hero budget**: The first viewport should usually contain only the brand, one headline, one short supporting sentence, one CTA group, and one dominant image. Do not place stats, schedules, event listings, address blocks, promos, "this week" callouts, metadata rows, or secondary marketing content in the first viewport.
- **No hero overlays**: Do not place detached labels, floating badges, promo stickers, info chips, or callout boxes on top of hero media.
- **Cards**: Default: no cards. Never use cards in the hero. Cards are allowed only when they are the container for a user interaction. If removing a border, shadow, background, or radius does not hurt interaction or understanding, it should not be a card.
- **One job per section**: Each section should have one purpose, one headline, and usually one short supporting sentence. Structure the page as a narrative (Hero -> Context -> Detail -> Proof -> CTA).
- **Real visual anchor**: Imagery should show the product, place, atmosphere, or context. Decorative gradients and abstract backgrounds do not count as the main visual idea.
- **Reduce clutter**: Avoid pill clusters, stat strips, icon rows, boxed promos, schedule snippets, and multiple competing text blocks.
- **Motion**: Use motion to create presence and hierarchy, not noise. Ship at least 2-3 intentional motions for visually led work. Focus on high-impact moments like a well-orchestrated page load rather than scattered micro-interactions.
- **Color & Look**: Choose a clear visual direction; define CSS variables; avoid purple-on-white defaults. No purple bias or dark mode bias.
- **Spatial Composition**: Unexpected layouts. Asymmetry. Overlap. Diagonal flow. Grid-breaking elements. Generous negative space OR controlled density.
- **Responsiveness**: Ensure the page loads properly on both desktop and mobile. Keep fixed or floating UI elements from overlapping text, buttons, or other key content across screen sizes. Place them in safe areas.

## Content & Tooling

- **Ground in real content**: Use real copy, product context, and clear goals. The design should utilize structurally meaningful narratives and believable messaging over placeholder patterns.
- **Visual References**: When available, rely on uploaded visual references or mood boards to inform layout rhythm, typography scale, spacing systems, and imagery treatment. 
- **Image Generation**: Default to using any uploaded/pre-generated images. Otherwise use the image generation tool to create visually stunning image artifacts. Do not reference or link to web images unless the user explicitly asks for them.

## Technical Implementation

- **React Code**: Prefer modern patterns including `useEffectEvent`, `startTransition`, and `useDeferredValue` when appropriate if used by the team. Do not add `useMemo`/`useCallback` by default unless already used; follow the repo's React Compiler guidance.
- **Existing Systems**: *Exception:* If working within an existing website or design system, preserve the established patterns, structure, and visual language.

## Summary & Creative Output

Interpret creatively and make unexpected choices that feel genuinely designed for the context. No design should be the same. Vary between light and dark themes, different fonts, different aesthetics. NEVER converge on common choices (e.g. Space Grotesk, SaaS cookie-cutter styling) across generations.

**IMPORTANT**: Match implementation complexity to the aesthetic vision. Maximalist designs need elaborate code with extensive animations and effects. Minimalist or refined designs need restraint, precision, and careful attention to spacing, typography, and subtle details. Elegance comes from executing the vision well.

Remember: You are capable of extraordinary creative work. Don't hold back, show what can truly be created when thinking outside the box, dialing in the perfect amount of reasoning, and committing fully to a distinctive vision.
