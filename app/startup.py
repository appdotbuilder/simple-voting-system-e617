from app.database import create_tables
from nicegui import ui
import app.auth
import app.dashboard
import app.poll_create
import app.poll_list


def startup() -> None:
    # this function is called before the first request
    create_tables()

    # Apply modern theme colors
    ui.colors(
        primary="#2563eb",  # Professional blue
        secondary="#64748b",  # Subtle gray
        accent="#10b981",  # Success green
        positive="#10b981",
        negative="#ef4444",  # Error red
        warning="#f59e0b",  # Warning amber
        info="#3b82f6",  # Info blue
    )

    # Register all modules
    app.auth.create()
    app.dashboard.create()
    app.poll_create.create()
    app.poll_list.create()
