"""
Tests for poll service layer business logic.
"""

import pytest
from app.database import reset_db
from app.poll_service import PollService, UserService
from app.models import PollCreate, VoteCreate


@pytest.fixture()
def fresh_db():
    """Reset database before and after each test."""
    reset_db()
    yield
    reset_db()


@pytest.fixture()
def poll_service():
    """Poll service instance."""
    return PollService()


@pytest.fixture()
def user_service():
    """User service instance."""
    return UserService()


@pytest.fixture()
def test_user(fresh_db, user_service):
    """Create a test user."""
    return user_service.create_user("testuser", "test@example.com")


@pytest.fixture()
def test_poll_data():
    """Sample poll data for testing."""
    return PollCreate(
        title="Favorite Programming Language",
        description="Choose your favorite programming language",
        options=["Python", "JavaScript", "Java", "C++"],
    )


class TestUserService:
    """Tests for user management."""

    def test_create_user_success(self, fresh_db, user_service):
        user = user_service.create_user("john_doe", "john@example.com")
        assert user.id is not None
        assert user.username == "john_doe"
        assert user.email == "john@example.com"
        assert user.created_at is not None

    def test_create_user_duplicate_username(self, fresh_db, user_service):
        user_service.create_user("john_doe", "john@example.com")

        with pytest.raises(ValueError, match="Username already exists"):
            user_service.create_user("john_doe", "different@example.com")

    def test_create_user_duplicate_email(self, fresh_db, user_service):
        user_service.create_user("john_doe", "john@example.com")

        with pytest.raises(ValueError, match="Email already exists"):
            user_service.create_user("different_user", "john@example.com")

    def test_get_user_by_id(self, fresh_db, user_service):
        user = user_service.create_user("testuser", "test@example.com")
        retrieved_user = user_service.get_user(user.id)

        assert retrieved_user is not None
        assert retrieved_user.username == "testuser"
        assert retrieved_user.email == "test@example.com"

    def test_get_user_nonexistent(self, fresh_db, user_service):
        result = user_service.get_user(999)
        assert result is None

    def test_get_user_by_username(self, fresh_db, user_service):
        user = user_service.create_user("testuser", "test@example.com")
        retrieved_user = user_service.get_user_by_username("testuser")

        assert retrieved_user is not None
        assert retrieved_user.id == user.id

    def test_get_user_by_username_nonexistent(self, fresh_db, user_service):
        result = user_service.get_user_by_username("nonexistent")
        assert result is None

    def test_get_all_users(self, fresh_db, user_service):
        user_service.create_user("alice", "alice@example.com")
        user_service.create_user("bob", "bob@example.com")

        all_users = user_service.get_all_users()
        assert len(all_users) == 2
        usernames = [u.username for u in all_users]
        assert "alice" in usernames
        assert "bob" in usernames


