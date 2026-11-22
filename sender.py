import smtplib
import ssl
import time
import random
import mimetypes
from email.message import EmailMessage
from pathlib import Path
from typing import Optional, Dict, Any, Callable
from config import Config
from tracker import Tracker

class EmailSender:
    def __init__(self, config=Config, tracker: Optional[Tracker] = None):
        self.config = config
        self.tracker = tracker or Tracker()

    def create_message(self, recipient_email: str, subject: str, body: str) -> EmailMessage:
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = f"{self.config.SENDER_NAME} <{self.config.SENDER_EMAIL}>"
        msg["To"] = recipient_email

        # Plain text
        msg.set_content(body)

        # HTML formatted version for rich link styling
        html_body = body.replace("\n", "<br/>")
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
          <style>
            body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; font-size: 15px; color: #222; line-height: 1.6; }}
            a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
            a:hover {{ text-decoration: underline; }}
          </style>
        </head>
        <body>
          <div>{html_body}</div>
        </body>
        </html>
        """
        msg.add_alternative(html_content, subtype="html")

        # Attach resume PDF if file exists
        if self.config.ATTACHMENT_PATH:
            attach_path = Path(self.config.ATTACHMENT_PATH)
            if attach_path.exists() and attach_path.is_file():
                ctype, encoding = mimetypes.guess_type(str(attach_path))
                if ctype is None or encoding is not None:
                    ctype = "application/octet-stream"
                maintype, subtype = ctype.split("/", 1)
                with open(attach_path, "rb") as f:
                    msg.add_attachment(
                        f.read(),
                        maintype=maintype,
                        subtype=subtype,
                        filename=attach_path.name
                    )

        return msg

    def send_single(self, recipient_email: str, subject: str, body: str, dry_run: bool = False) -> Dict[str, Any]:
        """Sends an email to a single recipient or simulates it in dry-run mode."""
        if dry_run:
            return {"success": True, "message": f"[DRY-RUN] Simulated send to {recipient_email}"}

        if not self.config.SENDER_EMAIL or not self.config.SENDER_PASSWORD:
            raise ValueError("Sender email and/or App Password not configured in .env or Config.")

        msg = self.create_message(recipient_email, subject, body)

        try:
            if self.config.SMTP_PORT == 465:
                context = ssl.create_default_context()
                with smtplib.SMTP_SSL(self.config.SMTP_SERVER, self.config.SMTP_PORT, context=context) as server:
                    server.login(self.config.SENDER_EMAIL, self.config.SENDER_PASSWORD)
                    server.send_message(msg)
            else:
                with smtplib.SMTP(self.config.SMTP_SERVER, self.config.SMTP_PORT) as server:
                    if self.config.SMTP_USE_TLS:
                        context = ssl.create_default_context()
                        server.starttls(context=context)
                    server.login(self.config.SENDER_EMAIL, self.config.SENDER_PASSWORD)
                    server.send_message(msg)

            return {"success": True, "message": f"Successfully sent to {recipient_email}"}
        except smtplib.SMTPAuthenticationError:
            err = "SMTP Authentication Failed. Check your SENDER_EMAIL and Gmail App Password."
            return {"success": False, "error": err}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def send_test_email(self, test_recipient: Optional[str] = None) -> Dict[str, Any]:
        """Send 1 test email to verify credentials and resume attachment."""
        target = test_recipient or self.config.SENDER_EMAIL
        subject = f"[TEST] Internship Outreach Preview - {self.config.SENDER_NAME}"
        body = f"""Hi there,

This is a test email sent from your Email Automation System!

Everything is configured properly:
- Sender: {self.config.SENDER_NAME} ({self.config.SENDER_EMAIL})
- University: {self.config.YOUR_UNIVERSITY}
- Portfolio: {self.config.YOUR_PORTFOLIO_URL}
- Resume Attachment: {'Attached' if Path(self.config.ATTACHMENT_PATH).exists() else 'No file found at ' + str(self.config.ATTACHMENT_PATH)}

If you're seeing this in your inbox, your SMTP credentials and deliverability settings are working!

Best regards,
{self.config.SENDER_NAME}"""
        return self.send_single(target, subject, body, dry_run=False)

    def dispatch_batch(self, lead_ids: list[int], dry_run: bool = False, 
                       progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None) -> Dict[str, Any]:
        """
        Sends emails sequentially with randomized safety delays to prevent spam flagging.
        """
        results = {"sent": 0, "failed": 0, "skipped": 0, "details": []}
        total = len(lead_ids)

        for idx, lead_id in enumerate(lead_ids):
            lead = self.tracker.get_lead(lead_id)
            if not lead:
                results["skipped"] += 1
                continue

            # Skip if already sent or missing subject/body
            if lead["status"] == "SENT" and not dry_run:
                results["skipped"] += 1
                if progress_callback:
                    progress_callback({
                        "index": idx + 1, "total": total, "lead": lead,
                        "status": "SKIPPED", "message": f"Already sent to {lead['email']}"
                    })
                continue

            if not lead.get("subject") or not lead.get("body"):
                results["failed"] += 1
                if progress_callback:
                    progress_callback({
                        "index": idx + 1, "total": total, "lead": lead,
                        "status": "FAILED", "message": f"Draft missing for {lead['email']}"
                    })
                continue

            if progress_callback:
                progress_callback({
                    "index": idx + 1, "total": total, "lead": lead,
                    "status": "SENDING", "message": f"Sending to {lead['company']} ({lead['email']})..."
                })

            res = self.send_single(lead["email"], lead["subject"], lead["body"], dry_run=dry_run)

            if res["success"]:
                results["sent"] += 1
                if not dry_run:
                    self.tracker.mark_lead_sent(lead_id, status="SENT")
                log_entry = {"lead_id": lead_id, "email": lead["email"], "status": "SENT"}
            else:
                results["failed"] += 1
                if not dry_run:
                    self.tracker.mark_lead_sent(lead_id, status="FAILED", error_message=res.get("error"))
                log_entry = {"lead_id": lead_id, "email": lead["email"], "status": "FAILED", "error": res.get("error")}

            results["details"].append(log_entry)

            if progress_callback:
                progress_callback({
                    "index": idx + 1, "total": total, "lead": lead,
                    "status": "COMPLETED" if res["success"] else "ERROR",
                    "result": res
                })

            # Apply random delay before the next email (unless this is the last email)
            if idx < total - 1 and not dry_run:
                delay = random.uniform(self.config.MIN_DELAY_SECONDS, self.config.MAX_DELAY_SECONDS)
                if progress_callback:
                    progress_callback({
                        "status": "WAITING",
                        "wait_seconds": int(delay),
                        "message": f"Cooling down for {int(delay)}s to prevent spam detection..."
                    })
                time.sleep(delay)

        return results
