# File Upload API

A production-style file upload REST API built with FastAPI, SQLAlchemy 2.0, PostgreSQL, and S3-compatible object storage (AWS S3, MinIO, Cloudflare R2, Backblaze B2, etc. via `boto3`). Implements JWT auth (register/login/refresh/logout) plus upload, list, metadata, download, and delete for per-user files.

## Stack

- **FastAPI** — web framework
- **SQLAlchemy 2.0** — ORM
- **PostgreSQL** — metadata database
- **Alembic** — schema migrations
- **boto3** — S3-compatible object storage client
- **Pydantic v2** — request/response validation
- **bcrypt** — password hashing
- **python-jose** — JWT signing/verification
- **slowapi** — rate limiting

## Features

- Email/password registration and login, JWT access/refresh tokens with server-side refresh-token revocation (same pattern as `fastapi-authentication-api`)
- Files are uploaded directly through the API (`UploadFile` multipart), streamed to the configured S3-compatible bucket, and streamed back on download — no file bytes ever touch local disk or the database
- File metadata (filename, content type, size, storage key, owner) is tracked in Postgres; every file is scoped to the uploading user — one user can never read, list, or delete another user's files
- Per-upload size limit (`MAX_UPLOAD_SIZE_MB`, default 25MB) enforced before the upload is streamed to storage
- Storage backend is configured via `S3_ENDPOINT_URL` — point it at AWS S3, or leave it set to a local MinIO/R2 endpoint for development, with no code changes
- Rate limiting on `/auth/login` and `/auth/register`
- Global exception handler: unexpected errors return a generic `500` and are logged server-side, never leaking internals to the client

## Endpoints

| Method | Path                  | Auth required | Description                                   |
|--------|-----------------------|----------------|------------------------------------------------|
| POST   | `/auth/register`      | No             | Create a new user                               |
| POST   | `/auth/login`         | No             | Exchange credentials for an access/refresh pair |
| GET    | `/auth/me`            | Yes            | Return the current authenticated user           |
| POST   | `/auth/refresh`       | No (refresh token in body) | Rotate a refresh token for a new pair |
| POST   | `/auth/logout`        | Yes            | Revoke a single refresh token                    |
| POST   | `/auth/logout-all`    | Yes            | Revoke every active refresh token for the user   |
| POST   | `/files/`             | Yes            | Upload a file                                    |
| GET    | `/files/`             | Yes            | List the current user's files                    |
| GET    | `/files/{file_id}`    | Yes            | Get a file's metadata                            |
| GET    | `/files/{file_id}/download` | Yes      | Stream-download the file                         |
| DELETE | `/files/{file_id}`    | Yes            | Delete a file (bucket object + DB row)           |
| GET    | `/health`             | No             | Health check                                     |

Interactive API docs are available at `/docs` (Swagger UI) once the server is running.

## Project structure

```
app/
├── main.py            # FastAPI app, middleware, global exception handler
├── config.py           # Typed settings loaded from .env (pydantic-settings)
├── database.py          # SQLAlchemy engine, session, declarative Base
├── security.py          # Password hashing + JWT create/decode helpers
├── storage.py            # boto3 S3-compatible client: upload/download/delete
├── dependencies.py       # get_current_user auth dependency
├── rate_limit.py         # slowapi limiter instance
├── models/               # SQLAlchemy models (User, RefreshToken, UploadedFile)
├── schemas/               # Pydantic request/response schemas
└── routers/
    ├── auth.py            # All /auth/* endpoints
    └── files.py            # All /files/* endpoints

alembic/                    # Migration environment and versions
```

## Setup

1. **Create a virtual environment and install dependencies:**

   ```bash
   python -m venv venv
   venv\Scripts\activate       # Windows
   pip install -r requirements.txt
   ```

2. **Configure environment variables.** Copy `.env.example` to `.env` and fill in real values:

   ```
   DATABASE_URL=postgresql+psycopg://user:password@host/dbname?sslmode=require
   SECRET_KEY=a-long-random-string
   S3_ENDPOINT_URL=http://localhost:9000   # blank/unset for real AWS S3
   S3_BUCKET_NAME=file-uploads
   S3_REGION=us-east-1
   S3_ACCESS_KEY_ID=...
   S3_SECRET_ACCESS_KEY=...
   MAX_UPLOAD_SIZE_MB=25
   ```

   For local development without a real cloud account, run [MinIO](https://min.io/) in Docker and point `S3_ENDPOINT_URL` at it — the same `boto3` code path works unmodified against AWS S3 in production.

3. **Run database migrations:**

   ```bash
   alembic upgrade head
   ```

4. **Start the dev server:**

   ```bash
   uvicorn app.main:app --reload --port 8000
   ```

   Visit `http://127.0.0.1:8000/docs` for interactive API docs.

## Notes on production readiness

- **Rate limiting** uses in-memory storage by default, which is only correct for a single running instance. For multi-instance/multi-worker deployments, set `RATE_LIMIT_STORAGE_URI` to a Redis URI.
- **Direct-through-API uploads** are simple but mean large files consume API server bandwidth/memory-in-flight. For very large files or high upload volume, a presigned-URL flow (client uploads directly to the bucket) scales better and is a natural next step.
- **Migrations** are managed with Alembic (`alembic revision --autogenerate -m "..."` after model changes, then `alembic upgrade head`).
