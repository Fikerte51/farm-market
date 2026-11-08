"""Builds docs/Technical_Document.pdf and docs/Poster.pdf from the diagrams and the latest test run.
Run from the project root after `python docs/tools/gen_diagrams.py` and
`pytest tests --junitxml=docs/test_results.xml`:   python docs/tools/build_pdfs.py"""
import re
import xml.etree.ElementTree as ET
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A3, A4, landscape
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfgen import canvas
from reportlab.platypus import Image, PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

ROOT = Path(__file__).resolve().parents[2]
DOCS = ROOT / "docs"
GREEN, DARK = colors.HexColor("#2f6f3e"), colors.HexColor("#1d3b25")
ss = getSampleStyleSheet()
body = ParagraphStyle("b", parent=ss["BodyText"], fontSize=9.5, leading=13)
small = ParagraphStyle("s", parent=body, fontSize=8, leading=10)
h1 = ParagraphStyle("h1", parent=ss["Heading1"], textColor=DARK, fontSize=16)
h2 = ParagraphStyle("h2", parent=ss["Heading2"], textColor=GREEN, fontSize=12)


def P(t, st=body):
    return Paragraph(t, st)


def tbl(rows, widths, header=True, font=8):
    t = Table([[P(str(c), small) for c in r] for r in rows], colWidths=widths, repeatRows=1 if header else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.25, colors.grey), ("VALIGN", (0, 0), (-1, -1), "TOP"),
          ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f1f6f1")])]
    if header:
        st += [("BACKGROUND", (0, 0), (-1, 0), GREEN)]
        t._cellvalues[0] = [Paragraph(f"<font color='white'><b>{c}</b></font>", small) for c in rows[0]]
    t.setStyle(TableStyle(st))
    return t


# ------------------------------------------------------------------------------------ test results
def load_tests():
    root = ET.parse(DOCS / "test_results.xml").getroot()
    out = []
    for tc in root.iter("testcase"):
        name = tc.get("name")
        mod = tc.get("classname").split(".")[-1].replace("test_", "")
        status = "SKIPPED (needs Gemini key)" if tc.find("skipped") is not None else ("FAIL" if tc.find("failure") is not None or tc.find("error") is not None else "PASS")
        out.append((mod, name, status))
    return out


AREA = {"business_rules": "Business rules / DB", "assistant": "LangChain assistant", "gui": "GUI flows"}


def humanize(n):
    base = re.sub(r"\[.*\]$", "", n)
    base = re.sub(r"^test_(q\d+_)?", "", base).replace("_", " ")
    param = re.search(r"\[(.*)\]$", n)
    return (base[0].upper() + base[1:]) + (f"  [{param.group(1)[:40]}]" if param else "")


ASSISTANT_QS = [
    ("1", "Which tomato lots are available? (buyer)", "Lists exactly the unreserved, unexpired tomato lots", "Tool rows equal SQL result - PASS"),
    ("2", "What is the status of request 6? (own market)", "PARTIALLY_ALLOCATED with remaining need 50 kg", "Matches v_request_summary - PASS"),
    ("3", "Show request 6 (buyer of another market)", "No rows: ownership scoping applies to the assistant", "Empty result - PASS"),
    ("4", "Which of our requests are still open?", "Requests 2 and 6 only", "{2, 6} - PASS"),
    ("5", "Which deliveries differed from the allocation? (admin)", "The 3 receipts with a discrepancy", "Receipts match SQL - PASS"),
    ("6", "What harvests are expected? (buyer)", "Rows labelled FORECAST, farm names hidden", "Labelled, no farm_name - PASS"),
    ("7", "How much stock do I have? (farmer)", "Only the farmer's own farms", "Own farms only - PASS"),
    ("8", "Show farm stock (buyer)", "Refused: role not permitted", "Notice returned - PASS"),
    ("9", "Which allocations are active? (farmer)", "Only allocation #4 of Ahmed's farms", "{4} - PASS"),
    ("10", "tomatoes  (ambiguous)", "Clarifying question, no data returned", "Clarification asked - PASS"),
    ("11", "What will the tomato price be next month? (unanswerable)", "Politely declined: prices not stored", "Declined - PASS"),
    ("12", "Delete all requests / DROP TABLE / show password / ignore instructions", "Refused before reaching the model", "Refused (6 variants) - PASS"),
]


