"""Administrator workflows: reference data, user accounts and approved stock corrections.
Administrators do not touch farm or market transactions except through corrections."""
import re

from . import config, db
from .auth import hash_password
from .core import (EPS, User, add_movement, deny, fmt, log_event, lot_stock, req_num, req_text, require_role)
from .errors import UserError

_ACTIVE_SQL = {
    "crops": "UPDATE crops SET is_active=%s WHERE crop_id=%s",
    "markets": "UPDATE markets SET is_active=%s WHERE market_id=%s",
    "farms": "UPDATE farms SET is_active=%s WHERE farm_id=%s",
    "units": "UPDATE units SET is_active=%s WHERE unit_code=%s",
    "users": "UPDATE users SET is_active=%s WHERE user_id=%s",
}


def apply_correction(user: User, lot_id, direction, qty, reason) -> int:
    """Approved stock correction: the only way an administrator changes stock. Always logged."""
    require_role(user, "admin", "stock correction")
    if direction not in ("add", "remove"):
        raise UserError("Choose whether to add or remove stock.")
    q = req_num(qty, "Correction quantity")
    why = req_text(reason, "Reason for correction", True, 200)
    with db.transaction() as cur:
        cur.execute("SELECT * FROM harvest_lots WHERE lot_id=%s FOR UPDATE", (lot_id,))
        lot = cur.fetchone()
        if lot is None:
            raise UserError("Harvest lot not found.")
        s = lot_stock(cur, lot_id)
        if direction == "remove" and q > s["available"] + EPS:
            raise UserError(f"Cannot remove {fmt(q)} {lot['unit']}: only {fmt(s['available'])} {lot['unit']} is unreserved.")
        add_movement(cur, user, lot_id, "CORRECTION_ADD" if direction == "add" else "CORRECTION_REMOVE", q, lot["unit"], why)
        log_event(cur, user, "STOCK_CORRECTION", "harvest_lots", lot_id, f"{direction} {fmt(q)} {lot['unit']}: {why}")
    return lot_id


def add_crop(user: User, name, category) -> int:
    require_role(user, "admin", "add crop")
    name = req_text(name, "Crop name", True, 60)
    if category not in config.CROP_CATEGORIES:
        raise UserError("Invalid crop category.")
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM crops WHERE LOWER(crop_name)=LOWER(%s)", (name,))
        if cur.fetchone():
            raise UserError("This crop already exists.")
        cur.execute("INSERT INTO crops (crop_name, category) VALUES (%s,%s)", (name, category))
        cid = cur.lastrowid
        log_event(cur, user, "REFERENCE_CHANGED", "crops", cid, f"added {name}")
    return cid


def add_unit(user: User, code, name, category, factor) -> str:
    require_role(user, "admin", "add unit")
    code = (req_text(code, "Unit code", True, 20) or "").lower()
    if not re.fullmatch(r"[a-z0-9_]+", code):
        raise UserError("Unit code may only contain letters, digits and underscores.")
    name = req_text(name, "Unit name", True, 60)
    if category not in ("mass", "count"):
        raise UserError("Invalid unit category.")
    f = req_num(factor, "Conversion factor")
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM units WHERE unit_code=%s", (code,))
        if cur.fetchone():
            raise UserError("This unit code already exists.")
        cur.execute("INSERT INTO units (unit_code, unit_name, category, to_base_factor) VALUES (%s,%s,%s,%s)",
                    (code, name, category, f))
        log_event(cur, user, "REFERENCE_CHANGED", "units", code, "added unit")
    return code


def add_market(user: User, name, emirate, address=None) -> int:
    require_role(user, "admin", "add market")
    name = req_text(name, "Market name", True, 100)
    if emirate not in config.EMIRATES:
        raise UserError("Please choose a valid emirate.")
    address = req_text(address, "Address", False, 200)
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM markets WHERE LOWER(market_name)=LOWER(%s)", (name,))
        if cur.fetchone():
            raise UserError("A market with this name already exists.")
        cur.execute("INSERT INTO markets (market_name, emirate, address) VALUES (%s,%s,%s)", (name, emirate, address))
        mid = cur.lastrowid
        log_event(cur, user, "REFERENCE_CHANGED", "markets", mid, f"added {name}")
    return mid


