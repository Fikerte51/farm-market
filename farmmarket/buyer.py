"""Market-buyer workflows. A buyer may only manage requests and receipts of their own market."""
import datetime as dt
from decimal import Decimal

from . import db
from .core import (EPS, User, add_movement, check_crop, check_unit, deny, fmt, log_event, record_status,
                   refresh_status, req_date, req_num, req_text, request_progress, require_role, today)
from .errors import UserError


def create_request(user: User, crop_id, qty, unit, needed_by, notes=None) -> int:
    require_role(user, "buyer", "create request")
    q = req_num(qty, "Quantity")
    needed = req_date(needed_by, "Needed-by date")
    notes = req_text(notes, "Notes", False, 200)
    if needed < today():
        raise UserError("Needed-by date cannot be in the past.")
    with db.transaction() as cur:
        check_unit(cur, unit)
        check_crop(cur, crop_id)
        cur.execute("SELECT 1 FROM markets WHERE market_id=%s AND is_active=1", (user.market_id,))
        if cur.fetchone() is None:
            raise UserError("Your market account is inactive.")
        cur.execute("INSERT INTO market_requests (market_id, crop_id, quantity, unit, needed_by_date, status, notes, created_by) "
                    "VALUES (%s,%s,%s,%s,%s,'SUBMITTED',%s,%s)", (user.market_id, crop_id, q, unit, needed, notes, user.user_id))
        rid = cur.lastrowid
        cur.execute("INSERT INTO request_status_history (request_id, old_status, new_status, changed_by, reason) "
                    "VALUES (%s,NULL,'SUBMITTED',%s,'Request created')", (rid, user.user_id))
        log_event(cur, user, "REQUEST_CREATED", "market_requests", rid, f"{fmt(q)} {unit}")
    return rid


def update_request(user: User, request_id, qty, needed_by, notes=None) -> int:
    require_role(user, "buyer", "update request")
    q = req_num(qty, "Quantity")
    needed = req_date(needed_by, "Needed-by date")
    notes = req_text(notes, "Notes", False, 200)
    if needed < today():
        raise UserError("Needed-by date cannot be in the past.")
    with db.transaction() as cur:
        cur.execute("SELECT market_id FROM market_requests WHERE request_id=%s FOR UPDATE", (request_id,))
        row = cur.fetchone()
        if row is None:
            raise UserError("Request not found.")
        if row["market_id"] != user.market_id:
            deny(user, "update another market's request", "market_requests", request_id)
        r = request_progress(cur, request_id)
        if r["status"] in ("FULFILLED", "CLOSED", "CANCELLED"):
            raise UserError(f"A {r['status'].lower().replace('_', ' ')} request can no longer be changed.")
        committed = r["allocated_open"] + r["received"]
        if q < committed - EPS:
            raise UserError(f"Quantity cannot be lower than the {fmt(committed)} {r['unit']} already allocated or received.")
        cur.execute("UPDATE market_requests SET quantity=%s, needed_by_date=%s, notes=%s, updated_at=NOW() WHERE request_id=%s",
                    (q, needed, notes, request_id))
        refresh_status(cur, user, request_id, "Quantity changed by buyer")
        log_event(cur, user, "REQUEST_UPDATED", "market_requests", request_id, f"{fmt(q)} {r['unit']}")
    return request_id


def close_request(user: User, request_id, reason) -> str:
    """Close or cancel a request; every active reservation is released back to stock."""
    require_role(user, "buyer", "close request")
    why = req_text(reason, "Reason", True, 200)
    with db.transaction() as cur:
        cur.execute("SELECT market_id FROM market_requests WHERE request_id=%s FOR UPDATE", (request_id,))
        row = cur.fetchone()
        if row is None:
            raise UserError("Request not found.")
        if row["market_id"] != user.market_id:
            deny(user, "close another market's request", "market_requests", request_id)
        r = request_progress(cur, request_id)
        if r["status"] in ("FULFILLED", "CLOSED", "CANCELLED"):
            raise UserError("This request is already closed.")
        cur.execute("SELECT * FROM allocations WHERE request_id=%s AND status='ACTIVE' FOR UPDATE", (request_id,))
        for a in cur.fetchall():
            add_movement(cur, user, a["lot_id"], "RESERVATION_RELEASED", a["quantity"], a["unit"],
                         f"Request closed: {why}", a["allocation_id"])
            cur.execute("UPDATE allocations SET status='RELEASED', closed_at=NOW() WHERE allocation_id=%s", (a["allocation_id"],))
        new = "CLOSED" if r["received"] > EPS else "CANCELLED"
        record_status(cur, user, request_id, r["status"], new, why)
        log_event(cur, user, "REQUEST_CLOSED", "market_requests", request_id, f"{new}: {why}")
    return new


def confirm_delivery(user: User, allocation_id, received, received_date, reason=None) -> int:
    """Record what was actually received. A different quantity creates a visible discrepancy
    (a reason is then required) and any unreceived part of the reservation returns to stock."""
    require_role(user, "buyer", "confirm delivery")
    recv = req_num(received, "Received quantity", allow_zero=True)
    rdate = req_date(received_date, "Received date")
    if rdate > today():
        raise UserError("Received date cannot be in the future.")
    with db.transaction() as cur:
        cur.execute("SELECT a.*, r.market_id FROM allocations a JOIN market_requests r ON r.request_id=a.request_id "
                    "WHERE a.allocation_id=%s FOR UPDATE", (allocation_id,))
        a = cur.fetchone()
        if a is None:
            raise UserError("Allocation not found.")
        if a["market_id"] != user.market_id:
            deny(user, "confirm another market's delivery", "allocations", allocation_id)
        if a["status"] != "ACTIVE":
            raise UserError("This allocation has already been delivered or released.")
        alloc_qty = a["quantity"]
        if recv > alloc_qty + EPS:
            raise UserError(f"Received quantity cannot exceed the allocated {fmt(alloc_qty)} {a['unit']} "
                            "(ask the farmer for a new allocation for extra produce).")
        diff = (recv - alloc_qty).quantize(Decimal("0.001"))
        why = req_text(reason, "Reason for the difference", required=abs(diff) >= EPS, max_len=200)
        cur.execute("INSERT INTO delivery_receipts (allocation_id, allocated_quantity, received_quantity, discrepancy, "
                    "discrepancy_reason, received_date, received_by) VALUES (%s,%s,%s,%s,%s,%s,%s)",
                    (allocation_id, alloc_qty, recv, diff, why, rdate, user.user_id))
        receipt_id = cur.lastrowid
        if recv > EPS:
            add_movement(cur, user, a["lot_id"], "DELIVERY", recv, a["unit"], f"Delivered to request #{a['request_id']}",
                         allocation_id, when=dt.datetime.combine(rdate, dt.time(12, 0)))
        if alloc_qty - recv > EPS:
            add_movement(cur, user, a["lot_id"], "RESERVATION_RELEASED", alloc_qty - recv, a["unit"],
                         f"Delivery shortfall: {why}", allocation_id)
        cur.execute("UPDATE allocations SET status='DELIVERED', closed_at=NOW() WHERE allocation_id=%s", (allocation_id,))
        refresh_status(cur, user, a["request_id"], "Delivery confirmed")
        log_event(cur, user, "DELIVERY_CONFIRMED", "delivery_receipts", receipt_id,
                  f"allocation #{allocation_id}: received {fmt(recv)} of {fmt(alloc_qty)} {a['unit']}")
    return receipt_id
