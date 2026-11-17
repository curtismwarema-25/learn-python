# Fuego responsive guidelines

Adapt behavior to available space; do not simply scale a desktop screen down.
Use the existing breakpoints documented in
[design tokens](design-tokens.md) unless a tested content need justifies a
change.

## Desktop: wider than 900px

- Use the available width for a stable navigation rail and flexible content.
- Preserve a comfortable message reading measure rather than stretching text
  across a wide monitor.
- Keep the composer close to the conversation and within the primary workflow.
- Do not fill spare space with decorative cards or unimplemented destinations.

## Tablet: 641px to 900px

- Reduce shell and content gutters before compressing text.
- Keep navigation labels and primary actions visible and operable.
- Avoid side-by-side panels when they make the conversation or composer too
  narrow.
- Let secondary details wrap or move below primary content.

## Mobile: 360px to 640px

- Prioritize the conversation, message history, and composer.
- Replace or reorganize desktop navigation rather than hiding the only way to
  reach working routes or actions.
- Keep primary actions comfortable to tap; aim for 44 by 44 CSS pixels.
- Keep the composer visible and usable when the on-screen keyboard opens.
- Avoid fixed-width columns, hover-dependent actions, and horizontal scrolling.
- Preserve the reading order and do not truncate essential status or errors.

## Very narrow screens: 320px to 359px

- Recheck button labels, input width, and long usernames or conversation
  identifiers.
- Allow nonessential metadata to wrap or move; do not shrink body text to
  illegibility.
- Test that the page has no horizontal overflow.

## Responsive validation

Check at least one wide desktop, tablet, standard mobile, and narrow mobile
width. Verify more than the landing page: inspect affected chat, authentication,
loading/error, and navigation states. Check document width against viewport
width and test keyboard access at each materially different layout.
