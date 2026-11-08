"""Shared building blocks: current-user object, input validation, audit logging, permission
checks, unit conversion and the stock / request-progress calculations."""
import datetime as dt
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

from . import db
from .errors import AccessDenied, UserError

EPS = Decimal("0.0005")
MAX_QTY = Decimal("9999999.999")


@dataclass(frozen=True)
class User:
    user_id: int
    username: str
    full_name: str
    role: str                      # 'farmer' | 'buyer' | 'admin'
    market_id: int | None = None
    market_name: str | None = None


# ----------------------------------------------------------------------------- validation
def req_text(value, name: str, required: bool = True, max_len: int = 200) -> str | None:
    text = (value or "").strip() if isinstance(value, str) or value is None else str(value).strip()
    if not text:
        if required:
            raise UserError(f"{name} is required.")
        return None
    if len(text) > max_len:
        raise UserError(f"{name} is too long (maximum {max_len} characters).")
    return text


def to_decimal(value, name: str) -> Decimal:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise UserError(f"{name} must be a number.")
    try:
        d = Decimal(str(value).strip().replace(",", ""))
    except (InvalidOperation, ValueError):
        raise UserError(f"{name} must be a number.") from None
    if not d.is_finite():
        raise UserError(f"{name} must be a number.")
    return d


def req_num(value, name: str, allow_zero: bool = False) -> Decimal:
    d = to_decimal(value, name)
    if d < 0 or (d == 0 and not allow_zero):
        raise UserError(f"{name} must be {'zero or ' if allow_zero else ''}greater than zero.")
    if d > MAX_QTY:
        raise UserError(f"{name} is too large.")
    d = d.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    if d == 0 and not allow_zero:
        raise UserError(f"{name} must be at least 0.001.")
    return d


def req_date(value, name: str, required: bool = True) -> dt.date | None:
    if value is None or value == "":
        if required:
            raise UserError(f"{name} is required.")
        return None
    if isinstance(value, dt.datetime):
        return value.date()
    if isinstance(value, dt.date):
        return value
    try:
        return dt.date.fromisoformat(str(value).strip())
    except ValueError:
        raise UserError(f"{name} must be a valid date (YYYY-MM-DD).") from None


def today() -> dt.date:
    return dt.date.today()


def fmt(q) -> str:
    """Quantity as text without trailing zeros."""
    d = Decimal(str(q))
    s = f"{d:f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


# ----------------------------------------------------------------------------- audit & access
def log_event(cur, user: User | None, action: str, table: str | None = None,
              record=None, details: str = "", success: bool = True) -> None:
    """Write an audit row inside the caller's transaction."""
    cur.execute(
        "INSERT INTO audit_log (user_id, username, action, table_name, record_id, details, success) "
        "VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (user.user_id if user else None, user.username if user else None, action, table,
         None if record is None else str(record)[:60], (details or "")[:500], 1 if success else 0),
    )


def deny(user: User, action: str, table: str | None = None, record=None):
    """Record the refused attempt (committed on its own connection so it survives any rollback)
    and raise AccessDenied."""
    db.execute_autocommit(
        "INSERT INTO audit_log (user_id, username, action, table_name, record_id, details, success) "
        "VALUES (%s,%s,'ACCESS_DENIED',%s,%s,%s,0)",
        (user.user_id, user.username, table, None if record is None else str(record)[:60],
         f"{user.role} tried: {action}"[:500]),
    )
    raise AccessDenied("You do not have permission to do that.")


def require_role(user: User, role: str, action: str) -> None:
    if user is None or user.role != role:
        if user is None:
            raise AccessDenied("Please sign in first.")
        deny(user, action)


def is_my_farm(cur, user: User, farm_id) -> bool:
    cur.execute("SELECT 1 FROM user_farms WHERE user_id=%s AND farm_id=%s", (user.user_id, farm_id))
    return cur.fetchone() is not None


def lot_farm(cur, lot_id) -> int | None:
    cur.execute("SELECT cy.farm_id FROM harvest_lots l JOIN crop_cycles cy ON cy.cycle_id=l.cycle_id "
                "WHERE l.lot_id=%s", (lot_id,))
    row = cur.fetchone()
    return row["farm_id"] if row else None


# ----------------------------------------------------------------------------- reference checks
def check_unit(cur, unit: str) -> None:
    cur.execute("SELECT 1 FROM units WHERE unit_code=%s AND is_active=1", (unit,))
    if cur.fetchone() is None:
        raise UserError(f"Unknown or inactive unit '{unit}'.")


