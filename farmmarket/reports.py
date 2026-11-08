"""CSV and PDF export of filtered analysis results."""
import csv
import datetime as dt
import io

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle


def _safe(v):
    """Prevent spreadsheet formula injection in text cells."""
    if isinstance(v, str) and v[:1] in ("=", "+", "-", "@"):
        return "'" + v
    return "" if v is None else v


def to_csv(rows: list[dict]) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.writer(buf)
    cols = list(rows[0].keys())
    w.writerow(cols)
    for r in rows:
        w.writerow([_safe(r[c]) for c in cols])
    return buf.getvalue().encode("utf-8-sig")


def to_pdf(title: str, filters_text: str, rows: list[dict]) -> bytes:
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=landscape(A4), leftMargin=24, rightMargin=24, topMargin=24, bottomMargin=24)
    styles = getSampleStyleSheet()
    story = [Paragraph(f"Farm &amp; Market - {title}", styles["Title"]),
             Paragraph(f"Filters: {filters_text} &middot; generated {dt.datetime.now():%Y-%m-%d %H:%M}", styles["Normal"]),
             Spacer(1, 10)]
    if rows:
        cols = list(rows[0].keys())
        data = [cols] + [[str(_safe(r[c])) for c in cols] for r in rows]
        t = Table(data, repeatRows=1)
        t.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2f6f3e")), ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("FONTSIZE", (0, 0), (-1, -1), 8), ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f1")]),
        ]))
        story.append(t)
    else:
        story.append(Paragraph("No data for these filters.", styles["Normal"]))
    doc.build(story)
    return buf.getvalue()
