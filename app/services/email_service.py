import random
import string
import logging
from fastapi_mail import ConnectionConfig, FastMail, MessageSchema, MessageType
from app.core.config import settings

logger = logging.getLogger(__name__)

conf = ConnectionConfig(
    MAIL_USERNAME=settings.MAIL_USERNAME,
    MAIL_PASSWORD=settings.MAIL_PASSWORD,
    MAIL_FROM=settings.MAIL_FROM,
    MAIL_PORT=settings.MAIL_PORT,
    MAIL_SERVER=settings.MAIL_SERVER,
    MAIL_STARTTLS=settings.MAIL_STARTTLS,
    MAIL_SSL_TLS=settings.MAIL_SSL_TLS,
    USE_CREDENTIALS=settings.USE_CREDENTIALS,
    VALIDATE_CERTS=True
)

class EmailService:
    @staticmethod
    async def send_otp_email(email: str, otp: str):
        message = MessageSchema(
            subject="OnisLanguage - Xác thực tài khoản",
            recipients=[email],
            body=f"Mã OTP của bạn là: {otp}. Mã này sẽ hết hạn sau 10 phút.",
            subtype=MessageType.plain
        )
        
        # In a real environment, we'd use fastmail.send_message(message)
        # For development without real SMTP credentials, we mock it:
        print("\n" + "="*50)
        print(f"📧 [MOCK EMAIL] Gửi đến: {email}")
        print(f"🔑 Mã OTP xác thực là: {otp}")
        print("💡 Mã này sẽ hết hạn sau 10 phút.")
        print("="*50 + "\n")
        
        # fm = FastMail(conf)
        # await fm.send_message(message)

email_service = EmailService()
