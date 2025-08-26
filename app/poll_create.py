"""
UI module for creating new polls.
"""

import logging
from nicegui import ui, app
from app.poll_service import PollService
from app.models import PollCreate

logger = logging.getLogger(__name__)


def create():
    """Register poll creation UI."""

    @ui.page("/create-poll")
    async def create_poll_page():
        await ui.context.client.connected()

        # Simple user session management - store user ID in session
        current_user_id = app.storage.user.get("user_id")
        if current_user_id is None:
            with ui.card().classes("w-96 p-6 shadow-lg rounded-lg mx-auto mt-8"):
                ui.label("Please log in first").classes("text-xl font-bold mb-4 text-center")
                ui.button("Go to Login", on_click=lambda: ui.navigate.to("/login")).classes("w-full")
            return

        poll_service = PollService()

        # Page header
        with ui.row().classes("w-full items-center justify-between mb-6"):
            ui.label("Create New Poll").classes("text-3xl font-bold text-gray-800")
            ui.button("Back to Polls", on_click=lambda: ui.navigate.to("/polls")).classes("px-4 py-2").props("outline")

        # Poll creation form
        with ui.card().classes("w-full max-w-2xl mx-auto p-8 shadow-lg rounded-xl"):
            ui.label("Poll Details").classes("text-xl font-semibold text-gray-700 mb-4")

            # Poll title
            title_input = ui.input(label="Poll Title", placeholder="What would you like to ask?").classes("w-full mb-4")

            # Poll description
            description_input = (
                ui.textarea(label="Description (optional)", placeholder="Provide additional context for your poll...")
                .classes("w-full mb-6")
                .props("rows=3")
            )

            # Options section
            ui.label("Poll Options").classes("text-lg font-semibold text-gray-700 mb-4")
            ui.label("Enter your poll options below (at least 2 required)").classes("text-sm text-gray-500 mb-4")

            # Fixed option inputs
            with ui.column().classes("w-full gap-2 mb-4"):
                option1_input = ui.input(placeholder="Option 1").classes("w-full")
                option2_input = ui.input(placeholder="Option 2").classes("w-full")
                option3_input = ui.input(placeholder="Option 3 (optional)").classes("w-full")
                option4_input = ui.input(placeholder="Option 4 (optional)").classes("w-full")
                option5_input = ui.input(placeholder="Option 5 (optional)").classes("w-full")
                option6_input = ui.input(placeholder="Option 6 (optional)").classes("w-full")

            options = [option1_input, option2_input, option3_input, option4_input, option5_input, option6_input]

            # Create poll button
            async def create_poll():
                """Create the poll with validation."""
                title = title_input.value.strip()
                description = description_input.value.strip()
                option_texts = [opt.value.strip() for opt in options if opt.value.strip()]

                # Validation
                if not title:
                    ui.notify("Poll title is required", type="negative")
                    return

                if len(option_texts) < 2:
                    ui.notify("At least 2 options are required", type="negative")
                    return

                if len(set(option_texts)) != len(option_texts):
                    ui.notify("All options must be unique", type="negative")
                    return

                try:
                    poll_data = PollCreate(title=title, description=description, options=option_texts)

                    created_poll = poll_service.create_poll(poll_data, current_user_id)
                    ui.notify(f'Poll "{title}" created successfully!', type="positive")
                    ui.navigate.to(f"/poll/{created_poll.id}")

                except Exception as e:
                    logger.error(f"Error creating poll for user {current_user_id}: {str(e)}")
                    ui.notify(f"Error creating poll: {str(e)}", type="negative")

            with ui.row().classes("w-full justify-end gap-4"):
                ui.button("Cancel", on_click=lambda: ui.navigate.to("/polls")).classes("px-6 py-2").props("outline")

                ui.button("Create Poll", icon="poll", on_click=create_poll).classes("bg-blue-500 text-white px-6 py-2")
