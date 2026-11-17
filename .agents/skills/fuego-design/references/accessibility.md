# Fuego accessibility

Accessibility is a product requirement consistent with
[`docs/FUEGO_MASTER.md`](../../../../docs/FUEGO_MASTER.md). Apply WCAG 2.2 AA
as the target for frontend work; automated checks supplement, but do not
replace, keyboard and visual inspection.

## Keyboard navigation

- All actions must be operable by keyboard without a pointer.
- Preserve logical DOM and tab order; avoid positive `tabindex`.
- Use semantic links for navigation and buttons for actions.
- Ensure menus and dialogs, when actually needed, support expected keyboard
  operation and return focus appropriately.
- Do not trap focus in ordinary page content.

## Focus and contrast

- Provide a visible focus indicator on every interactive control.
- Essential text should meet at least 4.5:1 contrast for normal-size text and
  3:1 for large text. Controls and focus indicators should meet applicable
  non-text contrast requirements.
- Verify actual token pairs on their actual surfaces; do not assume muted gray
  or orange combinations pass for small text.
- Do not use color alone to identify an active route, error, permission, or
  sender.
- Preserve browser zoom and reflow; do not disable scaling.

## Screen-reader semantics

- Use one main landmark per page, appropriate navigation landmarks, a logical
  heading hierarchy, and meaningful page titles.
- Associate every input with a persistent accessible label. A placeholder
  alone is insufficient.
- Give icon-only buttons accessible names; hide decorative icons from the
  accessibility tree.
- Use live regions selectively. Announce new messages or meaningful status
  changes without repeatedly reading the entire conversation.
- Use `role="alert"` for important errors and status semantics for loading
  where appropriate. Ensure error text is also visible.

## Controls and touch

- Prefer a 44 by 44 CSS pixel target for frequently used touch controls.
- Where a compact control is necessary, provide adequate spacing and do not
  place small targets tightly together.
- Ensure disabled, busy, selected, and invalid states are programmatically
  exposed, not just visually styled.
- Avoid hover-only actions and gestures without an equivalent control.

## Motion and content

- Respect `prefers-reduced-motion: reduce`.
- Do not use flashing, continuous motion, or animation as the only way to
  communicate a state.
- Use plain language, preserve text zoom, and avoid dense all-caps or
  low-contrast body copy.
- Render user-supplied conversation content safely as text.

## Verification

For affected work, combine semantic/component tests with browser checks for
keyboard focus, contrast-sensitive states, responsive reflow, and reduced
motion. Report any known accessibility gap rather than claiming an automated
pass proves full conformance.
