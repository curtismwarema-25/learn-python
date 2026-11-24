# Fuego backend implementation audit

Reviewed 2026-11-17 against the modified workspace at `main` / `029a571`.
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
| Applications | `chat` and `community` are active product apps. Django contrib, DRF/token auth, Channels, CORS, Djoser, and `notifications` are installed. `notes` is an empty placeholder and is not installed or routed. |
| Data | Chat uses `ChatSession`, `ChatSessionMessage`, and `ChatSessionMember`; migrations `0002` and `0003` add uniqueness and chat invite lifecycle data. Community uses `Space`, `SpaceMembership`, `SpaceJoinRequest`, and `Channel`; `community/0001` and `0002` are pending on the tracked local database. |
| API | Djoser auth is under `/auth/`. Chat routes include creation, owner-managed membership and invites, and member-authorized message reads/writes. Community routes cover Space membership plus channel listing/management/messages; channel access is derived from active Space membership. |
| Serialization | The Community API uses DRF serializers for Space and channel contracts. Chat APIViews validate message fields and construct response data with `to_json`/`deserialize_user`. Chat user payloads now contain usernames only. |
| Access | DRF requires authentication by default. Direct-chat APIs exclude channel-backed sessions. Space channel REST access checks current Space membership; only owners/admins may manage channels and archived channels reject new messages. Separate chat invite tokens expire after seven days; joined members retain full history. |
| Real time | Separate Django Channels consumers authenticate a DRF token from the first WebSocket frame. Direct chat checks current chat access; channel traffic checks current Space membership before subscription and before events. The optional uWSGI/RabbitMQ bridge excludes channel-backed sessions but does not revalidate direct-chat access during delivery. The local Channels layer is in-memory; `uwsgi` is not installed from the standard requirements. |
| Background work | A Celery app is configured with eager execution, but no project task modules or broker setup were found. No background-job feature is implemented. |
| Database | SQLite is configured. An aggregate-only check found 4 chats, 0 membership rows, and no duplicate URIs or memberships. Chat migrations `0002`/`0003` and Community migrations `0001`/`0002` are pending on the tracked local database; the suite applies them to its test database. No user or message contents were inspected. |
| Frontend contract | React + TypeScript consumes usernames from chat user payloads. Email and legal names were removed from message, member, and live-event user objects with explicit approval. Invite links now use `/invites/{token}`; chat URIs remain resource identifiers. |
| Community contract | `/api/spaces/` exposes discoverable metadata only; authenticated routes cover Space membership, channel lifecycle, and member-only channel messages. Every Space receives `general`; the migration backfills existing Spaces. The frontend provides directory, management, and channel-message flows. |
| Configuration | `DEBUG=True`, empty `ALLOWED_HOSTS`, permissive CORS, and development secret configuration remain unsuitable for production. WebSocket tokens are no longer accepted from query strings. TLS, deployment, monitoring, backup, and recovery configuration remain unverified. |
| Quality | `chat/tests.py` covers auth, access controls, invite expiry/rotation/revocation, data minimization, message access, RabbitMQ publishing via a mock, and WebSocket behavior. `community/tests.py` covers Space roles and membership plus channel API permissions, direct-chat and bridge isolation, history lifecycle, and channel WebSockets. The final validation run passed 56 backend and 12 frontend tests. |

## Product-to-implementation comparison

