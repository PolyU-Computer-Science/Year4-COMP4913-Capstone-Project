"""Reusable Filament-style UI components for NiceGUI."""

from nicegui import ui

CATEGORY_COLORS = {
    "question": "info",
    "incident": "negative",
    "problem": "warning",
    "task": "positive",
    "spam": "grey-5",
}

STAT_ICONS = {
    "primary": "trending_up",
    "success": "check_circle",
    "warning": "hourglass_top",
    "info": "insights",
    "danger": "error",
}


def stat_card(
    label: str,
    value: str | int,
    description: str = "",
    icon: str = "",
    color: str = "primary",
) -> None:
    """Render a Filament-style stats overview card."""
    color_class = f"text-{color}"
    with ui.card().classes("w-full shadow-md"):
        with ui.row().classes("w-full items-start justify-between"):
            with ui.column().classes("gap-0"):
                ui.label(label).classes("text-xs text-grey-6 font-medium")
                ui.label(str(value)).classes("text-2xl font-bold text-slate-900")
                if description:
                    ui.label(description).classes("text-xs text-grey-6")
            with ui.column().classes("items-center"):
                ui.icon(icon or STAT_ICONS.get(color, "info")).classes(
                    f"text-3xl {color_class}"
                )


def category_badge(category: str) -> None:
    """Render a colored pill badge for an email category."""
    color = CATEGORY_COLORS.get(category.lower(), "grey-6")
    ui.badge(category.title(), color=color).props("outline")


def page_heading(title: str, subtitle: str = "") -> None:
    """Render a page heading with title + subtitle."""
    with ui.column().classes("gap-0 w-full"):
        ui.label(title).classes("text-2xl font-bold text-slate-900")
        if subtitle:
            ui.label(subtitle).classes("text-sm text-grey-6")
