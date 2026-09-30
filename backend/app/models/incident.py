from typing import TYPE_CHECKING
from datetime import datetime, timezone
import sqlalchemy as sa
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
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
    status: IncidentStatus = Field(default=IncidentStatus.INVESTIGATING)
    impact: IncidentImpact

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
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: datetime | None = Field(default=None)

    owner: "User" = Relationship(back_populates="incidents")
    service_links: list["IncidentServiceLink"] = Relationship(back_populates="incident", cascade_delete=True)
    updates: list["IncidentUpdate"] = Relationship(back_populates="incident", cascade_delete=True)

class IncidentUpdateBase(SQLModel):
    status: IncidentStatus
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
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    incident: Incident = Relationship(back_populates="updates")

class IncidentCreate(IncidentBase):
    service_ids: list[int]
    message: str

class IncidentUpdateCreate(IncidentUpdateBase):
    pass

from app.models.service import ServiceResponse

class IncidentResponse(IncidentBase):
    id: int
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None
    services: list[ServiceResponse] = []
    updates: list[IncidentUpdate] = []
