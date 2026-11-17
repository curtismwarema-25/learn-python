# Fuego agent-context optimization

## Audit findings

- The repository has one project-local skill, `fuego-design`, with eight
  focused references; there are no other `AGENTS.md` files, agent rule
  directories, or CI workflows.
- The current runtime did not list the repository skill among automatically
  available skills. Root `AGENTS.md` is therefore the observed discovery hook;
  activation should be explicit, not assumed.
- The root instructions and design skill repeated product authority, source
  verification, preservation, validation, and design governance. The skill
  also directed agents to load broad standards even for routine changes.
- The Master Product document is the roadmap authority; the Technical Baseline
  is a dated snapshot, not an architecture spec. No separate Master
  Architecture document was found.
- No validation wrapper existed. Frontend test/build and Django check,
  migration, and test commands already exist and are reused below.

## Changes made

- Replaced the root instructions with a task-to-context matrix. It selects the
  design skill only for frontend work and routes backend, database, AI,
  security, bug-fix, and test/release tasks to the smallest relevant sources.
- Condensed the design skill and added a direct reference-selection table.
  Agents are told not to load every design reference or follow links
  transitively.
- Added `scripts/validate-fuego.ps1`, a dependency-free orchestrator for the
  existing frontend tests/build, Django system/migration/chat checks, and
  `git diff --check`. `-Scope frontend`, `-Scope backend`, and `-Scope all`
  avoid running unrelated suites. The production build already performs the
  frontend TypeScript check, so the wrapper does not run it twice.
- No product rules, security requirements, architecture, application code, or
  dependencies were changed.

## Evaluation

- The entry instructions are shorter and only task-selected references should
  be loaded. This reduces routine context requests without removing the
  detailed design standards.
- Validation is reproducible with one command and selectors. It composes
  existing project tooling instead of duplicating checks.
- `scripts/validate-fuego.ps1 -Scope all` passed: 5 frontend tests, frontend
  typecheck/build, Django system and migration checks, 14 chat tests, and
  `git diff --check`. Local Markdown links and skill frontmatter also passed
  validation.
- Root instructions plus the design skill entry point decreased from 1,117 to
  671 whitespace-delimited words (446 fewer). This is a measured size proxy,
  not an actual model-token count; no token-saving percentage is claimed.
- No controlled representative-task comparison was available: the repository
  code and test coverage changed between prior Fuego tasks, and historical
  token/tool metrics cannot isolate the effect of this edit.

## Remaining limitations

- Skill discovery still depends on the agent honoring root `AGENTS.md`; agents
  that ignore repository instructions may not load it.
- The repository has no local backend, database, AI, or security skill. The
  routing table does not invent these; it uses relevant project documents and
  the environment's specialized security-review workflow when available.
- The Technical Baseline still contains a statement that WebSocket reconnect
  is unimplemented, which is stale relative to current frontend code. Verify
  source before relying on that snapshot; refreshing the baseline is separate
  documentation work.
- The validation wrapper was written for PowerShell and expects the project's
  `.venv` for backend checks. Existing `npm` and Django commands remain usable
  directly in environments where the wrapper or virtual environment is absent.
