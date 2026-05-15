from fastapi import APIRouter, Depends
from typing import Union

from app.api import deps
from app.db.models import User
from app.schemas.auth import (
    AuthLoginRequest, 
    AuthRegisterRequest, 
    AuthResponse,
    OtpVerifyRequest,
    OtpResponse,
    ProfileUpdateRequest,
    EmailChangeVerifyRequest,
    UserResponse,
    PasswordChangeRequest,
    PasswordChangeVerifyRequest,
)
from app.services.auth_service import auth_service

router = APIRouter()


@router.post("/register/initiate", response_model=OtpResponse)
async def initiate_register(request: AuthRegisterRequest):
    return await auth_service.initiate_register(request)


@router.post("/register/verify", response_model=AuthResponse)
async def verify_register(request: OtpVerifyRequest):
    return auth_service.verify_registration(request)


@router.post("/login", response_model=AuthResponse)
async def login(request: AuthLoginRequest):
    return auth_service.login(request)


@router.patch("/profile", response_model=Union[OtpResponse, UserResponse])
async def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return await auth_service.update_profile(str(current_user.user_id), request)


@router.post("/profile/verify-email", response_model=UserResponse)
async def verify_email_change(
    request: EmailChangeVerifyRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return auth_service.verify_email_change(str(current_user.user_id), request)


@router.post("/profile/change-password", response_model=OtpResponse)
async def initiate_password_change(
    request: PasswordChangeRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return await auth_service.initiate_password_change(str(current_user.user_id), request)


@router.post("/profile/verify-password", response_model=UserResponse)
async def verify_password_change(
    request: PasswordChangeVerifyRequest,
    current_user: User = Depends(deps.get_current_user)
):
    return auth_service.verify_password_change(str(current_user.user_id), request)
