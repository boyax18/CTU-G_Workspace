"""CTU-G Workspace branded email layout (24 Nov 2026): one design for every notification.

* Table-based layout with inline CSS (Gmail, Outlook, Apple Mail and mobile clients). The only
  <style> block holds a mobile media query and is optional: the layout already fits 320 px.
* No JavaScript, web fonts, external images, tracking pixels or remote resources. The approved
  campus logo travels INSIDE the message as an inline attachment (Content-ID ``ctug-logo``).
* Every dynamic value is HTML-escaped here; callers pass plain text.
* OTPs are rendered as one run of digits (visual letter-spacing only, no separator characters),
  so selecting or long-pressing the code copies exactly the six digits. Codes are never placed in
  links, image URLs or the inbox preview text.
* ``send()`` is the single multipart sender: plain-text body + HTML alternative + inline logo.
  It returns the backend's accepted-message count and lets SMTP exceptions propagate unchanged,
  so existing retry/dead-letter handling keeps working. Nothing here logs content or recipients.
"""

from functools import lru_cache
from html import escape
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

LOGO_CID = "ctug-logo"
LOGO_PATH = Path(__file__).resolve().parent / "email_assets" / "ctug-logo.png"

# CTU-G Workspace palette (frontend/src/css/theme.css): forest green, emerald accents, white.
FOREST = "#143823"
FOREST_2 = "#1a4a2e"
EMERALD = "#15803d"
EMERALD_SOFT = "#ecfdf3"
EMERALD_LINE = "#bbf7d0"
INK = "#111827"
BODY = "#374151"
MUTED = "#6b7280"
PAGE = "#eef4f0"
LINE = "#e5e7eb"
DECLINE = "#9a3412"
DECLINE_SOFT = "#fff7ed"
DECLINE_LINE = "#fed7aa"

FONT = "'Segoe UI',Roboto,Helvetica,Arial,sans-serif"
MONO = "'Courier New',Consolas,'Liberation Mono',monospace"
CAMPUS = "Cebu Technological University – Ginatilan Campus"


@lru_cache(maxsize=1)
def _logo_bytes():
    try:
        return LOGO_PATH.read_bytes()
    except OSError:
        return None


def _e(value):
    return escape(str(value), quote=True)


def _paragraph(text):
    return (f'<p style="margin:0 0 14px 0;font-family:{FONT};font-size:15px;line-height:24px;'
            f'color:{BODY};">{_e(text)}</p>')


def _otp_block(code, expires_minutes, label):
    if type(code) is not str or not code.isdigit():
        raise ValueError("An OTP must be digits only.")
    minutes = f"{expires_minutes} minute{'s' if expires_minutes != 1 else ''}"
    return f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:6px 0 18px 0;">
  <tr><td align="center" style="background:{EMERALD_SOFT};border:1px solid {EMERALD_LINE};border-radius:14px;padding:22px 12px;">
    <div style="font-family:{FONT};font-size:12px;line-height:16px;font-weight:600;letter-spacing:1px;text-transform:uppercase;color:{EMERALD};">{_e(label)}</div>
    <div class="ctug-otp" style="margin:10px 0 8px 0;font-family:{MONO};font-size:38px;line-height:46px;font-weight:700;letter-spacing:10px;color:{FOREST};white-space:nowrap;-webkit-user-select:all;user-select:all;">{_e(code)}</div>
    <div style="font-family:{FONT};font-size:13px;line-height:20px;color:{BODY};">Expires in <strong style="color:{INK};">{_e(minutes)}</strong> &middot; Select the code to copy it</div>
  </td></tr>
</table>'''


def _status_block(status):
    approved = status == "approved"
    color, soft, line = (EMERALD, EMERALD_SOFT, EMERALD_LINE) if approved else (DECLINE, DECLINE_SOFT, DECLINE_LINE)
    mark, word = ("&#10003;", "Approved") if approved else ("&#9679;", "Not Approved")
    return f'''
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:0 0 18px 0;">
  <tr><td style="background:{soft};border:1px solid {line};border-radius:999px;padding:6px 14px;font-family:{FONT};font-size:13px;font-weight:700;color:{color};">
    <span aria-hidden="true">{mark}</span>&nbsp; Registration {word}
  </td></tr>
</table>'''


def _details_block(details):
    rows = "".join(
        f'<tr><td style="padding:10px 14px;font-family:{FONT};font-size:13px;color:{MUTED};width:38%;'
        f'border-top:1px solid {LINE};">{_e(label)}</td>'
        f'<td style="padding:10px 14px;font-family:{FONT};font-size:14px;color:{INK};font-weight:600;'
        f'border-top:1px solid {LINE};">{_e(value)}</td></tr>'
        for label, value in details)
    return (f'<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" '
            f'style="margin:0 0 18px 0;border:1px solid {LINE};border-radius:12px;border-collapse:separate;'
            f'border-top-width:0;">{rows}</table>')


def _button(label, url):
    return f'''
