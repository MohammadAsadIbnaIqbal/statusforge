import logging
import httpx
from typing import List, Protocol
from app.core.config import settings

logger = logging.getLogger("arq_worker.email")

class EmailService(Protocol):
    async def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> None:
        ...

class LogEmailService(EmailService):
    async def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> None:
        logger.info(f"--- SIMULATED EMAIL ---")
        logger.info(f"To: {to}")
        logger.info(f"Subject: {subject}")
        logger.info(f"Body (Text): {text_body}")
        logger.info(f"-----------------------")

class ResendEmailService(EmailService):
    def __init__(self):
        if not settings.EMAIL_PROVIDER_API_KEY:
            raise ValueError("EMAIL_PROVIDER_API_KEY is not set but NOTIFICATION_MODE is 'live'.")
        self.api_key = settings.EMAIL_PROVIDER_API_KEY
        self.base_url = "https://api.resend.com/emails"

    async def send_email(self, to: str, subject: str, html_body: str, text_body: str) -> None:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "from": settings.EMAIL_SENDER,
            "to": [to],
            "subject": subject,
            "html": html_body,
            "text": text_body
        }
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    self.base_url,
                    json=payload,
                    headers=headers,
                    timeout=10.0
                )
                response.raise_for_status()
            except httpx.HTTPStatusError as e:
                logger.error(f"Failed to send email to {to}: HTTP {e.response.status_code} - {e.response.text}")
                # 429 (Too Many Requests) or 5xx (Server Error) should be retried by ARQ
                if e.response.status_code == 429 or e.response.status_code >= 500:
                    raise
                # 400-403, 404, etc. are permanent client errors (bad API key, malformed email). 
                # Do not re-raise to prevent pointless infinite ARQ retries.
                return
            except httpx.RequestError as e:
                logger.error(f"Failed to send email to {to}: Request Error - {str(e)}")
                raise

def get_email_service() -> EmailService:
    if settings.NOTIFICATION_MODE.lower() == "live":
        return ResendEmailService()
    return LogEmailService()
