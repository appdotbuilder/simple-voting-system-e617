from sqlmodel import SQLModel, Field, Relationship, UniqueConstraint
from datetime import datetime
from typing import Optional, List


# Persistent models (stored in database)
class User(SQLModel, table=True):
    __tablename__ = "users"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    username: str = Field(max_length=50, unique=True)
    email: str = Field(max_length=255, unique=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    created_polls: List["Poll"] = Relationship(back_populates="creator")
    votes: List["Vote"] = Relationship(back_populates="user")


class Poll(SQLModel, table=True):
    __tablename__ = "polls"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    creator_id: int = Field(foreign_key="users.id")
    is_active: bool = Field(default=True)
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    creator: User = Relationship(back_populates="created_polls")
    options: List["Option"] = Relationship(back_populates="poll", cascade_delete=True)
    votes: List["Vote"] = Relationship(back_populates="poll")


class Option(SQLModel, table=True):
    __tablename__ = "options"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    text: str = Field(max_length=500)
    poll_id: int = Field(foreign_key="polls.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    poll: Poll = Relationship(back_populates="options")
    votes: List["Vote"] = Relationship(back_populates="option")


class Vote(SQLModel, table=True):
    __tablename__ = "votes"  # type: ignore[assignment]

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id")
    poll_id: int = Field(foreign_key="polls.id")
    option_id: int = Field(foreign_key="options.id")
    created_at: datetime = Field(default_factory=datetime.utcnow)

    # Relationships
    user: User = Relationship(back_populates="votes")
    poll: Poll = Relationship(back_populates="votes")
    option: Option = Relationship(back_populates="votes")

    # Ensure one vote per user per poll
    __table_args__ = (UniqueConstraint("user_id", "poll_id", name="unique_user_poll_vote"),)


# Non-persistent schemas (for validation, forms, API requests/responses)
class UserCreate(SQLModel, table=False):
    username: str = Field(max_length=50)
    email: str = Field(max_length=255)


class PollCreate(SQLModel, table=False):
    title: str = Field(max_length=200)
    description: str = Field(default="", max_length=1000)
    options: List[str] = Field(min_items=2, max_items=10)


class PollUpdate(SQLModel, table=False):
    title: Optional[str] = Field(default=None, max_length=200)
    description: Optional[str] = Field(default=None, max_length=1000)
    is_active: Optional[bool] = Field(default=None)


class VoteCreate(SQLModel, table=False):
    poll_id: int
    option_id: int


class PollResults(SQLModel, table=False):
    poll_id: int
    title: str
    description: str
    total_votes: int
    options: List["OptionResult"]


class OptionResult(SQLModel, table=False):
    option_id: int
    text: str
    vote_count: int
    percentage: float
