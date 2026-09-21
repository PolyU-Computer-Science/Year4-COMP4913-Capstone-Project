# Configuration & Development Guide

## Configuration

Settings can be provided two ways: **`.env` defaults** and **runtime Settings
UI** (stored in `data/settings.db`, overriding env).

### LLM Provider Selection

Set `LLM_PROVIDER` to exactly one of `local`, `openai`, `openrouter`,
`anthropic`, `groq`, `deepseek`, or `google`. Only the selected provider is
validated, so local mode does not require remote API keys. The active
provider/model can also be switched at runtime in **Settings → AI**.

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

# (also supported: openrouter, groq, deepseek — see .env.example)
```

### Email Configuration (IMAP)

Set in `.env` for the default account, or manage multiple accounts at runtime
in **Settings → Mail Accounts** (address, IMAP/SMTP host + port, folder, max
emails, enable toggle). Gmail requires an App Password.

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
# SETTINGS_ENCRYPTION_KEY=...             # Optional Fernet key; auto-generated to data/.secret_key

# Embeddings (planned RAG)
EMBEDDING_PROVIDER=ollama
EMBEDDING_BASE_URL=http://localhost:11434
EMBEDDING_MODEL=qwen3-embedding-4b
```

All state is persisted in two SQLite databases (auto-created on first run):

| Database | File | Contents |
| --- | --- | --- |
| **Email Store** | `data/emails.db` | Emails as tickets (sender, subject, body, classification fields, draft, sent timestamp) + inline attachments. IDs are content-hashed for dedupe. |
| **Settings Store** | `data/settings.db` | AI configs (single-active model, per-stage overrides), stage settings, mail accounts (IMAP/SMTP). |

**Secret handling:** API keys and mail passwords are encrypted at rest with
**Fernet** (`cryptography`). The key comes from `SETTINGS_ENCRYPTION_KEY` or is
auto-generated to `data/.secret_key`. Secrets are always masked in API
responses (`has_api_key` / `has_password` booleans).

---

## Usage

### Web UI (primary workflow)

1. **Settings → Mail Accounts** — add your IMAP/SMTP account (folder must be a valid IMAP mailbox name, e.g. `INBOX`).
2. **Settings → AI** — configure an LLM provider (use *Test Connection* to verify), then activate it.
3. **Inbox → Sync** — pull unread emails via IMAP into the ticket store.
4. **Inbox → Process** — run the Classifier → Drafter pipeline on an email.
5. **Cases** — review the classification and draft, edit if needed, then **Send** via SMTP.

### CLI Mode

```bash
uv run crewai run
```

Runs the full pipeline: `fetch_emails()` → Classifier → Drafter. The
classification result is validated against the `EmailClassification` Pydantic
model, and the final draft is written to `draft_reply.txt` (git-ignored runtime
artifact).

---

## Development

### Run Tests

```bash
uv run pytest            # 111 tests (core + backend API), no real API calls required
```

### Lint & Format

```bash
uv run ruff check .
uv run ruff format .

# Frontend
cd frontend && npm run lint
```

### Dependency Management

```bash
uv add <package>         # Add a Python dependency
uv sync                  # Sync environment
```
