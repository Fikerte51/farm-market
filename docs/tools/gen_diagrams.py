"""Generates the ER diagram and relational schema diagram.
Outputs (in docs/): ER_diagram.drawio, relational_schema.drawio (open/edit in diagrams.net / Draw.io),
and ER_diagram.png, relational_schema.png (used by the technical document and poster).
The relational schema is read from the live MySQL database, so it always matches the SQL script.
Run from the project root:  python docs/tools/gen_diagrams.py"""
import sys
from pathlib import Path
from xml.sax.saxutils import escape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle

from farmmarket import config, db

OUT = ROOT / "docs"

# ------------------------------------------------------------------------------------ conceptual ER
ENT = {  # name: (x, y, [attributes]);  * = key
    "Farms":            (40, 40,  ["*farm_id", "farm_name", "emirate", "area_hectares", "is_active"]),
    "Users":            (40, 330, ["*user_id", "username", "password_hash", "role", "is_active"]),
    "Markets":          (40, 620, ["*market_id", "market_name", "emirate", "is_active"]),
    "Crops":            (440, 40, ["*crop_id", "crop_name", "category", "is_active"]),
    "CropCycles":       (440, 230, ["*cycle_id", "planting_date", "expected_harvest (FORECAST)", "expected_quantity + unit", "status"]),
    "HarvestLots":      (440, 450, ["*lot_id", "quantity + unit", "harvest_date", "sell_by_date (optional)", "is_active"]),
    "HarvestLotImages": (840, 270, ["*image_id", "file_path", "mime_type (JPG/PNG)", "caption"]),
    "StockMovements":   (840, 40,  ["*movement_id", "movement_type", "quantity + unit", "movement_date", "reason"]),
    "Allocations":      (840, 500, ["*allocation_id", "quantity + unit", "status", "allocated_at"]),
    "MarketRequests":   (840, 730, ["*request_id", "quantity + unit", "needed_by_date", "status"]),
    "DeliveryReceipts": (1240, 500, ["*receipt_id", "allocated_quantity", "received_quantity", "discrepancy + reason"]),
    "RequestStatusHistory": (1240, 730, ["*history_id", "old_status -> new_status", "changed_at / changed_by", "reason"]),
    "AuditLog":         (440, 800, ["*audit_id", "user, action, record", "success", "created_at"]),
    "Units":            (1240, 270, ["*unit_code", "category (mass/count)", "to_base_factor", "(used by every quantity)"]),
}
W = 250
REL = [  # (entity A, label, entity B, card A, card B)
    ("Farms", "has", "CropCycles", "1", "N"), ("Crops", "grown in", "CropCycles", "1", "N"),
    ("CropCycles", "yields", "HarvestLots", "1", "N"), ("HarvestLots", "has photo", "HarvestLotImages", "1", "N"),
    ("HarvestLots", "changes by", "StockMovements", "1", "N"), ("HarvestLots", "reserved by", "Allocations", "1", "N"),
    ("MarketRequests", "filled by", "Allocations", "1", "N"), ("Allocations", "confirmed by", "DeliveryReceipts", "1", "1"),
    ("Markets", "places", "MarketRequests", "1", "N"), ("MarketRequests", "history", "RequestStatusHistory", "1", "N"),
    ("Users", "assigned to", "Farms", "M", "N"), ("Markets", "employs buyer", "Users", "1", "N"),
    ("Users", "performs", "AuditLog", "1", "N"),
]
RULES = ["Business rules shown in the model:",
         "1. Stock is never stored: current availability = sum of dated StockMovements.",
         "2. Expected harvest (CropCycles) is a forecast, kept apart from saleable stock.",
         "3. An allocation can never exceed the lot's available quantity; reserved stock is unavailable to others.",
         "4. A receipt may differ from the allocation; the discrepancy and reason are stored.",
         "5. Every quantity has a unit; conversion only through Units.to_base_factor.",
         "6. Farm users change only assigned farms; buyers only their own market's requests; admins keep reference data.",
         "7. Movements and status changes keep date, user and reason. Records are deactivated, not deleted."]


def eh(attrs):
    return 30 + 20 * len(attrs)


