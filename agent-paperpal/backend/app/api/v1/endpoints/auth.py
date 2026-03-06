# backend/app/api/v1/endpoints/auth.py
from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import get_db
from app.models.user import User
from app.schemas.user import UserCreate, Token, UserLogin
from app.services.auth_service import auth_service

router = APIRouter()

@router.post("/signup", response_model=Token, status_code=status.HTTP_201_CREATED)
async def signup(user_in: UserCreate, db: AsyncSession = Depends(get_db)):
    # Check if user already exists
    stmt = select(User).where(User.email == user_in.email)
    result = await db.execute(stmt)
    user = result.scalars().first()
    if user:
        raise HTTPException(
            status_code=400,
            detail="User with this email already exists"
        )
    
    # Create new user
    new_user = User(
        email=user_in.email,
        full_name=user_in.full_name,
        hashed_password=auth_service.get_password_hash(user_in.password),
        is_active=True
    )
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    
    # Return access token immediately
    access_token = auth_service.create_access_token(
        data={"sub": str(new_user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/login", response_model=Token)
async def login(
    # Handle both JSON and Form (FastAPI OAuth2 preference)
    username: str = Form(...),
    password: str = Form(...),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(User).where(User.email == username)
    result = await db.execute(stmt)
    user = result.scalars().first()
    
    if not user or not auth_service.verify_password(password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token = auth_service.create_access_token(
        data={"sub": str(user.id)}
    )
    return {"access_token": access_token, "token_type": "bearer"}
