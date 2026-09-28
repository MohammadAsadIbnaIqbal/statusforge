from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

from app.models.product import Product

class UserBase(SQLModel):
    username: str = Field(index=True, unique=True)
    email: str | None = Field(default=None, index=True)

class User(UserBase, table=True):
    __tablename__: str = "user"

    id: int | None = Field(default=None, primary_key=True)
    hashed_password: str

    # One-to-Many Relationship: A single user can have multiple products!
    products: list["Product"] = Relationship(back_populates="owner")

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int

class Token(SQLModel):
    access_token: str
    token_type: str = "bearer"