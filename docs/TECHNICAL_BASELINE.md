# Fuego Technical Baseline

| Field | Value |
|---|---|
| Status | Verified repository snapshot; not a production-readiness assessment |
| Reviewed | 2026-11-17 |
| Repository reference | Branch `main`, commit `49e4058` |
| Scope | Django backend, React frontend, configuration, tests, and tracked project files |

This document records what was verified in the repository and local development
environment on the review date. It distinguishes implemented behavior from
untested paths and future product ideas. It should be refreshed after material
code, dependency, or configuration changes.

## 1. Executive summary

Fuego is currently a small chat application with a Django REST backend and a
React + TypeScript frontend. It supports account registration and token login,
creating a chat, joining via a shareable URI, reading and sending messages, and
receiving real-time updates over WebSockets.

The current checkout does **not** implement the broader product described in
the [Fuego master](./FUEGO_MASTER.md): there are no implemented community
spaces, reusable knowledge system, learning pathways, or AI workflow features.
The `notes` directory is only a placeholder.

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

- Application source was inspected at `main` / `49e4058`.
- The working tree was not clean: `README.md` and
  `fuego/fuego-frontend/README.md` were modified, and `docs/` was untracked at
  the start of this review. This baseline describes the local checkout and is
  not a claim that those documentation changes are committed.
- The review did not inspect the contents of the tracked SQLite database.
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
4. The ASGI application routes WebSocket connections through token
   authentication and the chat consumer.
5. The consumer checks that the authenticated user owns or belongs to the
   requested chat before accepting the connection.
6. Message creation publishes a notification to the default Channels layer.

The default channel layer is `InMemoryChannelLayer`. It is appropriate for a
single local server process, not shared delivery across multiple server
processes.

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
[`fuego/chat/auth.py`](../fuego/chat/auth.py),
[`fuego/fuego-frontend/src/components/UserAuth.tsx`](../fuego/fuego-frontend/src/components/UserAuth.tsx).

### Chat API and access rules

| Method and path | Verified behavior |
|---|---|
| `POST /api/chats/` | Authenticated user creates a chat and receives its URI. |
| `PATCH /api/chats/{uri}/` | Chat owner adds a user by username. |
| `POST /api/chats/{uri}/join/` | Authenticated visitor joins the chat associated with the URI. |
| `GET /api/chats/{uri}/messages/` | Owner or member reads that chat's messages. |
| `POST /api/chats/{uri}/messages/` | Owner or member sends a non-empty message up to 2,000 characters. |
| `WS /ws/chats/{uri}/?token=...` | Active owner or member connects for real-time updates. |

The message API returns all messages for a chat; pagination is not implemented.
An authenticated user with a chat URI can join through the join endpoint. The
frontend calls this endpoint when opening a chat invite.

The REST API defaults to authenticated access. Message reads and writes also
check chat ownership or membership. The owner-only member-add operation rejects
other users. WebSocket connections apply a corresponding membership check.

Relevant implementation:
[`fuego/chat/urls.py`](../fuego/chat/urls.py),
[`fuego/chat/views.py`](../fuego/chat/views.py),
[`fuego/chat/consumers.py`](../fuego/chat/consumers.py),
[`fuego/chat/routing.py`](../fuego/chat/routing.py).

### Data model

The `chat` app defines:

- `ChatSession`: owner, generated URI, and create/update timestamps.
- `ChatSessionMember`: user-to-chat membership and timestamps.
- `ChatSessionMessage`: user, chat, message text, and timestamps.

The project uses Django's built-in user model. The checked-in initial chat
migration creates these three models. No learning, community, or knowledge
models were found in the active app configuration.

**Review needed:** the checked-in model and migration do not declare a
database uniqueness constraint for chat URIs or for `(chat_session, user)`
membership pairs. Application code uses `get_or_create` for memberships, but
the database does not enforce uniqueness under concurrent requests.

Relevant implementation:
[`fuego/chat/models.py`](../fuego/chat/models.py),
[`fuego/chat/migrations/0001_initial.py`](../fuego/chat/migrations/0001_initial.py).

### Frontend

The app defines `/auth`, `/`, and `/chats/:uri` routes. It supports
registration/sign-in, starting a chat, joining an invite, loading messages,
sending messages, and displaying WebSocket updates and errors. The API helper
validates several response shapes before components use them.

The frontend assumes the Django server is available on port `8000`; that
address is constructed in
[`fuego/fuego-frontend/src/api.ts`](../fuego/fuego-frontend/src/api.ts).
Reconnect behavior for dropped WebSockets is not implemented.

### Not implemented

- Community spaces, roles, moderation, or discovery.
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
| `python manage.py test chat` | **Passed:** 14 backend tests. |
| Frontend `npm run typecheck` | **Passed.** |
| Frontend `npm test` | **Passed:** 2 tests in 1 test file. |
| Frontend `npm run build` | **Passed:** TypeScript check and Vite production build. |

Run backend checks from the repository root with an explicit app label:

```powershell
.\.venv\Scripts\python.exe .\fuego\manage.py check
.\.venv\Scripts\python.exe .\fuego\manage.py makemigrations --check --dry-run
.\.venv\Scripts\python.exe .\fuego\manage.py test chat
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
permissions, invite joining, message access, and WebSocket access/delivery. The
RabbitMQ publisher test mocks the connection; it does not validate a live
RabbitMQ/uWSGI deployment. Frontend tests cover two authentication scenarios;
there are no frontend chat-component tests in the current test suite.

These automated checks do not establish that the full stack has been manually
walked through in a browser, that real-time delivery works across multiple
processes, or that deployment and operations are ready.

## 7. Security and operational findings

These are source-level findings for follow-up, not a formal security audit.

| Priority | Finding | Status / next verification |
|---|---|---|
| Blocker for public deployment | Development settings enable `DEBUG`, use a hard-coded development-marked key, leave `ALLOWED_HOSTS` empty, and allow all CORS origins. | **Verified.** Introduce and validate a separate production configuration before deployment; do not expose the development key. |
| High | The WebSocket token is supplied in the query string. | **Verified.** Review proxy, application, and analytics logging; choose and document a safer production transport. |
| High | The default in-memory channel layer is process-local. | **Verified.** Multi-worker or multi-instance message delivery is not established; select and test a shared channel layer before scaling. |
| High | SQLite is the configured database and the database file is tracked. | **Verified.** The database contents were not inspected. Decide how user data is protected, backed up, restored, and kept out of source control. |
| Medium | CORS allows all origins; DRF also enables Basic and Session authentication. | **Verified.** Reassess allowed origins and authentication methods for the intended deployment and transport. |
| Medium | No DRF throttling configuration was found. | **Verified in settings.** Define abuse/rate controls appropriate to public registration, login, and message endpoints. |
| Medium | Chat history has no pagination, and membership/URI uniqueness is not database-enforced. | **Verified in current source/migration.** Review expected data volume and concurrent membership behavior before expanding use. |
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
3. Decide whether joining by possession of a URI is the intended invite policy.
4. Record a product audience and initial user problem; the repository alone
   cannot establish user need.
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
  [`auth.py`](../fuego/chat/auth.py).
- Backend tests: [`tests.py`](../fuego/chat/tests.py).
- Frontend setup and scripts: [`package.json`](../fuego/fuego-frontend/package.json),
  [`fuego-frontend README`](../fuego/fuego-frontend/README.md).
