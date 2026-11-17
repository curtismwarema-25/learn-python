# Fuego Technical Baseline

| Field | Value |
|---|---|
| Status | Verified repository snapshot; not a production-readiness assessment |
| Reviewed | 2026-11-17 |
| Repository reference | Branch `main`, base commit `029a571`; this update is uncommitted |
| Scope | Django backend, React frontend, configuration, tests, and tracked project files |

This document records what was verified in the repository and local development
environment on the review date. It distinguishes implemented behavior from
untested paths and future product ideas. It should be refreshed after material
code, dependency, or configuration changes.

## 1. Executive summary

Fuego is a Django REST backend and React + TypeScript frontend. The implemented
product includes direct chat and Community Spaces with shared channels: users
can create private Spaces, discover public metadata, request or accept
membership, manage roles and invitations, and participate in Space channel
conversations. Knowledge, learning, and AI workflow capabilities remain
unimplemented.

The checkout does **not** implement the remaining broader product described in
the [Fuego master](./FUEGO_MASTER.md), including reusable knowledge, learning
pathways, or AI workflow features. The `notes` directory is only a placeholder.

The capability-by-capability comparison and selected backend milestone are in
the [Fuego backend implementation audit](./BACKEND_IMPLEMENTATION_AUDIT.md).

The default configuration is for local development. Production hosting,
security configuration, multi-process real-time delivery, data backup and
recovery, and operational support have not been demonstrated. Do not treat
this repository as production-ready on the basis of these tests.

## 2. Evidence and scope

### Evidence labels

- **Verified:** found in current source, manifests, or tracked files.
- **Tested:** exercised by a command listed in this document on the review date.
- **Review needed:** a source-level concern or unvalidated path; not a claim of
  an observed production incident.
- **Unknown:** not established by this repository review.

### Snapshot reference

- Application source was inspected at `main` / `029a571` and the modified
  local workspace. Findings include the uncommitted changes described here
  and are not a claim about the base commit alone.
- Database row contents were not inspected. An aggregate-only check found
  four chat sessions, no membership rows, and no duplicate chat URIs or
  memberships.
- This was a repository and local-test review, not a penetration test,
  dependency vulnerability assessment, load test, or production deployment
  review.

## 3. Stack and local environment

### Backend

The backend is a Django project with:

- Python **3.13.17** in the local environment used for checks.
- Django **6.1.3**.
- Django REST Framework **3.18.0** and Djoser **2.3.5** for API and account
  endpoints.
- Django Channels **4.3.2** and Daphne **4.2.3** for ASGI and WebSockets.
- `django-notifs` **4.0.0** for message notifications.
- SQLite as the configured database.
- Pika **1.3.2** and Celery **5.5.3** as declared dependencies.

The pinned backend dependencies are listed in
[`fuego/requirements.txt`](../fuego/requirements.txt).

### Frontend

The frontend is a Vite single-page application using React, TypeScript, and
React Router. The local installed versions observed on the review date were:

- React and React DOM **19.3.1**.
- React Router DOM **7.18.5**.
- TypeScript **7.0.2**.
- Vite **7.3.8** and Vitest **4.1.12**.
- Bootstrap **5.3.9**.

The frontend dependency declarations and lockfile are in
[`fuego/fuego-frontend/package.json`](../fuego/fuego-frontend/package.json)
and `package-lock.json`. The frontend runs type checking before producing its
Vite build.

### Runtime and data flow

1. The browser serves the frontend through Vite during local development.
2. The frontend sends HTTP requests to the same hostname on port `8000`.
3. Django serves authentication and chat REST endpoints.
4. The ASGI application routes direct-chat WebSockets and Space-channel
   WebSockets to separate consumers.
5. Consumers authenticate the DRF token from the first WebSocket frame. Direct
   chat checks chat membership; Space channels check current Space membership
   before joining the group and recheck authorization before frames and events.
6. Message creation publishes a notification to the default Channels layer.

The default channel layer is `InMemoryChannelLayer`. It is appropriate for a
single local server process, not shared delivery across multiple server
processes. The optional uWSGI/RabbitMQ bridge is separately configured and
excluded from channel-backed sessions; its direct-chat delivery loop does not
revalidate access after connection.

## 4. Implemented behavior

### Authentication

