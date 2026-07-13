"""
LionsylAI - Email Service
Priority: SMTP (Gmail/Outlook/any provider) -> SendGrid -> Dev-mode (console log)
SMTP is tried first because it works immediately with a Gmail app-password,
with no third-party account signup required.
"""
from __future__ import annotations
import logging
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Tuple

log = logging.getLogger("lionsylai.email")

try:
    import sendgrid
    from sendgrid.helpers.mail import Mail, Email, To, Content
    SENDGRID_LIB_OK = True
except ImportError:
    SENDGRID_LIB_OK = False

from config.settings import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_USE_TLS,
    SENDGRID_API_KEY, FROM_EMAIL, FROM_NAME, APP_URL, APP_NAME,
)


def email_delivery_configured() -> bool:
    """True if a real email channel (SMTP or SendGrid) is configured."""
    smtp_ok = bool(SMTP_HOST and SMTP_USER and SMTP_PASSWORD)
    sg_ok = bool(SENDGRID_API_KEY)
    return smtp_ok or sg_ok


def _send_smtp(to_email: str, subject: str, html_body: str) -> Tuple[bool, str]:
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"]    = f"{FROM_NAME} <{SMTP_USER}>"
        msg["To"]      = to_email
        msg.attach(MIMEText(html_body, "html"))

        context = ssl.create_default_context()
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            if SMTP_USE_TLS:
                server.starttls(context=context)
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_USER, [to_email], msg.as_string())
        return True, "sent via SMTP"
    except smtplib.SMTPAuthenticationError:
        log.error("SMTP auth failed - check SMTP_USER/SMTP_PASSWORD (use an App Password for Gmail)")
        return False, "SMTP authentication failed"
    except Exception as e:
        log.error(f"SMTP send error: {e}")
        return False, f"SMTP error: {e}"


def _send_sendgrid(to_email: str, subject: str, html_body: str) -> Tuple[bool, str]:
    try:
        sg = sendgrid.SendGridAPIClient(api_key=SENDGRID_API_KEY)
        message = Mail(
            from_email=Email(FROM_EMAIL, FROM_NAME),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_body),
        )
        resp = sg.send(message)
        ok = resp.status_code in (200, 201, 202)
        return ok, ("sent via SendGrid" if ok else f"SendGrid status {resp.status_code}")
    except Exception as e:
        log.error(f"SendGrid send error: {e}")
        return False, f"SendGrid error: {e}"


def _send(to_email: str, subject: str, html_body: str) -> Tuple[bool, str]:
    """
    Try SMTP first, then SendGrid, then fall back to dev-mode console logging.
    Returns (success, detail_message).
    """
    # Debug: Tell us exactly what config is loaded
    missing = []
    if not SMTP_HOST:
        missing.append("SMTP_HOST")
    if not SMTP_USER:
        missing.append("SMTP_USER")
    if not SMTP_PASSWORD:
        missing.append("SMTP_PASSWORD")
    
    if missing:
        log.warning(f"[EMAIL DEBUG] Missing config vars: {', '.join(missing)}")
    else:
        log.info(f"[EMAIL DEBUG] SMTP config OK. Attempting to send to {to_email}...")

    if SMTP_HOST and SMTP_USER and SMTP_PASSWORD:
        ok, detail = _send_smtp(to_email, subject, html_body)
        if ok:
            return True, detail
        if SENDGRID_API_KEY:
            return _send_sendgrid(to_email, subject, html_body)
        return False, detail

    if SENDGRID_API_KEY and SENDGRID_LIB_OK:
        return _send_sendgrid(to_email, subject, html_body)

    log.warning(f"[DEV-MODE, no email configured] Would send to {to_email}: {subject}")
    return False, "dev-mode (no SMTP/SendGrid configured - see Settings -> Email Setup)"


