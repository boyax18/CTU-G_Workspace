"""Branded email design (24 Nov 2026): content, OTP presentation, escaping, structure, layout.

No database or network: messages go to Django's locmem backend.
"""

import re

from django.core import mail
from django.test import SimpleTestCase, override_settings

from . import email_design
from .email_design import send_mail

LOCMEM = "django.core.mail.backends.locmem.EmailBackend"


def mime_tree(part, depth=0):
    rows = [(depth, part.get_content_type(), part["Content-ID"], part.get_content_disposition())]
    if part.is_multipart():
        for child in part.iter_parts():
            rows += mime_tree(child, depth + 1)
    return rows


@override_settings(EMAIL_BACKEND=LOCMEM, DEFAULT_FROM_EMAIL="CTU-G Workspace <no-reply@example.edu>")
class EmailDesignTests(SimpleTestCase):
    def setUp(self):
        mail.outbox = []

    def otp_messages(self):
        return [
            email_design.registration_otp(role="Student", code="048213", minutes=10, first_name="Ana"),
            email_design.registration_otp(role="Instructor", code="048213", minutes=10),
            email_design.password_reset_otp(code="048213", minutes=10, first_name="Ana"),
        ]

    def test_otp_is_one_selectable_run_of_digits_never_in_links_images_or_preview(self):
        for subject, text, html in self.otp_messages():
            with self.subTest(subject=subject):
                self.assertEqual(len(re.findall(r">048213<", html)), 1, "code rendered once, as one unbroken run")
                self.assertIn("font-size:38px", html)
                self.assertIn("user-select:all", html)
                self.assertNotRegex(html, r'(href|src)="[^"]*048213')
                preheader = re.search(r'<div style="display:none[^>]*>(.*?)</div>', html).group(1)
                self.assertNotIn("048213", preheader)
                self.assertIn("Expires in <strong", html)
                self.assertIn("10 minutes", html)
                self.assertIn("048213", text)  # plain-text fallback still carries the code

    def test_plain_text_fallbacks_keep_their_established_wording(self):
        (_, student, _), (_, instructor, _), (_, reset, _) = self.otp_messages()
        self.assertRegex(student, r"Your Student registration verification code is: 048213")
        self.assertRegex(instructor, r"Your Instructor registration verification code is: 048213")
        self.assertRegex(reset, r"password reset code is 048213\.")
        self.assertNotIn("http", reset)

    def test_recovery_emails_contain_no_links(self):
        for _, _, html in (self.otp_messages()[2], email_design.password_changed()):
            self.assertNotIn("<a ", html)
            self.assertNotIn("href=", html)

    def test_dynamic_values_are_escaped(self):
        _, _, html = email_design.registration_otp(role="Student", code="111111", minutes=10,
                                                   first_name='<script>alert("x")</script>')
        self.assertNotIn("<script>", html)
        self.assertIn("&lt;script&gt;", html)
        _, _, html = email_design.registration_decision(approved=False, url='http://localhost:5173/register"><x',
                                                        reason="A & B <b>")
        self.assertIn("A &amp; B &lt;b&gt;", html)
        self.assertNotIn('"><x', html)

    def test_no_scripts_fonts_or_remote_resources(self):
        samples = [m[2] for m in self.otp_messages()] + [
            email_design.registration_decision(approved=True, url="http://localhost:5173/")[2],
            email_design.registration_decision(approved=False, url="http://localhost:5173/register",
                                               reason="Duplicate registration request")[2],
            email_design.password_changed()[2],
        ]
        for html in samples:
            self.assertNotRegex(html, r"(?i)<script|@import|<link |@font-face|javascript:")
            # 25 Nov 2026: no images at all. With the embedded logo, Gmail accepted but never delivered.
            self.assertNotRegex(html, r"(?i)<img|src=|cid:")
            self.assertIn('<meta name="viewport" content="width=device-width,initial-scale=1">', html)
            self.assertIn("max-width:600px", html)
            self.assertIn("@media only screen and (max-width:620px)", html)
            self.assertIn("CTU-G Workspace", html)
            self.assertIn("This is an automated message", html)

    def test_approval_and_rejection_presentation(self):
        subject, text, html = email_design.registration_decision(approved=True, url="http://localhost:5173/")
        self.assertEqual(subject, "CTU-G Workspace | Registration Approved")
        self.assertIn("Registration Approved", html)
        self.assertIn("Your registration is approved", html)
        self.assertIn('href="http://localhost:5173/"', html)
        self.assertIn("Log In to CTU-G Workspace", html)
        self.assertIn("Registration status: APPROVED", text)
        subject, text, html = email_design.registration_decision(
            approved=False, url="http://localhost:5173/register", reason="Duplicate registration request")
        self.assertEqual(subject, "CTU-G Workspace | Registration Rejected")
        self.assertIn("Registration Not Approved", html)
        self.assertIn("Duplicate registration request", html)
        self.assertIn("same CTU-G ID and email address", html)
        self.assertIn('href="http://localhost:5173/register"', html)
        self.assertIn("Reason: Duplicate registration request", text)

    def test_message_structure_has_no_embedded_image(self):
        """25 Nov 2026 delivery evidence: the same message WITH an inline multipart/related logo was
        accepted by Gmail but never delivered; WITHOUT it, it arrived. Every kind stays image-free."""
        samples = [m for m in self.otp_messages()] + [
            email_design.email_verification_otp(code="048213", minutes=10),
            email_design.registration_decision(approved=True, url="http://localhost:5173/"),
            email_design.registration_decision(approved=False, url="http://localhost:5173/register",
                                               reason="Duplicate registration request"),
            email_design.password_changed(),
        ]
        for subject, text, html in samples:
            mail.outbox.clear()
            self.assertEqual(send_mail(subject, text, None, ["applicant@example.edu"], html_message=html), 1)
            tree = mime_tree(mail.outbox[0].message())
            self.assertEqual([(d, t) for d, t, _, _ in tree], [
                (0, "multipart/alternative"), (1, "text/plain"), (1, "text/html")], subject)

    def test_plain_messages_stay_single_part(self):
        self.assertEqual(send_mail("Subject", "Body only", None, ["applicant@example.edu"]), 1)
        self.assertEqual(mail.outbox[0].message().get_content_type(), "text/plain")
