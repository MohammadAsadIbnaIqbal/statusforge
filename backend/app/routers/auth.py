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
from app.models.user import User, UserCreate, UserResponse, Token, UserRegistrationResponse
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


import re

async def generate_unique_slug(session: AsyncSession, base_name: str) -> str:
    base_slug = re.sub(r'[^a-z0-9]+', '-', base_name.lower()).strip('-')
    if not base_slug:
        base_slug = "org"
        
    slug = base_slug[:100]
    counter = 1
    while True:
        statement = select(User).where(User.organization_slug == slug)
        if not (await session.exec(statement)).first():
            return slug
        counter += 1
        suffix = f"-{counter}"
        slug = f"{base_slug[:100 - len(suffix)]}{suffix}"


@router.post("/register", response_model=UserRegistrationResponse, status_code=201)
@limiter.limit("5/minute")
async def register_user(
    request: Request,
    user_data: UserCreate,
    session: AsyncSession = Depends(get_session)  # 👈 Removed background_tasks
):
    statement = select(User).where(User.username == user_data.username)
    if (await session.exec(statement)).first():
        raise HTTPException(status_code=409, detail="Username already taken")
        
    statement = select(User).where(User.email == user_data.email)
    if (await session.exec(statement)).first():
        raise HTTPException(status_code=409, detail="Email already registered")
        
    from sqlalchemy.exc import IntegrityError
    
    secure_hash = ph.hash(user_data.password)

    max_retries = 3
    for attempt in range(max_retries):
        organization_slug = await generate_unique_slug(session, user_data.organization_name)
        
        new_user = User(
            username=user_data.username,
            email=user_data.email,
            organization_name=user_data.organization_name,
            organization_slug=organization_slug,
            hashed_password=secure_hash
        )

        session.add(new_user)
        try:
            await session.commit()
            await session.refresh(new_user)
            break
        except IntegrityError:
            await session.rollback()
            if attempt == max_retries - 1:
                raise HTTPException(
                    status_code=409, 
                    detail="A conflict occurred during registration. Please try again or use a different username/email."
                )

    # 🚀 Enqueue job into Redis via ARQ for dedicated worker processing
    if new_user.email:
        try:
            redis = await create_pool(get_redis_settings(fast_fail=True))
            await redis.enqueue_job('send_welcome_email_task', email=new_user.email, username=new_user.username)
        except Exception as e:
            print(f"Failed to enqueue task to ARQ worker: {e}")

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": new_user.username}, expires_delta=access_token_expires
    )

    return UserRegistrationResponse(
        id=new_user.id,
        username=new_user.username,
        email=new_user.email,
        organization_name=new_user.organization_name,
        organization_slug=new_user.organization_slug,
        created_at=new_user.created_at,
        updated_at=new_user.updated_at,
        access_token=access_token
    )


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