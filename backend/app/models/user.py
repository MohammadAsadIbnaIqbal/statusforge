from typing import TYPE_CHECKING
from datetime import datetime, timezone
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.service import Service
    from app.models.incident import Incident
    from app.models.subscriber import Subscriber

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True, max_length=30)
    email: str = Field(index=True, unique=True, max_length=255)
    organization_name: str = Field(max_length=100)

class User(UserBase, table=True):
    __tablename__: str = "user"

    id: int | None = Field(default=None, primary_key=True)
    organization_slug: str = Field(max_length=100, index=True, unique=True)
    hashed_password: str = Field(max_length=255)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    services: list["Service"] = Relationship(back_populates="owner", cascade_delete=True)
    incidents: list["Incident"] = Relationship(back_populates="owner", cascade_delete=True)
    subscribers: list["Subscriber"] = Relationship(back_populates="owner", cascade_delete=True)

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    organization_slug: str
    created_at: datetime
    updated_at: datetime

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"

class UserRegistrationResponse(UserResponse):
    access_token: str
    token_type: str = "bearer"