from uuid import UUID
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, or_
from sqlalchemy.exc import IntegrityError
from app.models.user import User

class UserService:
    """
    Handles syncing authenticated Supabase users into our local database.
    Ensures that every user has a corresponding record in the `users` table.
    """

    @staticmethod
    async def sync_supabase_user(session: AsyncSession, supabase_user_id: UUID, email: str) -> User:
        """
        Check if user exists locally by supabase_user_id or email.
        If existing, update supabase_user_id if needed.
        If not, create them.
        """
        norm_email = email.strip().lower()

        # Try to fetch existing user by supabase_user_id OR email
        stmt = (
            select(User)
            .where(or_(User.supabase_user_id == supabase_user_id, User.email == norm_email))
        )
        result = await session.execute(stmt)
        user = result.scalars().first()

        if user:
            if user.supabase_user_id != supabase_user_id:
                user.supabase_user_id = supabase_user_id
                await session.commit()
                result = await session.execute(stmt)
                user = result.scalars().first()
            return user

        # User doesn't exist, create user record
        new_user = User(
            supabase_user_id=supabase_user_id,
            email=norm_email,
            is_active=True,
            is_deleted=False,
        )
        session.add(new_user)

        try:
            await session.commit()
            result = await session.execute(
                select(User).where(User.supabase_user_id == supabase_user_id)
            )
            found = result.scalars().first()
            if found is None:
                raise RuntimeError("User not found after commit.")
            return found
        except IntegrityError:
            await session.rollback()
            result = await session.execute(stmt)
            found = result.scalars().first()
            if found is None:
                raise RuntimeError("User not found after rollback sync.")
            return found

