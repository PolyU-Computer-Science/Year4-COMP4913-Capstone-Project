# Configuration & Development Guide

## Configuration

Settings can be provided two ways: **`.env` defaults** and **runtime Settings
UI** (stored in `data/settings.db`, overriding env).

### LLM Provider Selection

Set `LLM_PROVIDER` to exactly one of `local`, `openai`, `openrouter`,
`anthropic`, `groq`, `deepseek`, or `google`. Only the selected provider is
validated, so local mode does not require remote API keys. The active
provider/model can also be switched at runtime in **System → AI Models**.

```dotenv
# Provider & safety guardrails
LLM_PROVIDER=local
LLM_TEMPERATURE=0.2
LLM_TIMEOUT=120
LLM_MAX_TOKENS=2000

# Local / OpenAI-compatible server (LM Studio, vLLM, llama.cpp, Ollama)
LOCAL_BASE_URL=http://localhost:11434/v1
LOCAL_MODEL=local-model
# LOCAL_API_KEY=sk-...           # Optional: for authenticated proxies/middleware

# OpenRouter (recommended runtime provider)
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_MODEL=xiaomi/mimo-v2.5-pro
# OPENROUTER_API_KEY=sk-or-v1-...

# OpenAI Example
# OPENAI_API_KEY=sk-...
# OPENAI_BASE_URL=https://api.openai.com/v1
# OPENAI_MODEL=gpt-4o-mini

# Anthropic Example
# ANTHROPIC_API_KEY=sk-ant-...
# ANTHROPIC_MODEL=claude-3-5-sonnet-20241022

# Google Gemini Example
# GOOGLE_API_KEY=...
# GOOGLE_MODEL=gemini-2.0-flash

# (also supported: groq, deepseek — see .env.example)
```

### Embeddings (Knowledge / RAG)

```dotenv
# hashing (offline, deterministic, tests) | openrouter | openai | ollama
EMBEDDING_PROVIDER=hashing
EMBEDDING_BASE_URL=
EMBEDDING_MODEL=qwen/qwen3-embedding-8b
EMBEDDING_BATCH_SIZE=32
```

- `hashing` is a deterministic offline client used by tests/CI.
- `openrouter` uses `OPENROUTER_API_KEY` + `EMBEDDING_MODEL`; a missing key
  raises a configuration error (no silent fallback).
- The embedding dimension is discovered from the first response, never
  hardcoded. Changing provider/model/dimension marks existing indexes stale and
  triggers a reindex (see `core/embeddings.py`).

### Email Configuration (IMAP)

Mailboxes are the primary unit — each mailbox owns its own IMAP/SMTP
connection, topics, fields, knowledge, and connectors. Configure them in
**Mailboxes → Connection**, or use `.env` for a single legacy account.

```dotenv
EMAIL_ENABLED=false
EMAIL_SERVER=imap.gmail.com
EMAIL_PORT=993
EMAIL_ADDRESS=
EMAIL_PASSWORD=your-app-password   # Use Google App Password
EMAIL_FOLDER=INBOX
EMAIL_MAX_EMAILS=50
```

> **Folder naming:** use the exact IMAP mailbox name (e.g. `INBOX`).
> Sub-folders use the server's hierarchy separator (`INBOX.Subfolder` or
> `INBOX/Subfolder`) — not spaces.

### API Server

```dotenv
API_HOST=0.0.0.0
API_PORT=8000
CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173

# Frontend (frontend/.env)
# VITE_PORT=5173
# VITE_API_TARGET=http://localhost:8000
```

### Persistence & Secrets

```dotenv
SQLITE_SETTINGS_DB=data/settings.db
# SQLITE_EMAIL_DB=data/emails.db          (default shown)
# KNOWLEDGE_DB=data/knowledge.db
# OBSERVABILITY_DB=data/observability.db
# SETTINGS_ENCRYPTION_KEY=...             # Optional Fernet key; auto-generated to data/.secret_key
```

All state is persisted in SQLite (auto-created on first run):

| Database | File | Contents |
| --- | --- | --- |
| **Email Store** | `data/emails.db` | Emails as tickets (sender, subject, body, classification fields, draft, sent timestamp, mailbox_id) + attachments + case field values + draft knowledge provenance. IDs are content-hashed with mailbox scope for dedupe. |
| **Settings Store** | `data/settings.db` | AI configs, stage settings, mailboxes, topics, custom fields, knowledge sources, connectors, tool permissions. |
| **Knowledge Store** | `data/knowledge.db` | Indexed knowledge documents + chunks (embedding vectors as JSON, mailbox-scoped). |
| **Observability Store** | `data/observability.db` | Processing runs (latency/tokens/status) + tool audit logs. |

**Secret handling:** API keys and mail passwords are encrypted at rest with
**Fernet** (`cryptography`). The key comes from `SETTINGS_ENCRYPTION_KEY` or is
auto-generated to `data/.secret_key`. Secrets are always masked in API
responses and redacted in tool audit logs.

---

## Usage

### Web UI (primary workflow)

1. **Mailboxes → Add Mailbox** — create a business context (name, address, purpose).
2. **Mailbox → Connection** — configure IMAP/SMTP, then *Test Connection*.
3. **System → AI Models** — configure an LLM provider (use *Test Connection*), then activate it.
4. **Mailbox → Topics / Fields** — define the mailbox's taxonomy and custom fields.
5. **Mailbox → Knowledge** — add a source, *Index* it, then *Test Retrieval*.
6. **Mailbox → Connectors** — discover tools and set permissions (default deny).
7. **Inbox → Sync** — pull unread emails via IMAP into the ticket store.
8. **Inbox → Process** — run Classifier → Retrieval → Drafter on an email.
9. **Cases** — review the classification, fields, knowledge provenance and draft; edit if needed, then *Approve & Send*.

### CLI Mode

```bash
uv run crewai run
```

Runs the full pipeline: `fetch_emails()` → Classifier → Drafter. The
classification result is validated against the `EmailClassification` Pydantic
model, and the final draft is written to `draft_reply.txt` (git-ignored runtime
artifact).

### Evaluation

```bash
# Regenerate the synthetic evaluation datasets (seeded, deterministic).
uv run python -m evaluation.generator

# Run a real evaluation against OpenRouter (consumes credit).
uv run python -m scripts.run_evaluation --limit 20 --experiments cls,ret,fe,draft
```

See `evaluation/README.md` for dataset methodology and `evaluation/results/`
(git-ignored) for raw runs.

---

## Development

### Run Tests

```bash
uv run pytest            # 280 tests (core + backend API), no real API calls required
```

### Lint & Format

```bash
# Frontend (uses oxlint)
cd frontend && npm run lint

# Python (ruff, if installed)
uv run ruff check .
uv run ruff format .
```

### Typecheck & Build (frontend)

```bash
cd frontend && npm run build   # tsc -b && vite build
```

### Dependency Management

```bash
uv add <package>         # Add a Python dependency
uv sync                  # Sync environment
```
