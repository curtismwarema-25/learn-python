# Fuego design review checklist

Use this checklist before considering frontend work complete. Mark each item
as checked, not applicable, or an explicit follow-up.

## Product and function

- [ ] Does this match the approved product scope and the Fuego product master?
- [ ] Are implemented, under-development, and future capabilities clearly
      distinguished?
- [ ] Were existing routes, authentication, API behavior, permissions, and
      real-time behavior preserved?
- [ ] Do all visible controls do what their labels imply?
- [ ] Are loading, empty, error, and success states truthful and useful?

## Brand and visual language

- [ ] Does the result feel like Fuego: expressive identity with disciplined,
      editorial structure?
- [ ] Is orange used selectively for brand, focus, or important interaction?
- [ ] Are typography, color, spacing, border, and radius choices consistent
      with the canonical tokens?
- [ ] Are hierarchy, alignment, and whitespace intentional?
- [ ] Were unnecessary cards, shadows, gradients, decoration, and new colors
      avoided?

## Components and interaction

- [ ] Was an existing component or pattern reused where appropriate?
- [ ] Are component states consistent with existing buttons, inputs, messages,
      notices, and navigation?
- [ ] Are hover, focus, active, disabled, and busy states clear?
- [ ] Can key interactions be completed by keyboard and touch?
- [ ] If a new reusable pattern was introduced, is its guidance documented?

## Responsive and accessible behavior

- [ ] Were desktop, tablet, mobile, and narrow-screen layouts checked where
      relevant?
- [ ] Is there no unintended horizontal overflow?
- [ ] Are touch targets and composer placement practical on mobile?
- [ ] Are labels, landmarks, headings, status, and errors accessible?
- [ ] Is focus visible and are essential color pairs contrast-checked?
- [ ] Does motion respect reduced-motion preferences?

## Performance and verification

- [ ] Were unnecessary dependencies, media, fonts, and animations avoided?
- [ ] Were affected tests, type checks, and builds run?
- [ ] Were important browser flows and failure states inspected when available?
- [ ] Are known gaps or unvalidated behavior reported accurately?
