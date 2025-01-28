import smtplib
from email.mime.text import MIMEText
from utils.logger import setup_logger
from config.config import SMTP_SERVER, SMTP_PORT, EMAIL_USER, EMAIL_PASSWORD, ALERT_RECIPIENTS, EMAIL_ALERTS_ENABLED, LOG_FORMAT, LOG_LEVEL

logger = setup_logger(__name__)

def send_email(subject, body, to_emails=ALERT_RECIPIENTS, html=False):
    if not EMAIL_ALERTS_ENABLED:
        logger.info("Email alerts are disabled.")
        return

    from_email = EMAIL_USER

    if html:
        msg = MIMEText(body, 'html')
    else:
        msg = MIMEText(body, 'plain')

    msg['Subject'] = subject
    msg['From'] = from_email
    msg['To'] = ', '.join(to_emails)

    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(from_email, EMAIL_PASSWORD)
            server.sendmail(from_email, to_emails, msg.as_string())
        logger.info(f"Email sent to {', '.join(to_emails)} with subject: '{subject}'")
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred while sending email to {', '.join(to_emails)}: {e}")
    except Exception as e:
        logger.error(f"An unexpected error occurred while sending email to {', '.join(to_emails)}: {e}") 