class TestPollService:
    """Tests for poll management."""

    def test_create_poll_success(self, fresh_db, poll_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)

        assert poll.id is not None
        assert poll.title == test_poll_data.title
        assert poll.description == test_poll_data.description
        assert poll.creator_id == test_user.id
        assert poll.is_active
        assert poll.created_at is not None
        assert len(poll.options) == 4

        option_texts = [opt.text for opt in poll.options]
        assert "Python" in option_texts
        assert "JavaScript" in option_texts
        assert "Java" in option_texts
        assert "C++" in option_texts

    def test_create_poll_nonexistent_creator(self, fresh_db, poll_service, test_poll_data):
        with pytest.raises(ValueError, match="Creator not found"):
            poll_service.create_poll(test_poll_data, 999)

    def test_get_poll_success(self, fresh_db, poll_service, test_user, test_poll_data):
        created_poll = poll_service.create_poll(test_poll_data, test_user.id)
        retrieved_poll = poll_service.get_poll(created_poll.id)

        assert retrieved_poll is not None
        assert retrieved_poll.title == test_poll_data.title
        assert len(retrieved_poll.options) == 4

    def test_get_poll_nonexistent(self, fresh_db, poll_service):
        result = poll_service.get_poll(999)
        assert result is None

    def test_get_all_polls(self, fresh_db, poll_service, test_user, user_service):
        # Create multiple polls
        poll_data1 = PollCreate(title="Poll 1", options=["A", "B"])
        poll_data2 = PollCreate(title="Poll 2", options=["X", "Y"])

        poll_service.create_poll(poll_data1, test_user.id)
        poll_service.create_poll(poll_data2, test_user.id)

        all_polls = poll_service.get_all_polls()
        assert len(all_polls) == 2

        # Should be ordered by created_at desc (newest first)
        poll_titles = [p.title for p in all_polls]
        assert poll_titles == ["Poll 2", "Poll 1"]

    def test_get_active_polls(self, fresh_db, poll_service, test_user):
        poll_data1 = PollCreate(title="Active Poll", options=["A", "B"])
        poll_data2 = PollCreate(title="Inactive Poll", options=["X", "Y"])

        poll_service.create_poll(poll_data1, test_user.id)
        inactive_poll = poll_service.create_poll(poll_data2, test_user.id)

        # Deactivate one poll
        if inactive_poll.id is not None:
            poll_service.deactivate_poll(inactive_poll.id, test_user.id)

        active_polls = poll_service.get_active_polls()
        assert len(active_polls) == 1
        assert active_polls[0].title == "Active Poll"


