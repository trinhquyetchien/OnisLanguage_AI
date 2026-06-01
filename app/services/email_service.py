import logging
from fastapi import HTTPException, status
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
    def _validate_smtp_config() -> None:
        if not settings.MAIL_USERNAME or not settings.MAIL_PASSWORD:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="SMTP is not configured. Please set MAIL_USERNAME and MAIL_PASSWORD.",
            )

    @staticmethod
    async def send_otp_email(email: str, otp: str):
        EmailService._validate_smtp_config()
        message = MessageSchema(
            subject="OnisLanguage - Xác thực tài khoản",
            recipients=[email],
            body=f"Mã OTP của bạn là: {otp}. Mã này sẽ hết hạn sau 10 phút.",
            subtype=MessageType.plain
        )

        try:
            fm = FastMail(conf)
            await fm.send_message(message)
            logger.info(f"Real email sent to {email}")
        except Exception as e:
            logger.error(f"Failed to send real email to {email}: {e}")
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Unable to send OTP email. Please verify SMTP settings and try again.",
            ) from e


email_service = EmailService()
