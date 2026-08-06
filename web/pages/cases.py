"""Cases page - Processed emails and AI-generated drafts."""

from nicegui import app, ui

from web.components import category_badge, page_heading

RESULTS_KEY = "results"


def _results() -> dict[int, object]:
    """Get the per-user processing results."""
    return app.storage.user.setdefault(RESULTS_KEY, {})


def render() -> None:
    """Render the cases page."""
    page_heading("Cases", "Processed emails and AI-generated draft replies")
    ui.separator().classes("my-4")

    results = _results()

    if not results:
        with ui.column().classes("w-full items-center py-12"):
            ui.icon("folder_open", size="3rem").classes("text-grey-4")
            ui.label("No processed cases yet").classes("text-lg text-grey-6")
            ui.label(
                "Go to **Inbox** and click **AI Process** on an email."
            ).classes("text-sm text-grey-5")
        return

    for idx, result in results.items():
        email = app.storage.user["emails"][idx]
        subject = email.get("subject", "(no subject)")
        sender = email.get("sender", "Unknown")

        with ui.card().classes("w-full shadow-md"):
            with ui.row().classes("w-full items-center justify-between"):
                with ui.column().classes("gap-0"):
                    ui.label(subject).classes("text-lg font-semibold text-slate-900")
                    ui.label(f"From: {sender}").classes("text-sm text-grey-6")
                category = getattr(getattr(result, "pydantic", None), "category", None)
                if category:
                    category_badge(category)

            ui.separator().classes("my-3")

            with ui.grid(columns=2).classes("w-full gap-4"):
                with ui.column().classes("gap-1"):
                    ui.label("🤖 AI Draft Reply").classes(
                        "text-sm font-semibold text-slate-800"
                    )
                    draft = getattr(result, "raw", "") or str(result)
                    ui.textarea(value=draft).props(
                        "readonly outlined dense rows=10"
                    ).classes("w-full")

                with ui.column().classes("gap-1"):
                    ui.label("📋 Classification").classes(
                        "text-sm font-semibold text-slate-800"
                    )
                    pydantic = getattr(result, "pydantic", None)
                    if pydantic is not None:
                        ui.json_editor(
                            {
                                "content": {
                                    "json": pydantic.model_dump(),
                                }
                            }
                        ).classes("w-full")
                    else:
                        ui.label("No structured classification available.").classes(
                            "text-sm text-grey-6"
                        )
