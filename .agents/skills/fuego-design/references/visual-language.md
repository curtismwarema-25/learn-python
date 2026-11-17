# Fuego visual language

This reference describes how to apply the canonical
[design tokens](design-tokens.md). It is subordinate to product and
architecture requirements.

## Colour hierarchy

Use the established hierarchy:

1. Near-black background for the application environment.
2. Dark surfaces for functional grouping and inputs.
3. Off-white primary text for essential content.
4. Secondary gray for supporting copy.
5. Muted gray for nonessential metadata only.
6. Fuego orange for brand, active, focus, and important action states.

Use the shared CSS custom properties; do not add another palette. Do not rely
on color alone to convey selection, error, success, or permission. Error and
warning notices must retain explicit text and semantic roles.

## Typography

The current system stack starts with Inter and falls back to Helvetica Neue,
Arial, and sans-serif. Use the existing stack and monospace metadata token.
Do not silently load a remote font or add a font dependency.

- Use clear, moderate-weight headings with controlled tracking.
- Keep working conversation text comfortable to read and left aligned.
- Use compact uppercase monospace for short labels, IDs, and metadata only.
- Differentiate a display introduction from ordinary workflow headings.
- Avoid all-caps body copy, long runs of monospace, and overly light essential
  text.
- Use line height and width to support reading; do not shrink body text to
  fit a dense layout.

The current stylesheet has no complete type scale expressed as custom
properties. Follow the established component roles and actual usage before
adding sizes. If a shared type scale is approved, centralize it in the existing
root token block and update [design tokens](design-tokens.md).

## Composition and alignment

- Establish one dominant content column and a clear relationship to the shell.
- Align headings, reading content, actions, and separators to a consistent
  edge.
- Keep conversation text to a comfortable reading measure; let the composer
  remain easy to reach.
- Use density for navigation and metadata, not to compress messages or forms.
- Avoid centering routine working content when left alignment improves scanning.
- Use a brand motif sparingly and never let it compete with actual content.

The current desktop shell uses a fixed-width sidebar and flexible main column;
tablet and mobile layouts change that relationship. Treat those as responsive
starting points, not fixed requirements for every future page.

## Grid and spacing

Use the spacing values documented in
[design tokens](design-tokens.md). Prefer the existing 4px-based scale and
consistent alignment. Fluid sizing is appropriate for content width and
display type, but do not introduce a new arbitrary spacing system for one
screen.

Use responsive grids only when the content benefits from parallel comparison.
Do not create a grid of cards just to represent roadmap areas or fill empty
space.

## Borders and surfaces

- A one-pixel border is the default separator.
- Use a surface change to distinguish a real functional group, such as a
  composer, input, or sidebar.
- Keep radii small and purposeful. Circular avatars and status dots are
  exceptions for those forms, not a general component style.
- Avoid shadows and gradients by default. Elevation should be conveyed by
  contrast and boundaries.
- Do not put every message, paragraph, or navigation item inside a card.

## Iconography

Use the project's existing icon treatment if one exists. Prefer a small,
consistent set of simple icons with accessible names for icon-only controls.
Do not use emoji as interface icons or introduce an icon library for a handful
of controls. Never make an icon the only indication of an important action or
state.

## Visual hierarchy and whitespace

Hierarchy should answer, in order: where am I, what is important here, what
can I do, and what happened. Use size, weight, alignment, spacing, and color
in that order; avoid multiple competing accents.

Whitespace is structural. Use it to separate tasks, establish a reading
rhythm, and let messages breathe. Remove empty decorative space if it pushes
the composer or essential conversation content out of reach.

## Reference relationships

- [Design philosophy](design-philosophy.md)
- [Component guidelines](component-guidelines.md)
- [Responsive guidelines](responsive-guidelines.md)
