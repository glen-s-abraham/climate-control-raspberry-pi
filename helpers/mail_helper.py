import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import os
import logging
from dotenv import find_dotenv,load_dotenv
load_dotenv(find_dotenv())

# Configurations - In a production setting, these should be pulled from environment
# variables or a secure configuration management system, not hardcoded.
ZOHO_SMTP_SERVER = os.getenv("ZOHO_SMTP_SERVER", None)
ZOHO_SMTP_PORT = os.getenv("ZOHO_SMTP_PORT",587)  # TLS port
ZOHO_SMTP_USER = os.getenv("ZOHO_SMTP_USER",None)  # Securely fetch this from environment
ZOHO_SMTP_PASSWORD = os.getenv("ZOHO_SMTP_PASSWORD",None)  # Securely fetch this from environment

# Configure logging
logging.basicConfig(level=logging.INFO)

def send_email(subject, body, recipients, sender=ZOHO_SMTP_USER):
    """
    Send an email using Zoho SMTP service.

    Parameters
    ----------
    subject : str
        The subject of the email.
    body : str
        The body of the email.
    recipients : list
        The list of email recipients.
    sender : str, optional
        The sender's email address.

    Returns
    -------
    None

    """

    # Message container setup
    msg = MIMEMultipart()
    msg['From'] = sender
    msg['To'] = ", ".join(recipients)
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))

    try:
        # Establishing connection with Zoho SMTP server
        with smtplib.SMTP(ZOHO_SMTP_SERVER, ZOHO_SMTP_PORT) as server:
            server.ehlo()
            server.starttls()  # Secure the connection
            server.login(ZOHO_SMTP_USER, ZOHO_SMTP_PASSWORD)
            
            # Send the email
            server.sendmail(sender, recipients, msg.as_string())
            logging.info("Email sent successfully.")
    except smtplib.SMTPException as e:
        # Log the exception without exposing sensitive information
        logging.error(f"SMTP exception occurred: {e}")
    except Exception as e:
        # Catch-all for other exceptions
        logging.error(f"An error occurred: {e}")

# if __name__ == "__main__":
#     # Example usage:
#     send_email(
#         subject="Test Email",
#         body="This is a test email from Python using Zoho SMTP.",
#         recipients=["glenabraham27@gmail.com"]
#     )