| Capability | Master requirement and current status | Dependencies and architecture | Security/privacy | Priority |
| --- | --- | --- | --- | --- |
| Phase 1 chat foundation | Master §16 requires dependable auth, creation, invites, history, real-time messaging, understandable failures, and critical access tests. Chat flows, owner-managed seven-day invitations, and database uniqueness are implemented and covered by tests. | Keep the current Django modular monolith and REST/Channels boundaries. Migrations `0002` and `0003` must be applied in environments that use the new code. | Owner/member checks remain server-side. Invite tokens are separate from chat IDs, owner-only, expiring, and revocable. Existing members retain full history. Production settings and TLS remain unverified. | Highest: preserve and validate chat before Community schema work. |
| Phase 2 community | The approved Space foundation and shared Channels slice are implemented: default `general`, channel lifecycle, member-only history/send, and responsive navigation. Moderation/reporting and knowledge features remain unimplemented. | A dedicated `community` app preserves the modular monolith; `Channel` has one `ChatSession`, while current Space membership remains the authorization source at REST/WebSocket boundaries. Migrations `community/0001` and `0002` must be applied in environments that use the new code. | API and WebSocket tests cover role separation, member revocation, direct-chat isolation, and bridge exclusion. Detailed moderation/reporting policy remains open. | Proceed to knowledge lifecycle design only after its permissions and data boundaries are approved. |
| Phase 3 knowledge | Searchable discussions, saved/structured content, attribution, corrections, and links to conversations are proposed; none exist. | Depends on community foundations and a knowledge lifecycle/search design. | Preserve source access permissions; attribution and corrections are required considerations. | After Phase 2. |
| Phase 4 learning | Master §8 proposes `Learning hub -> Pathway -> Unit -> Lesson -> Activity`, with learning-by-doing. No learning models/API exist; `notes` is not a learning app. | Roadmap explicitly depends on Phases 2 and 3. Define content ownership, publication, versioning, and learner enrollment before schema work. | Content visibility, authorship, and progress access need server-side rules. | Defer until prerequisites and first pathway are validated. |
| Progress | Progress and knowledge checks appear in proposed Phase 4 capabilities; no progress records or endpoints exist. | Depends on stable learning content IDs and a validated completion/progress model. | Users must not read or alter another learner's progress. | With the learning MVP, not before it. |
| Practical AI/workflows | Workflow learning is proposed for Phase 5; a contextual companion is Phase 6. Neither is implemented. | Depends on evidence, learning/knowledge foundations, provider boundaries, and evaluation; no provider or execution infrastructure is justified now. | Define consent, retention, cost/rate controls, source handling, evaluation, and human review before sending user content to providers. Never execute generated code in Django. | Later phases only; no placeholder integration. |
| Security and operations | The Master requires permission boundaries and privacy; deployment requirements remain open. Chat payloads are minimized and WebSocket query-string tokens are removed, but local settings are development-only. | Production configuration, logging policy, rate limiting, database operations, and deployment architecture require separate decisions. | Revalidate token/account/member access before socket events. Idle sockets are closed on their next event after access changes; prompt idle disconnection would require a separate mechanism. | Track remaining operational risks before public deployment. |

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

## Approved chat security hardening

The owner approved these changes after reviewing the chat security findings:

- Chat user payloads now expose only `username`.
- Invite tokens are separate from stable chat URIs, owner-managed, and expire
  seven days after creation or rotation. Owners can rotate or revoke them;
  members cannot retrieve the token. Revocation prevents new joins but does not
  remove current members or their full-history access.
- The frontend joins through a dedicated invite route and submits the invite
  token in the request body, not the API URL.
- WebSocket tokens are sent in the first client frame, not the connection URL.
  The Channels consumer checks the token, active account, and membership
  before joining the group and before each inbound frame/outbound event. The
  optional uWSGI bridge also uses first-frame auth, excludes channel-backed
  sessions, but still checks direct-chat access only at connection time.
- Migration `0003_chatsession_invite_token_and_expiry.py` backfills existing
  chats with seven-day invite links. Both `0002` and `0003` remain unapplied on
  the tracked local database.

The API response shape for chat participants changed by approval. Existing
invite links based on the chat URI no longer grant membership; owners can get
new links from the conversation interface. The WebSocket transport still
requires HTTPS/WSS in deployment; this repository does not establish TLS
termination or production logging behavior.

The optional uWSGI bridge's per-event revalidation finding was separately
reported. The owner selected removal of its query-string token path; the
remaining revalidation change was not selected and is still open. uWSGI is not
installed locally, so bridge protocol validation uses a mock rather than a
live deployment.

## Community foundation and Channels milestone