<table role="presentation" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0 20px 0;">
  <tr><td align="center" bgcolor="{EMERALD}" style="border-radius:10px;">
    <a href="{_e(url)}" target="_blank" rel="noopener" style="display:inline-block;padding:13px 26px;font-family:{FONT};font-size:15px;font-weight:700;line-height:20px;color:#ffffff;text-decoration:none;border-radius:10px;">{_e(label)}</a>
  </td></tr>
</table>
<p style="margin:0 0 18px 0;font-family:{FONT};font-size:12px;line-height:18px;color:{MUTED};word-break:break-all;">Or open this address: <a href="{_e(url)}" style="color:{EMERALD};">{_e(url)}</a></p>'''


def _security_block(title, text):
    return f'''
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="margin:4px 0 0 0;">
  <tr><td style="background:#f9fafb;border:1px solid {LINE};border-left:4px solid {EMERALD};border-radius:10px;padding:14px 16px;">
    <div style="font-family:{FONT};font-size:13px;font-weight:700;color:{INK};margin:0 0 4px 0;">&#128274; {_e(title)}</div>
    <div style="font-family:{FONT};font-size:13px;line-height:20px;color:{BODY};">{_e(text)}</div>
  </td></tr>
</table>'''


def render(*, title, preheader, eyebrow, heading, greeting, paragraphs, otp=None, otp_label="Your verification code",
           expires_minutes=None, status=None, details=(), action=None, closing=(), security=None):
    """Return the complete HTML document. All arguments are plain text (escaped here)."""
    has_logo = _logo_bytes() is not None
    logo = (f'<img src="cid:{LOGO_CID}" width="44" height="44" alt="CTU-G" '
            f'style="display:block;width:44px;height:44px;border:0;border-radius:10px;background:#ffffff;">'
            if has_logo else "")
    parts = [_paragraph(greeting)] + [_paragraph(p) for p in paragraphs]
    if status:
        parts.insert(0, _status_block(status))
    if otp is not None:
        parts.append(_otp_block(otp, expires_minutes, otp_label))
    if details:
        parts.append(_details_block(details))
    if action:
        parts.append(_button(*action))
    parts += [_paragraph(p) for p in closing]
    if security:
        parts.append(_security_block(*security))
    body = "\n".join(parts)
    logo_cell = f'<td width="56" valign="middle" style="padding-right:12px;">{logo}</td>' if has_logo else ""
    return f'''<!doctype html>
<html lang="en"><head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="color-scheme" content="light"><meta name="supported-color-schemes" content="light">
<title>{_e(title)}</title>
<style>
  @media only screen and (max-width:620px) {{
    .ctug-card {{ border-radius:0 !important; }}
    .ctug-pad {{ padding:22px 18px !important; }}
    .ctug-otp {{ font-size:32px !important; letter-spacing:7px !important; }}
  }}
