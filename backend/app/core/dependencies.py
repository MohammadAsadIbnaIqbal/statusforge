from fastapi import Depends, HTTPException, status, Header
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlmodel.ext.asyncio.session import AsyncSession
from sqlmodel import select
import firebase_admin.auth

from app.core.database import get_session
from app.models.user import User
from app.models.organization import Organization
from app.models.membership import Membership, Role

security = HTTPBearer()

def verify_firebase_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        decoded_token = firebase_admin.auth.verify_id_token(credentials.credentials)
        return decoded_token
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication credentials: {e}",
            headers={"WWW-Authenticate": "Bearer"},
        )

async def get_current_user_firebase(
    decoded_token: dict = Depends(verify_firebase_token),
    session: AsyncSession = Depends(get_session)
) -> User:
    firebase_uid = decoded_token.get("uid")
    if not firebase_uid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")
        
    statement = select(User).where(User.firebase_uid == firebase_uid)
    result = await session.exec(statement)
    user = result.first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found. Please bootstrap account.",
        )
    return user

async def get_organization_from_header(
    x_organization_id: int | None = Header(None),
    x_organization_slug: str | None = Header(None),
    session: AsyncSession = Depends(get_session)
) -> Organization:
    if not x_organization_id and not x_organization_slug:
        raise HTTPException(status_code=400, detail="Missing organization context")
        
    org = None
    if x_organization_id:
        org = await session.get(Organization, x_organization_id)
    elif x_organization_slug:
        statement = select(Organization).where(Organization.slug == x_organization_slug)
        org = (await session.exec(statement)).first()
        
    if not org:
        raise HTTPException(status_code=404, detail="Organization not found")
    return org

async def require_organization_member(
    current_user: User = Depends(get_current_user_firebase),
    organization: Organization = Depends(get_organization_from_header),
    session: AsyncSession = Depends(get_session)
) -> Membership:
    statement = select(Membership).where(
        Membership.user_id == current_user.id,
        Membership.organization_id == organization.id
    )
    membership = (await session.exec(statement)).first()
    
    if not membership:
        raise HTTPException(status_code=403, detail="Not a member of this organization")
        
    return membership

async def require_organization_admin(
    membership: Membership = Depends(require_organization_member)
) -> Membership:
    if membership.role not in (Role.OWNER, Role.ADMIN):
        raise HTTPException(status_code=403, detail="Requires ADMIN or OWNER role")
    return membership

async def require_organization_owner(
    membership: Membership = Depends(require_organization_member)
) -> Membership:
    if membership.role != Role.OWNER:
        raise HTTPException(status_code=403, detail="Requires OWNER role")
    return membership