The approved Space foundation and Channels slices are implemented in the
`community` Django app with migrations `0001_initial.py` and `0002_channel.py`,
DRF endpoints, role/ownership checks, channel-aware ASGI routing, frontend
routes and screens, and focused tests. The migrations are intentionally not
applied to the tracked local database. `scripts/validate-fuego.ps1 -Scope all`
passed with 56 backend tests and 12 frontend tests.

Structured knowledge, moderation reports, and AI remain deferred; no
placeholder functionality is presented. Remaining follow-up includes
production security, privacy, backup, and deployment requirements. The
optional uWSGI bridge excludes channels but still lacks per-event direct-chat
authorization revalidation; production TLS/WSS behavior has not been verified.

## Product completion audit refresh — 2026-11-24

This section reflects the current workspace after the knowledge lifecycle,
indexing, embedding foundation, and first learning MVP work. It supersedes the
older capability claims above where they conflict with current source.

| Product area | Classification | Current evidence and gap |
| --- | --- | --- |
| Direct chat and real-time messaging | IMPLEMENTED | Authenticated chat creation, invites, history, message sending, WebSocket delivery, access checks, and regression tests are connected. Presence, reactions, threading, and richer notification UX remain missing. |
| Spaces and channels | IMPLEMENTED | Space membership, roles, invitations, channel management, resources, search, message editing/deletion, and live updates are connected. Moderation/reporting remains missing. |
| Knowledge preservation | IMPLEMENTED | Explicit preservation, immutable versions, corrections, source revisions, soft deletion, withdrawal, source-deletion state, history, and permission-aware search are connected. |
| Knowledge indexing and embeddings | PARTIAL | Database chunks, lifecycle invalidation, deterministic local embeddings, provider contracts, vector candidates, durable job state, and Celery task entry points exist. External provider adapters, production broker/worker configuration, and user-facing semantic search remain deferred. |
| Learning pathways | IMPLEMENTED (MVP) | Authenticated users can discover and enroll in published pathways, read units/lessons, complete short-response activities, and retain private progress. Creator/staff authoring, draft/published/archived lifecycle, publication validation, lesson discussion links, and member question posting are now connected. Content versioning, richer checks, projects, and deletion workflows remain missing. |
| Practical AI and workflows | MISSING | No external AI provider, workflow editor, guided practical workspace, approval flow, or outcome comparison exists. |
| Creation and business workflows | MISSING | No social planning, marketing, sales, customer, project, or operations modules exist. |
| Platform operations | PARTIAL | Authentication and server-side access boundaries are tested. Production settings, rate limiting, observability, deployment, backups, and migration operations remain incomplete. |

### Milestone 2 — learning authoring, publication, and community integration

The learning domain now has a minimal authoring surface for pathway creators and
staff. Draft pathways can be edited with units, lessons, and short-response
activities, then published only after structural validation. Published pathways
can be archived without deleting enrollments or progress. The frontend exposes
the management route separately from learner discovery and includes loading,
error, and destructive-action confirmation states.

Lessons can link to an existing Space channel or source message. Learner-facing
links are filtered through current Space membership and deleted source messages
are excluded. Enrolled members can post a question through the lesson view;
the backend creates the ordinary channel message and records its lesson
attribution. No ordinary conversation is implicitly converted into learning
content.

This is intentionally not a full CMS: published content has no immutable
authoring revisions yet, lesson ordering is position-based, the first activity
kind is `short_response`, and there is no author delete endpoint.

### Major architectural inconsistencies

- The repository now contains the beginning of a learning domain, but content
  authoring and publication ownership are not yet modeled; seeded content is
  deliberately a bootstrap mechanism, not a complete CMS.
- Celery is configured for local eager execution and the embedding task is
  durable in code, but no production broker, worker supervision, or retry
  monitoring configuration is established.
- The local database vector store is suitable for deterministic preparation,
  not for production-scale semantic retrieval; it must remain behind the
  vector-store contract.
- Frontend navigation is functional but still primarily oriented around chat
  and Spaces; learning discovery is now available but not yet a broader
  workspace dashboard.

### Milestone 3 — non-AI product completion audit

