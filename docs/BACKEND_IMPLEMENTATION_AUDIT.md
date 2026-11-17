# Fuego backend implementation audit

Reviewed 2026-11-17 against the modified workspace at `main` / `a55a4f8`.
This is a repository and local-development audit, not a production assessment
or formal security review. Product capabilities in the Master are not
automatically implementation commitments. Product requirements below are
distinguished from technical recommendations.

## Guidance and evidence

- Product authority: relevant requirements and priorities in
  [`FUEGO_MASTER.md`](FUEGO_MASTER.md), especially §§5–8, 13–17.
- Technical evidence: current Django source, dependency manifests, migrations,
  database migration state, API/frontend use, and tests; the dated
  [`TECHNICAL_BASELINE.md`](TECHNICAL_BASELINE.md) was cross-checked against
  current source.
- Python engineering: the available Python fact-grounded guidance and
  Pylance-selected interpreter/import facts were used.
- No separate Architecture Guardian, backend, security/privacy, or QA guidance
  files/skills were found in this repository or the current agent skill list.
  Relevant architecture and security requirements in the Master and baseline
  were used instead. This is not a penetration test.

## Verified backend baseline

| Area | Current evidence |
| --- | --- |
| Runtime | Selected project interpreter is Python 3.13.17. Installed direct backend versions are Django 6.1.3, DRF 3.18.0, django-cors-headers 4.9.0, Djoser 2.3.5, django-notifs 4.0.0, Channels 4.3.2, Daphne 4.2.3, Pika 1.3.2, and Celery 5.5.3; they match `fuego/requirements.txt`. The optional `uwsgi` import is unresolved and is not declared there. |
| Applications | `chat` is the active product app. Django contrib, DRF/token auth, Channels, CORS, Djoser, and `notifications` are installed. `notes` is an empty placeholder and is not installed or routed. |
| Data | `ChatSession` has a protected owner and URI; `ChatSessionMessage` has protected user/chat foreign keys and a 2,000-character limit; `ChatSessionMember` connects users to chats. The implementation adds unique URI and per-chat membership constraints in migration `0002`. |
| API | Djoser auth is under `/auth/`. Chat routes are `POST /api/chats/`, owner-only `PATCH /api/chats/{uri}/`, `POST /api/chats/{uri}/join/`, and member-authorized `GET`/`POST /api/chats/{uri}/messages/`. This milestone changes no endpoint or response shape. |
| Serialization | There are no DRF serializer classes. APIViews read `request.data`, validate message fields in the view, and construct response data with `to_json`/`deserialize_user`. |
| Access | DRF requires authentication by default. Message reads/writes and WebSocket admission check owner or membership; only the owner may add members. Possession of an invite URI currently permits joining; the intended invite policy remains an explicit product decision. |
| Real time | Django Channels routes authenticated sockets through a custom DRF-token middleware and the chat consumer. The local layer is in-memory. RabbitMQ publishing and a uWSGI bridge are optional/experimental; `uwsgi` is not installed from the standard requirements. |
| Background work | A Celery app is configured with eager execution, but no project task modules or broker setup were found. No background-job feature is implemented. |
| Database | SQLite is configured. All existing chat migrations were applied before this change. An aggregate-only check found 4 chats, 0 membership rows, and no duplicate URIs or memberships. Migration `0002` is intentionally not applied to the tracked local database; the suite applies it to its test database. No user or message contents were inspected. |
| Frontend contract | React + TypeScript consumes username, message, and ID fields; it does not use email or names from chat user payloads. The backend currently includes email and first/last names in serialized user objects, including message/real-time payloads; changing that response requires an explicit compatibility decision. |
| Configuration | `DEBUG=True`, empty `ALLOWED_HOSTS`, permissive CORS, development secret configuration, and query-string WebSocket tokens are not production settings. No deployment, monitoring, backup, or recovery setup was established. |
| Quality | `chat/tests.py` covers auth, access controls, joins, messages, RabbitMQ publishing via a mock, and WebSockets. The new tests assert database uniqueness. Validation commands are listed in the Technical Baseline and composed by `scripts/validate-fuego.ps1`. |

## Product-to-implementation comparison