- Djoser authentication URLs are mounted under `/auth/`.
- The frontend supports account registration and username/password sign-in.
- DRF token authentication is used by the frontend for authenticated API
  requests.
- The frontend stores the token and username in browser `sessionStorage`.
- The UI redirects unauthenticated visitors to `/auth` and returns them to a
  requested chat path after sign-in.

Relevant implementation:
[`fuego/fuego/urls.py`](../fuego/fuego/urls.py),
[`fuego/fuego-frontend/src/components/UserAuth.tsx`](../fuego/fuego-frontend/src/components/UserAuth.tsx).

### Chat API and access rules

| Method and path | Verified behavior |
|---|---|
| `POST /api/chats/` | Authenticated user creates a chat and receives its URI; a seven-day invite is created. |
| `PATCH /api/chats/{uri}/` | Chat owner adds a user by username. |
| `GET /api/chats/{uri}/invite/` | Chat members can check invite-management availability; only the owner receives the active token. |
| `POST /api/chats/{uri}/invite/` | Owner rotates the invite; the prior link is invalidated and the new link expires after seven days. |
| `DELETE /api/chats/{uri}/invite/` | Owner revokes the active invite; existing members keep their access. |
| `POST /api/chats/invites/join/` | Authenticated visitor submits an invite token in the request body and joins the chat. |
| `GET /api/chats/{uri}/messages/` | Owner or member reads that chat's messages. |
| `POST /api/chats/{uri}/messages/` | Owner or member sends a non-empty message up to 2,000 characters. |
| `WS /ws/chats/{uri}/` | Client authenticates with `{"type":"authenticate","token":"…"}` as its first frame; the token is not accepted from the URL. |
| `GET /api/spaces/{id}/channels/` | Active Space member lists its channels. |
| `POST /api/spaces/{id}/channels/` | Space owner/admin creates a channel. |
| `GET/PATCH/DELETE /api/spaces/{id}/channels/{channel_id}/` | Active member reads channel metadata; owner/admin edits, archives, restores, or deletes only an empty channel. |
| `GET/POST /api/spaces/{id}/channels/{channel_id}/messages/` | Active Space member reads channel history or sends a message; archived channels are read-only. |
| `WS /ws/spaces/{id}/channels/{channel_id}/` | First-frame token authentication; current Space membership is verified before subscription and delivery. |

The message API returns all messages for a chat; pagination is not implemented.
Chat identifiers and invite tokens are separate. New invitation links use
`/invites/{token}` in the frontend and are managed by the owner. Invites expire
after seven days; rotating or revoking one prevents future joins but does not
remove existing members. Joined members retain access to the full chat history.
The `uri` alone no longer grants membership.

The REST API defaults to authenticated access. Message reads and writes also
check chat ownership or membership and explicitly exclude channel-backed
conversations. The owner-only member-add operation rejects other users.
WebSocket authentication, token activity, account activity, and direct-chat
membership are checked before delivery on the default Channels path.
Space-channel authorization is based on current Space membership, not
`ChatSession.owner` or `ChatSessionMember`. The optional uWSGI bridge excludes
channel sessions but checks direct-chat access at connection time only.

Relevant implementation:
[`fuego/chat/urls.py`](../fuego/chat/urls.py),
[`fuego/chat/views.py`](../fuego/chat/views.py),
[`fuego/chat/consumers.py`](../fuego/chat/consumers.py),
[`fuego/chat/routing.py`](../fuego/chat/routing.py),
[`fuego/chat/websocket.py`](../fuego/chat/websocket.py),
[`fuego/chat/migrations/0003_chatsession_invite_token_and_expiry.py`](../fuego/chat/migrations/0003_chatsession_invite_token_and_expiry.py).

### Data model

The `chat` app defines:

- `ChatSession`: owner, generated URI, separate nullable invite token and
  expiry, and create/update timestamps.
- `ChatSessionMember`: user-to-chat membership and timestamps.
- `ChatSessionMessage`: user, chat, message text, and timestamps.

The project uses Django's built-in user model. The checked-in initial chat
migration creates the three chat models.