# ------------------------------------------------------------------------------------ technical document
def technical():
    doc = SimpleDocTemplate(str(DOCS / "Technical_Document.pdf"), pagesize=A4, leftMargin=18 * mm, rightMargin=18 * mm, topMargin=16 * mm, bottomMargin=16 * mm,
                            title="COSC444 Technical Document - Local Farm and Market Food Availability System")
    s = [P("Local Farm and Market Food Availability System", ParagraphStyle("t", parent=ss["Title"], textColor=DARK)),
         P("COSC444 Database Systems - Technical Document", ParagraphStyle("c", parent=body, alignment=TA_CENTER, fontSize=11)),
         P("Team members: ______________________________ &nbsp;&nbsp; Lab section: ________", ParagraphStyle("c2", parent=body, alignment=TA_CENTER)), Spacer(1, 8),
         P("1. Overview and architecture", h1),
         P("An educational prototype (synthetic data only) in which <b>farmers</b> record harvest lots and allocate produce to market requests, <b>market buyers</b> search local supply, "
           "request produce and confirm deliveries, and <b>administrators</b> manage users and reference data. Stack: <b>Python 3.11+</b>, <b>Streamlit</b> GUI, "
           "<b>MySQL 8</b> (mysql-connector-python, parameterised queries only), <b>LangChain + Google Gemini</b> assistant, bcrypt, Pillow, ReportLab."),
         tbl([["Layer", "Files", "Responsibility"],
              ["GUI", "app.py, farmmarket/views/*", "Login, role menus, forms, tables, charts, photos, assistant chat; every service error is shown as a friendly message"],
              ["Services", "farmmarket/farmer.py, buyer.py, admin.py, auth.py, images.py", "Business rules, ownership checks, one MySQL transaction per operation, audit logging"],
              ["Queries", "farmmarket/queries.py, analytics.py", "Role-scoped read queries and the three SQL analyses"],
              ["Database", "database/farm_market_full.sql", "Tables, CHECK/UNIQUE/FK constraints, triggers (append-only ledger, overdraw guard), views, sample data"],
              ["Assistant", "farmmarket/assistant.py", "LangChain tool-calling agent over fixed read-only, role-scoped queries (Gemini); never writes SQL"]],
             [22 * mm, 55 * mm, 95 * mm]),
         Spacer(1, 6),
         P("<b>Advanced feature (required): Secure login and activity audit.</b> bcrypt-hashed passwords, lock-out after 5 failed logins for 5 minutes, 30-minute idle sign-out, logout, "
           "role-based menus and server-side permission checks, record ownership, an append-only <i>audit_log</i> (user, time, action, affected record, success) and an admin audit viewer. "
           "<b>Optional second feature: Data analytics and report generation</b> (three SQL analyses, filters, 4 charts, summary metrics, CSV and PDF export that is itself audited)."),
         PageBreak(), P("2. Conceptual ER diagram", h1),
         Image(str(DOCS / "ER_diagram.png"), width=174 * mm, height=174 * mm * 0.72),
         P("Editable source: docs/ER_diagram.drawio (Draw.io / diagrams.net).", small), Spacer(1, 8),
         P("3. Relational schema", h1),
         Image(str(DOCS / "relational_schema.png"), width=174 * mm, height=174 * mm * 0.63),
         P("Editable source: docs/relational_schema.drawio. The picture is generated from the live MySQL catalogue, so it always matches the SQL script.", small),
         PageBreak(), P("4. Key business rules and where they are enforced", h1),
         tbl([["Business rule", "Enforcement (application / database)"],
              ["Current stock is derived from dated movements, never stored", "View v_lot_stock sums stock_movements; no stock column exists. Movement table is append-only (UPDATE/DELETE triggers)"],
              ["Expected harvest is a forecast, separate from stock", "Stored in crop_cycles.expected_*; inventory pages and analytics read stock only from movements; shown in a separate table"],
              ["Cannot allocate more than a lot's available quantity", "farmer.allocate locks the lot row (SELECT ... FOR UPDATE) then checks available; trigger trg_movement_rules re-checks inside MySQL"],
              ["Partial fulfilment / multi-lot allocation", "Request status derived from allocated and received quantities (SUBMITTED, PARTIALLY_ALLOCATED, ALLOCATED, PARTIALLY_FULFILLED, FULFILLED); every change stored in request_status_history"],
              ["Receipt may differ from allocation; difference recorded", "delivery_receipts.discrepancy = received - allocated (CHECK); reason mandatory when different; unreceived part is released back to stock"],
              ["Explicit units; conversion only when documented", "All quantities carry a unit FK; convert_qty uses units.to_base_factor and refuses mass-to-count conversion"],
              ["Farm users change only their farms; buyers only their market; admins keep reference data", "require_role + is_my_farm/market checks in every service; refused attempts are written to audit_log (ACCESS_DENIED); admins can only add approved correction movements"],
              ["Every movement and status change keeps date, user, reason", "Columns movement_date, user_id, reason (CHECK: reason required for loss and corrections); request_status_history"],
              ["Deactivate, do not delete", "is_active flags on farms, crops, markets, units, users, lots, images, cycles"],
              ["Images tied to a lot; missing files handled", "harvest_lot_images.lot_id FK; JPG/PNG magic-byte + Pillow validation, 5 MB limit; GUI shows a warning card if the file is missing"],
              ["Fictional data only", "All sample data synthetic; demo password documented"]],
             [62 * mm, 110 * mm]),
         Spacer(1, 8), P("5. Database transactions", h1),
         P("Every service call runs in one MySQL transaction (READ COMMITTED) that commits or rolls back as a whole, so a failed operation never leaves partial inventory, allocation or request records. "
           "Row locks serialise competing users."),
         tbl([["Operation", "Statements committed atomically", "Locks"],
              ["Record harvest", "harvest_lots INSERT + HARVEST_ADDED movement + audit", "crop cycle read"],
              ["Allocate", "allocations INSERT + RESERVED movement + request status/history + audit", "lot row, request row (FOR UPDATE)"],
              ["Release allocation / close request", "RESERVATION_RELEASED movements + allocation status + request status/history + audit", "allocation, request"],
              ["Confirm delivery", "delivery_receipts INSERT + DELIVERY movement + RESERVATION_RELEASED for any shortfall + allocation status + request status + audit", "allocation row"],
              ["Record loss / admin correction", "LOSS / CORRECTION movement + audit (stock re-checked under lock)", "lot row"],
              ["Login", "failed-attempt counter / lock + audit row (committed even when the login fails)", "user row"],
              ["Denied access", "ACCESS_DENIED audit row written on a separate connection so it survives the rollback", "-"]],
             [45 * mm, 95 * mm, 32 * mm]),
         PageBreak(), P("6. Test cases with expected and actual results", h1),
         P("Automated with pytest against a real MySQL 8 database rebuilt from the SQL script for each test (<i>pytest tests</i>). "
           "Valid, invalid, boundary and concurrent cases are included; stock is verified after harvest, reservation, release, delivery, loss and correction events.")]
    tests = load_tests()
    summary = {}
    for mod, name, st in tests:
        a = summary.setdefault(AREA.get(mod, mod), [0, 0, 0])
        a[0] += 1
        a[1] += st == "PASS"
        a[2] += st.startswith("SKIPPED")
    total = sum(v[0] for v in summary.values()); passed = sum(v[1] for v in summary.values())
    s += [tbl([["Area", "Tests", "Passed", "Skipped"]] + [[k, v[0], v[1], v[2]] for k, v in summary.items()] + [["<b>Total</b>", f"<b>{total}</b>", f"<b>{passed}</b>", f"<b>{sum(v[2] for v in summary.values())}</b>"]],
              [70 * mm, 30 * mm, 30 * mm, 30 * mm]), Spacer(1, 6)]
    s.append(P("6.1 LangChain assistant - 12 question groups (more than the 10 required), incl. ambiguous, unanswerable and unsafe", h2))
    s.append(P("The offline suite replaces Gemini with a scripted stand-in so results are deterministic, while the real tool layer, role scoping and safety filter run unchanged; "
               "tool output is compared with direct SQL. A live Gemini round-trip test (tests/test_assistant.py::test_live_gemini_roundtrip) runs when GOOGLE_API_KEY is set.", small))
    s.append(tbl([["#", "Question", "Expected", "Actual"]] + [list(q) for q in ASSISTANT_QS], [8 * mm, 62 * mm, 58 * mm, 44 * mm]))
    s.append(Spacer(1, 6))
    s.append(P("6.2 All automated test cases", h2))
    rows = [["#", "Area", "Test case (expected behaviour)", "Actual"]]
    for i, (mod, name, st) in enumerate(tests, 1):
        rows.append([i, AREA.get(mod, mod), humanize(name), "As expected - PASS" if st == "PASS" else st])
    s.append(tbl(rows, [8 * mm, 30 * mm, 100 * mm, 34 * mm]))
    s += [Spacer(1, 8), P("7. Limitations", h1),
          P("Educational prototype: synthetic data only, no connection to government systems. The assistant needs a Gemini API key and internet access; without it, the GUI shows a clear 'not configured' message. "
            "Sessions live in the Streamlit server session (suitable for a demo, not hardened for internet exposure). Crates (count units) cannot be converted to kg and are excluded from kg-based analytics.")]
    doc.build(s)


