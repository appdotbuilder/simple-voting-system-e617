"""
Simple user authentication and session management.
"""

import logging
from nicegui import ui, app
from app.poll_service import UserService

logger = logging.getLogger(__name__)


def create():
    """Register authentication UI."""

    @ui.page("/login")
    async def login_page():
        await ui.context.client.connected()

        # Check if already logged in
        current_user_id = app.storage.user.get("user_id")
        if current_user_id is not None:
            ui.navigate.to("/polls")
            return

        user_service = UserService()

        # Page layout
        with ui.column().classes("w-full max-w-md mx-auto mt-16 gap-8"):
            # Header
            with ui.card().classes("w-full p-8 shadow-lg rounded-xl text-center"):
                ui.icon("poll", size="48px").classes("text-blue-500 mb-4")
                ui.label("Voting System").classes("text-3xl font-bold text-gray-800 mb-2")
                ui.label("Sign in to create and vote on polls").classes("text-gray-600")

            # Login form
            with ui.card().classes("w-full p-8 shadow-lg rounded-xl"):
                ui.label("Sign In or Create Account").classes("text-xl font-bold text-gray-800 mb-6")

                username_input = ui.input(label="Username", placeholder="Enter your username").classes("w-full mb-4")

                email_input = ui.input(label="Email", placeholder="Enter your email").classes("w-full mb-6")

                async def handle_login():
                    """Handle login/registration."""
                    username = username_input.value.strip()
                    email = email_input.value.strip()

                    if not username or not email:
                        ui.notify("Please enter both username and email", type="warning")
                        return

                    # Basic email validation
                    if "@" not in email or "." not in email:
                        ui.notify("Please enter a valid email address", type="warning")
                        return

                    try:
                        # Try to find existing user by username
                        existing_user = user_service.get_user_by_username(username)

                        if existing_user is not None:
                            # User exists, check if email matches
                            if existing_user.email.lower() == email.lower():
                                # Valid login
                                app.storage.user["user_id"] = existing_user.id
                                app.storage.user["username"] = existing_user.username
                                ui.notify(f"Welcome back, {username}!", type="positive")
                                ui.navigate.to("/polls")
                            else:
                                ui.notify("Username exists with different email", type="negative")
                        else:
                            # Create new user
                            try:
                                new_user = user_service.create_user(username, email)
                                app.storage.user["user_id"] = new_user.id
                                app.storage.user["username"] = new_user.username
                                ui.notify(f"Welcome, {username}! Account created successfully.", type="positive")
                                ui.navigate.to("/polls")

                            except ValueError as ve:
                                logger.warning(f"User creation failed for {username}: {str(ve)}")
                                if "Username already exists" in str(ve):
                                    ui.notify("Username already exists", type="negative")
                                elif "Email already exists" in str(ve):
                                    ui.notify("Email already registered with different username", type="negative")
                                else:
                                    ui.notify(f"Error creating account: {str(ve)}", type="negative")

                    except Exception as e:
                        logger.error(f"Login error for user {username}: {str(e)}")
                        ui.notify(f"Login error: {str(e)}", type="negative")

                ui.button("Sign In / Create Account", icon="login", on_click=handle_login).classes(
                    "w-full bg-blue-500 text-white py-3"
                )

                ui.separator().classes("my-4")

                ui.label("How it works:").classes("text-sm font-medium text-gray-700 mb-2")
                with ui.column().classes("gap-1"):
                    ui.label("• Enter username and email").classes("text-xs text-gray-600")
                    ui.label("• If username exists, we'll sign you in").classes("text-xs text-gray-600")
                    ui.label("• If username is new, we'll create your account").classes("text-xs text-gray-600")

    @ui.page("/logout")
    async def logout_page():
        """Handle user logout."""
        await ui.context.client.connected()

        # Clear user session
        app.storage.user.clear()
        ui.notify("Logged out successfully", type="positive")
        ui.navigate.to("/login")
