from datetime import timedelta
import jwt
from fastapi import APIRouter, Depends, HTTPException, status, Request
from slowapi import Limiter
from slowapi.util import get_remote_address
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession
import argon2.exceptions as argon2_exceptions
from arq import create_pool

from app.core.config import settings
from app.core.database import get_session
from app.core.security import ph, create_access_token
from app.models.user import User, UserCreate, UserResponse, Token
from app.worker import get_redis_settings

limiter = Limiter(key_func=get_remote_address)
router = APIRouter(tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    session: AsyncSession = Depends(get_session)
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        username: str | None = payload.get("sub")
        if username is None:
            raise credentials_exception
    except jwt.PyJWTError:
        raise credentials_exception

    statement = select(User).where(User.username == username)
    result = await session.exec(statement)
    user = result.first()
    if user is None:
        raise credentials_exception
    return user


@router.post("/register", response_model=UserResponse)
@limiter.limit("5/minute")
async def register_user(
    request: Request,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)  # 👈 Removed background_tasks
):
    statement = select(User).where(User.username == user_data.username)
    result = await session.exec(statement)
    existing_user = result.first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already exists."
        )

    secure_hash = ph.hash(user_data.password)

    new_user = User(
        username=user_data.username,
        email=user_data.email,
        hashed_password=secure_hash
    )

    session.add(new_user)
    await session.commit()
    await session.refresh(new_user)

    # 🚀 Enqueue job into Redis via ARQ for dedicated worker processing
    if new_user.email:
        try:
            redis = await create_pool(get_redis_settings())
            await redis.enqueue_job('send_welcome_email_task', email=new_user.email, username=new_user.username)
        except Exception as e:
            print(f"Failed to enqueue task to ARQ worker: {e}")

    return new_user


@router.post("/login", response_model=Token)
@limiter.limit("10/minute")
async def login_user(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session)
):
    statement = select(User).where(User.username == form_data.username)
    result = await session.exec(statement)
    user = result.first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        ph.verify(user.hashed_password, form_data.password)
    except argon2_exceptions.VerificationError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )
    
    return Token(access_token=access_token, token_type="bearer")


@router.get("/users/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    return current_user