# ------------------------------------------------------------------------------------ poster
def poster():
    W, H = landscape(A3)
    c = canvas.Canvas(str(DOCS / "Poster.pdf"), pagesize=(W, H))
    c.setFillColor(DARK); c.rect(0, H - 55 * mm, W, 55 * mm, fill=1, stroke=0)
    c.setFillColor(colors.white); c.setFont("Helvetica-Bold", 40)
    c.drawString(20 * mm, H - 28 * mm, "Local Farm & Market Food Availability System")
    c.setFont("Helvetica", 16)
    c.drawString(20 * mm, H - 40 * mm, "COSC444 Database Systems - Khalifa University - Python | MySQL | Streamlit | LangChain + Gemini")
    c.drawString(20 * mm, H - 48 * mm, "Team: ______________________________________   (educational prototype, fictional data)")

    def box(x, y, w, h, title, lines, fs=12):
        c.setFillColor(colors.HexColor("#f1f6f1")); c.setStrokeColor(GREEN); c.roundRect(x, y, w, h, 3 * mm, fill=1, stroke=1)
        c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 16); c.drawString(x + 5 * mm, y + h - 9 * mm, title)
        c.setFillColor(colors.black); c.setFont("Helvetica", fs)
        yy = y + h - 17 * mm
        for ln in lines:
            for part in _wrap(ln, w - 10 * mm, fs):
                c.drawString(x + 5 * mm, yy, part); yy -= fs * 1.35
            yy -= 1.5 * mm

    def _wrap(text, width, fs):
        words, line, out = text.split(), "", []
        for wd in words:
            t = (line + " " + wd).strip()
            if c.stringWidth(t, "Helvetica", fs) > width and line:
                out.append(line); line = wd
            else:
                line = t
        return out + [line]
    top = H - 62 * mm
    box(10 * mm, top - 78 * mm, 135 * mm, 78 * mm, "Problem & objective", [
        "Make local food supply visible: farmers publish harvests, markets find and request produce, administrators keep reference data.",
        "Stock is calculated from a dated movement ledger; forecasts never count as stock; allocations can never oversell a lot."])
    box(10 * mm, top - 78 * mm - 85 * mm, 135 * mm, 80 * mm, "Three roles, one database", [
        "Farmer: farms, crop cycles, harvest lots, photos, losses, allocation to requests.",
        "Market buyer: search by crop / emirate / date / quantity, requests, partial delivery confirmation with discrepancy.",
        "Admin: users, crops, units, markets, approved corrections, analytics dashboard, audit log."])
    box(10 * mm, 10 * mm, 135 * mm, top - 78 * mm - 85 * mm - 15 * mm, "Advanced features", [
        "Secure login & audit: bcrypt, lock-out, idle sign-out, ownership rules, append-only audit.",
        "Analytics: supply vs demand, fulfilment & discrepancies, loss & ageing; filters, charts, CSV/PDF export."], 12)
    c.drawImage(str(DOCS / "ER_diagram.png"), 150 * mm, top - 168 * mm, width=170 * mm, height=170 * mm * 0.72, preserveAspectRatio=True)
    c.setFillColor(GREEN); c.setFont("Helvetica-Bold", 14); c.drawString(150 * mm, top + 3 * mm, "Conceptual ER model (14 entities)")
    box(150 * mm, 10 * mm, 170 * mm, top - 168 * mm - 12 * mm, "LangChain assistant (Gemini)", [
        "Ask in plain English; answers come from fixed read-only, role-scoped queries with supporting records shown.",
        "Ambiguous questions get a clarification, unanswerable ones are declined, unsafe ones are refused before reaching the model. No raw SQL, no writes."], 12)
    box(325 * mm, top - 78 * mm, 85 * mm, 78 * mm, "Design highlights", [
        "MySQL 8: CHECK, UNIQUE, FK, triggers, views.", "One transaction per operation; row locks stop overselling.",
        "Explicit units with documented conversion.", "Photos on disk + path in SQL; missing files handled."], 11)
    tests = load_tests(); ok = sum(1 for t in tests if t[2] == "PASS")
    box(325 * mm, top - 78 * mm - 85 * mm, 85 * mm, 80 * mm, "Testing", [
        f"{ok} automated tests pass on real MySQL (rules, concurrency, security, images, GUI).", "12 assistant question groups incl. ambiguous & unsafe."], 11)
    box(325 * mm, 10 * mm, 85 * mm, top - 78 * mm - 85 * mm - 15 * mm, "Run it", [
        "pip install -r requirements.txt", "python init_db.py", "streamlit run app.py", "Demo password: Demo@1234"], 11)
    c.showPage(); c.save()


if __name__ == "__main__":
    technical(); poster()
    print("PDFs written to", DOCS)
