"""
Service layer for poll management operations.
Handles business logic for polls, voting, and results calculation.
"""

from typing import List, Optional
from sqlmodel import select, func
from sqlalchemy.sql import text
from app.database import get_session
from app.models import Poll, Option, Vote, User, PollCreate, VoteCreate, PollResults, OptionResult


class PollService:
    """Service for managing polls, voting, and results."""

    def create_poll(self, poll_data: PollCreate, creator_id: int) -> Poll:
        """Create a new poll with options."""
        with get_session() as session:
            # Verify creator exists
            creator = session.get(User, creator_id)
            if creator is None:
                raise ValueError("Creator not found")

            # Create poll
            poll = Poll(title=poll_data.title, description=poll_data.description, creator_id=creator_id)
            session.add(poll)
            session.commit()
            session.refresh(poll)

            # Create options
            if poll.id is not None:
                for option_text in poll_data.options:
                    option = Option(text=option_text, poll_id=poll.id)
                    session.add(option)

            session.commit()

            # Return fresh poll with all relationships loaded
            if poll.id is not None:
                return self.get_poll(poll.id) or poll
            return poll

    def get_poll(self, poll_id: int) -> Optional[Poll]:
        """Get a poll by ID with its options."""
        with get_session() as session:
            poll = session.get(Poll, poll_id)
            if poll is None:
                return None

            # Create a new poll object with all data to avoid session issues
            creator = session.get(User, poll.creator_id)
            options = list(session.exec(select(Option).where(Option.poll_id == poll_id)).all())
            votes = list(session.exec(select(Vote).where(Vote.poll_id == poll_id)).all())

            # Create a detached poll object with loaded relationships
            detached_poll = Poll(
                id=poll.id,
                title=poll.title,
                description=poll.description,
                creator_id=poll.creator_id,
                is_active=poll.is_active,
                created_at=poll.created_at,
            )

            # Manually set relationships
            if creator:
                detached_poll.creator = creator
            detached_poll.options = options
            detached_poll.votes = votes

            return detached_poll

    def get_all_polls(self) -> List[Poll]:
        """Get all polls ordered by creation date (newest first)."""
        with get_session() as session:
            statement = select(Poll).order_by(text("created_at DESC"))
            polls = session.exec(statement).all()

            # Load all polls with their relationships
            result_polls = []
            for poll in polls:
                if poll.id is not None:
                    loaded_poll = self.get_poll(poll.id)
                    if loaded_poll:
                        result_polls.append(loaded_poll)

            return result_polls

    def get_active_polls(self) -> List[Poll]:
        """Get all active polls."""
        with get_session() as session:
            statement = select(Poll).where(Poll.is_active).order_by(text("created_at DESC"))
            polls = session.exec(statement).all()

            # Load all polls with their relationships
            result_polls = []
            for poll in polls:
                if poll.id is not None:
                    loaded_poll = self.get_poll(poll.id)
                    if loaded_poll:
                        result_polls.append(loaded_poll)

            return result_polls

    def cast_vote(self, vote_data: VoteCreate, user_id: int) -> bool:
        """Cast a vote for a user on a poll. Returns True if successful, False if already voted."""
        with get_session() as session:
            # Verify user exists
            user = session.get(User, user_id)
            if user is None:
                raise ValueError("User not found")

            # Verify poll exists and is active
            poll = session.get(Poll, vote_data.poll_id)
            if poll is None:
                raise ValueError("Poll not found")
            if not poll.is_active:
                raise ValueError("Poll is not active")

            # Verify option exists and belongs to poll
            option = session.get(Option, vote_data.option_id)
            if option is None:
                raise ValueError("Option not found")
            if option.poll_id != vote_data.poll_id:
                raise ValueError("Option does not belong to this poll")

            # Check if user already voted on this poll
            existing_vote = session.exec(
                select(Vote).where(Vote.user_id == user_id, Vote.poll_id == vote_data.poll_id)
            ).first()

            if existing_vote is not None:
                return False  # User already voted

            # Create vote
            vote = Vote(user_id=user_id, poll_id=vote_data.poll_id, option_id=vote_data.option_id)
            session.add(vote)
            session.commit()
            return True

    def get_poll_results(self, poll_id: int) -> Optional[PollResults]:
        """Get poll results with vote counts and percentages."""
        with get_session() as session:
            poll = session.get(Poll, poll_id)
            if poll is None:
                return None

            # Get total votes for this poll
            total_votes_result = session.exec(select(func.count()).where(Vote.poll_id == poll_id)).first()
            total_votes = total_votes_result if total_votes_result is not None else 0

            # Get all options for this poll
            options = list(session.exec(select(Option).where(Option.poll_id == poll_id)).all())

            # Get vote count for each option
            option_results = []
            for option in options:
                if option.id is not None:
                    vote_count_result = session.exec(select(func.count()).where(Vote.option_id == option.id)).first()
                    vote_count = vote_count_result if vote_count_result is not None else 0

                    percentage = round((vote_count / total_votes * 100), 2) if total_votes > 0 else 0

                    option_results.append(
                        OptionResult(
                            option_id=option.id, text=option.text, vote_count=vote_count, percentage=percentage
                        )
                    )

            if poll.id is not None:
                return PollResults(
                    poll_id=poll.id,
                    title=poll.title,
                    description=poll.description,
                    total_votes=total_votes,
                    options=option_results,
                )
            return None

    def has_user_voted(self, poll_id: int, user_id: int) -> bool:
        """Check if a user has already voted on a poll."""
        with get_session() as session:
            vote = session.exec(select(Vote).where(Vote.user_id == user_id, Vote.poll_id == poll_id)).first()
            return vote is not None

    def deactivate_poll(self, poll_id: int, user_id: int) -> bool:
        """Deactivate a poll. Only the creator can deactivate their own poll."""
        with get_session() as session:
            poll = session.get(Poll, poll_id)
            if poll is None:
                return False

            if poll.creator_id != user_id:
                return False  # Not the creator

            poll.is_active = False
            session.add(poll)
            session.commit()
            return True


class UserService:
    """Service for managing users."""

    def create_user(self, username: str, email: str) -> User:
        """Create a new user."""
        with get_session() as session:
            # Check if username already exists
            existing_user = session.exec(select(User).where(User.username == username)).first()
            if existing_user is not None:
                raise ValueError("Username already exists")

            # Check if email already exists
            existing_email = session.exec(select(User).where(User.email == email)).first()
            if existing_email is not None:
                raise ValueError("Email already exists")

            user = User(username=username, email=email)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        """Get a user by ID."""
        with get_session() as session:
            return session.get(User, user_id)

    def get_user_by_username(self, username: str) -> Optional[User]:
        """Get a user by username."""
        with get_session() as session:
            return session.exec(select(User).where(User.username == username)).first()

    def get_all_users(self) -> List[User]:
        """Get all users."""
        with get_session() as session:
            statement = select(User).order_by(User.username)
            users = session.exec(statement).all()
            return list(users)
