# Component guidelines

Use the shared tokens in [design-tokens.md](design-tokens.md) and the visual
rules in [visual-language.md](visual-language.md). Before creating a
component, search the current frontend for an existing implementation or
pattern.

## Application shell

- Keep the working area focused on implemented tasks.
- Provide clear brand identity, primary navigation, contextual content, and
  account context where supported by existing functionality.
- Keep shell behavior consistent across signed-in pages; let content vary.
- A shell is an extensible frame, not a reason to create future feature
  destinations.
- Use semantic landmarks and keep exactly one main landmark per screen.

## Navigation and sidebar

- Show only routes and actions that work in the current product.
- Keep the active destination visible with more than color alone, such as a
  marker and accessible current-page state.
- Use compact labels and consistent alignment. Do not sacrifice touch size or
  keyboard access for density.
- Do not show disabled "coming soon" items as a substitute for approved
  functionality.
- The current backend exposes chat-by-URI routes, not a conversation-list
  endpoint. Do not fabricate recent conversations or a searchable history.
  Introduce a conversation list only when a real data source and behavior
  exist.

## Conversation list

There is no current conversation index API. If one is approved and implemented,
design list items around real titles or useful identifiers, clear active state,
keyboard navigation, and a real new-conversation action. Add search and
management only when those actions are supported. Include empty, loading, and
failure states. Never use hard-coded sample conversations as live content.

## Messages

- Give messages a readable width and clear sender attribution.
- Keep decoration light. Use alignment, author labels, and restrained rules or
  surface changes instead of a large rounded card for every message.
- Preserve line breaks and safely render text as text; do not interpret
  untrusted message content as HTML.
- Distinguish sender roles using text and more than color alone.
- The current implementation supports user/peer messages, not an AI
  assistant. Do not label a peer as an assistant or add assistant-only
  controls until a real assistant behavior is approved and implemented.
- Add contextual actions only when their corresponding operation exists and
  is keyboard and touch accessible.

## Message composer

- Keep the composer adjacent to the conversation and easy to reach.
- Preserve visible focus, clear placeholder/label, disabled and sending
  states, and a reliable submit action.
- Respect the current API's 2,000-character message limit.
- Do not add attachment, microphone, file context, task assistance, or AI
  controls before their behavior and API contracts exist.
- Do not make keyboard shortcuts the only way to send or edit a message.

## Buttons and icon buttons

- Use a clear primary action and secondary action hierarchy.
- Keep concise verbs and explicit busy/disabled states.
- Ensure icon-only buttons have an accessible name and visible focus.
- Avoid using the primary orange accent for every button.

## Inputs

- Give every input an accessible label; placeholder text is not a label.
- Show focus, invalid, disabled, and submission states.
- Keep validation messages adjacent to their control and connected to it when
  practical.
- Preserve browser autocomplete semantics for authentication fields.

## Menus, dialogs, and tooltips

- Add them only when a real action or information need requires them.
- Support keyboard entry, focus movement, dismissal, and return of focus.
- A tooltip must not be the only source of essential information and must not
  require hover alone.
- Do not create a menu or modal as a visual placeholder for future settings.

## Empty, loading, and notification states

- Empty states should describe the actual state and offer one relevant,
  functional next action where possible.
- Loading states must be truthful, concise, and not imply success before data
  arrives.
- Keep errors explicit, preserve the user's context, and use an accessible
  announcement such as `role="alert"` for actionable failures.
- Distinguish an API failure from a real-time/WebSocket failure.
- Do not use success-shaped fallbacks or fake data to make an empty screen look
  populated.

## Cards, borders, and containers

Use a card only when it groups a distinct task or object. Prefer alignment and
whitespace for ordinary content. Use a border for a meaningful boundary,
control, or state; avoid enclosing each message, paragraph, or list row in a
separate panel. Avoid decorative shadows and unnecessary nested containers.

## Related references

- [Interaction patterns](interaction-patterns.md)
- [Accessibility](accessibility.md)
- [Design review checklist](design-review-checklist.md)
