# Fuego design philosophy

## Product before appearance

Fuego is a conversation-first technology and learning platform. Its product
direction is Chat -> Community -> Knowledge -> Learning -> Creation, but the
current verified product is a chat application. The
[Fuego Product and Development Master](../../../../docs/FUEGO_MASTER.md) is the
source for product meaning and roadmap status. The
[Technical Baseline](../../../../docs/TECHNICAL_BASELINE.md) records verified
implementation; always check current source as well.

Design should make the working chat clear and useful now while allowing the
system to grow. It must not make a future proposal look like an implemented
destination. A coherent shell and reusable primitives are enough preparation;
placeholder sections, fake activity, and nonfunctional controls are not.

## Editorial Intelligence Interface

Fuego's direction is an **Editorial Intelligence Interface**: the clarity of a
well-edited publication applied to a capable digital workspace. The interface
should feel thoughtful and technically confident without demanding technical
fluency from a beginner.

Editorial means content has hierarchy, an intentional reading order, clear
attribution, and enough whitespace to be understood. Intelligence means the
interface brings relevant context forward and avoids noisy ornament. Neither
term authorizes an AI feature that the product does not implement.

## Reference synthesis

The references are sources of design principles, not templates:

- [BOC Studio](https://boc.studio/) contributes confident identity, visual
  energy, expressive presentation, and a willingness to use a strong accent.
  Its observed work index combines an orange band and navigation with
  image-led project groupings, differentiated type scale, and direct project
  actions. Motion and media should be used only when they help communicate
  content or state.
- [Haikoo Studio](https://haikoo.org/) contributes structure: a near-black
  canvas, precise alignment, thin rules, compact project metadata, restrained
  typography, and dense but orderly indexes. Its project navigation adapts to
  a compact control on mobile rather than simply shrinking the desktop index.

The observations above were made from the live pages on 2026-11-17. Live
content and behavior can change. Some BOC media requests were unavailable in
the browser session, so no claim is made about every animation or media
fallback. No reference screenshots are stored in this skill; do not fabricate
or copy screenshots. Revisit the original sites when a task depends on their
current behavior.

### Fuego's synthesis

- **BOC contributes the fire:** one confident orange identity, expressive
  editorial moments, and emphasis used with intent.
- **Haikoo contributes the discipline:** aligned grids, quiet surfaces,
  typographic restraint, thin separators, and compact metadata.
- **Fuego contributes its own purpose:** a human, accessible conversation
  space where people can ask, understand, and make progress together.

The working application is not a studio portfolio. Do not import project
galleries, marketing navigation, autoplay media, or showreel treatments into
routine workflows. Translate principles into functional product UI.

## Brand identity and working interface

Keep these related but distinct:

- **Brand identity:** wordmark, accent, voice, and occasional expressive
  moments. Use these to make Fuego recognizable.
- **Working interface:** conversation content, navigation, controls, status,
  and account access. Optimize these for legibility, focus, and predictable
  use.

The accent should identify the product and direct attention; it should not
become a background color for every control or content block. Expressive
typography belongs in a landing or section introduction, not in message text,
forms, or dense navigation.

## Visual restraint

1. Give each screen one clear primary action or content focus.
2. Use near-black, gray, and off-white to establish structure; reserve orange
   for active, important, or brand-specific details.
3. Prefer spacing and alignment to containers. Use a border only when it
   clarifies a boundary, input, or state.
4. Avoid default card grids, heavy shadows, gradients, glass effects, and
   excessive rounding.
5. Use animation sparingly and only to communicate a real transition.
6. Keep labels plain and understandable. Do not use editorial tone to obscure
   status, access, or error information.
7. Respect beginner confidence: precise does not mean cryptic or overly dense.

## Long-term direction without premature UI

The visual language must be able to support communities, reusable knowledge,
learning experiences, creation, and contextual AI-assisted work in the future.
Those are not current UI requirements by themselves. Add a new destination,
tool, or workflow only when it is approved and functional within the task.
Integrate future AI context into the relevant work rather than treating AI as
an unrelated collection of tools.

## Related standards

- [Visual language](visual-language.md)
- [Design tokens](design-tokens.md)
- [Component guidelines](component-guidelines.md)
- [Fuego Master Product Document](../../../../docs/FUEGO_MASTER.md)