| Capability | Master requirement and current status | Dependencies and architecture | Security/privacy | Priority |
| --- | --- | --- | --- | --- |
| Phase 1 chat foundation | Master §16 requires dependable auth, creation, invites, history, real-time messaging, understandable failures, and critical access tests. Most flows exist and are tested; the database previously allowed duplicate invite URIs and duplicate membership rows. This change adds both constraints. | Keep the current Django modular monolith and REST/Channels boundaries. Migration `0002` must be applied in environments that use the new code. | Preserve owner/member checks. Invite-by-URI policy is open. Query-string tokens and non-production settings remain deployment risks. | Highest: preserve chat and enforce its relational invariants. |
| Phase 2 community | Proposed spaces, membership, descriptions, roles, onboarding, moderation, and discovery are not implemented. | Depends on Phase 1 and decisions about the initial community and permissions. Do not infer a community schema from the roadmap alone. | Moderation, reporting, blocking, visibility, and roles need explicit policy. | After chat acceptance and product decisions. |
| Phase 3 knowledge | Searchable discussions, saved/structured content, attribution, corrections, and links to conversations are proposed; none exist. | Depends on community foundations and a knowledge lifecycle/search design. | Preserve source access permissions; attribution and corrections are required considerations. | After Phase 2. |
| Phase 4 learning | Master §8 proposes `Learning hub -> Pathway -> Unit -> Lesson -> Activity`, with learning-by-doing. No learning models/API exist; `notes` is not a learning app. | Roadmap explicitly depends on Phases 2 and 3. Define content ownership, publication, versioning, and learner enrollment before schema work. | Content visibility, authorship, and progress access need server-side rules. | Defer until prerequisites and first pathway are validated. |
| Progress | Progress and knowledge checks appear in proposed Phase 4 capabilities; no progress records or endpoints exist. | Depends on stable learning content IDs and a validated completion/progress model. | Users must not read or alter another learner's progress. | With the learning MVP, not before it. |
| Practical AI/workflows | Workflow learning is proposed for Phase 5; a contextual companion is Phase 6. Neither is implemented. | Depends on evidence, learning/knowledge foundations, provider boundaries, and evaluation; no provider or execution infrastructure is justified now. | Define consent, retention, cost/rate controls, source handling, evaluation, and human review before sending user content to providers. Never execute generated code in Django. | Later phases only; no placeholder integration. |
| Security and operations | The Master requires permission boundaries and privacy; deployment requirements remain open. Current auth/access checks are present, but settings are development-only and query tokens expose a sensitive transport choice. | Production configuration, logging policy, rate limiting, database operations, and deployment architecture require separate decisions. | Do not expose this configuration publicly; review token logging and minimize user data in response payloads. | Track before public deployment; payload minimization needs an API decision. |

## Technical recommendations

These are engineering recommendations, not additional product requirements:

- Keep the Django modular monolith and DRF/Channels API boundaries. Avoid new
  infrastructure or app domains until their product dependencies are met.
- Use DRF serializers for new request/response contracts so field validation
  and exposure are explicit. Do not refactor existing API payloads without a
  compatibility plan.
- Keep ownership and membership authorization server-side and back
  concurrency-sensitive invariants with database constraints.
- Apply migrations through deployment/local setup procedures; do not treat
  generated migration files as evidence that an existing database was updated.

## First milestone selected and implemented

The highest-priority sufficiently specified backend work was database
enforcement of existing chat identity invariants:

- `ChatSession.uri` is now unique at the database level.
- `(ChatSessionMember.chat_session, ChatSessionMember.user)` is now unique.
- Migration `0002_alter_chatsession_uri_and_more.py` adds both constraints.
- Tests cover each constraint through actual database inserts. Existing
  `get_or_create` membership paths remain unchanged.
- No API endpoints, response shapes, authentication rules, or product
  destinations changed.

The local database had no conflicting duplicates, so the migration is
well-defined for this checkout. It was not applied to the tracked database to
avoid modifying local data; run migrations in the intended environment.

## Decisions and follow-up

1. Decide whether possession of a chat URI is the intended invite/access
   policy.
2. Decide whether chat participants should receive peers' email and legal
   names. The current frontend only needs usernames, but changing existing
   payloads without an API compatibility decision would be unsafe.
3. Complete Phase 0 demonstrations and product validation before creating
   Community, Knowledge, or Learning schemas. In particular, Phases 2 and 3
   are dependencies of the proposed learning hierarchy.
4. Define production security, privacy, backup, and deployment requirements
   before public release.
