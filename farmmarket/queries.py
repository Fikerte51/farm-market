"""Read-only, role-scoped queries. Every statement is parameterised.
Scoping rules: farmers see only their own farms' stock, movements and allocations; buyers see only their
own market's requests and receipts and the public (available-only) produce search; admins see everything."""
import datetime as dt

from . import db
from .core import User, today
from .errors import AccessDenied

OPEN = ("SUBMITTED", "PARTIALLY_ALLOCATED", "ALLOCATED", "PARTIALLY_FULFILLED")


def _where(conds: list[str]) -> str:
    return (" WHERE " + " AND ".join(conds)) if conds else ""


def _farm_scope(user: User, conds: list, params: list, col: str = "farm_id") -> None:
    if user.role == "farmer":
        conds.append(f"{col} IN (SELECT farm_id FROM user_farms WHERE user_id=%s)")
        params.append(user.user_id)
    elif user.role != "admin":
        raise AccessDenied("You do not have permission to view this data.")


# ------------------------------------------------------------------ reference data
def units(active_only=True):
    return db.query("SELECT * FROM units" + (" WHERE is_active=1" if active_only else "") + " ORDER BY category DESC, to_base_factor")


def crops(active_only=True):
    return db.query("SELECT * FROM crops" + (" WHERE is_active=1" if active_only else "") + " ORDER BY crop_name")


def markets(active_only=True):
    return db.query("SELECT * FROM markets" + (" WHERE is_active=1" if active_only else "") + " ORDER BY market_name")


def farms(active_only=False):
    return db.query("SELECT * FROM farms" + (" WHERE is_active=1" if active_only else "") + " ORDER BY farm_name")


def my_farms(user: User):
    return db.query("SELECT f.* FROM farms f JOIN user_farms uf ON uf.farm_id=f.farm_id WHERE uf.user_id=%s "
                    "ORDER BY f.farm_name", (user.user_id,))


# ------------------------------------------------------------------ lots / stock
def list_lots(user: User, crop_id=None, farm_id=None, emirate=None, available_only=False,
              harvest_from=None, harvest_to=None, include_inactive=False):
    """Full stock detail (on hand / reserved / available). Farmers and admins only."""
    conds, params = [], []
    _farm_scope(user, conds, params)
    if not include_inactive:
        conds.append("is_active=1")
    if crop_id:
        conds.append("crop_id=%s"); params.append(crop_id)
    if farm_id:
        conds.append("farm_id=%s"); params.append(farm_id)
    if emirate:
        conds.append("emirate=%s"); params.append(emirate)
    if available_only:
        conds.append("available>0.0005")
    if harvest_from:
        conds.append("harvest_date>=%s"); params.append(harvest_from)
    if harvest_to:
        conds.append("harvest_date<=%s"); params.append(harvest_to)
    return db.query("SELECT lot_id, crop_name, farm_name, emirate, harvest_date, sell_by_date, harvested_quantity, unit, "
                    "on_hand, reserved, available, is_active, image_count FROM v_lot_details" + _where(conds) +
                    " ORDER BY harvest_date DESC, lot_id DESC", params)


def search_produce(crop_id=None, emirate=None, needed_by=None, min_qty=None, min_unit=None):
    """What a market buyer sees: only AVAILABLE (unreserved, unexpired) quantities, never farm stock detail.
    needed_by keeps lots that are still within their sell-by date on that day."""
    conds = ["d.is_active=1", "d.available>0.0005", "(d.sell_by_date IS NULL OR d.sell_by_date>=%s)"]
    params: list = [max(today(), needed_by) if needed_by else today()]
    if crop_id:
        conds.append("d.crop_id=%s"); params.append(crop_id)
    if emirate:
        conds.append("d.emirate=%s"); params.append(emirate)
    join = ""
    if min_qty and min_unit:
        join = " JOIN units mu ON mu.unit_code=%s JOIN units lu ON lu.unit_code=d.unit"
        conds.append("lu.category=mu.category AND d.available*lu.to_base_factor >= %s*mu.to_base_factor")
        params = [min_unit] + params + [min_qty]
    sql = ("SELECT d.lot_id, d.crop_name, d.farm_name, d.emirate, d.harvest_date, d.sell_by_date, d.available, d.unit, "
           "d.image_count FROM v_lot_details d" + join + _where(conds) + " ORDER BY d.crop_name, d.sell_by_date, d.lot_id")
    return db.query(sql, params)


