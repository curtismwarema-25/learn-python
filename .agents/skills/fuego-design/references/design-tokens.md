# Fuego design tokens

This is the single documentation source for shared visual values. The
implemented CSS source of truth is
[`fuego/fuego-frontend/src/styles.css`](../../../../fuego/fuego-frontend/src/styles.css),
in its `:root` block. Keep documentation and CSS aligned when an approved
permanent decision changes.

## Canonical implemented tokens

The current CSS values match the proposed Fuego palette. Preserve these values
unless an explicit design decision changes them.

| CSS variable | Value | Use |
|---|---|---|
| `--background` | `#08090a` | Application canvas |
| `--surface` | `#101214` | Functional surface and input background |
| `--surface-raised` | `#181b1e` | Small, distinct elevated surface |
| `--text-primary` | `#f3f3f3` | Essential text |
| `--text-secondary` | `#85898d` | Supporting text |
| `--text-muted` | `#60656a` | Nonessential metadata; check contrast before use |
| `--border` | `#272a2d` | Standard separator |
| `--accent` | `#ff4421` | Brand and primary interaction |
| `--accent-hover` | `#ff6045` | Hover state for the primary accent |

These are semantic roles. Use the CSS variable rather than repeating its
literal value in component rules.

## CSS variable conventions

- Define shared tokens once in `:root` in `src/styles.css`.
- Use semantic names such as `--text-secondary`, not names tied to a page or
  component.
- Use an existing token when its meaning matches. Do not create aliases for
  the same color or parallel tokens in component files.
- Add a token only for a recurring, approved need. Give it one canonical
  value, document it here, and migrate affected uses consistently.
- Keep truly local one-off values rare. The current stylesheet contains a few
  local contour, focus, and notice colors; do not treat them as alternate
  palette choices. When a value becomes shared, promote it to a semantic
  token and update this table.
- Do not define a second token file or replace the existing CSS system with a
  new framework as part of routine feature work.

## Typography

The current base stack is `Inter, "Helvetica Neue", Arial, sans-serif`;
`--font-mono` is `"SFMono-Regular", Consolas, "Liberation Mono", monospace`.
Inter is a preferred installed-font match, not a bundled asset. Preserve
system fallbacks and avoid a network font dependency unless approved.

Typography roles currently used in the interface:

| Role | Guidance |
|---|---|
| Display | Responsive, expressive page introduction; use sparingly |
| Section heading | Compact and clear; moderate weight |
| Body | Readable conversation and explanatory text |
| Metadata | Small monospace labels; nonessential only |

The CSS does not yet expose a complete size scale as custom properties. Do
not invent competing scale definitions. When a permanent scale is approved,
define semantic variables in `:root`, map existing roles to them, and update
this document.

## Spacing

The implemented 4px-based spacing variables are:

| Variable | Value |
|---|---:|
| `--space-1` | `4px` |
| `--space-2` | `8px` |
| `--space-3` | `12px` |
| `--space-4` | `16px` |
| `--space-6` | `24px` |
| `--space-8` | `32px` |

Prefer these for shared layout and component spacing. Fluid layout gaps may
use `clamp()` where the layout requires it. Do not add missing numbered steps
or another scale without an approved repeated use.

## Borders, radii, and elevation

- Standard border: `--border`, one pixel.
- `--radius-small`: `2px`.
- `--radius-medium`: `4px`.
- Use the smallest radius that supports the control's purpose.
- The current system has no shadow/elevation token. Prefer no shadow; use
  surface contrast and a border. Do not introduce a shadow scale without a
  repeated, approved need.

## Transitions and motion

- `--transition-fast`: `140ms ease`.
- Use it only for short state feedback such as hover or focus.
- Motion must be optional, purposeful, and reduced under
  `prefers-reduced-motion: reduce`.
- Do not add a motion library for small CSS transitions.

## Breakpoints

Current source breakpoints are `900px`, `640px`, and `360px`. Use them as the
existing responsive convention: compact desktop/tablet adaptation, mobile
layout transition, and very narrow-device adjustments. Add a breakpoint only
when content behavior demonstrably needs one; update this reference if the
canonical thresholds change.

## Contrast caution

Do not assume every text token is suitable for every background. Use primary
or secondary text for essential information, and verify actual foreground /
background pairs. Muted text is for low-priority metadata only and must not
carry instructions, errors, or required labels.

## Related references

- [Visual language](visual-language.md)
- [Accessibility](accessibility.md)
- [Design philosophy](design-philosophy.md)
