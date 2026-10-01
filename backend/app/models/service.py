from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlalchemy import DateTime
import sqlalchemy as sa
from enum import Enum
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.incident import IncidentServiceLink

class ServiceStatus(str, Enum):
    OPERATIONAL = "OPERATIONAL"
    DEGRADED_PERFORMANCE = "DEGRADED_PERFORMANCE"
    PARTIAL_OUTAGE = "PARTIAL_OUTAGE"
    MAJOR_OUTAGE = "MAJOR_OUTAGE"
    UNDER_MAINTENANCE = "UNDER_MAINTENANCE"

class ServiceBase(SQLModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)
    current_status: ServiceStatus = Field(default=ServiceStatus.OPERATIONAL)
    display_order: int = Field(default=0)
    is_visible: bool = Field(default=True)

class Service(ServiceBase, table=True):
    __tablename__ = "service"
    __table_args__ = (
        sa.CheckConstraint(
            "current_status IN ('OPERATIONAL', 'DEGRADED_PERFORMANCE', 'PARTIAL_OUTAGE', 'MAJOR_OUTAGE', 'UNDER_MAINTENANCE')",
            name="chk_service_status"
        ),
    )
    
    id: int | None = Field(default=None, primary_key=True)
    owner_id: int = Field(foreign_key="user.id", index=True)
    created_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(sa_type=DateTime(timezone=True), default_factory=lambda: datetime.now(timezone.utc))
    
    owner: "User" = Relationship(back_populates="services")
    incident_links: list["IncidentServiceLink"] = Relationship(back_populates="service", cascade_delete=True)

class ServiceCreate(SQLModel):
    name: str = Field(max_length=100)
    description: str | None = Field(default=None, max_length=500)

class ServiceUpdate(SQLModel):
    name: str | None = Field(default=None, max_length=100)
    description: str | None = Field(default=None, max_length=500)
    display_order: int | None = Field(default=None)
    is_visible: bool | None = Field(default=None)
class ServiceResponse(ServiceBase):
    id: int
    owner_id: int
    created_at: datetime
    updated_at: datetime
