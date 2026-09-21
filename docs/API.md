# API Reference

Base URL: `http://localhost:8000/api`

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/health` | Health check |
| GET | `/emails` | List stored emails |
| POST | `/emails/sync` | Fetch unread emails via IMAP (502 on IMAP failure) |
| POST | `/emails/{id}/process` | Run the CrewAI pipeline (classify + draft) on an email |
| GET | `/emails/{id}/attachments/{cid}` | Serve an inline attachment |
| GET | `/cases` | List processed cases |
| PATCH | `/cases/{id}` | Edit a draft reply |
| POST | `/cases/{id}/send` | Send the approved draft via SMTP |
| GET | `/stats` | Dashboard statistics (totals, category distribution, activity) |
| GET/POST | `/settings/ai` | List / create AI configs |
| PUT/DELETE | `/settings/ai/{id}` | Update / delete an AI config |
| POST | `/settings/ai/{id}/activate` | Set the active AI config (single-active) |
| POST | `/settings/ai/test` · `/settings/ai/{id}/test` | LLM connection test |
| GET/PUT | `/settings/stages` | Per-stage settings (classification / draft) |
| GET/POST | `/settings/mail` | List / create mail accounts |
| PUT/DELETE | `/settings/mail/{id}` | Update / delete a mail account |
