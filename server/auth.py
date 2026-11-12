from typing import Annotated

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

import models
from database import get_db


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, password_hash: str) -> bool:
    return bcrypt.checkpw(password.encode(), password_hash.encode())


# Used on EVERY route except /login. Pages get redirected to /login by the
# exception handler in main.py, /api routes get a 401 JSON response.
def get_current_user(request: Request, db: Annotated[Session, Depends(get_db)]) -> models.User:
    user_id = request.session.get("user_id")
    if user_id is not None:
        result = db.execute(select(models.User).where(models.User.id == user_id))
        user = result.scalars().first()
        if user:
            return user
    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Please log in")
