# Fuego frontend

The frontend is a React and TypeScript single-page app built with Vite. It
uses React Router for `/auth`, `/`, and `/chats/<uri>` routes and keeps the
existing Django REST API and Channels WebSocket integration.

Fuego is currently a chat app and the foundation for a broader,
conversation-first technology and learning platform. The long-term goal is to
connect community, useful knowledge, category-based learning, and practical
creation. Python is an important learning area, not the platform's limit; AI
applied to real-world workflows is another potential area. See the
[project README](../../README.md) for the full direction.

## Frontend structure

- `src/App.tsx` defines routes and the signed-in route guard.
- `src/components/UserAuth.tsx` handles account creation and sign-in.
- `src/components/Chat.tsx` handles chat sessions, message history, and
  WebSocket updates.
- `src/api.ts` contains the API request helper and validates API response
  shapes before the components use them.
- `tsconfig.json` enables strict type checking. The production build runs
  TypeScript checking before Vite bundles the app.

## Run locally

From the repository root, install the Django requirements, apply migrations,
and install frontend dependencies:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\fuego\requirements.txt
.\.venv\Scripts\python.exe .\fuego\manage.py migrate
npm --prefix .\fuego\fuego-frontend install
```

Start the backend and frontend together:

```powershell
npm --prefix .\fuego\fuego-frontend run dev:all
```

Open `http://localhost:5173`. The frontend sends API and WebSocket requests to
Django on port 8000. Press `Ctrl+C` to stop both servers. The development
channel layer is in-memory and intended for one local server process.

After signing in, start a chat and share its URL. Visitors opening an invite
URL are added to the chat before its message history is loaded.

## Build and preview

```powershell
npm run build
npm run preview -- --host 127.0.0.1 --port 8080
```

Use an SPA-aware static host for production so direct requests to paths such as
`/chats/<uri>` fall back to `index.html`.

## Optional RabbitMQ WebSocket bridge

The default local setup uses Django Channels. To use the optional RabbitMQ/
uWSGI bridge, run RabbitMQ and uWSGI, set `CHAT_RABBITMQ_ENABLED=true` and
`CHAT_RABBITMQ_HOST` for Django, and route WebSocket requests for
`/ws/chats/<uri>/` to `chat.websocket.application`. Keep ordinary HTTP API
requests routed to Django's ASGI/WSGI application. The bridge and publisher
must use the same RabbitMQ host. This deployment path is not available with
the Windows development server; leave `CHAT_RABBITMQ_ENABLED` unset locally.

## Tests

```powershell
npm run typecheck
npm test
```

The local real-time setup uses Django Channels. The optional RabbitMQ/uWSGI
bridge above is not part of the default Windows development setup.