Migration `0002_alter_chatsession_uri_and_more.py` enforces database uniqueness
for chat URIs and `(chat_session, user)` membership pairs. Migration
`0003_chatsession_invite_token_and_expiry.py` adds separate invite fields and
backfills existing chats with seven-day invite links. Both migrations are
pending on the tracked local database; apply them before using this code with
that database.

The `community` app defines `Space`, `SpaceMembership`, `SpaceJoinRequest`,
`Channel`, `Resource`, and `ResourceReference`. A Channel has a one-to-one
`ChatSession` for message storage and notifications, and a per-Space unique
slug. A Resource is currently an external link with title and description;
uploaded files and private media storage are not implemented. A
ResourceReference links a channel message to a Resource. The Space owner is
stored directly on `Space`; other active members have one of the
Administrator, Moderator, or Member roles. Spaces are private by default,
with optional metadata-only discovery. Space content, channel messages,
resources, member rosters, requests, and invitation tokens are protected by
server-side checks.

New Spaces receive a default `general` channel. The Channels data migration
backfills existing Spaces. Channel history is preserved by archiving; channel
and Space deletion are blocked when relevant message history exists. Space
links support metadata search, creator/moderator/manager lifecycle controls,
and deletion tombstones that preserve existing channel references. Link
references are created atomically with channel messages and are not exposed
through direct-chat APIs. Community migrations `0001`, `0002`, and `0003` are
pending on the tracked local database, as are chat migrations `0002` and
`0003`. The `0002_channel` data migration is intentionally irreversible to
avoid orphaning channel conversations if rolled back.

Relevant implementation:
[`fuego/chat/models.py`](../fuego/chat/models.py),
[`fuego/chat/migrations/0001_initial.py`](../fuego/chat/migrations/0001_initial.py),
[`fuego/chat/migrations/0002_alter_chatsession_uri_and_more.py`](../fuego/chat/migrations/0002_alter_chatsession_uri_and_more.py).
Community implementation:
[`fuego/community/models.py`](../fuego/community/models.py),
[`fuego/community/views.py`](../fuego/community/views.py),
[`fuego/community/consumers.py`](../fuego/community/consumers.py),
[`fuego/community/migrations/0001_initial.py`](../fuego/community/migrations/0001_initial.py),
[`fuego/community/migrations/0002_channel.py`](../fuego/community/migrations/0002_channel.py),
[`fuego/community/migrations/0003_resource_resourcereference.py`](../fuego/community/migrations/0003_resource_resourcereference.py).

### Frontend

The app defines `/auth`, `/`, `/chats/:uri`, `/invites/:inviteToken`,
`/spaces`, `/spaces/:spaceId`, `/spaces/:spaceId/resources`,
`/spaces/:spaceId/resources/:resourceId`,
`/spaces/:spaceId/channels/:channelId`, and
`/spaces/invites/:inviteToken` routes. It supports registration/sign-in, direct
chat, a Space directory and creation, join requests, membership and channel
management, invite joining, channel messages, link-resource management,
resource references in channel messages, and WebSocket updates. The API
helper validates response shapes before components use them.

The frontend assumes the Django server is available on port `8000`; that
address is constructed in
[`fuego/fuego-frontend/src/api.ts`](../fuego/fuego-frontend/src/api.ts).
Dropped WebSockets now use bounded automatic retries, a manual retry after
exhaustion, and message-history synchronization after reconnection.

### Not implemented

- Uploaded files/private media storage, content moderation/reporting,
  private/restricted channels, and separate structured discussion models.
- Text extraction from linked resources, source-eligibility controls, and
  semantic/vector search. The link library's metadata search is not RAG.
- A searchable knowledge base or reusable discussion content.
- Learning hubs, pathways, lessons, activities, or progress tracking.
- AI provider integrations or workflow-learning features.
- A substantive `notes` application. The folder contains placeholder files
  and is not included in `INSTALLED_APPS` or the root URL configuration.

## 5. Configuration and local development

### Observed configuration

- Django uses `fuego/db.sqlite3` as its database.
- `DEBUG` is enabled, `ALLOWED_HOSTS` is empty, and a development-marked
  secret key is hard-coded in `fuego/settings.py`. The key value is
  intentionally not reproduced here.
- CORS is configured to allow all origins.
- DRF authentication classes include token, session, and basic authentication;
  the default permission class is `IsAuthenticated`.
