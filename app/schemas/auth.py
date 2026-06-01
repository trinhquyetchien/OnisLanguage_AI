from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator, model_validator


class UserResponse(BaseModel):
    user_id: str
    email: str
    display_name: str


class AuthRegisterRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=6, max_length=128)
    confirm_password: str = Field(min_length=6, max_length=128)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email address")
        return value.lower()

    @model_validator(mode="after")
    def validate_passwords(self) -> AuthRegisterRequest:
        if self.password != self.confirm_password:
            raise ValueError("Passwords do not match")
        return self


class AuthLoginRequest(BaseModel):
    email: str = Field(min_length=3, max_length=254)
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email address")
        return value.lower()


class AuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


class OtpVerifyRequest(BaseModel):
    email: str
    otp: str

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email address")
        return value.lower().strip()

    @field_validator("otp")
    @classmethod
    def validate_otp(cls, value: str) -> str:
        otp = value.strip()
        if not (len(otp) == 6 and otp.isdigit()):
            raise ValueError("OTP must be 6 digits")
        return otp


class OtpResponse(BaseModel):
    message: str
    email: str


class ProfileUpdateRequest(BaseModel):
    display_name: Optional[str] = None
    email: Optional[str] = None
    avatar_url: Optional[str] = None


class EmailChangeVerifyRequest(BaseModel):
    new_email: str
    otp: str

    @field_validator("new_email")
    @classmethod
    def validate_new_email(cls, value: str) -> str:
        if "@" not in value or "." not in value.split("@")[-1]:
            raise ValueError("Invalid email address")
        return value.lower().strip()

    @field_validator("otp")
    @classmethod
    def validate_email_otp(cls, value: str) -> str:
        otp = value.strip()
        if not (len(otp) == 6 and otp.isdigit()):
            raise ValueError("OTP must be 6 digits")
        return otp


class PasswordChangeRequest(BaseModel):
    current_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)
    confirm_new_password: str = Field(min_length=6, max_length=128)

    @model_validator(mode="after")
    def validate_passwords(self) -> "PasswordChangeRequest":
        if self.new_password != self.confirm_new_password:
            raise ValueError("Passwords do not match")
        return self


class PasswordChangeVerifyRequest(BaseModel):
    otp: str

    @field_validator("otp")
    @classmethod
    def validate_password_otp(cls, value: str) -> str:
        otp = value.strip()
        if not (len(otp) == 6 and otp.isdigit()):
            raise ValueError("OTP must be 6 digits")
        return otp
