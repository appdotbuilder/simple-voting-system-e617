"""
UI module for displaying polls and handling voting.
"""

import logging
from nicegui import ui, app
from app.poll_service import PollService, UserService
from app.models import VoteCreate

logger = logging.getLogger(__name__)


def create():
    """Register poll listing and voting UI."""

    @ui.page("/polls")
    async def polls_list_page():
        await ui.context.client.connected()

        current_user_id = app.storage.user.get("user_id")
        if current_user_id is None:
            with ui.card().classes("w-96 p-6 shadow-lg rounded-lg mx-auto mt-8"):
                ui.label("Please log in first").classes("text-xl font-bold mb-4 text-center")
                ui.button("Go to Login", on_click=lambda: ui.navigate.to("/login")).classes("w-full")
            return

        poll_service = PollService()
        user_service = UserService()

        # Get current user info
        current_user = user_service.get_user(current_user_id)
        if current_user is None:
            ui.notify("User session invalid", type="negative")
            ui.navigate.to("/login")
            return

        # Page header
        with ui.row().classes("w-full items-center justify-between mb-6"):
            with ui.column():
                ui.label("Active Polls").classes("text-3xl font-bold text-gray-800")
                ui.label(f"Welcome back, {current_user.username}!").classes("text-gray-600")

            ui.button("Create Poll", icon="add_circle", on_click=lambda: ui.navigate.to("/create-poll")).classes(
                "bg-blue-500 text-white px-6 py-3 rounded-lg hover:bg-blue-600"
            )

        # Polls container
        polls_container = ui.column().classes("w-full gap-6")

        @ui.refreshable
        def show_polls():
            """Display all active polls."""
            polls_container.clear()

            with polls_container:
                polls = poll_service.get_active_polls()

                if not polls:
                    with ui.card().classes("w-full p-8 text-center shadow-lg"):
                        ui.icon("poll", size="64px").classes("text-gray-400 mb-4")
                        ui.label("No active polls yet").classes("text-xl text-gray-600 mb-2")
                        ui.label("Be the first to create a poll!").classes("text-gray-500")
                        ui.button(
                            "Create Your First Poll", icon="add", on_click=lambda: ui.navigate.to("/create-poll")
                        ).classes("bg-blue-500 text-white px-6 py-2 mt-4")
                    return

                for poll in polls:
                    with ui.card().classes("w-full p-6 shadow-lg rounded-xl hover:shadow-xl transition-shadow"):
                        # Poll header
                        with ui.row().classes("w-full items-start justify-between mb-4"):
                            with ui.column().classes("flex-1"):
                                ui.link(poll.title, f"/poll/{poll.id}").classes(
                                    "text-xl font-bold text-blue-600 hover:text-blue-800 no-underline"
                                )

                                if poll.description:
                                    ui.label(poll.description).classes("text-gray-600 mt-1")

                                # Poll meta info
                                created_date = poll.created_at.strftime("%B %d, %Y")
                                ui.label(f"Created by {poll.creator.username} on {created_date}").classes(
                                    "text-sm text-gray-500 mt-2"
                                )

                            # Vote status indicator
                            has_voted = False
                            if poll.id is not None:
                                has_voted = poll_service.has_user_voted(poll.id, current_user_id)

                            if has_voted:
                                ui.chip("Voted", icon="check_circle").classes("bg-green-100 text-green-800")
                            else:
                                ui.chip("Not Voted", icon="radio_button_unchecked").classes("bg-gray-100 text-gray-600")

                        # Quick vote preview or results
                        results = None
                        if poll.id is not None:
                            results = poll_service.get_poll_results(poll.id)
                        if results and results.total_votes > 0:
                            ui.label(f"{results.total_votes} vote{'s' if results.total_votes != 1 else ''}").classes(
                                "text-sm text-gray-600 mb-3"
                            )

                            # Show top option
                            top_option = max(results.options, key=lambda x: x.vote_count)
                            if top_option.vote_count > 0:
                                ui.label(f"Leading: {top_option.text} ({top_option.percentage:.1f}%)").classes(
                                    "text-sm font-medium text-gray-700"
                                )
                        else:
                            ui.label("No votes yet - be the first to vote!").classes("text-sm text-gray-500 italic")

                        # Action buttons
                        with ui.row().classes("w-full justify-end gap-2 mt-4"):
                            ui.button(
                                "View Details",
                                icon="visibility",
                                on_click=lambda poll_id=poll.id: ui.navigate.to(f"/poll/{poll_id}"),
                            ).classes("px-4 py-2").props("outline")

                            if not has_voted:
                                ui.button(
                                    "Vote Now",
                                    icon="how_to_vote",
                                    on_click=lambda poll_id=poll.id: ui.navigate.to(f"/poll/{poll_id}"),
                                ).classes("bg-blue-500 text-white px-4 py-2")

        show_polls()

    @ui.page("/poll/{poll_id}")
    async def poll_detail_page(poll_id: int):
        await ui.context.client.connected()

        current_user_id = app.storage.user.get("user_id")
        if current_user_id is None:
            with ui.card().classes("w-96 p-6 shadow-lg rounded-lg mx-auto mt-8"):
                ui.label("Please log in first").classes("text-xl font-bold mb-4 text-center")
                ui.button("Go to Login", on_click=lambda: ui.navigate.to("/login")).classes("w-full")
            return

        poll_service = PollService()
        poll = poll_service.get_poll(poll_id)

        if poll is None:
            with ui.card().classes("w-96 p-6 shadow-lg rounded-lg mx-auto mt-8"):
                ui.label("Poll not found").classes("text-xl font-bold mb-4 text-center")
                ui.button("Back to Polls", on_click=lambda: ui.navigate.to("/polls")).classes("w-full")
            return

        # Page header
        with ui.row().classes("w-full items-center justify-between mb-6"):
            ui.button("← Back to Polls", on_click=lambda: ui.navigate.to("/polls")).classes("px-4 py-2").props(
                "outline"
            )

        # Poll content container
        poll_container = ui.column().classes("w-full max-w-4xl mx-auto")

        @ui.refreshable
        def show_poll_content():
            """Display poll details, voting interface, and results."""
            poll_container.clear()

            with poll_container:
                # Refresh poll data
                current_poll = poll_service.get_poll(poll_id)
                if current_poll is None:
                    return

                results = poll_service.get_poll_results(poll_id)
                has_voted = poll_service.has_user_voted(poll_id, current_user_id)

                # Poll header
                with ui.card().classes("w-full p-8 shadow-lg rounded-xl mb-6"):
                    ui.label(current_poll.title).classes("text-3xl font-bold text-gray-800 mb-4")

                    if current_poll.description:
                        ui.label(current_poll.description).classes("text-lg text-gray-600 mb-4")

                    # Poll metadata
                    created_date = current_poll.created_at.strftime("%B %d, %Y at %I:%M %p")
                    with ui.row().classes("items-center gap-6 text-sm text-gray-500"):
                        ui.label(f"Created by {current_poll.creator.username}")
                        ui.label(f"Created on {created_date}")
                        ui.label(f"Status: {'Active' if current_poll.is_active else 'Inactive'}")
                        if results:
                            ui.label(f"Total votes: {results.total_votes}")

                if not current_poll.is_active:
                    with ui.card().classes("w-full p-6 bg-yellow-50 border-l-4 border-yellow-400 mb-6"):
                        ui.label("This poll is no longer active").classes("text-yellow-800 font-medium")

                # Voting section or results
                if has_voted or not current_poll.is_active:
                    # Show results
                    with ui.card().classes("w-full p-8 shadow-lg rounded-xl"):
                        ui.label("Poll Results").classes("text-2xl font-bold text-gray-800 mb-6")

                        if results and results.total_votes > 0:
                            for option_result in results.options:
                                with ui.row().classes("w-full items-center mb-4"):
                                    with ui.column().classes("flex-1"):
                                        ui.label(option_result.text).classes("text-lg font-medium mb-1")

                                        # Progress bar
                                        with ui.row().classes("w-full items-center gap-4"):
                                            ui.linear_progress(value=option_result.percentage / 100).classes("flex-1")

                                            ui.label(
                                                f"{option_result.vote_count} votes ({option_result.percentage:.1f}%)"
                                            ).classes("text-sm text-gray-600 min-w-[120px] text-right")
                        else:
                            ui.label("No votes yet").classes("text-center text-gray-500 text-lg py-8")

                        if has_voted:
                            ui.label("✓ You have already voted in this poll").classes(
                                "text-center text-green-600 font-medium mt-6"
                            )

                else:
                    # Show voting interface
                    with ui.card().classes("w-full p-8 shadow-lg rounded-xl"):
                        ui.label("Cast Your Vote").classes("text-2xl font-bold text-gray-800 mb-6")

                        selected_option = (
                            ui.radio(options={opt.id: opt.text for opt in current_poll.options}, value=None)
                            .classes("w-full")
                            .props("size=lg")
                        )

                        async def cast_vote():
                            """Handle vote submission."""
                            if selected_option.value is None:
                                ui.notify("Please select an option", type="warning")
                                return

                            try:
                                vote_data = VoteCreate(poll_id=poll_id, option_id=selected_option.value)
                                success = poll_service.cast_vote(vote_data, current_user_id)

                                if success:
                                    ui.notify("Vote cast successfully!", type="positive")
                                    show_poll_content.refresh()
                                else:
                                    ui.notify("You have already voted in this poll", type="warning")

                            except Exception as e:
                                logger.error(
                                    f"Error casting vote for user {current_user_id} on poll {poll_id}: {str(e)}"
                                )
                                ui.notify(f"Error casting vote: {str(e)}", type="negative")

                        with ui.row().classes("w-full justify-center mt-8"):
                            ui.button("Submit Vote", icon="how_to_vote", on_click=cast_vote).classes(
                                "bg-blue-500 text-white px-8 py-3 text-lg"
                            )

        show_poll_content()