</style>
</head>
<body style="margin:0;padding:0;background:{PAGE};-webkit-text-size-adjust:100%;">
<div style="display:none;max-height:0;overflow:hidden;opacity:0;color:transparent;">{_e(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" border="0" style="background:{PAGE};">
<tr><td align="center" style="padding:24px 10px;">
  <table role="presentation" class="ctug-card" width="100%" cellpadding="0" cellspacing="0" border="0"
    style="max-width:600px;background:#ffffff;border-radius:18px;overflow:hidden;border:1px solid #d7e5dc;">
    <tr><td style="background:{FOREST};background-image:linear-gradient(135deg,{FOREST} 0%,{FOREST_2} 100%);padding:20px 24px;">
      <table role="presentation" cellpadding="0" cellspacing="0" border="0"><tr>
        {logo_cell}
        <td valign="middle">
          <div style="font-family:{FONT};font-size:19px;line-height:24px;font-weight:700;color:#ffffff;">CTU-G Workspace</div>
          <div style="font-family:{FONT};font-size:12px;line-height:18px;color:#bbf7d0;">{_e(CAMPUS)}</div>
        </td>
      </tr></table>
    </td></tr>
    <tr><td class="ctug-pad" style="padding:28px 32px 26px 32px;">
      <div style="font-family:{FONT};font-size:12px;line-height:16px;font-weight:700;letter-spacing:1px;text-transform:uppercase;color:{EMERALD};margin:0 0 8px 0;">{_e(eyebrow)}</div>
      <h1 style="margin:0 0 18px 0;font-family:{FONT};font-size:22px;line-height:30px;font-weight:700;color:{INK};">{_e(heading)}</h1>
      {body}
    </td></tr>
    <tr><td style="background:#f6faf7;border-top:1px solid #e3ece6;padding:18px 32px;">
      <div style="font-family:{FONT};font-size:12px;line-height:18px;color:{MUTED};">
        <strong style="color:{FOREST};">CTU-G Workspace</strong> &middot; {_e(CAMPUS)}<br>
        This is an automated message. Please do not reply to this email.
      </div>
    </td></tr>
  </table>
</td></tr>
</table>
</body></html>'''


class BrandedEmail(EmailMultiAlternatives):
    """multipart/alternative(text/plain, multipart/related(text/html, image/png logo)).

    Django 6 builds messages with the modern ``email`` API, so the logo is added to the HTML
    part with ``add_related`` after the standard message is built (no private hooks).
    """

    inline_logo = None

    def message(self, *args, **kwargs):
        msg = super().message(*args, **kwargs)
        if self.inline_logo:
            html_part = msg.get_body(preferencelist=("html",))
            if html_part is not None:
                html_part.add_related(self.inline_logo, "image", "png", cid=f"<{LOGO_CID}>",
                                      disposition="inline", filename="ctug-logo.png")
        return msg


def new_message_id(from_email=None):
    """RFC 5322 Message-ID on the sender's domain, used to trace a message in the Sent folder."""
    from email.utils import make_msgid, parseaddr
    address = parseaddr(from_email or settings.DEFAULT_FROM_EMAIL)[1]
    domain = address.rpartition("@")[2] or "ctug-workspace.local"
    return make_msgid(idstring="ctug", domain=domain)


def build_message(subject, text, html, recipients, *, from_email=None, connection=None, headers=None):
    """Multipart message: plain text first, HTML alternative, inline logo when the HTML uses it."""
    message = BrandedEmail(subject, text, from_email or settings.DEFAULT_FROM_EMAIL,
                           list(recipients), connection=connection, headers=dict(headers or {}))
    if html:
        message.attach_alternative(html, "text/html")
        logo = _logo_bytes()
        if logo and f"cid:{LOGO_CID}" in html:
            message.inline_logo = logo
    return message


def send_mail(subject, message, from_email, recipient_list, fail_silently=False, html_message=None,
              connection=None, headers=None):
    """Drop-in for django.core.mail.send_mail: same signature and return value, but the HTML
    alternative is sent as the branded multipart message with the inline logo. Senders keep a
    module-level ``send_mail`` name, so existing failure-path tests still patch the same seam."""
    return build_message(subject, message, html_message, recipient_list, from_email=from_email,
                         connection=connection, headers=headers).send(fail_silently=fail_silently)


def send(subject, text, html, recipients, *, from_email=None, connection=None):
    """Send one branded message; returns the accepted count (SMTP errors propagate unchanged)."""
    return build_message(subject, text, html, recipients, from_email=from_email, connection=connection).send(
        fail_silently=False)


# ----------------------------------------------------------------------------- notifications
def registration_otp(*, role, code, minutes, first_name=None):
    """WF-01.01/01.02 registration OTP: (subject, text, html)."""
    subject = "CTU-G Workspace registration verification code"
    role_word = "Instructor" if role == "Instructor" else "Student"
    text = (
        f"Your {role_word} registration verification code is: {code}\n\n"
        f"This code expires in {minutes} minutes. "
        "It does not approve or activate your account.\n"
        "If you did not request this registration, ignore this email."
    )
    html = render(
        title=subject, preheader=f"Verify your email to continue your {role_word} registration.",
        eyebrow=f"{role_word} registration", heading="Verify your email address",
        greeting=f"Hello {first_name}," if first_name else "Hello,",
        paragraphs=[f"Use this code to confirm your email and continue your CTU-G Workspace {role_word} registration."],
        otp=code, expires_minutes=minutes,
        closing=["Entering this code does not approve or activate your account. Your application is reviewed "
                 "by the School Admin after verification."],
        security=("Security reminder", "CTU-G Workspace staff will never ask for this code. Do not share it. "
                                       "If you did not request this registration, you can ignore this email."),
    )
    return subject, text, html


def password_reset_otp(*, code, minutes, first_name=None):
    """WF-01.05 password-recovery OTP: (subject, text, html). Deliberately contains no links."""
    subject = "CTU-G Workspace password reset code"
    text = (
        f"Your CTU-G Workspace password reset code is {code}.\n\n"
        f"It expires in {minutes} minutes. Do not share it with anyone.\n\n"
        "If you did not request this, ignore this email."
    )
    html = render(
        title=subject, preheader="Use this code to reset your CTU-G Workspace password.",
        eyebrow="Password recovery", heading="Reset your password",
        greeting=f"Hello {first_name}," if first_name else "Hello,",
        paragraphs=["We received a request to reset the password for your CTU-G Workspace account. "
                    "Enter this code on the password reset page to choose a new password."],
        otp=code, otp_label="Your password reset code", expires_minutes=minutes,
        closing=["Resetting your password signs you out of other sessions. You will sign in again with "
                 "your new password; you are not signed in automatically."],
        security=("Didn't request this?", "Ignore this email and your password stays the same. Never share "
                                          "this code, not even with CTU-G Workspace staff."),
    )
    return subject, text, html


def email_verification_otp(*, code, minutes, first_name=None):
    """Signed-in account confirming its CURRENT email address (enables password recovery)."""
    subject = "CTU-G Workspace email verification code"
    text = (
        f"Your CTU-G Workspace email verification code is {code}.\n\n"
        f"It expires in {minutes} minutes. Enter it on your My profile page to confirm this email address.\n\n"
        "If you did not request this, ignore this email and contact the campus administrator."
    )
    html = render(
        title=subject, preheader="Confirm your email address for CTU-G Workspace.",
        eyebrow="Account security", heading="Confirm your email address",
        greeting=f"Hello {first_name}," if first_name else "Hello,",
        paragraphs=["Enter this code on your My profile page to confirm that this email address belongs to you. "
                    "A confirmed address lets you recover your password by email."],
        otp=code, otp_label="Your email verification code", expires_minutes=minutes,
        security=("Didn't request this?", "Ignore this email. Never share this code, not even with CTU-G Workspace staff."),
    )
    return subject, text, html


def password_changed(*, first_name=None):
    subject = "CTU-G Workspace password changed"
    text = (
        "The password for your CTU-G Workspace account was just changed.\n\n"
        "If you made this change, no action is needed. "
        "If you did not, contact support immediately."
    )
    html = render(
        title=subject, preheader="Your CTU-G Workspace password was changed.",
        eyebrow="Account security", heading="Your password was changed",
        greeting=f"Hello {first_name}," if first_name else "Hello,",
        paragraphs=["The password for your CTU-G Workspace account was just changed. "
                    "Other signed-in sessions have been ended."],
        security=("Wasn't you?", "If you did not change your password, contact the campus administrator immediately."),
    )
    return subject, text, html


def registration_decision(*, approved, url, reason=None):
    """WF-02.03/02.04 decision notification (also each applicant of a bulk decision)."""
    if approved:
        subject = "CTU-G Workspace | Registration Approved"
        description = "Your account registration has been approved by the administrator."
        further = "You can now sign in using your registered CTU-G ID and password."
        action = "Log In to CTU-G Workspace"
    else:
        subject = "CTU-G Workspace | Registration Rejected"
        description = "Your account registration has been rejected by the administrator."
        further = "You may submit a new registration by completing the registration form again."
        action = "Register Again"
    status = "APPROVED" if approved else "REJECTED"
    reason_text = f"\nReason: {reason}\n" if reason else ""
    text = (
        "CTU-G Workspace\nCebu Technological University - Ginatilan Campus\n\n"
        f"Registration status: {status}\n\n{description}\n"
        f"{reason_text}\n{further}\n\n{action}: {url}\n\n"
        "This is an automated notification. If you need help, contact the campus administrator."
    )
    if approved:
        html = render(
            title=subject, preheader="Your CTU-G Workspace account is ready.",
            eyebrow="Registration decision", heading="Your registration is approved",
            greeting="Hello,", status="approved",
            paragraphs=["Good news! The School Admin has reviewed and approved your CTU-G Workspace registration.",
                        "Your account is now active. Sign in with the CTU-G ID and password you registered with."],
            action=(action, url),
            security=("Keep your account safe", "Never share your password. CTU-G Workspace staff will never ask for it."),
        )
    else:
        html = render(
            title=subject, preheader="An update on your CTU-G Workspace registration.",
            eyebrow="Registration decision", heading="Your registration was not approved",
            greeting="Hello,", status="rejected",
            paragraphs=["Thank you for registering for CTU-G Workspace. After review, the School Admin was unable "
                        "to approve your registration at this time."],
            details=[("Reason", reason)] if reason else (),
            closing=["Your registration information has been removed. You are welcome to submit a new registration "
                     "with the same CTU-G ID and email address after addressing the reason above."],
            action=(action, url),
            security=("Need help?", "If you have questions about this decision, contact the campus administrator."),
        )
    return subject, text, html
