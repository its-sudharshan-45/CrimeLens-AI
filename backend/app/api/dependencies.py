from supabase import Client
import uuid
from typing import Annotated, List

from fastapi import Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.supabase import supabase_client
from app.db.session import get_db
from app.services.auth_service import AuthService
from app.services.user_service import UserService
from app.models.user import User
from app.core.exceptions import UnauthorizedException, ForbiddenException


def get_supabase() -> Client:
    """
    FastAPI dependency that returns the Supabase client instance.
    This allows route handlers to easily inject the Supabase client.
    """
    return supabase_client

# Reusable security scheme
security = HTTPBearer()

async def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
    db: AsyncSession = Depends(get_db)
) -> User:
    """
    Dependency that validates the JWT token and returns the current user.
    If the user doesn't exist locally yet, it synchronizes them from Supabase.
    """
    token = credentials.credentials
    payload = AuthService.verify_token(token)
    
    supabase_user_id_str = payload.get("sub")
    email = payload.get("email")
    
    if not supabase_user_id_str or not email:
        raise UnauthorizedException(detail="Invalid token payload")
        
    try:
        supabase_user_id = uuid.UUID(supabase_user_id_str)
    except ValueError:
         raise UnauthorizedException(detail="Invalid user ID format")
         
    user = await UserService.sync_supabase_user(db, supabase_user_id, email)
    return user

async def get_current_active_user(
    current_user: Annotated[User, Depends(get_current_user)]
) -> User:
    """
    Dependency that ensures the current user is active and not softly deleted.
    """
    if not current_user.is_active or current_user.is_deleted:
        raise ForbiddenException(detail="User is inactive or deleted")
    return current_user
