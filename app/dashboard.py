"""
Main dashboard and navigation for the voting system.
"""

from nicegui import ui, app
from app.poll_service import PollService, UserService


def create():
    """Register dashboard and home page."""

    @ui.page("/")
    async def home_page():
        """Landing page that redirects based on login status."""
        await ui.context.client.connected()

        current_user_id = app.storage.user.get("user_id")
        if current_user_id is not None:
            ui.navigate.to("/polls")
        else:
            ui.navigate.to("/login")

    @ui.page("/dashboard")
    async def dashboard_page():
        """User dashboard with statistics and quick actions."""
        await ui.context.client.connected()

        current_user_id = app.storage.user.get("user_id")
        if current_user_id is None:
            ui.navigate.to("/login")
            return

        poll_service = PollService()
        user_service = UserService()

        # Get current user
        current_user = user_service.get_user(current_user_id)
        if current_user is None:
            ui.navigate.to("/login")
            return

        # Page header with navigation
        with ui.row().classes("w-full items-center justify-between mb-8"):
            with ui.column():
                ui.label(f"Welcome, {current_user.username}!").classes("text-3xl font-bold text-gray-800")
                ui.label("Your Voting Dashboard").classes("text-gray-600")

            with ui.row().classes("gap-2"):
                ui.button("View All Polls", icon="poll", on_click=lambda: ui.navigate.to("/polls")).classes(
                    "px-4 py-2"
                ).props("outline")

                ui.button("Create Poll", icon="add_circle", on_click=lambda: ui.navigate.to("/create-poll")).classes(
                    "bg-blue-500 text-white px-4 py-2"
                )

                ui.button("Logout", icon="logout", on_click=lambda: ui.navigate.to("/logout")).classes(
                    "px-4 py-2"
                ).props("outline color=negative")

        # Statistics cards
        with ui.row().classes("w-full gap-6 mb-8"):
            # User's created polls
            user_polls = [p for p in poll_service.get_all_polls() if p.creator_id == current_user_id]
            active_user_polls = [p for p in user_polls if p.is_active]

            with ui.card().classes("flex-1 p-6 shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                ui.label("My Polls").classes("text-sm text-gray-500 uppercase tracking-wider")
                ui.label(str(len(user_polls))).classes("text-3xl font-bold text-blue-600 mt-2")
                ui.label(f"{len(active_user_polls)} active").classes("text-sm text-gray-600")

            # Total votes received on user's polls
            total_votes_received = sum(len(poll.votes) for poll in user_polls)

            with ui.card().classes("flex-1 p-6 shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                ui.label("Votes Received").classes("text-sm text-gray-500 uppercase tracking-wider")
                ui.label(str(total_votes_received)).classes("text-3xl font-bold text-green-600 mt-2")
                ui.label("on your polls").classes("text-sm text-gray-600")

            # Polls user has voted on
            user_votes = 0
            for poll in poll_service.get_all_polls():
                if poll.id is not None and poll_service.has_user_voted(poll.id, current_user_id):
                    user_votes += 1

            with ui.card().classes("flex-1 p-6 shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                ui.label("Polls Voted").classes("text-sm text-gray-500 uppercase tracking-wider")
                ui.label(str(user_votes)).classes("text-3xl font-bold text-purple-600 mt-2")
                ui.label("participated").classes("text-sm text-gray-600")

        # Recent activity sections
        with ui.row().classes("w-full gap-6"):
            # User's recent polls
            with ui.column().classes("flex-1"):
                with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                    ui.label("My Recent Polls").classes("text-xl font-bold text-gray-800 mb-4")

                    if not user_polls:
                        ui.label("You haven't created any polls yet").classes("text-gray-500 text-center py-8")
                        ui.button(
                            "Create Your First Poll", icon="add", on_click=lambda: ui.navigate.to("/create-poll")
                        ).classes("bg-blue-500 text-white px-4 py-2")
                    else:
                        recent_polls = sorted(user_polls, key=lambda p: p.created_at, reverse=True)[:3]
                        for poll in recent_polls:
                            if poll.id is not None:
                                results = poll_service.get_poll_results(poll.id)
                                vote_count = results.total_votes if results else 0
                            else:
                                vote_count = 0

                            with ui.row().classes("w-full items-center justify-between py-2 border-b border-gray-100"):
                                with ui.column():
                                    ui.link(poll.title, f"/poll/{poll.id}").classes(
                                        "font-medium text-blue-600 hover:text-blue-800"
                                    )
                                    ui.label(
                                        f"{vote_count} votes • {'Active' if poll.is_active else 'Inactive'}"
                                    ).classes("text-sm text-gray-500")

                                ui.button(
                                    "View",
                                    icon="visibility",
                                    on_click=lambda poll_id=poll.id: ui.navigate.to(f"/poll/{poll_id}"),
                                ).classes("text-sm").props("flat size=sm")

                        if len(user_polls) > 3:
                            ui.button(
                                f"View all {len(user_polls)} polls", on_click=lambda: ui.navigate.to("/polls")
                            ).classes("w-full mt-4").props("outline")

            # Available polls to vote on
            with ui.column().classes("flex-1"):
                with ui.card().classes("w-full p-6 shadow-lg rounded-xl"):
                    ui.label("Polls to Vote On").classes("text-xl font-bold text-gray-800 mb-4")

                    # Get polls user hasn't voted on yet
                    all_active_polls = poll_service.get_active_polls()
                    unvoted_polls = []
                    for poll in all_active_polls:
                        if poll.id is not None:
                            if (
                                not poll_service.has_user_voted(poll.id, current_user_id)
                                and poll.creator_id != current_user_id
                            ):
                                unvoted_polls.append(poll)

                    if not unvoted_polls:
                        ui.label("No new polls to vote on").classes("text-gray-500 text-center py-8")
                        ui.button("View All Polls", icon="poll", on_click=lambda: ui.navigate.to("/polls")).classes(
                            "px-4 py-2"
                        ).props("outline")
                    else:
                        recent_unvoted = unvoted_polls[:3]
                        for poll in recent_unvoted:
                            if poll.id is not None:
                                results = poll_service.get_poll_results(poll.id)
                                vote_count = results.total_votes if results else 0
                            else:
                                vote_count = 0

                            with ui.row().classes("w-full items-center justify-between py-2 border-b border-gray-100"):
                                with ui.column():
                                    ui.link(poll.title, f"/poll/{poll.id}").classes(
                                        "font-medium text-blue-600 hover:text-blue-800"
                                    )
                                    ui.label(f"By {poll.creator.username} • {vote_count} votes").classes(
                                        "text-sm text-gray-500"
                                    )

                                ui.button(
                                    "Vote",
                                    icon="how_to_vote",
                                    on_click=lambda poll_id=poll.id: ui.navigate.to(f"/poll/{poll_id}"),
                                ).classes("bg-blue-500 text-white text-sm").props("size=sm")

                        if len(unvoted_polls) > 3:
                            ui.button(
                                f"View all {len(unvoted_polls)} unvoted polls",
                                on_click=lambda: ui.navigate.to("/polls"),
                            ).classes("w-full mt-4").props("outline")
