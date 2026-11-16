# Learn Python

## Why this repository exists

This is my learn-as-I-go workspace for refreshing my Python skills and
developing as a software builder. I use it to learn through practical work,
including backend development with Django, and to improve the project as my
understanding grows. It is an evolving learning project rather than a finished
product.

The long-term vision for **Fuego** is a conversation-first technology and
learning platform. It starts as a chat app and can grow to connect community,
useful knowledge, guided learning, and practical creation:

**Conversation → Community → Knowledge → Learning → Creation**

Fuego should organize learning into focused hubs by category, keeping
discussion, useful resources, guided learning, and hands-on work connected.
Python is an important foundation and learning area, but it does not define the
platform's limits. Other areas may include emerging technology and using AI
effectively in everyday work.

For practical AI learning, the focus is on improving real workflows: understand
the work, identify where AI may help, apply it, evaluate the results, and
improve the process. The exact categories and features will evolve through
learning and validation; the goal is a coherent platform, not a collection of
unrelated demos.

## What I'm working on

**Fuego is currently a full-stack chat app**, which provides the foundation
for this broader platform. Its current features give me a place to practice
backend concepts in context:

- Django models, migrations, and application structure
- REST APIs and token-based authentication with Django REST Framework
- Chat ownership, membership, and access control
- Real-time messaging with Django Channels and WebSockets
- An optional RabbitMQ/uWSGI bridge that I am exploring alongside the local
  Channels setup
- Connecting a React + TypeScript frontend to the Django backend

## What I want to learn

- Design and build reliable Django APIs
- Understand how authentication and permissions shape an application
- Test backend behavior and the flows that connect its components
- Explore asynchronous and real-time patterns without losing sight of a
  straightforward local development setup
- Learn to connect conversations, knowledge, and practical learning in focused
  category hubs

## Run Fuego locally

Do the setup once from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\fuego\requirements.txt
.\.venv\Scripts\python.exe .\fuego\manage.py migrate
npm --prefix .\fuego\fuego-frontend install
```

Then start Django and the React frontend together with one command:

```powershell
npm --prefix .\fuego\fuego-frontend run dev:all
```

Open `http://localhost:5173` for the app. The frontend connects to Django on
port 8000. Press `Ctrl+C` in the terminal to stop both servers.

More setup details, build commands, and notes about the optional RabbitMQ
bridge are in the
[Fuego setup guide](./fuego/fuego-frontend/README.md).

## Project status

Features and structure may change as I learn. The local real-time setup uses
Channels' in-memory layer and is intended for a single server process.
RabbitMQ/uWSGI requires separate services and deployment configuration; it is
an optional experiment, not part of the default Windows setup.