- The default channel layer is in-memory.
- RabbitMQ publishing is disabled unless `CHAT_RABBITMQ_ENABLED` is set.
- `CELERY_TASK_ALWAYS_EAGER` is enabled. A Celery app is configured, but no
  application task modules or broker configuration were found in the tracked
  project files.
- The optional RabbitMQ/uWSGI WebSocket bridge is separate from the default
  local setup. `uwsgi` is not listed in the standard Python requirements.

### Local startup

From the repository root, the documented Windows setup is:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\fuego\requirements.txt
.\.venv\Scripts\python.exe .\fuego\manage.py migrate
npm --prefix .\fuego\fuego-frontend install
npm --prefix .\fuego\fuego-frontend run dev:all
```

The combined command starts Django on port `8000` and Vite on port `5173`.
This is a local-development workflow, not a production deployment procedure.

## 6. Tests and verification

Commands were run on **2026-11-17** in the local environment.

| Check | Result |
|---|---|
| `python manage.py check` | **Passed:** no system-check issues. |
| `python manage.py makemigrations --check --dry-run` | **Passed:** no model changes detected that require a migration. |
| `python manage.py test chat community` | **Passed:** 62 backend tests, including resource role/visibility rules, tombstones, channel references, direct-chat isolation, and WebSocket delivery. |
| Frontend `npm run typecheck` | **Passed.** |
| Frontend `npm test` | **Passed:** 13 tests, including channel history, message sending/deduplication, archived-channel behavior, and resource workflows. |
| Frontend `npm run build` | **Passed:** TypeScript check and Vite production build. |
| `scripts/validate-fuego.ps1 -Scope all` | **Passed:** frontend tests (13), TypeScript/production build, Django system checks, migration consistency, backend tests (62), and Git whitespace check. |
| Browser/device accessibility review | **Partial:** the resource library was visually inspected with fixture data at desktop and mobile widths. Full 320px, keyboard, screen-reader, reduced-motion, and WCAG conformance reviews remain outstanding. |

Run backend checks from the repository root with an explicit app label:

```powershell
.\.venv\Scripts\python.exe .\fuego\manage.py check
.\.venv\Scripts\python.exe .\fuego\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe .\fuego\manage.py test chat community
```

Running `manage.py test` from the repository root **without** an app label
reported zero tests. Do not treat that invocation as evidence that the backend
suite passed.

Run frontend checks from its directory:

```powershell
Push-Location .\fuego\fuego-frontend
npm run typecheck
npm test
npm run build
Pop-Location
```

Backend tests cover registration/token login, ownership and membership
permissions, invite joining, message access, database uniqueness, direct-chat
isolation, Space channel and Resource permissions, resource tombstones and
references, and WebSocket access/delivery. The RabbitMQ publisher test mocks
the connection; it does not validate a live RabbitMQ/uWSGI deployment.
Frontend tests cover authentication, chat/reconnect, Spaces, link-resource
management, and channel message references.

These automated checks do not establish that the full stack has been manually
walked through in a browser, that real-time delivery works across multiple
processes, or that deployment and operations are ready.

## 7. Security and operational findings

These are source-level findings and mitigations, not a formal security audit.

| Priority | Finding | Status / next verification |
|---|---|---|
| Blocker for public deployment | Development settings enable `DEBUG`, use a hard-coded development-marked key, leave `ALLOWED_HOSTS` empty, and allow all CORS origins. | **Verified.** Introduce and validate a separate production configuration before deployment; do not expose the development key. |
| Medium | WebSocket authentication uses the first client frame rather than the URL; the browser selects `wss:` only when the page/API uses HTTPS. | **Query-string transport removed and tested.** Production TLS termination and logging configuration remain unverified; require HTTPS/WSS in deployment. |
| Medium | Chat user objects previously included email and legal names. | **Mitigated.** Message, member, and live-event user objects now expose only usernames; this approved response-shape change may affect external consumers. |
| Medium | Existing sockets previously retained access after token or membership changes. | **Mitigated on the default Channels path.** Token validity, account activity, and chat membership are rechecked before delivery. An idle socket remains open until its next event, per the approved policy. |
| Medium | Optional uWSGI bridge does not revalidate direct-chat access after connection. | **Open.** Channel-backed sessions are excluded. For direct chats, first-frame token authentication is implemented and query-string auth removed, but this bridge still needs token/account/member checks before each forwarded event. uWSGI is unavailable locally; the protocol is covered only by mocked tests. |
| Medium | Chat URIs previously doubled as durable join secrets. | **Mitigated in source.** Separate owner-managed invite tokens expire after seven days and can be rotated or revoked. Existing members retain access and history; invite links remain bearer links until expiry or revocation. |
| High | The default in-memory channel layer is process-local. | **Verified.** Multi-worker or multi-instance message delivery is not established; select and test a shared channel layer before scaling. |
| High | SQLite is the configured database and the database file is tracked. | **Verified.** Row contents were not inspected; only aggregate counts and duplicate checks were run. Decide how user data is protected, backed up, restored, and kept out of source control. |
| Medium | CORS allows all origins; DRF also enables Basic and Session authentication. | **Verified.** Reassess allowed origins and authentication methods for the intended deployment and transport. |
| Medium | No DRF throttling configuration was found. | **Verified in settings.** Define abuse/rate controls appropriate to public registration, login, and message endpoints. |
| Medium | Chat history has no pagination; channel history also reuses the unpaginated message store. | **Verified in source.** Chat migrations `0002`/`0003` and Community migrations `0001`/`0002`/`0003` are pending on the tracked local database; apply them before using this database with the updated models. Review history volume before expansion. |
| Medium | The RabbitMQ/uWSGI bridge depends on separately provisioned services and is outside the standard local setup. | **Verified in source and setup docs; not live-tested.** Treat as experimental until deployment and failure behavior are exercised. |
| Low | Tracked files include Python bytecode caches and pre-access-control source snapshots. | **Verified in the tracked-file inventory.** Decide on repository hygiene separately; ensure snapshot files are not mistaken for active code. |

The repository review found no tracked CI workflow, container/orchestration
manifest, or production deployment manifest. Hosting, TLS termination,
monitoring, alerting, log retention, backup/recovery procedures, privacy
operations, and incident response remain **unknown**.

## 8. Phase 0 status and next checks

This baseline satisfies the documentation/inventory deliverable for Phase 0
of the [master roadmap](./FUEGO_MASTER.md), but it does not complete all Phase 0
acceptance criteria.

Before calling Phase 0 complete:

1. Manually demonstrate registration/sign-in, chat creation, invite joining,
   message history, message sending, and live updates in the local app.
2. Demonstrate that a non-member cannot read messages, send messages, or open
   the WebSocket, and that only the owner can add members.
3. Demonstrate that invite tokens expire, owner rotation/revocation works, old
   URI-only joins are rejected, and revocation does not remove existing members.
4. The founder has selected non-technical aspiring technology learners who
   are new to hands-on AI and want to learn by making. The founder's current
   learning hypothesis is to explain simply how data is used to build or adapt
   a model and how a trained model turns input into output, then help learners
   narrow a broad problem into a practical use and tangible project. Validate
   the first problem, sequence, and outcome through conversations; this
   repository review does not establish user need.
5. Decide how database and generated artifacts should be handled in version
   control, without deleting or exposing existing user data.
6. Track the production-security and operational unknowns above before any
   public deployment.

No broad rewrite is supported by this evidence. Preserve the current chat
foundation while validating its reliability and intended invite/permission
behavior.

## 9. Source map

- Project setup and product direction: [`README.md`](../README.md).
- Product roadmap and proposed capabilities: [`FUEGO_MASTER.md`](./FUEGO_MASTER.md).
- Django settings and URL routing: [`settings.py`](../fuego/fuego/settings.py),
  [`urls.py`](../fuego/fuego/urls.py).
- Chat models, API, and WebSockets: [`models.py`](../fuego/chat/models.py),
  [`views.py`](../fuego/chat/views.py), [`consumers.py`](../fuego/chat/consumers.py),
  and migration [`0003_chatsession_invite_token_and_expiry.py`](../fuego/chat/migrations/0003_chatsession_invite_token_and_expiry.py).
- Backend tests: [`tests.py`](../fuego/chat/tests.py).
- Frontend setup and scripts: [`package.json`](../fuego/fuego-frontend/package.json),
  [`fuego-frontend README`](../fuego/fuego-frontend/README.md).
