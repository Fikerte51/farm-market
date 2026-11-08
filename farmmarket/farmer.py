"""Farmer workflows: farms, crop cycles, harvest lots, losses and allocations.
Farmers may only change records of farms assigned to them."""
import datetime as dt
from decimal import Decimal

from . import config, db
from .core import (EPS, User, add_movement, check_crop, check_unit, convert_qty, deny, fmt, is_my_farm,
                   log_event, lot_farm, lot_stock, refresh_status, req_date, req_num, req_text,
                   request_progress, require_role, today)
from .errors import UserError


def add_farm(user: User, name, emirate, location=None, area=None) -> int:
    require_role(user, "farmer", "add farm")
    name = req_text(name, "Farm name", True, 100)
    if emirate not in config.EMIRATES:
        raise UserError("Please choose a valid emirate.")
    location = req_text(location, "Location", False, 200)
    area_val = None
    if area not in (None, "", 0, 0.0):
        area_val = req_num(area, "Area (hectares)")
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM farms WHERE LOWER(farm_name)=LOWER(%s)", (name,))
        if cur.fetchone():
            raise UserError("A farm with this name already exists.")
        cur.execute("INSERT INTO farms (farm_name, emirate, location_desc, area_hectares) VALUES (%s,%s,%s,%s)",
                    (name, emirate, location, area_val))
        farm_id = cur.lastrowid
        cur.execute("INSERT INTO user_farms (user_id, farm_id) VALUES (%s,%s)", (user.user_id, farm_id))
        log_event(cur, user, "FARM_CREATED", "farms", farm_id, name)
    return farm_id


def add_crop_cycle(user: User, farm_id, crop_id, planting, expected_date, expected_qty, unit, notes=None) -> int:
    require_role(user, "farmer", "add crop cycle")
    planting = req_date(planting, "Planting date")
    expected_date = req_date(expected_date, "Expected harvest date")
    if expected_date < planting:
        raise UserError("Expected harvest date cannot be before the planting date.")
    qty = req_num(expected_qty, "Expected quantity", allow_zero=True)
    notes = req_text(notes, "Notes", False, 200)
    with db.transaction() as cur:
        if not is_my_farm(cur, user, farm_id):
            deny(user, "add crop cycle to another farm", "crop_cycles", farm_id)
        cur.execute("SELECT is_active FROM farms WHERE farm_id=%s", (farm_id,))
        farm = cur.fetchone()
        if not farm or not farm["is_active"]:
            raise UserError("This farm is inactive.")
        check_crop(cur, crop_id)
        check_unit(cur, unit)
        cur.execute("SELECT 1 FROM crop_cycles WHERE farm_id=%s AND crop_id=%s AND planting_date=%s",
                    (farm_id, crop_id, planting))
        if cur.fetchone():
            raise UserError("This farm already has a cycle for this crop with the same planting date.")
        cur.execute("INSERT INTO crop_cycles (farm_id, crop_id, planting_date, expected_harvest_date, expected_quantity, "
                    "expected_unit, status, notes) VALUES (%s,%s,%s,%s,%s,%s,'GROWING',%s)",
                    (farm_id, crop_id, planting, expected_date, qty, unit, notes))
        cycle_id = cur.lastrowid
        log_event(cur, user, "CYCLE_CREATED", "crop_cycles", cycle_id, f"expected {fmt(qty)} {unit} (forecast)")
    return cycle_id


def update_cycle_forecast(user: User, cycle_id, expected_date, expected_qty, status) -> int:
    """Updates the FORECAST only. It never creates stock."""
    require_role(user, "farmer", "update forecast")
    expected_date = req_date(expected_date, "Expected harvest date")
    qty = req_num(expected_qty, "Expected quantity", allow_zero=True)
    if status not in config.CYCLE_STATUSES:
        raise UserError("Invalid cycle status.")
    with db.transaction() as cur:
        cur.execute("SELECT * FROM crop_cycles WHERE cycle_id=%s FOR UPDATE", (cycle_id,))
        cy = cur.fetchone()
        if cy is None:
            raise UserError("Crop cycle not found.")
        if not is_my_farm(cur, user, cy["farm_id"]):
            deny(user, "edit another farm's crop cycle", "crop_cycles", cycle_id)
        if expected_date < cy["planting_date"]:
            raise UserError("Expected harvest date cannot be before the planting date.")
        cur.execute("UPDATE crop_cycles SET expected_harvest_date=%s, expected_quantity=%s, status=%s WHERE cycle_id=%s",
                    (expected_date, qty, status, cycle_id))
        log_event(cur, user, "FORECAST_UPDATED", "crop_cycles", cycle_id, f"{fmt(qty)} {cy['expected_unit']}, {status}")
    return cycle_id


