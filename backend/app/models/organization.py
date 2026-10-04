from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.membership import Membership
    from app.models.service import Service
    from app.models.incident import Incident
    from app.models.subscriber import Subscriber
    from app.models.invitation import Invitation

class OrganizationBase(SQLModel):
    name: str = Field(max_length=100)
    slug: str = Field(max_length=100, index=True, unique=True)

class Organization(OrganizationBase, table=True):
    __tablename__: str = "organization"

    id: int | None = Field(default=None, primary_key=True)
    created_by: int | None = Field(foreign_key="user.id", default=None)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    memberships: list["Membership"] = Relationship(back_populates="organization", cascade_delete=True)
    invitations: list["Invitation"] = Relationship(back_populates="organization", cascade_delete=True)
    services: list["Service"] = Relationship(back_populates="organization", cascade_delete=True)
    incidents: list["Incident"] = Relationship(back_populates="organization", cascade_delete=True)
    subscribers: list["Subscriber"] = Relationship(back_populates="organization", cascade_delete=True)

class OrganizationResponse(OrganizationBase):
    id: int
    created_at: datetime
    updated_at: datetime