The current repository verifies a usable vertical slice across chat, Spaces,
channels, knowledge preservation/lifecycle, indexing preparation, and learning
authoring/publication. Community moderation was the highest-value missing
non-AI slice: members can now report a channel message, duplicate reports are
prevented, and Space owners/administrators can review and resolve reports.
The frontend exposes reporting from the existing channel message actions.

The future AI requirements are documented separately in
[`FUEGO_AI_REQUIREMENTS.md`](./FUEGO_AI_REQUIREMENTS.md). They define provider
boundaries, permission-aware retrieval, attribution, human approval, privacy,
cost controls, and staged delivery, but do not authorize AI implementation.

| Capability | Classification | Current state | Value / next dependency | Priority |
| --- | --- | --- | --- | --- |
| Direct messaging and real-time communication | IMPLEMENTED | Authenticated chats, invites, history, REST/WebSocket access checks, and lifecycle tests exist. | Add richer presence, replies, and notification UX later. | Medium |
| Spaces, Channels, membership, roles, invitations | IMPLEMENTED | Space administration, membership lifecycle, channels, resources, and permission-aware search are connected. | Production operations and moderation policy refinement remain. | High |
| Message reporting and moderation review | IMPLEMENTED (MVP) | Members report messages; managers list and resolve reports with notes. | Add a dedicated moderation queue and automated notifications later. | High |
| Knowledge preservation and lifecycle | IMPLEMENTED | Explicit preservation, versions, corrections, withdrawal, source deletion, and traceability exist. | Organisation, categorisation, and richer reuse remain. | High |
| Learning authoring and publication | IMPLEMENTED (MVP) | Creator/staff authoring, publication validation, archive retention, progress, and discussion linkage exist. | Add immutable content revisions and richer activities. | High |
| Profiles and notification preferences | MISSING | No complete user-facing profile/settings workflow is present. | Needed for identity, preferences, and safer notification delivery. | High |
| Projects and task/work management | MISSING | No persistent projects, tasks, ownership, status, or collaboration workflow exists. | Main bridge from learning to practical creation; depends on product scope decisions. | Highest next product slice |
| Content planning, campaigns, sales, operations | MISSING | No bounded workflow modules exist. | Should follow a validated project/task foundation; do not build all domains at once. | Later |
| AI-powered features | DEFERRED | Requirements are documented only; existing embeddings remain indexing preparation. | Requires complete permissions, retrieval evaluation, privacy, and human-control gates. | Later |

### Selected implementation and remaining backlog

Message reporting was selected for this milestone because it directly improves
community safety, completes a member-to-manager workflow, and uses existing
Space authorization without introducing speculative infrastructure.

Remaining non-AI backlog, in order:

1. Build the project/task foundation: project workspace, owned tasks, status,
   assignment, due dates, and a usable member collaboration flow.
2. Add profiles and notification preferences, then connect moderation and
   learning events to user-controlled notifications.
3. Add immutable learning content revisions and safer published-content
   replacement while preserving progress.
4. Improve moderation with a Space-level queue, notifications, and documented
   enforcement actions.
5. Add categorisation and reuse workflows for resources and preserved
   knowledge.
6. Reassess the AI roadmap only after permission-aware retrieval and the above
   product foundations are validated.

### Prioritized implementation backlog

1. Build the project/task foundation as the next non-AI product slice.
2. Add profiles and notification preferences.
3. Add immutable learning content revisions and safe published-content
   replacement while preserving learner progress.
4. Complete semantic retrieval behind the existing vector-store interface,
   starting with a local similarity endpoint and explicit source citations.
5. Define and implement one validated practical workflow lesson with a human
   review/approval step; do not build autonomous agents.
6. Harden production operations: secure settings, rate limits, structured
   error handling, worker supervision, observability, backups, and migration
   deployment procedures.
7. Add richer learning activities and projects only after the first pathway is
   used and validated.

The next selected milestone is immutable learning content revisions or a local
semantic retrieval endpoint with explicit citations. Both must preserve the
current Space and knowledge access boundaries.