def record_harvest_lot(user: User, cycle_id, qty, unit, harvest_date, sell_by=None) -> int:
    """Creates the lot AND its HARVEST_ADDED movement in one transaction."""
    require_role(user, "farmer", "record harvest")
    q = req_num(qty, "Harvested quantity")
    harvest_date = req_date(harvest_date, "Harvest date")
    sell_by = req_date(sell_by, "Sell-by date", required=False)
    with db.transaction() as cur:
        cur.execute("SELECT * FROM crop_cycles WHERE cycle_id=%s AND is_active=1", (cycle_id,))
        cy = cur.fetchone()
        if cy is None:
            raise UserError("Crop cycle not found.")
        if not is_my_farm(cur, user, cy["farm_id"]):
            deny(user, "record harvest on another farm", "crop_cycles", cycle_id)
        check_unit(cur, unit)
        if harvest_date > today():
            raise UserError("Harvest date cannot be in the future (use the expected harvest forecast instead).")
        if harvest_date < cy["planting_date"]:
            raise UserError("Harvest date cannot be before the planting date.")
        if sell_by is not None and sell_by < harvest_date:
            raise UserError("Sell-by date cannot be before the harvest date.")
        cur.execute("INSERT INTO harvest_lots (cycle_id, crop_id, quantity, unit, harvest_date, sell_by_date) "
                    "VALUES (%s,%s,%s,%s,%s,%s)", (cycle_id, cy["crop_id"], q, unit, harvest_date, sell_by))
        lot_id = cur.lastrowid
        add_movement(cur, user, lot_id, "HARVEST_ADDED", q, unit, "Harvest recorded",
                     when=dt.datetime.combine(harvest_date, dt.time(12, 0)))
        log_event(cur, user, "LOT_CREATED", "harvest_lots", lot_id, f"{fmt(q)} {unit}")
    return lot_id


def record_loss(user: User, lot_id, qty, reason) -> int:
    require_role(user, "farmer", "record loss")
    q = req_num(qty, "Loss quantity")
    why = req_text(reason, "Reason", True, 200)
    with db.transaction() as cur:
        cur.execute("SELECT * FROM harvest_lots WHERE lot_id=%s FOR UPDATE", (lot_id,))
        lot = cur.fetchone()
        if lot is None:
            raise UserError("Harvest lot not found.")
        if not is_my_farm(cur, user, lot_farm(cur, lot_id)):
            deny(user, "record loss on another farm's lot", "harvest_lots", lot_id)
        s = lot_stock(cur, lot_id)
        if q > s["available"] + EPS:
            raise UserError(f"Cannot record a loss of {fmt(q)} {lot['unit']}: only {fmt(s['available'])} "
                            f"{lot['unit']} is unreserved in this lot.")
        add_movement(cur, user, lot_id, "LOSS", q, lot["unit"], why)
        log_event(cur, user, "LOSS_RECORDED", "harvest_lots", lot_id, f"{fmt(q)} {lot['unit']}: {why}")
    return lot_id


def set_lot_active(user: User, lot_id, active: bool) -> int:
    require_role(user, "farmer", "deactivate lot")
    with db.transaction() as cur:
        cur.execute("SELECT 1 FROM harvest_lots WHERE lot_id=%s FOR UPDATE", (lot_id,))
        if cur.fetchone() is None:
            raise UserError("Harvest lot not found.")
        if not is_my_farm(cur, user, lot_farm(cur, lot_id)):
            deny(user, "deactivate another farm's lot", "harvest_lots", lot_id)
        s = lot_stock(cur, lot_id)
        if not active and s["reserved"] > EPS:
            raise UserError("This lot has reserved stock; release the allocations before deactivating it.")
        cur.execute("UPDATE harvest_lots SET is_active=%s WHERE lot_id=%s", (1 if active else 0, lot_id))
        log_event(cur, user, "LOT_REACTIVATED" if active else "LOT_DEACTIVATED", "harvest_lots", lot_id)
    return lot_id


