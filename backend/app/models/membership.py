from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
import sqlalchemy as sa
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User, UserResponse
    from app.models.organization import Organization

class Role(str, Enum):
    OWNER = "OWNER"
    ADMIN = "ADMIN"
    MEMBER = "MEMBER"
    VIEWER = "VIEWER"

class MembershipBase(SQLModel):
    role: Role = Field(
        default=Role.VIEWER,
        sa_type=sa.Enum(Role, native_enum=False, length=20)
    )

class Membership(MembershipBase, table=True):
    __tablename__: str = "membership"
    __table_args__ = (
        sa.UniqueConstraint("user_id", "organization_id", name="uq_membership_user_org"),
        sa.CheckConstraint(
            "role IN ('OWNER', 'ADMIN', 'MEMBER', 'VIEWER')",
            name="chk_membership_role"
        ),
    )

    id: int | None = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="user.id", index=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    user: "User" = Relationship(back_populates="memberships")
    organization: "Organization" = Relationship(back_populates="memberships")

class MembershipResponse(MembershipBase):
    id: int
    user_id: int
    organization_id: int
    created_at: datetime
    updated_at: datetime
