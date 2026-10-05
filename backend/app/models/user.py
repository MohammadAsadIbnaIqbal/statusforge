from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.organization import Organization

class UserBase(SQLModel):
    email: str = Field(index=True, unique=True, max_length=255)
    display_name: str | None = Field(default=None, max_length=100)
    photo_url: str | None = Field(default=None, max_length=500)
    email_verified: bool = Field(default=False)

class User(UserBase, table=True):
    __tablename__: str = "user"

    id: int | None = Field(default=None, primary_key=True)
    firebase_uid: str = Field(max_length=128, index=True, unique=True)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    memberships: list["Membership"] = Relationship(back_populates="user", cascade_delete=True)

class UserResponse(UserBase):
    id: int
    created_at: datetime
    updated_at: datetime