def build_er():
    cells, nid = [], [2]

    def new():
        nid[0] += 1
        return f"n{nid[0]}"
    ids = {}
    for name, (x, y, attrs) in ENT.items():
        i = ids[name] = new()
        body = "<br>".join(("<u><b>%s</b></u>" % a[1:]) if a.startswith("*") else a for a in attrs)
        val = escape(f"<b>{name}</b><hr>{body}")
        cells.append(f'<mxCell id="{i}" value="{val}" style="rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacingLeft=8;fillColor=#e8f3e8;strokeColor=#2f6f3e;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{W}" height="{eh(attrs)}" as="geometry"/></mxCell>')
    for a, label, b, ca, cb in REL:
        ax, ay, aa = ENT[a]; bx, by, ba = ENT[b]
        mx = (ax + W / 2 + bx + W / 2) / 2 - 55; my = (ay + eh(aa) / 2 + by + eh(ba) / 2) / 2 - 25
        d = new()
        cells.append(f'<mxCell id="{d}" value="{escape(label)}" style="rhombus;whiteSpace=wrap;html=1;fillColor=#fff4cc;strokeColor=#b58900;fontSize=10;" vertex="1" parent="1"><mxGeometry x="{mx:.0f}" y="{my:.0f}" width="110" height="50" as="geometry"/></mxCell>')
        for ent, card in ((a, ca), (b, cb)):
            e = new()
            cells.append(f'<mxCell id="{e}" value="{card}" style="endArrow=none;html=1;labelBackgroundColor=#ffffff;fontStyle=1;" edge="1" parent="1" source="{ids[ent]}" target="{d}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    note = escape("<b>" + RULES[0] + "</b><br>" + "<br>".join(RULES[1:]))
    cells.append(f'<mxCell id="{new()}" value="{note}" style="text;html=1;whiteSpace=wrap;align=left;verticalAlign=top;fillColor=#f5f5f5;strokeColor=#999999;spacing=8;" vertex="1" parent="1"><mxGeometry x="40" y="950" width="1450" height="150" as="geometry"/></mxCell>')
    return wrap("Conceptual ER diagram", cells)


def wrap(name, cells):
    return ('<mxfile host="app.diagrams.net"><diagram name="%s" id="d1"><mxGraphModel dx="1400" dy="900" grid="1" gridSize="10" page="1" pageWidth="1600" pageHeight="1200">'
            '<root><mxCell id="0"/><mxCell id="1" parent="0"/>%s</root></mxGraphModel></diagram></mxfile>') % (name, "".join(cells))


def png_er():
    fig, ax = plt.subplots(figsize=(16, 11.5))
    for name, (x, y, attrs) in ENT.items():
        h = eh(attrs)
        ax.add_patch(Rectangle((x, y), W, h, fc="#e8f3e8", ec="#2f6f3e", lw=1.4))
        ax.plot([x, x + W], [y + 26, y + 26], color="#2f6f3e", lw=1)
        ax.text(x + W / 2, y + 13, name, ha="center", va="center", fontsize=10.5, fontweight="bold")
        for k, a in enumerate(attrs):
            key = a.startswith("*")
            ax.text(x + 10, y + 42 + 20 * k, a[1:] if key else a, va="center", fontsize=8.5, fontweight="bold" if key else "normal",
                    style="normal", family="DejaVu Sans")
            if key:
                ax.plot([x + 10, x + 10 + 6.2 * len(a[1:])], [y + 50 + 20 * k, y + 50 + 20 * k], color="black", lw=0.8)
    for a, label, b, ca, cb in REL:
        ax_, ay_, aa = ENT[a]; bx_, by_, ba = ENT[b]
        p1 = (ax_ + W / 2, ay_ + eh(aa) / 2); p2 = (bx_ + W / 2, by_ + eh(ba) / 2)
        m = ((p1[0] + p2[0]) / 2, (p1[1] + p2[1]) / 2)
        ax.plot([p1[0], m[0]], [p1[1], m[1]], color="#555", lw=1, zorder=0); ax.plot([m[0], p2[0]], [m[1], p2[1]], color="#555", lw=1, zorder=0)
        ax.add_patch(Polygon([(m[0] - 55, m[1]), (m[0], m[1] - 25), (m[0] + 55, m[1]), (m[0], m[1] + 25)], fc="#fff4cc", ec="#b58900", zorder=2))
        ax.text(m[0], m[1], label, ha="center", va="center", fontsize=7.5, zorder=3)
        for (px, py), card in ((p1, ca), (p2, cb)):
            t = 0.28
            cx, cy = px + (m[0] - px) * t * 2.2, py + (m[1] - py) * t * 2.2
            ax.text(cx, cy, card, fontsize=9, fontweight="bold", ha="center", va="center", bbox=dict(fc="white", ec="none", pad=1), zorder=4)
    ax.text(40, 960, "\n".join(RULES), va="top", fontsize=8.5, bbox=dict(fc="#f5f5f5", ec="#999", pad=8))
    ax.set_xlim(0, 1540); ax.set_ylim(1130, 0); ax.axis("off")
    ax.set_title("Conceptual ER diagram - Local Farm and Market Food Availability System", fontsize=13, fontweight="bold")
    fig.savefig(OUT / "ER_diagram.png", dpi=130, bbox_inches="tight"); plt.close(fig)


# ------------------------------------------------------------------------------------ relational schema (from MySQL)
POS = {  # table: (x, y)
    "farms": (30, 30), "crops": (330, 30), "units": (630, 30), "markets": (930, 30), "users": (1230, 30),
    "user_farms": (30, 270), "crop_cycles": (330, 270), "harvest_lots": (630, 270), "harvest_lot_images": (930, 270), "audit_log": (1230, 300),
    "stock_movements": (330, 620), "allocations": (630, 620), "market_requests": (930, 620), "request_status_history": (1230, 620),
    "delivery_receipts": (30, 600),
}
TW = 270


def short_type(t):
    return t.replace("varchar", "VARCHAR").replace("decimal", "DECIMAL").replace("datetime", "DATETIME").replace("tinyint(1)", "BOOL").replace("int", "INT") \
            .replace("date", "DATE") if t else t


def introspect():
    cols = db.query("SELECT table_name t, column_name c, column_type ty, is_nullable n, column_key k FROM information_schema.columns "
                    "WHERE table_schema=%s ORDER BY table_name, ordinal_position", (config.DB_NAME,))
    fks = db.query("SELECT table_name t, column_name c, referenced_table_name rt, referenced_column_name rc FROM information_schema.key_column_usage "
                   "WHERE table_schema=%s AND referenced_table_name IS NOT NULL", (config.DB_NAME,))
    uniq = {(r["t"], r["c"]) for r in db.query("SELECT table_name t, column_name c FROM information_schema.statistics WHERE table_schema=%s AND non_unique=0 AND index_name<>'PRIMARY'", (config.DB_NAME,))}
    tables = {}
    for r in cols:
        if r["t"].startswith("v_"):
            continue
        tables.setdefault(r["t"], []).append(r)
    return tables, fks, uniq


def th(cols):
    return 28 + 19 * len(cols)


def line_of(r, fkset, uniq):
    tags = []
    if r["k"] == "PRI": tags.append("PK")
    if (r["t"], r["c"]) in fkset: tags.append("FK")
    if (r["t"], r["c"]) in uniq: tags.append("UQ")
    if r["n"] == "NO" and r["k"] != "PRI": tags.append("NN")
    return f"{r['c']}  {short_type(r['ty'])}", " ".join(tags)


def build_schema():
    tables, fks, uniq = introspect()
    fkset = {(f["t"], f["c"]) for f in fks}
    cells, ids, nid = [], {}, [2]
    for t, (x, y) in POS.items():
        nid[0] += 1; ids[t] = f"t{nid[0]}"
        rows = tables[t]
        body = "<br>".join((lambda l: f"{'<b>' if 'PK' in l[1] else ''}{escape(l[0])}{'</b>' if 'PK' in l[1] else ''} <font color='#888'>{l[1]}</font>")(line_of(r, fkset, uniq)) for r in rows)
        cells.append(f'<mxCell id="{ids[t]}" value="{escape("<b>" + t + "</b><hr>" + body)}" style="rounded=0;whiteSpace=wrap;html=1;align=left;verticalAlign=top;spacingLeft=6;fontSize=10;fillColor=#e8eef8;strokeColor=#2b5a9e;" vertex="1" parent="1"><mxGeometry x="{x}" y="{y}" width="{TW}" height="{th(rows)}" as="geometry"/></mxCell>')
    for f in fks:
        if f["t"] in ids and f["rt"] in ids:
            nid[0] += 1
            cells.append(f'<mxCell id="e{nid[0]}" value="" style="edgeStyle=entityRelationEdgeStyle;endArrow=ERone;startArrow=ERmany;html=1;strokeColor=#666;" edge="1" parent="1" source="{ids[f["t"]]}" target="{ids[f["rt"]]}"><mxGeometry relative="1" as="geometry"/></mxCell>')
    nid[0] += 1
    cells.append(f'<mxCell id="n{nid[0]}" value="{escape("PK = primary key, FK = foreign key, UQ = unique, NN = not null. Quantities DECIMAL(12,3); every quantity has a unit FK to units. CHECK constraints: quantities > 0, valid statuses, dates in order. Triggers: append-only ledger/audit, stock overdraw guard.")}" style="text;html=1;whiteSpace=wrap;align=left;fillColor=#f5f5f5;strokeColor=#999999;spacing=6;" vertex="1" parent="1"><mxGeometry x="30" y="1010" width="1470" height="50" as="geometry"/></mxCell>')
    return wrap("Relational schema", cells), tables, fks, fkset, uniq


def png_schema(tables, fks, fkset, uniq):
    fig, ax = plt.subplots(figsize=(18, 11.5))
    centers, boxes = {}, {}
    for t, (x, y) in POS.items():
        rows = tables[t]; h = th(rows)
        centers[t] = (x + TW / 2, y + h / 2); boxes[t] = (x, y, TW, h)

    def edge_point(frm, to):
        """Point where the line from centre `frm` towards `to` leaves the rectangle of `frm`."""
        x, y, w, h = boxes[frm]; cx, cy = centers[frm]; tx, ty = centers[to]
        dx, dy = tx - cx, ty - cy
        if dx == 0 and dy == 0:
            return cx, cy
        k = min((w / 2) / abs(dx) if dx else 1e9, (h / 2) / abs(dy) if dy else 1e9)
        return cx + dx * k, cy + dy * k
    for f in fks:
        if f["t"] in centers and f["rt"] in centers:
            a, b = edge_point(f["t"], f["rt"]), edge_point(f["rt"], f["t"])
            ax.annotate("", xy=b, xytext=a, arrowprops=dict(arrowstyle="-|>", color="#777", lw=0.9, shrinkA=0, shrinkB=0), zorder=1)
    for t, (x, y) in POS.items():
        rows = tables[t]; h = th(rows)
        ax.add_patch(Rectangle((x, y), TW, h, fc="#e8eef8", ec="#2b5a9e", lw=1.3, zorder=2))
        ax.text(x + TW / 2, y + 13, t, ha="center", va="center", fontsize=9.5, fontweight="bold", zorder=3)
        ax.plot([x, x + TW], [y + 24, y + 24], color="#2b5a9e", lw=0.8, zorder=3)
        for k, r in enumerate(rows):
            txt, tag = line_of(r, fkset, uniq)
            ax.text(x + 6, y + 37 + 19 * k, txt, fontsize=6.8, va="center", fontweight="bold" if "PK" in tag else "normal", zorder=3)
            ax.text(x + TW - 6, y + 37 + 19 * k, tag, fontsize=6.3, va="center", ha="right", color="#a33" if "FK" in tag else "#666", zorder=3)
    ax.text(30, 1000, "PK primary key | FK foreign key (arrows point to the referenced table) | UQ unique | NN not null.  Quantities are DECIMAL(12,3) with a unit FK; "
                     "CHECK: quantity > 0, valid statuses, ordered dates; triggers: append-only ledger and audit, stock overdraw guard.", fontsize=8,
            bbox=dict(fc="#f5f5f5", ec="#999", pad=5))
    ax.set_xlim(0, 1530); ax.set_ylim(1040, 0); ax.axis("off")
    ax.set_title("Relational schema (MySQL 8) - tables, keys, data types, constraints", fontsize=13, fontweight="bold")
    fig.savefig(OUT / "relational_schema.png", dpi=125, bbox_inches="tight"); plt.close(fig)


if __name__ == "__main__":
    (OUT / "ER_diagram.drawio").write_text(build_er(), encoding="utf-8")
    png_er()
    xml, tables, fks, fkset, uniq = build_schema()
    (OUT / "relational_schema.drawio").write_text(xml, encoding="utf-8")
    png_schema(tables, fks, fkset, uniq)
    print("diagrams written to", OUT)
