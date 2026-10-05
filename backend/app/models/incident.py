from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
import sqlalchemy as sa
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.organization import Organization
    from app.models.user import User
    from app.models.service import Service

class IncidentStatus(str, Enum):
    INVESTIGATING = "INVESTIGATING"
    IDENTIFIED = "IDENTIFIED"
    MONITORING = "MONITORING"
    RESOLVED = "RESOLVED"

class IncidentImpact(str, Enum):
    NONE = "NONE"
    MINOR = "MINOR"
    MAJOR = "MAJOR"
    CRITICAL = "CRITICAL"

class IncidentServiceLink(SQLModel, table=True):
    __tablename__ = "incident_services"
    incident_id: int = Field(foreign_key="incident.id", primary_key=True)
    service_id: int = Field(foreign_key="service.id", primary_key=True)
    
    incident: "Incident" = Relationship(back_populates="service_links")
    service: "Service" = Relationship(back_populates="incident_links")

class IncidentBase(SQLModel):
    title: str = Field(max_length=200)
    status: IncidentStatus = Field(
        default=IncidentStatus.INVESTIGATING,
        sa_type=sa.Enum(IncidentStatus, native_enum=False, length=20)
    )
    impact: IncidentImpact = Field(
        sa_type=sa.Enum(IncidentImpact, native_enum=False, length=20)
    )

class Incident(IncidentBase, table=True):
    __tablename__ = "incident"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED')",
            name="chk_incident_status"
        ),
        sa.CheckConstraint(
            "impact IN ('NONE', 'MINOR', 'MAJOR', 'CRITICAL')",
            name="chk_incident_impact"
        ),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    organization_id: int = Field(foreign_key="organization.id", index=True)
    created_by_user_id: int | None = Field(foreign_key="user.id", default=None)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = Field(sa_type=DateTime(timezone=True), default=None)

    organization: "Organization" = Relationship(back_populates="incidents")
    service_links: list["IncidentServiceLink"] = Relationship(back_populates="incident", cascade_delete=True)
    updates: list["IncidentUpdate"] = Relationship(back_populates="incident", cascade_delete=True)

class IncidentUpdateBase(SQLModel):
    status: IncidentStatus = Field(
        sa_type=sa.Enum(IncidentStatus, native_enum=False, length=20)
    )
    message: str

class IncidentUpdate(IncidentUpdateBase, table=True):
    __tablename__ = "incident_updates"
    __table_args__ = (
        sa.CheckConstraint(
            "status IN ('INVESTIGATING', 'IDENTIFIED', 'MONITORING', 'RESOLVED')",
            name="chk_incident_update_status"
        ),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    incident_id: int = Field(foreign_key="incident.id", index=True)
    created_by_user_id: int | None = Field(foreign_key="user.id", default=None)
    
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))

    incident: Incident = Relationship(back_populates="updates")

class IncidentCreate(IncidentBase):
    service_ids: list[int]
    message: str

class IncidentUpdateCreate(IncidentUpdateBase):
    pass

from app.models.service import ServiceResponse

class IncidentResponse(IncidentBase):
    id: int
    organization_id: int
    created_by_user_id: int | None
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    services: list[ServiceResponse] = []
    updates: list[IncidentUpdate] = []
