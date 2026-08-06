"""Dashboard page - Overview and analytics."""

from nicegui import ui

from web.components import page_heading, stat_card


def render() -> None:
    """Render the dashboard page."""
    page_heading("Dashboard", "Overview of your email assistant")
    ui.separator().classes("my-4")

    # ---- Stats overview ----
    with ui.row().classes("w-full gap-4"):
        with ui.column().classes("flex-1"):
            stat_card("Total Emails", "156", "+12 from last week", "email", "primary")
        with ui.column().classes("flex-1"):
            stat_card("Processed", "142", "completed", "check_circle", "success")
        with ui.column().classes("flex-1"):
            stat_card("Pending", "14", "awaiting action", "hourglass_top", "warning")
        with ui.column().classes("flex-1"):
            stat_card("Success Rate", "91%", "↑ 5% this week", "insights", "info")

    ui.separator().classes("my-6")

    # ---- Recent activity table ----
    with ui.card().classes("w-full shadow-md"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("list_alt").classes("text-xl text-slate-700")
            ui.label("Recent Activity").classes("text-lg font-semibold text-slate-900")
        ui.label("The most recently processed emails.").classes(
            "text-sm text-grey-6 mb-3"
        )
        columns = [
            {"name": "email", "label": "Email", "field": "email", "align": "left"},
            {"name": "topic", "label": "Topic", "field": "topic", "align": "left"},
            {"name": "category", "label": "Category", "field": "category", "align": "left"},
            {"name": "priority", "label": "Priority", "field": "priority", "align": "left"},
            {"name": "status", "label": "Status", "field": "status", "align": "left"},
            {"name": "time", "label": "Time", "field": "time", "align": "left"},
        ]
        rows = [
            {"email": "Meeting Request", "topic": "meeting", "category": "task", "priority": "normal", "status": "Processed", "time": "2 min ago"},
            {"email": "Invoice #1234", "topic": "invoice", "category": "question", "priority": "normal", "status": "Processed", "time": "15 min ago"},
            {"email": "Server Down", "topic": "outage", "category": "incident", "priority": "urgent", "status": "Processing", "time": "2 hours ago"},
            {"email": "Billing Bug", "topic": "bug_report", "category": "problem", "priority": "high", "status": "Open", "time": "1 hour ago"},
            {"email": "Newsletter", "topic": "promo", "category": "spam", "priority": "low", "status": "Skipped", "time": "3 hours ago"},
        ]
        ui.table(columns=columns, rows=rows).props("flat bordered dense")

    ui.separator().classes("my-6")

    # ---- Category distribution chart ----
    with ui.card().classes("w-full shadow-md"):
        with ui.row().classes("items-center gap-2"):
            ui.icon("donut_large").classes("text-xl text-slate-700")
            ui.label("Category Distribution").classes(
                "text-lg font-semibold text-slate-900"
            )
        ui.label("Incoming email by classification.").classes(
            "text-sm text-grey-6 mb-3"
        )
        ui.echart(
            {
                "tooltip": {"trigger": "item"},
                "legend": {"bottom": 0},
                "series": [
                    {
                        "name": "Category",
                        "type": "pie",
                        "radius": ["40%", "70%"],
                        "avoidLabelOverlap": False,
                        "itemStyle": {"borderRadius": 8, "borderColor": "#fff", "borderWidth": 2},
                        "label": {"show": False},
                        "emphasis": {"label": {"show": True, "fontWeight": "bold"}},
                        "data": [
                            {"value": 38, "name": "Question", "itemStyle": {"color": "#3b82f6"}},
                            {"value": 42, "name": "Incident", "itemStyle": {"color": "#ef4444"}},
                            {"value": 30, "name": "Problem", "itemStyle": {"color": "#f59e0b"}},
                            {"value": 12, "name": "Task", "itemStyle": {"color": "#10b981"}},
                            {"value": 34, "name": "Spam", "itemStyle": {"color": "#94a3b8"}},
                        ],
                    }
                ],
            }
        ).classes("w-full h-72")