class TestVotingLogic:
    """Tests for voting functionality."""

    def test_cast_vote_success(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        vote_data = VoteCreate(poll_id=poll.id, option_id=poll.options[0].id)
        result = poll_service.cast_vote(vote_data, voter.id)

        assert result is True

    def test_cast_vote_already_voted(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        vote_data = VoteCreate(poll_id=poll.id, option_id=poll.options[0].id)

        # First vote should succeed
        result1 = poll_service.cast_vote(vote_data, voter.id)
        assert result1 is True

        # Second vote should fail
        result2 = poll_service.cast_vote(vote_data, voter.id)
        assert result2 is False

    def test_cast_vote_nonexistent_user(self, fresh_db, poll_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        vote_data = VoteCreate(poll_id=poll.id, option_id=poll.options[0].id)

        with pytest.raises(ValueError, match="User not found"):
            poll_service.cast_vote(vote_data, 999)

    def test_cast_vote_nonexistent_poll(self, fresh_db, poll_service, user_service):
        voter = user_service.create_user("voter", "voter@example.com")
        vote_data = VoteCreate(poll_id=999, option_id=1)

        with pytest.raises(ValueError, match="Poll not found"):
            poll_service.cast_vote(vote_data, voter.id)

    def test_cast_vote_inactive_poll(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        # Deactivate poll
        poll_service.deactivate_poll(poll.id, test_user.id)

        vote_data = VoteCreate(poll_id=poll.id, option_id=poll.options[0].id)

        with pytest.raises(ValueError, match="Poll is not active"):
            poll_service.cast_vote(vote_data, voter.id)

    def test_cast_vote_nonexistent_option(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        vote_data = VoteCreate(poll_id=poll.id, option_id=999)

        with pytest.raises(ValueError, match="Option not found"):
            poll_service.cast_vote(vote_data, voter.id)

    def test_cast_vote_option_wrong_poll(self, fresh_db, poll_service, user_service, test_user):
        # Create two polls
        poll1_data = PollCreate(title="Poll 1", options=["A", "B"])
        poll2_data = PollCreate(title="Poll 2", options=["X", "Y"])

        poll1 = poll_service.create_poll(poll1_data, test_user.id)
        poll2 = poll_service.create_poll(poll2_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        # Try to vote for poll1 using poll2's option
        vote_data = VoteCreate(poll_id=poll1.id, option_id=poll2.options[0].id)

        with pytest.raises(ValueError, match="Option does not belong to this poll"):
            poll_service.cast_vote(vote_data, voter.id)

    def test_has_user_voted(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        voter = user_service.create_user("voter", "voter@example.com")

        # Initially should not have voted
        assert not poll_service.has_user_voted(poll.id, voter.id)

        # After voting should return True
        vote_data = VoteCreate(poll_id=poll.id, option_id=poll.options[0].id)
        poll_service.cast_vote(vote_data, voter.id)

        assert poll_service.has_user_voted(poll.id, voter.id)


class TestPollResults:
    """Tests for poll results calculation."""

    def test_get_poll_results_no_votes(self, fresh_db, poll_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        results = poll_service.get_poll_results(poll.id)

        assert results is not None
        assert results.poll_id == poll.id
        assert results.title == test_poll_data.title
        assert results.total_votes == 0
        assert len(results.options) == 4

        for option_result in results.options:
            assert option_result.vote_count == 0
            assert option_result.percentage == 0

    def test_get_poll_results_with_votes(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)

        # Create voters
        voter1 = user_service.create_user("voter1", "voter1@example.com")
        voter2 = user_service.create_user("voter2", "voter2@example.com")
        voter3 = user_service.create_user("voter3", "voter3@example.com")

        # Cast votes: 2 for Python, 1 for JavaScript
        python_option = next(opt for opt in poll.options if opt.text == "Python")
        js_option = next(opt for opt in poll.options if opt.text == "JavaScript")

        poll_service.cast_vote(VoteCreate(poll_id=poll.id, option_id=python_option.id), voter1.id)
        poll_service.cast_vote(VoteCreate(poll_id=poll.id, option_id=python_option.id), voter2.id)
        poll_service.cast_vote(VoteCreate(poll_id=poll.id, option_id=js_option.id), voter3.id)

        results = poll_service.get_poll_results(poll.id)

        assert results is not None
        assert results.total_votes == 3

        # Find results for each option
        python_result = next(opt for opt in results.options if opt.text == "Python")
        js_result = next(opt for opt in results.options if opt.text == "JavaScript")
        java_result = next(opt for opt in results.options if opt.text == "Java")
        cpp_result = next(opt for opt in results.options if opt.text == "C++")

        assert python_result.vote_count == 2
        assert abs(python_result.percentage - 66.67) < 0.01  # 2/3 * 100, approximately

        assert js_result.vote_count == 1
        assert abs(js_result.percentage - 33.33) < 0.01  # 1/3 * 100, approximately

        assert java_result.vote_count == 0
        assert java_result.percentage == 0

        assert cpp_result.vote_count == 0
        assert cpp_result.percentage == 0

    def test_get_poll_results_nonexistent_poll(self, fresh_db, poll_service):
        result = poll_service.get_poll_results(999)
        assert result is None


class TestPollDeactivation:
    """Tests for poll deactivation."""

    def test_deactivate_poll_success(self, fresh_db, poll_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        assert poll.is_active

        result = poll_service.deactivate_poll(poll.id, test_user.id)
        assert result is True

        # Verify poll is deactivated
        updated_poll = poll_service.get_poll(poll.id)
        assert updated_poll is not None
        assert not updated_poll.is_active

    def test_deactivate_poll_not_creator(self, fresh_db, poll_service, user_service, test_user, test_poll_data):
        poll = poll_service.create_poll(test_poll_data, test_user.id)
        other_user = user_service.create_user("other", "other@example.com")

        result = poll_service.deactivate_poll(poll.id, other_user.id)
        assert result is False

        # Poll should remain active
        updated_poll = poll_service.get_poll(poll.id)
        assert updated_poll is not None
        assert updated_poll.is_active

    def test_deactivate_nonexistent_poll(self, fresh_db, poll_service, test_user):
        result = poll_service.deactivate_poll(999, test_user.id)
        assert result is False