def inventory_overview(user: User):
    """Stock and forecast kept strictly apart. Returns (stock_by_crop, forecast_by_crop)."""
    conds, params = ["is_active=1"], []
    _farm_scope(user, conds, params)
    stock = db.query("SELECT crop_name, unit, ROUND(SUM(on_hand),3) AS on_hand, ROUND(SUM(reserved),3) AS reserved, "
                     "ROUND(SUM(available),3) AS available FROM v_lot_details" + _where(conds) +
                     " GROUP BY crop_name, unit ORDER BY crop_name", params)
    conds, params = ["status IN ('PLANNED','GROWING','HARVESTING')", "is_active=1"], []
    _farm_scope(user, conds, params)
    forecast = db.query("SELECT crop_name, expected_unit AS unit, ROUND(SUM(expected_quantity),3) AS expected_quantity, "
                        "MIN(expected_harvest_date) AS earliest_expected FROM v_cycles" + _where(conds) +
                        " GROUP BY crop_name, expected_unit ORDER BY crop_name", params)
    return stock, forecast


def lot_images(lot_id):
    return db.query("SELECT image_id, lot_id, file_path, mime_type, caption, uploaded_at FROM harvest_lot_images "
                    "WHERE lot_id=%s AND is_active=1 ORDER BY image_id", (lot_id,))


# ------------------------------------------------------------------ crop cycles (forecasts)
def list_cycles(user: User, crop_id=None, farm_id=None, emirate=None, status=None, expected_from=None, expected_to=None):
    conds, params = ["is_active=1"], []
    if user.role in ("farmer",):
        _farm_scope(user, conds, params)
    if crop_id:
        conds.append("crop_id=%s"); params.append(crop_id)
    if farm_id:
        conds.append("farm_id=%s"); params.append(farm_id)
    if emirate:
        conds.append("emirate=%s"); params.append(emirate)
    if status:
        conds.append("status=%s"); params.append(status)
    if expected_from:
        conds.append("expected_harvest_date>=%s"); params.append(expected_from)
    if expected_to:
        conds.append("expected_harvest_date<=%s"); params.append(expected_to)
    rows = db.query("SELECT cycle_id, farm_id, farm_name, emirate, crop_name, planting_date, expected_harvest_date, "
                    "expected_quantity, expected_unit, status, notes FROM v_cycles" + _where(conds) +
                    " ORDER BY expected_harvest_date, cycle_id", params)
    if user.role == "buyer":   # buyers see the forecast, not which farm it belongs to
        for r in rows:
            r.pop("farm_name", None); r.pop("farm_id", None); r.pop("notes", None)
    return rows


# ------------------------------------------------------------------ requests / allocations / receipts
def list_requests(user: User, market_id=None, crop_id=None, emirate=None, status=None, open_only=False,
                  created_from=None, created_to=None, needed_from=None, needed_to=None, needs_supply=False):
    conds, params = [], []
    if user.role == "buyer":
        conds.append("market_id=%s"); params.append(user.market_id)
    elif market_id:
        conds.append("market_id=%s"); params.append(market_id)
    if crop_id:
        conds.append("crop_id=%s"); params.append(crop_id)
    if emirate:
        conds.append("market_emirate=%s"); params.append(emirate)
    if status:
        conds.append("status=%s"); params.append(status)
    if open_only:
        conds.append("status IN ('SUBMITTED','PARTIALLY_ALLOCATED','ALLOCATED','PARTIALLY_FULFILLED')")
    if needs_supply:
        conds.append("remaining_need>0.0005 AND status IN ('SUBMITTED','PARTIALLY_ALLOCATED','PARTIALLY_FULFILLED','ALLOCATED')")
    if created_from:
        conds.append("DATE(created_at)>=%s"); params.append(created_from)
    if created_to:
        conds.append("DATE(created_at)<=%s"); params.append(created_to)
    if needed_from:
        conds.append("needed_by_date>=%s"); params.append(needed_from)
    if needed_to:
        conds.append("needed_by_date<=%s"); params.append(needed_to)
    return db.query("SELECT request_id, market_id, market_name, market_emirate, crop_id, crop_name, requested, unit, "
                    "needed_by_date, status, allocated_open, received, remaining_need, notes, created_at "
                    "FROM v_request_summary" + _where(conds) + " ORDER BY request_id DESC", params)


def list_allocations(user: User, status=None, request_id=None, farm_id=None, crop_id=None, market_id=None):
    conds, params = [], []
    if user.role == "farmer":
        _farm_scope(user, conds, params)
    elif user.role == "buyer":
        conds.append("market_id=%s"); params.append(user.market_id)
    if status:
        conds.append("status=%s"); params.append(status)
    if request_id:
        conds.append("request_id=%s"); params.append(request_id)
    if farm_id and user.role != "buyer":
        conds.append("farm_id=%s"); params.append(farm_id)
    if market_id and user.role != "buyer":
        conds.append("market_id=%s"); params.append(market_id)
    rows = db.query("SELECT allocation_id, request_id, market_name, lot_id, crop_name, farm_name, quantity, unit, status, "
                    "allocated_at, closed_at FROM v_allocations" + _where(conds) + " ORDER BY allocation_id DESC", params)
    if crop_id:
        names = {c["crop_id"]: c["crop_name"] for c in crops(False)}
        rows = [r for r in rows if r["crop_name"] == names.get(crop_id)]
    return rows


