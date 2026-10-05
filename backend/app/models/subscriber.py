from typing import TYPE_CHECKING
from datetime import datetime, timezone, timedelta
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel, UniqueConstraint

if TYPE_CHECKING:
    from app.models.organization import Organization

class SubscriberBase(SQLModel):
    email: str = Field(max_length=255)

class Subscriber(SubscriberBase, table=True):
    __tablename__ = "subscriber"
    __table_args__ = (
        UniqueConstraint("organization_id", "email", name="uq_subscriber_organization_email"),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    is_confirmed: bool = Field(default=False)
    confirmation_token: str | None = Field(default=None, max_length=64, index=True, unique=True)
    confirmation_token_expires_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)
    unsubscribe_token: str = Field(max_length=64, index=True, unique=True)
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    organization: "Organization" = Relationship(back_populates="subscribers")

class SubscriberCreate(SubscriberBase):
    pass
