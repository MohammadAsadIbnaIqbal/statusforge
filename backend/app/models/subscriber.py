from typing import TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.user import User

class SubscriberBase(SQLModel):
    email: str = Field(max_length=255)

class Subscriber(SubscriberBase, table=True):
    __tablename__ = "subscriber"
    __table_args__ = (
        UniqueConstraint("owner_id", "email", name="uq_subscriber_owner_email"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    is_confirmed: bool = Field(default=False)
    confirmation_token: str | None = Field(default=None, max_length=64, index=True, unique=True)
    confirmation_token_expires_at: datetime | None = Field(default=None)
    unsubscribe_token: str = Field(max_length=64, index=True, unique=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    owner: "User" = Relationship(back_populates="subscribers")

class SubscriberCreate(SubscriberBase):
    pass
