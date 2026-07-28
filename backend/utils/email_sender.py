import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from backend.core.config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, FROM_EMAIL
from backend.core.logger import logger
import asyncio

async def send_email_async(to_email: str, subject: str, body_html: str):
    """Sends an email asynchronously so it doesn't block the API thread."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning(f"Skipping email to {to_email} because SMTP credentials are not set in .env")
        return False
        
    def _send():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"VIA Platform <{FROM_EMAIL or SMTP_USER}>"
        msg["To"] = to_email
        
        # Adding plain text fallback prevents strict spam filters from silently dropping the email
        import re
        body_text = re.sub('<[^<]+?>', '', body_html).strip() # basic HTML stripper
        part1 = MIMEText(body_text, "plain")
        part2 = MIMEText(body_html, "html")
        
        msg.attach(part1)
        msg.attach(part2)
        
        try:
            server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
            server.ehlo()
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(msg["From"], [to_email], msg.as_string())
            server.quit()
            logger.info(f"Email sent successfully to {to_email}")
            return True
        except Exception as e:
            logger.error(f"Failed to send email to {to_email}: {e}")
            return False

    return await asyncio.to_thread(_send)

async def send_verification_email(to_email: str, code: str):
    subject = "Verify your VIA Platform Account"
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
        <h2 style="color: #4f46e5; text-align: center;">VIA Platform</h2>
        <p>Hello!</p>
        <p>Thank you for registering. Please use the following 6-digit verification code to verify your account:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; margin: 20px 0;">
            {code}
        </div>
        <p>This code will expire in 15 minutes.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;" />
        <p style="font-size: 12px; color: #6b7280; text-align: center;">If you didn't request this, you can safely ignore this email.</p>
    </div>
    """
    await send_email_async(to_email, subject, body_html)

async def send_reset_password_email(to_email: str, code: str):
    subject = "Reset Your VIA Platform Password"
    body_html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #e0e0e0; border-radius: 10px;">
        <h2 style="color: #4f46e5; text-align: center;">VIA Platform</h2>
        <p>Hello,</p>
        <p>We received a request to reset your password. Please use the following 6-digit reset code:</p>
        <div style="background-color: #f3f4f6; padding: 15px; text-align: center; font-size: 24px; font-weight: bold; letter-spacing: 5px; border-radius: 5px; margin: 20px 0;">
            {code}
        </div>
        <p>This code will expire in 15 minutes.</p>
        <p>If you didn't request a password reset, please ignore this email or contact support if you have concerns.</p>
        <hr style="border: none; border-top: 1px solid #e0e0e0; margin: 20px 0;" />
        <p style="font-size: 12px; color: #6b7280; text-align: center;">VIA Autonomous AI Digital Team Platform</p>
    </div>
    """
    await send_email_async(to_email, subject, body_html)