def _base_template(title: str, body_html: str) -> str:
    return f"""
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1.0"/>
  <title>{title}</title>
  <style>
    body {{font-family:'Segoe UI',Arial,sans-serif;background:#0D0F14;margin:0;padding:0;}}
    .wrap {{max-width:600px;margin:40px auto;background:#141720;border-radius:16px;overflow:hidden;
            border:1px solid #252836;}}
    .header {{background:linear-gradient(135deg,#6C63FF,#0AEFFF);padding:40px 32px;text-align:center;}}
    .header h1 {{color:#fff;font-size:28px;margin:0;letter-spacing:1px;}}
    .header p {{color:rgba(255,255,255,0.85);margin:8px 0 0;font-size:14px;}}
    .body {{padding:40px 32px;color:#E0E4F0;line-height:1.7;}}
    .body h2 {{color:#fff;font-size:22px;margin:0 0 16px;}}
    .btn {{display:inline-block;background:linear-gradient(90deg,#6C63FF,#0AEFFF);
           color:#fff!important;padding:14px 36px;border-radius:8px;text-decoration:none;
           font-weight:700;font-size:16px;margin:24px 0;letter-spacing:0.5px;}}
    .code-box {{background:#0D0F14;border:2px dashed #6C63FF;border-radius:10px;
                padding:20px;text-align:center;font-size:36px;font-weight:800;
                letter-spacing:8px;color:#0AEFFF;margin:24px 0;}}
    .footer {{padding:24px 32px;text-align:center;color:#6B7280;font-size:12px;
              border-top:1px solid #252836;}}
    .divider {{border:none;border-top:1px solid #252836;margin:24px 0;}}
  </style>
</head>
<body>
<div class="wrap">
  <div class="header">
    <h1>LionsylAI</h1>
    <p>Enterprise Analytics Intelligence</p>
  </div>
  <div class="body">
    {body_html}
  </div>
  <div class="footer">
    <p>&copy; 2026 {APP_NAME}. All rights reserved.</p>
    <p>If you didn't request this email, you can safely ignore it.</p>
    <p><a href="{APP_URL}" style="color:#6C63FF;">Visit {APP_NAME}</a></p>
  </div>
</div>
</body>
</html>
"""


def send_verification_email(to_email: str, full_name: str, code: str) -> Tuple[bool, str]:
    body = f"""
<h2>Verify your email address</h2>
<p>Hi <strong>{full_name or 'there'}</strong>,</p>
<p>Welcome to {APP_NAME}! Please confirm your email address by entering
the verification code below in the app:</p>
<div class="code-box">{code}</div>
<p>This code expires in <strong>15 minutes</strong>. If you did not create a
{APP_NAME} account, you can safely ignore this email.</p>
"""
    html = _base_template("Verify your email - LionsylAI", body)
    return _send(to_email, f"Verify your {APP_NAME} email", html)


def send_password_reset(to_email: str, full_name: str, reset_link: str) -> Tuple[bool, str]:
    body = f"""
<h2>Reset your password</h2>
<p>Hi <strong>{full_name or 'there'}</strong>,</p>
<p>We received a request to reset your {APP_NAME} password.
Click the button below to create a new password:</p>
<p style="text-align:center;">
  <a class="btn" href="{reset_link}">Reset Password</a>
</p>
<hr class="divider"/>
<p style="font-size:13px;color:#9CA3AF;">
  This link expires in <strong>1 hour</strong>. If you did not request a password
  reset, please ignore this email. Your password will not change.
</p>
<p style="font-size:12px;color:#6B7280;">
  Or paste this link into your browser:<br/>
  <span style="color:#6C63FF;">{reset_link}</span>
</p>
"""
    html = _base_template("Reset your password - LionsylAI", body)
    return _send(to_email, f"Reset your {APP_NAME} password", html)


