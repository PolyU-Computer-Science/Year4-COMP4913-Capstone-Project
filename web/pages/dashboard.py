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
            stat_card("Processed", "142", "✅ completed", "check_circle", "success")
        with ui.column().classes("flex-1"):
            stat_card("Pending", "14", "awaiting action", "hourglass_top", "warning")
        with ui.column().classes("flex-1"):
            stat_card("Success Rate", "91%", "↑ 5% this week", "insights", "info")

    ui.separator().classes("my-6")

    # ---- Recent activity table ----
    with ui.card().classes("w-full shadow-md"):
        ui.label("📋 Recent Activity").classes("text-lg font-semibold text-slate-900")
        ui.label("The most recently processed emails.").classes(
            "text-sm text-grey-6 mb-3"
        )
        columns = [
            {"name": "email", "label": "Email", "field": "email", "align": "left"},
            {"name": "category", "label": "Category", "field": "category", "align": "left"},
            {"name": "status", "label": "Status", "field": "status", "align": "left"},
            {"name": "time", "label": "Time", "field": "time", "align": "left"},
        ]
        rows = [
            {"email": "Meeting Request", "category": "meeting", "status": "Processed", "time": "2 min ago"},
            {"email": "Invoice #1234", "category": "inquiry", "status": "Processed", "time": "15 min ago"},
            {"email": "Newsletter", "category": "notification", "status": "Skipped", "time": "1 hour ago"},
            {"email": "Urgent: Server Down", "category": "urgent", "status": "Processing", "time": "2 hours ago"},
            {"email": "Project Update", "category": "inquiry", "status": "Processed", "time": "3 hours ago"},
        ]
        ui.table(columns=columns, rows=rows).props("flat bordered dense")

    ui.separator().classes("my-6")

    # ---- Category distribution chart ----
    with ui.card().classes("w-full shadow-md"):
        ui.label("🏷️ Category Distribution").classes(
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
                            {"value": 38, "name": "Meeting", "itemStyle": {"color": "#3b82f6"}},
                            {"value": 42, "name": "Inquiry", "itemStyle": {"color": "#f59e0b"}},
                            {"value": 30, "name": "Notification", "itemStyle": {"color": "#94a3b8"}},
                            {"value": 12, "name": "Urgent", "itemStyle": {"color": "#ef4444"}},
                            {"value": 34, "name": "Spam", "itemStyle": {"color": "#cbd5e1"}},
                        ],
                    }
                ],
            }
        ).classes("w-full h-72")
