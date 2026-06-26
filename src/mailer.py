import logging
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logger = logging.getLogger(__name__)

class EmailService:
    def __init__(
        self,
        sender,
        password,
        smtp_server="smtp.office365.com",
        smtp_port=587
    ):
        self.sender = sender
        self.password = password
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def send_price_floor_alert(
            self,
            order_number,
            violation_text,
            recipient
        ):
        # Outlook SMTP settings
        SMTP_SERVER = self.smtp_server
        SMTP_PORT = self.smtp_port

        sender = self.sender

        receiver = recipient

        cc="no_reply@pjdsafetysupplies.com"

        password = self.password

        # Create the email
        msg = MIMEMultipart()
        msg["Subject"] = f"{order_number} Locked, price too low"
        msg["From"] = sender
        msg["To"] = receiver
        msg['Cc'] = cc
        
        recipients = [receiver] + [cc]

        # Body of the email
        msg_str = violation_text
        msg.attach(MIMEText(msg_str, "plain"))

        # Send the email
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(sender, password)
            try:
                result = server.sendmail(sender, recipients, msg.as_string())

                if result:
                    # Some recipients failed
                    logger.info("Email partially failed")
                    for failed_recipient, error in result.items():
                        logger.info(f"Failed: {failed_recipient} -> {error}")
                else:
                    # All good
                    logger.info("Email sent successfully to all recipients")

            except smtplib.SMTPException as e:
                logger.info("SMTP error occurred:", str(e))

            except Exception as e:
                logger.info("Unexpected error:", str(e))

        logger.info("Email with attachments sent successfully!")