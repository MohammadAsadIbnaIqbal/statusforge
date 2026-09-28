from typing import TYPE_CHECKING
from sqlmodel import Field, Relationship, SQLModel

if TYPE_CHECKING:
    from app.models.user import User

class ProductBase(SQLModel):
    name: str
    price: float
    in_stock: bool = True

class Product(ProductBase, table=True):
    __tablename__ = "product"
    
    id: int | None = Field(default=None, primary_key=True)
    
    # 1. Foreign Key linking to the 'user' table's 'id' column
    owner_id: int = Field(foreign_key="user.id")
    
    # 2. Relationship linking back to the User model object
    owner: "User" = Relationship(back_populates="products")

class ProductCreate(ProductBase):
    pass