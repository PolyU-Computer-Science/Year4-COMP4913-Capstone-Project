"""Shared page layout: Filament-style dark drawer + content area."""

from nicegui import ui

BRAND = "Email Assistant"

GLOBAL_CSS = """
.nicegui-content {
    max-width: 1100px;
    margin: 0 auto;
    padding: 1.5rem 1.5rem 3rem;
    background: #f1f5f9;
}
"""


def _nav_item(label: str, icon: str, target: str, active: bool) -> None:
    """Render a drawer navigation item."""
    color = "text-white bg-indigo-500" if active else "text-slate-300 hover:bg-slate-700 hover:text-white"
    with ui.row().classes(
        f"w-full items-center gap-3 px-3 py-2 rounded-lg cursor-pointer transition-colors {color}"
    ).on("click", lambda t=target: ui.navigate.to(t)):
        ui.icon(icon).classes("text-lg")
        ui.label(label)


def create_layout(title: str, active: str) -> None:
    """Build the app shell: dark drawer navigation + content header."""
    ui.query("body").classes("bg-slate-100")
    ui.add_css(GLOBAL_CSS)
    ui.page_title(f"{title} · {BRAND}")

    # ---- Dark drawer ----
    with ui.left_drawer(value=True, bordered=False).classes("bg-slate-900").props("fixed"):
        with ui.column().classes("w-full gap-1 p-3"):
            with ui.row().classes("items-center gap-2 px-3 pt-2 pb-4"):
                ui.icon("mark_email_read").classes("text-2xl text-indigo-400")
                ui.label(BRAND).classes("text-white text-xl font-bold")
            ui.separator().classes("bg-slate-700")

            _nav_item("Dashboard", "dashboard", "/", active == "dashboard")
            _nav_item("Inbox", "inbox", "/inbox", active == "inbox")
            _nav_item("Cases", "folder", "/cases", active == "cases")

            ui.separator().classes("bg-slate-700 mt-4")
            ui.label("AI Email Assistant · v1.0").classes(
                "text-slate-500 text-xs px-3 pt-2"
            )

    # ---- Top header ----
    with ui.header().classes(
        "bg-white text-slate-900 shadow-sm border-b border-slate-200"
    ).props("flat"):
        with ui.row().classes("w-full items-center justify-between px-4"):
            ui.label(title).classes("text-xl font-bold text-slate-900")
            with ui.row().classes("gap-2 items-center"):
                ui.badge("Online", color="positive").props("outline")
