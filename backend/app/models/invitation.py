from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
import sqlalchemy as sa
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.membership import Role

class InvitationBase(SQLModel):
    email: str = Field(index=True, max_length=255)
    role: str = Field(max_length=20) # We use str to avoid circular enum import or just duplicate Enum

class Invitation(InvitationBase, table=True):
    __tablename__: str = "invitation"
    __table_args__ = (
        sa.CheckConstraint(
            "role IN ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER')",
            name="chk_invitation_role"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    
    token_hash: str = Field(max_length=255, unique=True, index=True)
    
    invited_by_user_id: int = Field(foreign_key="user.id")
    
    expires_at: datetime = Field(sa_type=DateTime(timezone=True))
    accepted_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)
    revoked_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    organization: "Organization" = Relationship(back_populates="invitations")

class InvitationResponse(InvitationBase):
    id: int
    organization_id: int
    invited_by_user_id: int
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime
