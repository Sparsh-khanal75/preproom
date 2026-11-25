from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..db import get_db
from ..models import User
from ..schemas import LoginIn, RegisterIn, UserOut
from ..security import auth_limiter, clear_session, current_user, hash_password, issue_session, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])
# A precomputed hash so failed logins for unknown emails take as long as wrong passwords (no user enumeration)
_DUMMY_HASH = hash_password("not-a-real-password-0000")


def out(u: User) -> UserOut:
    return UserOut(id=u.id, email=u.email, name=u.name, role=u.role)


@router.post("/register", response_model=UserOut, status_code=201, dependencies=[Depends(auth_limiter)])
async def register(body: RegisterIn, response: Response, db: AsyncSession = Depends(get_db)):
    email = body.email.lower()
    if await db.scalar(select(User.id).where(func.lower(User.email) == email)):
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")
    first = (await db.scalar(select(func.count(User.id)))) == 0
    user = User(
        email=email,
        name=body.name.strip(),
        password_hash=hash_password(body.password),
        role="admin" if first else "candidate",
    )  # the first account bootstraps the admin
    db.add(user)
    await db.commit()
    issue_session(response, user)
    return out(user)


@router.post("/login", response_model=UserOut, dependencies=[Depends(auth_limiter)])
async def login(body: LoginIn, response: Response, db: AsyncSession = Depends(get_db)):
    user = await db.scalar(select(User).where(func.lower(User.email) == body.email.lower()))
    ok = verify_password(body.password, user.password_hash if user else _DUMMY_HASH)
    if not user or not ok:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Wrong email or password")
    issue_session(response, user)
    return out(user)


@router.post("/logout", status_code=204)
async def logout(response: Response):
    clear_session(response)


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(current_user)):
    return out(user)
