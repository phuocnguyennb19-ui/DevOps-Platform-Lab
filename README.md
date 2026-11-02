# dev.notes — DevOps Knowledge Hub

A Docker Compose starter that expands the static DevOps portfolio into a full-stack knowledge hub. It keeps the dark navy / purple / cyan design and adds real account authentication, PostgreSQL persistence, private workspaces, article CRUD, drafts, and public publishing.

## Stack

- Frontend: HTML/CSS/vanilla JavaScript served by Nginx on port `8080`
- API: Python 3.12, FastAPI, SQLAlchemy 2, PyJWT, Argon2 password hashing
- Database: PostgreSQL 17 with a named persistent volume
- Runtime: Docker Compose

## Start locally

1. Copy the environment template and replace the secrets:

   ```bash
   cp .env.example .env
   ```

   Set a strong unique `POSTGRES_PASSWORD` and `JWT_SECRET`. The values in `.env.example` are placeholders only.

2. Build and start the stack:

   ```bash
   docker compose up -d --build
   docker compose ps
   docker compose logs -f api
   ```

3. Open the app:

   - Website: http://localhost:8080
   - API health: http://localhost:8080/health
   - OpenAPI docs: http://localhost:8080/docs (API container is internal by default; for local API docs, temporarily add `ports: ["8000:8000"]` to the `api` service, then open http://localhost:8000/docs.)

4. Create an account from **Login / Register**. Registration creates a personal workspace. Create articles as drafts or publish them. Published + public articles appear in the Blog section. Data persists in the `postgres_data` volume.

## Useful commands

```bash
# Inspect logs
docker compose logs -f api db frontend

# Check API health through Nginx
curl -i http://localhost:8080/health

# Stop without deleting database data
docker compose down

# WARNING: delete the database volume and all local data
docker compose down -v
```

## Repository layout

```text
devops-knowledge-hub/
├── backend/
│   ├── app/
│   │   ├── config.py       # Environment settings
│   │   ├── database.py     # SQLAlchemy engine/session
│   │   ├── main.py         # Auth, workspace, article API
│   │   ├── models.py       # User, workspace, membership, article
│   │   ├── schemas.py      # Request/response validation
│   │   └── security.py     # Argon2 hashes and JWTs
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   ├── index.html          # Responsive multi-context UI + API client
│   ├── Dockerfile
│   └── default.conf        # Nginx reverse proxy config
├── nginx/default.conf      # Reference copy of proxy config
├── docker-compose.yml
├── .env.example
└── README.md
```

## API overview

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/api/v1/auth/register` | Register and create a personal workspace |
| POST | `/api/v1/auth/login` | Get a bearer access token |
| GET | `/api/v1/auth/me` | Current user profile |
| GET / POST | `/api/v1/workspaces` | List or create the caller's workspaces |
| GET | `/api/v1/workspaces/{id}/members` | List members for a workspace member |
| POST | `/api/v1/workspaces/{id}/members` | Owner adds an existing user as editor/viewer |
| GET / POST | `/api/v1/workspaces/{id}/articles` | List workspace articles or create a draft/published article |
| PATCH / DELETE | `/api/v1/articles/{id}` | Update or delete an article after membership/role checks |
| GET | `/api/v1/articles/public` | List published public articles; optional `?context=Kubernetes%20%26%20Helm` |
| GET | `/api/v1/articles/{id}` | Read a public published article |

## Permissions model

- A new user gets an `owner` membership in their personal workspace.
- `owner` and `editor` can create, edit and delete workspace articles. `viewer` can read workspace articles.
- Only a workspace `owner` can add an already registered user as `editor` or `viewer` using `POST /api/v1/workspaces/{id}/members` with `{ "email": "person@example.com", "role": "editor" }`.
- A draft is private to authenticated workspace members. Public listing only returns articles where `status=published` and `is_public=true`.
- Passwords are Argon2-hashed; API writes require a signed, expiring JWT.

## Phased implementation plan

### Phase 1 — Local MVP (included)

- Dark responsive UI, DevOps context taxonomy, register/login/logout
- Separate user accounts and personal workspaces
- Workspace creation and membership-scoped article access
- Create, read, update, delete, draft and publish article flows
- PostgreSQL persistence and Docker Compose

### Phase 2 — Collaboration and content quality

- UI for inviting existing users, managing roles and removing members
- Article detail routes, Markdown rendering with sanitization, image/diagram uploads
- Slugs, pagination, sorting, richer search, tags and related-article links
- Email verification, password reset, login rate limiting and audit log

### Phase 3 — Production hardening

- Alembic migrations instead of `create_all`, automated tests and CI pipeline
- Strong secret management, HTTPS, secure refresh/session strategy, CSP and security headers
- Backups/restore drills, structured logs, metrics, health/readiness checks
- Object storage for media, malware/content checks, database least privilege

## Important security notes

This is a functional starter, not a production security review. Set real secrets in `.env`; never commit `.env`. Do not expose the database port publicly. The API currently creates tables on startup for convenience; use Alembic migrations for controlled upgrades. Before production, add rate limiting, email verification and password reset, robust audit logging, HTTPS, tested backups, and a reviewed token/session lifecycle. The article body is rendered as escaped text in the starter UI, not as HTML, to avoid executing untrusted content.
# DevOps-Platform-Lab
