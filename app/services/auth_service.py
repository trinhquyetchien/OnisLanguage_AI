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
    ,
    PasswordChangeRequest,
    PasswordChangeVerifyRequest,
)
from app.services.email_service import email_service

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class AuthService:
    OTP_TTL_MINUTES = 10
    OTP_RESEND_COOLDOWN_SECONDS = 45

    def __init__(self) -> None:
        # Stores OTPs: {email: {"otp": code, "expires": datetime, "data": pending_user_data, "type": str, "user_id": str}}
        self._pending_otps: Dict[str, dict] = {}

    @staticmethod
    def _password_change_key(user_id: str) -> str:
        return f"password_change:{user_id}"

    def _enforce_otp_cooldown(self, key: str) -> None:
        pending = self._pending_otps.get(key)
        if not pending:
            return
        issued_at: datetime | None = pending.get("issued_at")
        if issued_at is None:
            return
        elapsed = (datetime.now(timezone.utc) - issued_at).total_seconds()
        if elapsed < self.OTP_RESEND_COOLDOWN_SECONDS:
            wait_seconds = int(self.OTP_RESEND_COOLDOWN_SECONDS - elapsed) + 1
            raise HTTPException(
                status_code=429,
                detail=f"Please wait {wait_seconds}s before requesting a new OTP.",
            )

    async def initiate_register(self, request: AuthRegisterRequest) -> OtpResponse:
        normalized_email = request.email.lower().strip()
        db = SessionLocal()
        try:
            existing_user = db.query(User).filter(User.email == normalized_email).first()
            if existing_user:
                raise HTTPException(status_code=400, detail="User already exists")
            self._enforce_otp_cooldown(normalized_email)
            
            otp = self._generate_otp()
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(minutes=self.OTP_TTL_MINUTES)
            
            self._pending_otps[normalized_email] = {
                "otp": otp,
                "expires": expiry,
                "issued_at": now,
                "data": request.model_dump(),
                "type": "registration"
            }
            
            await email_service.send_otp_email(normalized_email, otp)
            
            return OtpResponse(
                message="OTP đã được gửi về email của bạn.",
                email=normalized_email
            )
        finally:
            db.close()

    def verify_registration(self, request: OtpVerifyRequest) -> AuthResponse:
        normalized_email = request.email.lower().strip()
        pending = self._pending_otps.get(normalized_email)
        if not pending or pending.get("type") != "registration":
            raise HTTPException(status_code=400, detail="No pending registration found")
        
        if datetime.now(timezone.utc) > pending["expires"]:
            del self._pending_otps[normalized_email]
            raise HTTPException(status_code=400, detail="OTP expired")
        
        if pending["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")
        
        # Complete registration in DB
        db = SessionLocal()
        try:
            user_data = pending["data"]
            new_user = User(
                email=normalized_email,
                password_hash=self._hash_password(user_data["password"]),
                display_name=user_data["display_name"] or normalized_email.split("@")[0],
            )
            db.add(new_user)
            db.commit()
            db.refresh(new_user)
            
            # Cleanup
            del self._pending_otps[normalized_email]
            
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
                self._enforce_otp_cooldown(request.email.lower())
                now = datetime.now(timezone.utc)
                expiry = now + timedelta(minutes=self.OTP_TTL_MINUTES)
                
                self._pending_otps[request.email.lower()] = {
                    "otp": otp,
                    "expires": expiry,
                    "issued_at": now,
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

    async def initiate_password_change(self, user_id: str, request: PasswordChangeRequest) -> OtpResponse:
        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            if not self._verify_password(request.current_password, user.password_hash):
                raise HTTPException(status_code=400, detail="Current password is incorrect")

            otp = self._generate_otp()
            key = self._password_change_key(user_id)
            self._enforce_otp_cooldown(key)
            now = datetime.now(timezone.utc)
            expiry = now + timedelta(minutes=self.OTP_TTL_MINUTES)
            self._pending_otps[key] = {
                "otp": otp,
                "expires": expiry,
                "issued_at": now,
                "type": "password_change",
                "user_id": user_id,
                "new_password": request.new_password,
            }

            await email_service.send_otp_email(user.email, otp)
            return OtpResponse(
                message="Mã OTP đổi mật khẩu đã được gửi vào email của bạn.",
                email=user.email,
            )
        finally:
            db.close()

    def verify_password_change(self, user_id: str, request: PasswordChangeVerifyRequest) -> UserResponse:
        key = self._password_change_key(user_id)
        pending = self._pending_otps.get(key)
        if not pending or pending.get("type") != "password_change" or pending.get("user_id") != user_id:
            raise HTTPException(status_code=400, detail="No pending password change found")

        if datetime.now(timezone.utc) > pending["expires"]:
            del self._pending_otps[key]
            raise HTTPException(status_code=400, detail="OTP expired")

        if pending["otp"] != request.otp:
            raise HTTPException(status_code=400, detail="Invalid OTP")

        db = SessionLocal()
        try:
            user = db.query(User).filter(User.user_id == user_id).first()
            if not user:
                raise HTTPException(status_code=404, detail="User not found")
            user.password_hash = self._hash_password(pending["new_password"])
            db.commit()
            db.refresh(user)
            del self._pending_otps[key]
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