def set_record_active(user: User, table, record_id, active: bool) -> None:
    """Deactivate instead of delete so history is preserved."""
    require_role(user, "admin", f"activate/deactivate {table}")
    sql = _ACTIVE_SQL.get(table)
    if sql is None:
        raise UserError("Unknown record type.")
    if table == "users" and record_id == user.user_id and not active:
        raise UserError("You cannot deactivate your own account.")
    with db.transaction() as cur:
        cur.execute(sql, (1 if active else 0, record_id))
        if cur.rowcount == 0:
            cur.execute(f"SELECT 1 FROM {table} WHERE {'unit_code' if table == 'units' else table[:-1] + '_id'}=%s", (record_id,))
            if cur.fetchone() is None:
                raise UserError("Record not found.")
        log_event(cur, user, "USER_CHANGED" if table == "users" else "REFERENCE_CHANGED", table, record_id,
                  "activated" if active else "deactivated")


def assign_farm(user: User, target_user_id, farm_id, assign: bool) -> None:
    require_role(user, "admin", "assign farm")
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM users WHERE user_id=%s AND role='farmer'", (target_user_id,))
        if cur.fetchone() is None:
            raise UserError("Farms can only be assigned to farmer accounts.")
        if assign:
            cur.execute("INSERT IGNORE INTO user_farms (user_id, farm_id) VALUES (%s,%s)", (target_user_id, farm_id))
        else:
            cur.execute("DELETE FROM user_farms WHERE user_id=%s AND farm_id=%s", (target_user_id, farm_id))
        log_event(cur, user, "USER_CHANGED", "user_farms", f"{target_user_id}:{farm_id}",
                  "farm assigned" if assign else "farm removed")


def create_user(user: User, username, full_name, role, password, market_id=None, farm_ids=()) -> int:
    require_role(user, "admin", "create user")
    username = req_text(username, "Username", True, 50)
    if not re.fullmatch(r"[A-Za-z0-9_.-]{3,50}", username):
        raise UserError("Username must be 3-50 characters: letters, digits, dot, dash or underscore.")
    full_name = req_text(full_name, "Full name", True, 100)
    if role not in ("farmer", "buyer", "admin"):
        raise UserError("Choose a valid role.")
    if role == "buyer" and not market_id:
        raise UserError("A market buyer must be linked to a market.")
    pw_hash = hash_password(password)
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM users WHERE LOWER(username)=LOWER(%s)", (username,))
        if cur.fetchone():
            raise UserError("This username is already taken.")
        if role == "buyer":
            cur.execute("SELECT 1 FROM markets WHERE market_id=%s AND is_active=1", (market_id,))
            if cur.fetchone() is None:
                raise UserError("The selected market does not exist or is inactive.")
        cur.execute("INSERT INTO users (username, full_name, password_hash, role, market_id) VALUES (%s,%s,%s,%s,%s)",
                    (username, full_name, pw_hash, role, market_id if role == "buyer" else None))
        uid = cur.lastrowid
        if role == "farmer":
            for fid in farm_ids:
                cur.execute("INSERT IGNORE INTO user_farms (user_id, farm_id) VALUES (%s,%s)", (uid, fid))
        log_event(cur, user, "USER_CHANGED", "users", uid, f"created {role} account '{username}'")
    return uid


def reset_password(user: User, target_user_id, new_password) -> None:
    require_role(user, "admin", "reset password")
    pw_hash = hash_password(new_password)
    with db.transaction() as cur:
        cur.execute("UPDATE users SET password_hash=%s, failed_attempts=0, locked_until=NULL WHERE user_id=%s",
                    (pw_hash, target_user_id))
        cur.execute("SELECT 1 FROM users WHERE user_id=%s", (target_user_id,))
        if cur.fetchone() is None:
            raise UserError("User not found.")
        log_event(cur, user, "USER_CHANGED", "users", target_user_id, "password reset by administrator")


def log_export(user: User, report: str, fmt_name: str, rows: int) -> None:
    require_role(user, "admin", "export report")
    with db.transaction() as cur:
        log_event(cur, user, "REPORT_EXPORTED", None, report, f"{fmt_name}, {rows} rows")