def open_lot(user: User, lot_id) -> dict:
    """Open a lot by its number. Another farm's lot is refused and the attempt is audited."""
    require_role(user, "farmer", "view lot")
    with db.transaction() as cur:
        farm = lot_farm(cur, lot_id)
        if farm is None:
            raise UserError("Harvest lot not found.")
        if not is_my_farm(cur, user, farm):
            deny(user, "open another farm's lot", "harvest_lots", lot_id)
        cur.execute("SELECT * FROM v_lot_details WHERE lot_id=%s", (lot_id,))
        return cur.fetchone()


def allocate(user: User, request_id, lot_id, qty) -> int:
    """Reserve produce from one of the farmer's lots for a market request.
    Locks the lot row, so two simultaneous allocations can never oversell it."""
    require_role(user, "farmer", "allocate produce")
    q = req_num(qty, "Allocation quantity")
    with db.transaction() as cur:
        cur.execute("SELECT * FROM harvest_lots WHERE lot_id=%s FOR UPDATE", (lot_id,))
        lot = cur.fetchone()
        if lot is None:
            raise UserError("Harvest lot not found.")
        if not is_my_farm(cur, user, lot_farm(cur, lot_id)):
            deny(user, "allocate from another farm's lot", "harvest_lots", lot_id)
        cur.execute("SELECT 1 FROM market_requests WHERE request_id=%s FOR UPDATE", (request_id,))
        if cur.fetchone() is None:
            raise UserError("Request not found.")
        r = request_progress(cur, request_id)
        if r["status"] in ("FULFILLED", "CLOSED", "CANCELLED"):
            raise UserError("This request is already closed, cancelled or fulfilled.")
        if not lot["is_active"]:
            raise UserError("This harvest lot is inactive.")
        if lot["crop_id"] != r["crop_id"]:
            cur.execute("SELECT crop_id, crop_name FROM crops WHERE crop_id IN (%s,%s)", (lot["crop_id"], r["crop_id"]))
            names = {x["crop_id"]: x["crop_name"] for x in cur.fetchall()}
            raise UserError(f"Lot crop ({names.get(lot['crop_id'])}) does not match the requested crop "
                            f"({names.get(r['crop_id'])}).")
        if lot["sell_by_date"] is not None and lot["sell_by_date"] < today():
            raise UserError("This lot is past its sell-by date and cannot be allocated.")
        s = lot_stock(cur, lot_id)
        if q > s["available"] + EPS:
            raise UserError(f"Cannot allocate {fmt(q)} {lot['unit']}: only {fmt(s['available'])} {lot['unit']} "
                            f"is available in lot #{lot_id}.")
        q_req = convert_qty(cur, q, lot["unit"], r["unit"])
        if q_req > r["remaining_need"] + EPS:
            raise UserError(f"This would exceed the request: only {fmt(r['remaining_need'])} {r['unit']} is still needed.")
        cur.execute("INSERT INTO allocations (request_id, lot_id, quantity, unit, status, allocated_by) "
                    "VALUES (%s,%s,%s,%s,'ACTIVE',%s)", (request_id, lot_id, q, lot["unit"], user.user_id))
        alloc_id = cur.lastrowid
        add_movement(cur, user, lot_id, "RESERVED", q, lot["unit"], f"Allocated to request #{request_id}", alloc_id)
        refresh_status(cur, user, request_id, "Allocation created")
        log_event(cur, user, "ALLOCATION_CREATED", "allocations", alloc_id,
                  f"request #{request_id}, lot #{lot_id}, {fmt(q)} {lot['unit']}")
    return alloc_id


def release_allocation(user: User, allocation_id, reason) -> int:
    require_role(user, "farmer", "release allocation")
    why = req_text(reason, "Reason", True, 200)
    with db.transaction() as cur:
        cur.execute("SELECT * FROM allocations WHERE allocation_id=%s FOR UPDATE", (allocation_id,))
        a = cur.fetchone()
        if a is None:
            raise UserError("Allocation not found.")
        if not is_my_farm(cur, user, lot_farm(cur, a["lot_id"])):
            deny(user, "release another farm's allocation", "allocations", allocation_id)
        if a["status"] != "ACTIVE":
            raise UserError("Only active allocations can be released.")
        add_movement(cur, user, a["lot_id"], "RESERVATION_RELEASED", Decimal(a["quantity"]), a["unit"], why, allocation_id)
        cur.execute("UPDATE allocations SET status='RELEASED', closed_at=NOW() WHERE allocation_id=%s", (allocation_id,))
        refresh_status(cur, user, a["request_id"], f"Allocation released: {why}")
        log_event(cur, user, "ALLOCATION_RELEASED", "allocations", allocation_id, why)
    return allocation_id
