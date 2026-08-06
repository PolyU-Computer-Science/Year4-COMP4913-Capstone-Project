#!/usr/bin/env python
"""Email Assistant web interface built with NiceGUI."""

import sys
from pathlib import Path

# Add project root to Python path
sys.path.insert(0, str(Path(__file__).parent.parent))

from nicegui import app, ui

from web.layout import create_layout

# Per-user session data
DEFAULT_EMAILS: list[dict] = []
DEFAULT_RESULTS: dict[int, object] = {}


@ui.page("/")
def dashboard_page() -> None:
    """Dashboard route."""
    create_layout("Dashboard", active="dashboard")
    from web.pages import dashboard

    dashboard.render()


@ui.page("/inbox")
def inbox_page() -> None:
    """Inbox route."""
    create_layout("Inbox", active="inbox")
    from web.pages import inbox

    inbox.render()


@ui.page("/cases")
def cases_page() -> None:
    """Cases route."""
    create_layout("Cases", active="cases")
    from web.pages import cases

    cases.render()


def main() -> None:
    """Start the NiceGUI app."""
    ui.run(
        title="Email Assistant",
        favicon="📧",
        host="0.0.0.0",
        port=8080,
        storage_secret="email-assistant-dev-secret",
        reload=False,
    )


if __name__ in {"__main__", "__mp_main__"}:
    main()
