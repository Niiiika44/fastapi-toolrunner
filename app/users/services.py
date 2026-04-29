# смена email
# удаление пользователя
import uuid
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException

from app.users.models import User
from app.users.schemas import UserCreate, UserUpdate
from app.auth.hash_utils import get_password_hash, verify_password


async def get_user_by_id(user_id: uuid.UUID, db: AsyncSession):
    user = await db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_by_username(username: str, db: AsyncSession):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_user_by_email(email: str, db: AsyncSession):
    query = select(User).where(User.email == email)
    result = await db.execute(query)
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def create_user(user_data: UserCreate, db: AsyncSession):
    if not user_data.email.endswith("@ispras.ru"):
        raise HTTPException(status_code=400, detail="Only @ispras.ru email addresses are allowed")

    existing_user_query = select(User).where(User.email == user_data.email)
    result = await db.execute(existing_user_query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    username = user_data.email.rsplit("@", maxsplit=1)[0]
    user_data.password = get_password_hash(user_data.password)
    new_user = User(**user_data.model_dump(), username=username)
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user


async def update_user(user_id: uuid.UUID, user_data: UserUpdate, db: AsyncSession):
    user = await get_user_by_id(user_id, db)
    for field, value in user_data.model_dump(exclude_unset=True).items():
        setattr(user, field, value)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def change_password(user_id: uuid.UUID, old_password: str, new_password: str, db: AsyncSession):
    user = await get_user_by_id(user_id, db)
    if not verify_password(old_password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect old password")
    user.password = get_password_hash(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def change_email(user_id: uuid.UUID, new_email: str, password: str, db: AsyncSession):
    user = await get_user_by_id(user_id, db)

    if not verify_password(password, user.password):
        raise HTTPException(status_code=400, detail="Incorrect password")

    if not new_email.endswith("@ispras.ru"):
        raise HTTPException(status_code=400, detail="Only @ispras.ru email addresses are allowed")

    existing_user_query = select(User).where(User.email == new_email)
    result = await db.execute(existing_user_query)
    existing_user = result.scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    user.email = new_email
    user.username = new_email.rsplit("@", maxsplit=1)[0]
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def delete_user(user_id: uuid.UUID, db: AsyncSession):
    user = await get_user_by_id(user_id, db)
    await db.delete(user)
    await db.commit()


async def show_all(db: AsyncSession):
    query = select(User)
    result = await db.execute(query)
    return result.scalars().all()
