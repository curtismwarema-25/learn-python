---
name: fuego-design
description: Use for Fuego frontend development, UI implementation, UX improvements, component creation or modification, visual redesign, responsive design, design-system maintenance, and interface reviews.
---

# Fuego design skill

The visual and interaction authority for Fuego's frontend. It does not define
product scope, API behavior, or architecture.

## Authority and boundaries

- Read relevant product requirements from
  [`docs/FUEGO_MASTER.md`](../../../docs/FUEGO_MASTER.md); consult relevant
  constraints in [`docs/TECHNICAL_BASELINE.md`](../../../docs/TECHNICAL_BASELINE.md)
  and any separately added architecture document.
- Verify current routes, components, styles, API behavior, and tests. A dated
  baseline or roadmap is not proof of current functionality.
- Keep implemented, explicitly approved in-progress, and future capabilities
  distinct. Do not design a future proposal as a working control or destination.
- Preserve existing behavior unless the task explicitly changes it.

## Use only the relevant references

| Work | Read |
| --- | --- |
| Routine component or layout work | [Design tokens](references/design-tokens.md), [component guidelines](references/component-guidelines.md) |
| Interaction, messages, or status | [Interaction patterns](references/interaction-patterns.md), plus component guidelines as needed |
| Responsive behavior | [Responsive guidelines](references/responsive-guidelines.md) |
| Accessibility | [Accessibility](references/accessibility.md) |
| New visual direction, brand, or screen | [Design philosophy](references/design-philosophy.md), [visual language](references/visual-language.md), and design tokens |
| Broad interface review | [Design review checklist](references/design-review-checklist.md) and only the applicable standards above |

Do not load every reference by default or follow reference links transitively.

## Workflow

1. Inspect the affected UI, existing patterns, relevant API/state, working-tree
   changes, and tests before editing.
2. Read the selected references and relevant product/technical requirements.
3. Reuse existing components and CSS tokens. Add no competing token set,
   dependency, or future feature without an approved need.
4. Preserve functional behavior; make statuses, errors, and controls truthful
   and accessible.
5. Run the smallest relevant tests and type/build checks. Check affected
   responsive states and keyboard interactions when applicable; use the review
   checklist for substantial UI work and report anything not verified.
6. Document approved permanent decisions in their canonical reference and
   check affected components for consistency.

## Canonical implementation

The current frontend is React and TypeScript with Vite and React Router.
Verify the source rather than relying on this snapshot. Shared visual tokens
are in `fuego/fuego-frontend/src/styles.css`; reuse existing system fonts and
primitives. Check the package scripts for validation commands. Do not add a
library for a small styling or interaction need.
