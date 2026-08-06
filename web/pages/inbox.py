"""Inbox page - Email list and processing."""

from nicegui import app, background_tasks, run, ui

from email_assistant.core import fetch_emails, format_email
from web.components import page_heading

EMAILS_KEY = "emails"
RESULTS_KEY = "results"


def _emails() -> list[dict]:
    """Get the per-user email list."""
    return app.storage.user.setdefault(EMAILS_KEY, [])


def _results() -> dict[int, object]:
    """Get the per-user processing results."""
    return app.storage.user.setdefault(RESULTS_KEY, {})


@ui.refreshable
def email_list() -> None:
    """Render the list of emails with expandable details and AI processing."""
    emails = _emails()

    if not emails:
        with ui.column().classes("w-full items-center py-12"):
            ui.icon("inbox", size="3rem").classes("text-grey-4")
            ui.label("No emails loaded yet").classes("text-lg text-grey-6")
            ui.label("Click Fetch Emails to retrieve your inbox.").classes(
                "text-sm text-grey-5"
            )
        return

    for i, email in enumerate(emails):
        subject = email.get("subject", "(no subject)")
        sender = email.get("sender", "Unknown")
        timestamp = email.get("timestamp", "Unknown")
        processed = i in _results()

        with ui.expansion(f"**{subject}**", icon="email").classes(
            "w-full bg-white shadow-sm"
        ):
            with ui.column().classes("w-full gap-2"):
                with ui.row().classes("w-full items-center justify-between"):
                    with ui.row().classes("items-center gap-1 text-sm text-grey-7"):
                        ui.icon("schedule", size="sm")
                        ui.label(f"From: {sender}  ·  {timestamp}")
                    if processed:
                        ui.badge("Processed", color="positive").props("outline")

                ui.separator()
                ui.textarea(
                    value=format_email(email), label="Content"
                ).props("readonly outlined dense rows=8").classes("w-full")

                with ui.row().classes("w-full justify-end"):
                    if processed:
                        ui.button("Done", icon="check", color="positive").props(
                            "flat disabled"
                        )
                    else:
                        ui.button(
                            "AI Process",
                            icon="auto_awesome",
                            color="primary",
                            on_click=lambda i=i: process_email(i),
                        ).props("unelevated")


def process_email(i: int) -> None:
    """Run the AI pipeline on a single email in a background thread."""
    from email_assistant.agents import EmailAssistant

    email = _emails()[i]

    async def process() -> None:
        try:
            result = await run.io_bound(
                EmailAssistant().crew().kickoff,
                inputs={"email_content": format_email(email)},
            )
            _results()[i] = result
            ui.notify("Email processed!", type="positive")
        except Exception as e:
            ui.notify(f"Processing failed: {e}", type="negative")
        finally:
            email_list.refresh()

    with ui.row().classes("items-center gap-2").style("color: #6366f1"):
        ui.spinner(size="sm")
        ui.label("AI is analyzing the email and drafting a reply...")
    background_tasks.create(process())


def render() -> None:
    """Render the inbox page."""
    page_heading("Inbox", "Manage and process incoming emails")
    ui.separator().classes("my-4")

    # Toolbar with per-page state (closure, not module globals)
    with ui.row().classes("w-full items-center justify-between"):
        count_label = ui.label(f"{len(_emails())} emails loaded").classes(
            "text-grey-7"
        )
        with ui.row().classes("items-center gap-2"):
            loading = ui.spinner(size="sm").classes("text-primary")
            loading.visible = False
            fetch_btn = ui.button(
                "Fetch Emails",
                icon="download",
                color="primary",
            ).props("unelevated")

    def fetch_now() -> None:
        fetch_btn.disable()
        fetch_btn.props("loading")
        loading.visible = True

        async def fetch() -> None:
            try:
                emails = await run.io_bound(fetch_emails)
                _emails().clear()
                _emails().extend(emails)
                _results().clear()
                count_label.set_text(f"{len(emails)} emails loaded")
                ui.notify(f"Fetched {len(emails)} emails", type="positive")
            except Exception as e:
                ui.notify(f"Fetch failed: {e}", type="negative")
            finally:
                fetch_btn.enable()
                fetch_btn.props(remove="loading")
                loading.visible = False
                email_list.refresh()

        background_tasks.create(fetch())

    fetch_btn.on_click(fetch_now)

    ui.separator().classes("my-4")

    email_list()
