# ratings/pdf_reports.py
from io import BytesIO

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

TOP = 790
BOTTOM = 80


def _student_name(user):
    return user.get_full_name() or user.username


def build_student_pdf(result):
    """One student's own released result. No rater identities or counts."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=0)
    c.setTitle("Peer rating result")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, TOP, "Peer Rating Result")

    c.setFont("Helvetica", 12)
    score = "Not rated" if result.final_score is None else f"{result.final_score:.2f} / 5.00"
    rows = [
        ("Session", result.period.title),
        ("Student", _student_name(result.student)),
        ("Final score", score),
        ("Released", result.released_at.strftime("%Y-%m-%d")),
    ]
    y = TOP - 40
    for label, value in rows:
        c.drawString(50, y, f"{label}:")
        c.drawString(200, y, str(value))
        y -= 22

    c.setFont("Helvetica-Oblique", 9)
    c.drawString(50, 60, "Individual ratings are confidential and are not included in this report.")
    c.showPage()
    c.save()
    return buf.getvalue()


def build_summary_pdf(period, results):
    """Instructor-only class summary: student names and final scores. No individual ratings."""
    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4, pageCompression=0)
    c.setTitle(f"Results: {period.title}")

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, TOP, f"Results: {period.title}")

    c.setFont("Helvetica-Bold", 11)
    c.drawString(50, TOP - 35, "Student")
    c.drawString(350, TOP - 35, "Final score")
    c.drawString(460, TOP - 35, "Raters")

    c.setFont("Helvetica", 11)
    y = TOP - 60
    for r in results:
        if y < BOTTOM:
            c.showPage()
            c.setFont("Helvetica", 11)
            y = TOP
        score = "Not rated" if r.final_score is None else f"{r.final_score:.2f}"
        c.drawString(50, y, _student_name(r.student))
        c.drawString(350, y, score)
        c.drawString(460, y, str(r.rater_count))
        y -= 18

    c.showPage()
    c.save()
    return buf.getvalue()