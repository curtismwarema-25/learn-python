# Chatire frontend

The frontend is a React and TypeScript single-page app built with Vite. It
uses React Router for `/auth`, `/`, and `/chats/<uri>` routes and keeps the
existing Django REST API and Channels WebSocket integration.

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

From the repository root, install the Django requirements and run the backend:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\chatire\requirements.txt
.\.venv\Scripts\python.exe .\chatire\manage.py migrate
.\.venv\Scripts\python.exe .\chatire\manage.py runserver 8000
```

In another terminal, install frontend dependencies and start Vite:

```powershell
Set-Location .\chatire\chatire-frontend
npm install
npm run dev
```

Open the frontend URL printed by Vite (by default
`http://localhost:5173`). The frontend sends API and WebSocket requests to port
8000. The development channel layer is in-memory and intended for one local
server process.

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
bridge is documented in the backend deployment notes and is not part of the
default Windows development setup.