def list_movements(user: User, lot_id=None, farm_id=None, crop_id=None, movement_type=None, date_from=None, date_to=None):
    conds, params = [], []
    _farm_scope(user, conds, params)           # buyers are refused here
    if lot_id:
        conds.append("lot_id=%s"); params.append(lot_id)
    if farm_id:
        conds.append("farm_id=%s"); params.append(farm_id)
    if movement_type:
        conds.append("movement_type=%s"); params.append(movement_type)
    if date_from:
        conds.append("DATE(movement_date)>=%s"); params.append(date_from)
    if date_to:
        conds.append("DATE(movement_date)<=%s"); params.append(date_to)
    rows = db.query("SELECT movement_id, movement_date, lot_id, crop_name, farm_name, emirate, movement_type, quantity, unit, "
                    "username, reason FROM v_movements" + _where(conds) + " ORDER BY movement_id DESC", params)
    if crop_id:
        names = {c["crop_id"]: c["crop_name"] for c in crops(False)}
        rows = [r for r in rows if r["crop_name"] == names.get(crop_id)]
    return rows


def list_receipts(user: User, market_id=None, farm_id=None, crop_id=None, only_discrepancies=False,
                  date_from=None, date_to=None):
    conds, params = [], []
    if user.role == "farmer":
        _farm_scope(user, conds, params)
    elif user.role == "buyer":
        conds.append("market_id=%s"); params.append(user.market_id)
    if market_id and user.role != "buyer":
        conds.append("market_id=%s"); params.append(market_id)
    if farm_id and user.role != "buyer":
        conds.append("farm_id=%s"); params.append(farm_id)
    if only_discrepancies:
        conds.append("ABS(discrepancy)>=0.0005")
    if date_from:
        conds.append("received_date>=%s"); params.append(date_from)
    if date_to:
        conds.append("received_date<=%s"); params.append(date_to)
    rows = db.query("SELECT receipt_id, request_id, market_name, crop_name, farm_name, allocated_quantity, received_quantity, "
                    "discrepancy, unit, discrepancy_reason, received_date FROM v_receipts" + _where(conds) +
                    " ORDER BY receipt_id DESC", params)
    if crop_id:
        names = {c["crop_id"]: c["crop_name"] for c in crops(False)}
        rows = [r for r in rows if r["crop_name"] == names.get(crop_id)]
    return rows


def allocatable_lots(user: User, request_id: int):
    """Lots of the farmer's own farms that could supply this request (same crop, unexpired, stock available)."""
    return db.query(
        "SELECT d.lot_id, d.crop_name, d.farm_name, d.harvest_date, d.sell_by_date, d.available, d.unit "
        "FROM v_lot_details d JOIN market_requests r ON r.request_id=%s AND r.crop_id=d.crop_id "
        "WHERE d.is_active=1 AND d.available>0.0005 AND (d.sell_by_date IS NULL OR d.sell_by_date>=%s) "
        "AND d.farm_id IN (SELECT farm_id FROM user_farms WHERE user_id=%s) "
        "ORDER BY d.sell_by_date IS NULL, d.sell_by_date, d.lot_id", (request_id, today(), user.user_id))


def request_history(user: User, request_id: int):
    if user.role == "buyer":
        owner = db.query_one("SELECT market_id FROM market_requests WHERE request_id=%s", (request_id,))
        if not owner or owner["market_id"] != user.market_id:
            return []
    return db.query("SELECT h.changed_at, h.old_status, h.new_status, u.username AS changed_by, h.reason "
                    "FROM request_status_history h JOIN users u ON u.user_id=h.changed_by WHERE h.request_id=%s "
                    "ORDER BY h.history_id", (request_id,))


# ------------------------------------------------------------------ admin
def list_users(user: User):
    if user.role != "admin":
        raise AccessDenied("You do not have permission to view this data.")
    return db.query("SELECT user_id, username, full_name, role, market_name, farms, is_active, failed_attempts, "
                    "locked_until, created_at FROM v_users ORDER BY user_id")


def list_audit(user: User, action=None, success=None, username=None, date_from=None, date_to=None, limit=500):
    if user.role != "admin":
        raise AccessDenied("You do not have permission to view this data.")
    conds, params = [], []
    if action:
        conds.append("action=%s"); params.append(action)
    if success is not None:
        conds.append("success=%s"); params.append(1 if success else 0)
    if username:
        conds.append("username LIKE %s"); params.append(f"%{username}%")
    if date_from:
        conds.append("DATE(created_at)>=%s"); params.append(date_from)
    if date_to:
        conds.append("DATE(created_at)<=%s"); params.append(date_to)
    params.append(int(limit))
    return db.query("SELECT audit_id, created_at, username, action, table_name, record_id, details, success "
                    "FROM audit_log" + _where(conds) + " ORDER BY audit_id DESC LIMIT %s", params)


def audit_actions():
    return [r["action"] for r in db.query("SELECT DISTINCT action FROM audit_log ORDER BY action")]
