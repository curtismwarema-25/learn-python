# Fuego agent instructions

## Product and technical authority

- Read only the relevant sections of [`docs/FUEGO_MASTER.md`](docs/FUEGO_MASTER.md)
  for product scope, requirements, and roadmap status. Treat proposed work as
  unimplemented unless the task approves it and current code verifies it.
- Read relevant sections of [`docs/TECHNICAL_BASELINE.md`](docs/TECHNICAL_BASELINE.md)
  when implementation constraints or verified behavior matter; check current
  source because the baseline is a dated snapshot.
- No separate Master Architecture document was found in the repository. Do not
  infer its contents; report an undocumented architecture decision when it
  blocks the task.

## Select context by task

| Task | Load |
| --- | --- |
| Frontend, UI, UX, or visual review | `.agents/skills/fuego-design/SKILL.md`; then only its task-relevant references and relevant product/technical sections. |
| Backend, API, or real-time work | Relevant product/technical sections, current implementation, and affected tests. Do not load the design skill unless the interface changes. |
| Database or schema work | Relevant product/technical sections, models, migrations, and tests. |
| AI integration | Product Master sections 9–11, 14–15, current data/API boundaries, and privacy/security requirements. Implement only explicitly approved scope. |
| Bug fix or refactor | Affected source and tests plus only the applicable product/technical guidance; load design skill only for interface changes. |
| Security review | Use the environment's dedicated security-review workflow and inspect current source. Do not substitute a general bug fix or design review for a security review. |
| Testing or release preparation | Run checks for changed areas; use `scripts/validate-fuego.ps1` for the full repository validation. |

The repository-local skill is stored only at `.agents/skills/fuego-design/`.
Do not assume it was automatically loaded: explicitly read its `SKILL.md`
when the task-selection table calls for it. Use other agent-provided skills
only when their activation conditions match.
