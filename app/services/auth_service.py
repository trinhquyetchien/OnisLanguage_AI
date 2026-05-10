from __future__ import annotations

import random
import string
from datetime import datetime, timedelta, timezone
from typing import Dict, Optional, Union
from uuid import uuid4

import jwt
from fastapi import HTTPException, status
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.session import SessionLocal
from app.db.models import User
from app.schemas.auth import (
    AuthLoginRequest, 
    AuthRegisterRequest, 
    AuthResponse, 
    UserResponse,
    OtpVerifyRequest,
    OtpResponse,
    ProfileUpdateRequest,
    EmailChangeVerifyRequest
)
from app.services.email_service import email_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    def __init__(self) -> None:
        # Stores OTPs: {email: {"otp": code, "expires": datetime, "data": pending_user_data, "type": str, "user_id": str}}
        self._pending_otps: Dict[str, dict] = {}

    async def initiate_register(self, request: AuthRegisterRequest) -> OtpResponse:
        db = SessionLocal()
        try:
            existing_user = db.query(User).filter(User.email == request.email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="User already exists")
            
            otp = self._generate_otp()
            expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
            
            self._pending_otps[request.email] = {
                "otp": otp,
                "expires": expiry,
                "data": request.model_dump(),
                "type": "registration"
            }
            
            await email_service.send_otp_email(request.email, otp)
            
            return OtpResponse(
                message="OTP đã được gửi về email của bạn.",
                email=request.email
            )
        finally:
            db.close()

    def verify_registration(self, request: OtpVerifyRequest) -> AuthResponse:
        pending = self._pending_otps.get(request.email)
        if not pending or pending.get("type") != "registration":
            raise HTTPException(status_code=400, detail="No pending registration found")
        
        if datetime.now(timezone.utc) > pending["expires"]:
            del self._pending_otps[request.email]
            raise HTTPException(status_code=400, detail="OTP expired")
        
        if pending["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Complete registration in DB
        db = SessionLocal()
        try:
            user_data = pending["data"]
            new_user = User(
                email=user_data["email"],
                password_hash=self._hash_password(user_data["password"]),
                display_name=user_data["display_name"] or user_data["email"].split("@")[0],
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Cleanup
            del self._pending_otps[request.email]
            
            token = self.create_access_token({"sub": str(new_user.user_id)})
            return AuthResponse(
                access_token=token,
                user=UserResponse(
                    user_id=str(new_user.user_id), 
                    email=new_user.email, 
                    display_name=new_user.display_name
                ),
            )
        except Exception as e:
            db.rollback()
            raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")
        finally:
            db.close()

    def login(self, request: AuthLoginRequest) -> AuthResponse:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.email == request.email).first()
            if not user or not self._verify_password(request.password, user.password_hash):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Incorrect email or password",
                )
            
            token = self.create_access_token({"sub": str(user.user_id)})
            return AuthResponse(
                access_token=token,
                user=UserResponse(
                    user_id=str(user.user_id), 
                    email=user.email, 
                    display_name=user.display_name
                ),
            )
        finally:
            db.close()

    async def update_profile(self, user_id: str, request: ProfileUpdateRequest) -> Union[OtpResponse, UserResponse]:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")

            if request.display_name is not None:
                user.display_name = request.display_name
            if request.avatar_url is not None:
                user.avatar_url = request.avatar_url

            # Handle email change with OTP
            if request.email is not None and request.email.lower() != str(user.email).lower():
                existing = db.query(User).filter(User.email == request.email.lower()).first()
                if existing:
                    raise HTTPException(status_code=400, detail="Email already in use")
                
                otp = self._generate_otp()
                expiry = datetime.now(timezone.utc) + timedelta(minutes=10)
                
                self._pending_otps[request.email.lower()] = {
                    "otp": otp,
                    "expires": expiry,
                    "type": "email_change",
                    "user_id": user_id
                }
                
                await email_service.send_otp_email(request.email.lower(), otp)
                db.commit()
                return OtpResponse(message="Mã xác thực đã được gửi đến email mới của bạn.", email=request.email.lower())

            db.commit()
            db.refresh(user)
            return UserResponse(user_id=str(user.user_id), email=user.email, display_name=user.display_name)
        finally:
            db.close()

    def verify_email_change(self, user_id: str, request: EmailChangeVerifyRequest) -> UserResponse:
        pending = self._pending_otps.get(request.new_email.lower())
        if not pending or pending.get("type") != "email_change" or pending.get("user_id") != user_id:
            raise HTTPException(status_code=400, detail="No pending email change found")
        
        if datetime.now(timezone.utc) > pending["expires"]:
            del self._pending_otps[request.new_email.lower()]
            raise HTTPException(status_code=400, detail="OTP expired")
        
        if pending["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            user.email = request.new_email.lower()
            db.commit()
            db.refresh(user)
            
            del self._pending_otps[request.new_email.lower()]
            
            return UserResponse(user_id=str(user.user_id), email=user.email, display_name=user.display_name)
        finally:
            db.close()

    def create_access_token(self, data: dict, expires_delta: Optional[timedelta] = None):
        to_encode = data.copy()
        if expires_delta:
            expire = datetime.now(timezone.utc) + expires_delta
        else:
            expire = datetime.now(timezone.utc) + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        to_encode.update({"exp": expire})
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt

    def _hash_password(self, password: str) -> str:
        return pwd_context.hash(password)

    def _verify_password(self, plain_password: str, hashed_password: str) -> bool:
        return pwd_context.verify(plain_password, hashed_password)

    def _generate_otp(self, length: int = 6) -> str:
        return ''.join(random.choices(string.digits, k=length))

    def seed_dummy_user(self):
        db = SessionLocal()
        try:
            dummy_email = "demo@onis.app"
            user = db.query(User).filter(User.email == dummy_email).first()
            if not user:
                new_user = User(
                    email=dummy_email,
                    password_hash=self._hash_password("123456"),
                    display_name="Onis Demo",
                )
                db.add(new_user)
                db.commit()
                print(f"Seeded dummy user: {dummy_email}")
        finally:
            db.close()

auth_service = AuthService()
auth_service.seed_dummy_user()
