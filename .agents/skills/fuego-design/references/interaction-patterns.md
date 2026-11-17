# Fuego interaction patterns

Interactions should be predictable, purposeful, and quiet. Follow
[component guidelines](component-guidelines.md) and
[accessibility](accessibility.md).

## Hover, focus, and active states

- Hover may add a restrained color, border, or surface change to an actionable
  element.
- Every hover behavior must have an equivalent keyboard focus treatment.
- Use a persistent active/current state for the selected route or tab.
- Do not use hover-only content to expose an essential action or label.
- Keep focus visible and distinct from hover; do not remove the browser outline
  without providing a stronger replacement.

## Navigation

- Prefer the routing and link conventions already used by the application.
- Keep route changes direct and preserve the intended return path through
  authentication.
- A transition may use the existing short timing token, but must not delay
  access to the destination or imply loading where none exists.
- Do not add navigation interactions to a future or unavailable route.

## Messages and real-time updates

- Present a newly accepted message once, even if it is received through both
  the send response and the real-time channel; preserve the existing
  identifier-based deduplication.
- Preserve chronological reading order, sender attribution, and scroll access.
- Announce new messages politely without moving focus or re-announcing the
  entire history.
- Communicate WebSocket errors separately from message send/load errors.
- Do not add typing indicators, read receipts, reactions, editing, or streaming
  behavior unless the product and backend support them.

## Composer

- Keep submit behavior available by button and keyboard.
- Disable duplicate sends while a request is pending and show concise busy
  feedback.
- Clear the draft only after a successful response; preserve it on failure.
- Keep the current message length and API contract intact.
- Do not imply file attachment or AI context is available when it is not.

## Loading and feedback

- Use a clear loading status for the task in progress.
- Do not display a permanent "live", "connected", or "saved" indicator unless
  the state is actually known.
- Keep feedback near the affected content and make failures recoverable where
  the existing behavior allows.

## Micro-interactions and motion

- Use `--transition-fast` for brief hover/focus feedback.
- Animate a component only when motion explains a real state change.
- Avoid continuous marquee, parallax, animated backgrounds, cursor effects,
  and repeated message entrance animations in working conversation views.
- If an expressive brand motion is approved, keep it short, nonessential, and
  disabled or reduced by `prefers-reduced-motion: reduce`.
- Never make motion necessary to understand status or complete a task.