def send_welcome_pro(to_email: str, full_name: str) -> Tuple[bool, str]:
    body = f"""
<h2>Welcome to {APP_NAME} Professional!</h2>
<p>Hi <strong>{full_name or 'there'}</strong>,</p>
<p>Your Professional subscription is now <strong>active</strong>.
You have full access to every feature in {APP_NAME}:</p>
<ul style="color:#E0E4F0;line-height:2;">
  <li>Unlimited data uploads</li>
  <li>All 12 analytics modules</li>
  <li>AI-powered predictions &amp; forecasting</li>
  <li>Advanced FP&amp;A automation</li>
  <li>Team collaboration (5 seats)</li>
  <li>Priority email support</li>
  <li>Full API access</li>
</ul>
<p style="text-align:center;">
  <a class="btn" href="{APP_URL}">Go to Dashboard</a>
</p>
<p>Have questions? Reply to this email - we're always here.</p>
"""
    html = _base_template("You're now on Pro - LionsylAI", body)
    return _send(to_email, f"Welcome to {APP_NAME} Professional!", html)


def send_team_invite(to_email: str, invited_name: str, inviter_name: str,
                     org_name: str, role: str, temp_password: str = None) -> Tuple[bool, str]:
    pwd_section = ""
    if temp_password:
        pwd_section = f"""
<p style="font-size:14px;color:#E0E4F0;margin-top:16px;">
  A temporary password has been generated for you:
</p>
<div class="code-box">{temp_password}</div>
<p style="font-size:13px;color:#9CA3AF;">
  Please sign in and change your password immediately from Settings → Security.
</p>
"""
    body = f"""
<h2>You've been invited to join {org_name}</h2>
<p>Hi <strong>{invited_name or 'there'}</strong>,</p>
<p><strong>{inviter_name}</strong> has invited you to collaborate on
<strong>{org_name}</strong>'s {APP_NAME} workspace as a <strong>{role}</strong>.</p>
{pwd_section}
<p style="text-align:center;">
  <a class="btn" href="{APP_URL}">Accept Invitation</a>
</p>
<hr class="divider"/>
<p style="font-size:13px;color:#9CA3AF;">
  Create your free account with this email address to join the team automatically.
</p>
"""
    html = _base_template(f"You're invited to {org_name} - LionsylAI", body)
    return _send(to_email, f"{inviter_name} invited you to {org_name} on {APP_NAME}", html)


def send_notification(to_email: str, full_name: str, message: str) -> Tuple[bool, str]:
    body = f"""
<h2>Platform Notification</h2>
<p>Hi <strong>{full_name or 'there'}</strong>,</p>
<p>{message}</p>
<p style="text-align:center;">
  <a class="btn" href="{APP_URL}">Open {APP_NAME}</a>
</p>
"""
    html = _base_template(f"{APP_NAME} Notification", body)
    return _send(to_email, f"{APP_NAME} - {message[:60]}", html)


def send_payment_receipt(to_email: str, full_name: str, amount: str,
                         currency: str, plan: str, gateway: str) -> Tuple[bool, str]:
    body = f"""
<h2>Payment Receipt</h2>
<p>Hi <strong>{full_name or 'there'}</strong>,</p>
<p>Thank you for your payment. Here are your transaction details:</p>
<table style="width:100%;border-collapse:collapse;margin:16px 0;">
  <tr><td style="padding:8px 0;color:#9CA3AF;">Plan</td><td style="padding:8px 0;color:#fff;text-align:right;">{plan}</td></tr>
  <tr><td style="padding:8px 0;color:#9CA3AF;">Amount</td><td style="padding:8px 0;color:#0AEFFF;text-align:right;font-weight:700;">{amount} {currency}</td></tr>
  <tr><td style="padding:8px 0;color:#9CA3AF;">Payment Method</td><td style="padding:8px 0;color:#fff;text-align:right;">{gateway}</td></tr>
</table>
<p style="text-align:center;">
  <a class="btn" href="{APP_URL}">Go to Dashboard</a>
</p>
"""
    html = _base_template("Payment Receipt - LionsylAI", body)
    return _send(to_email, f"Payment Receipt - {APP_NAME} {plan}", html)