def check_crop(cur, crop_id) -> None:
    cur.execute("SELECT 1 FROM crops WHERE crop_id=%s AND is_active=1", (crop_id,))
    if cur.fetchone() is None:
        raise UserError("Unknown or inactive crop.")


def convert_qty(cur, qty: Decimal, unit_from: str, unit_to: str) -> Decimal:
    """Convert only through the documented unit table; refuse mass <-> count conversions."""
    if unit_from == unit_to:
        return qty.quantize(Decimal("0.001"), rounding=ROUND_HALF_UP)
    cur.execute("SELECT unit_code, category, to_base_factor FROM units WHERE unit_code IN (%s,%s) AND is_active=1",
                (unit_from, unit_to))
    found = {r["unit_code"]: r for r in cur.fetchall()}
    if unit_from not in found or unit_to not in found:
        raise UserError("Unknown or inactive unit.")
    a, b = found[unit_from], found[unit_to]
    if a["category"] != b["category"]:
        raise UserError(f"No documented conversion between '{unit_from}' and '{unit_to}'.")
    return (qty * Decimal(a["to_base_factor"]) / Decimal(b["to_base_factor"])).quantize(
        Decimal("0.001"), rounding=ROUND_HALF_UP)


# ----------------------------------------------------------------------------- stock & requests
def lot_stock(cur, lot_id) -> dict:
    """On hand, reserved and available, always calculated from the movement ledger."""
    cur.execute(
        "SELECT "
        " COALESCE(SUM(CASE movement_type WHEN 'HARVEST_ADDED' THEN quantity WHEN 'CORRECTION_ADD' THEN quantity "
        "   WHEN 'DELIVERY' THEN -quantity WHEN 'LOSS' THEN -quantity WHEN 'CORRECTION_REMOVE' THEN -quantity ELSE 0 END),0) AS on_hand, "
        " COALESCE(SUM(CASE movement_type WHEN 'RESERVED' THEN quantity WHEN 'RESERVATION_RELEASED' THEN -quantity "
        "   WHEN 'DELIVERY' THEN -quantity ELSE 0 END),0) AS reserved "
        "FROM stock_movements WHERE lot_id=%s", (lot_id,))
    row = cur.fetchone()
    on_hand, reserved = Decimal(row["on_hand"]), Decimal(row["reserved"])
    return {"on_hand": on_hand, "reserved": reserved, "available": on_hand - reserved}


def request_progress(cur, request_id) -> dict | None:
    cur.execute("SELECT request_id, market_id, crop_id, requested, unit, status, allocated_open, received, remaining_need "
                "FROM v_request_summary WHERE request_id=%s", (request_id,))
    row = cur.fetchone()
    if row:
        for k in ("requested", "allocated_open", "received", "remaining_need"):
            row[k] = Decimal(row[k])
    return row


def derive_status(requested: Decimal, allocated: Decimal, received: Decimal) -> str:
    if received >= requested - EPS:
        return "FULFILLED"
    if received > EPS:
        return "PARTIALLY_FULFILLED"
    if allocated >= requested - EPS:
        return "ALLOCATED"
    if allocated > EPS:
        return "PARTIALLY_ALLOCATED"
    return "SUBMITTED"


def record_status(cur, user: User, request_id, old: str | None, new: str, reason: str) -> None:
    cur.execute("UPDATE market_requests SET status=%s, updated_at=NOW() WHERE request_id=%s", (new, request_id))
    cur.execute("INSERT INTO request_status_history (request_id, old_status, new_status, changed_by, reason) "
                "VALUES (%s,%s,%s,%s,%s)", (request_id, old, new, user.user_id, reason[:255]))


def refresh_status(cur, user: User, request_id, reason: str) -> None:
    p = request_progress(cur, request_id)
    if p is None or p["status"] in ("CANCELLED", "CLOSED"):
        return
    new = derive_status(p["requested"], p["allocated_open"], p["received"])
    if new != p["status"]:
        record_status(cur, user, request_id, p["status"], new, reason)


def add_movement(cur, user: User, lot_id, mtype: str, qty: Decimal, unit: str, reason: str | None,
                 allocation_id=None, when: dt.datetime | None = None) -> None:
    if when is None:
        cur.execute(
            "INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, user_id, reason, allocation_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s)", (lot_id, mtype, qty, unit, user.user_id, reason, allocation_id))
    else:
        cur.execute(
            "INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, movement_date, user_id, reason, allocation_id) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (lot_id, mtype, qty, unit, when, user.user_id, reason, allocation_id))
