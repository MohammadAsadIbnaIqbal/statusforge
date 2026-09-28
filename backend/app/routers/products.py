from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
from fastapi_cache.decorator import cache

from app.core.database import get_session
from app.models.product import Product, ProductCreate
from app.models.user import User
from app.routers.auth import get_current_user

router = APIRouter(prefix="/products", tags=["Products"])

@router.post("", response_model=Product)
async def create_product(
    product_data: ProductCreate,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    db_product = Product.model_validate(
        product_data, update={"owner_id": current_user.id}
    )
    session.add(db_product)
    await session.commit()
    await session.refresh(db_product)
    return db_product

@router.get("", response_model=list[Product])
@cache(expire=60)
async def read_products(
    session: AsyncSession = Depends(get_session)
):
    result = await session.exec(select(Product))
    products = result.all()
    return products

@router.delete("/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    product_id: int,
    session: AsyncSession = Depends(get_session),
    current_user: User = Depends(get_current_user)
):
    product = await session.get(Product, product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Product not found"
        )
        
    # Check ownership!
    if product.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="Not authorized to delete this product"
        )

    await session.delete(product)
    await session.commit()
    return None