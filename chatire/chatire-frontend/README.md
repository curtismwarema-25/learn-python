# chatire-frontend

> A Vue.js project

## Run with the Django API

From the repository root, install the backend dependencies, apply migrations,
and start Django:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\chatire\requirements.txt
.\.venv\Scripts\python.exe .\chatire\manage.py migrate
.\.venv\Scripts\python.exe .\chatire\manage.py runserver 8000
```

In another terminal, build and serve the frontend:

```powershell
Set-Location .\chatire\chatire-frontend
npm run build
Set-Location ..\..
.\.venv\Scripts\python.exe -m http.server 8080 --bind 127.0.0.1 --directory .\chatire\chatire-frontend\dist
```

Open `http://127.0.0.1:8080`. The development channel layer is in-memory and
is intended for a single local server process.

After signing in, start a chat and share its URL. A signed-in visitor opening
that invite URL is added to the chat before its message history is loaded.

## Optional RabbitMQ WebSocket bridge

The local setup above uses Django Channels. To use the RabbitMQ/uWSGI bridge
instead, run RabbitMQ and uWSGI, set `CHAT_RABBITMQ_ENABLED=true` and
`CHAT_RABBITMQ_HOST` for the Django process, and route WebSocket requests for
`/ws/chats/<uri>/` to `chat.websocket.application`. Keep ordinary HTTP API
requests routed to Django's ASGI/WSGI application. The bridge and publisher
must use the same RabbitMQ host. This deployment path is not available with
the Windows development server; leave `CHAT_RABBITMQ_ENABLED` unset for local
development.

## Build Setup

``` bash
# install dependencies
npm install

# serve with hot reload at localhost:8080
npm run dev

# build for production with minification
npm run build

# build for production and view the bundle analyzer report
npm run build --report

# run unit tests
npm run unit

# run e2e tests
npm run e2e

# run all tests
npm test
```

The webpack development server is from an older toolchain and may fail on
recent Node.js releases. On Node 24, use the build-and-serve commands above.

For a detailed explanation on how things work, check out the [guide](http://vuejs-templates.github.io/webpack/) and [docs for vue-loader](http://vuejs.github.io/vue-loader).
