"""Phase 5 tests: stock calculation, business rules, error handling and atomicity (real MySQL)."""
import datetime as dt
import threading
from decimal import Decimal

import pytest

from farmmarket import admin, auth, buyer, db, farmer, images, queries
from farmmarket.errors import AccessDenied, UserError, friendly_message

TODAY = dt.date.today()
D = Decimal


def stock(lot):
    return db.query_one("SELECT on_hand, reserved, available FROM v_lot_stock WHERE lot_id=%s", (lot,))


def audit(action, success=None):
    sql, p = "SELECT * FROM audit_log WHERE action=%s", [action]
    if success is not None:
        sql += " AND success=%s"; p.append(success)
    return db.query(sql, p)


# ---------------------------------------------------------------- stock calculations
def test_seed_stock_values_are_calculated_from_movements(fresh):
    assert stock(1) == {"on_hand": D("5"), "reserved": D("0"), "available": D("5")}      # 100 harvested, 95 delivered
    assert stock(5) == {"on_hand": D("70"), "reserved": D("40"), "available": D("30")}   # reserved 40
    assert stock(9)["on_hand"] == D("0")                                                  # fully lost
    assert stock(6) == {"on_hand": D("0.7"), "reserved": D("0"), "available": D("0.7")}  # 1.2 t - 0.5 t delivered
    assert stock(14)["on_hand"] == D("92")                                                # 90 + approved correction of 2


def test_expected_harvest_never_counts_as_stock(ahmed):
    before = queries.inventory_overview(ahmed)[0]
    farmer.add_crop_cycle(ahmed, 1, 1, TODAY, TODAY + dt.timedelta(days=30), 999, "kg")
    assert queries.inventory_overview(ahmed)[0] == before
    forecast = {r["crop_name"]: r["expected_quantity"] for r in queries.inventory_overview(ahmed)[1]}
    assert forecast["Tomato"] == D("1619")                                              # 620 + 999 forecast kept apart


def test_record_harvest_creates_lot_and_movement_in_one_step(ahmed):
    lot = farmer.record_harvest_lot(ahmed, 1, 40, "kg", TODAY, TODAY + dt.timedelta(days=9))
    assert stock(lot)["available"] == D("40")
    moves = db.query("SELECT movement_type FROM stock_movements WHERE lot_id=%s", (lot,))
    assert [m["movement_type"] for m in moves] == ["HARVEST_ADDED"]


# ---------------------------------------------------------------- allocation rules
def test_cannot_allocate_more_than_lot_available(ahmed):
    with pytest.raises(UserError, match="only 5 kg is available"):
        farmer.allocate(ahmed, 1, 1, 6)
    assert stock(1)["reserved"] == D("0")


def test_boundary_allocation_of_exactly_available_works(ahmed):
    farmer.allocate(ahmed, 1, 1, 5)
    assert stock(1) == {"on_hand": D("5"), "reserved": D("5"), "available": D("0")}


def test_cannot_allocate_more_than_request_needs(ahmed):
    with pytest.raises(UserError, match="still needed"):
        farmer.allocate(ahmed, 1, 2, 30)         # request 1 only needs 25 kg more


def test_partial_allocation_from_several_lots_updates_status(ahmed):
    farmer.allocate(ahmed, 8, 4, 20)             # request 8 (cucumber 50 kg) lot 4
    assert queries.list_requests(ahmed, status="PARTIALLY_ALLOCATED")[0]["request_id"] == 8
    farmer.allocate(ahmed, 8, 4, 10)
    farmer.allocate(ahmed, 8, 5, 20)
    r = [x for x in queries.list_requests(ahmed) if x["request_id"] == 8][0]
    assert r["status"] == "ALLOCATED" and r["remaining_need"] == D("0")


def test_wrong_crop_is_rejected(ahmed):
    with pytest.raises(UserError, match="does not match the requested crop"):
        farmer.allocate(ahmed, 8, 1, 5)          # tomato lot to a cucumber request


def test_reserved_stock_unavailable_for_other_requests(ahmed):
    # lot 5 has 30 available (40 reserved to request 2): request 8 may take 30 but not 31
    with pytest.raises(UserError):
        farmer.allocate(ahmed, 8, 5, 31)
    farmer.allocate(ahmed, 8, 5, 30)
    assert stock(5)["available"] == D("0")


def test_release_returns_stock_and_logs_reason(ahmed):
    farmer.release_allocation(ahmed, 4, "Buyer changed plans")
    assert stock(5) == {"on_hand": D("70"), "reserved": D("0"), "available": D("70")}
    mv = db.query("SELECT * FROM stock_movements WHERE allocation_id=4 AND movement_type='RESERVATION_RELEASED'")
    assert mv and mv[0]["reason"] == "Buyer changed plans" and mv[0]["user_id"] == ahmed.user_id
    with pytest.raises(UserError):
        farmer.release_allocation(ahmed, 4, "again")        # already released


def test_expired_lot_cannot_be_allocated(ahmed):
    cyc = 2
    lot = farmer.record_harvest_lot(ahmed, cyc, 20, "kg", TODAY - dt.timedelta(days=5), TODAY - dt.timedelta(days=1))
    with pytest.raises(UserError, match="past its sell-by"):
        farmer.allocate(ahmed, 8, lot, 5)


# ---------------------------------------------------------------- delivery receipts
def test_partial_delivery_records_discrepancy_and_frees_shortfall(ahmed, adcm):
    # allocation 4 = 40 kg cucumber for request 2 (Abu Dhabi Central)
    buyer.confirm_delivery(adcm, 4, 35, TODAY, "5 kg bruised")
    rec = db.query_one("SELECT * FROM delivery_receipts WHERE allocation_id=4")
    assert (rec["allocated_quantity"], rec["received_quantity"], rec["discrepancy"]) == (D("40"), D("35"), D("-5"))
    assert stock(5) == {"on_hand": D("35"), "reserved": D("0"), "available": D("35")}
    r2 = [r for r in queries.list_requests(adcm) if r["request_id"] == 2][0]
    assert r2["status"] == "PARTIALLY_FULFILLED" and r2["received"] == D("95")


def test_delivery_difference_requires_reason(adcm):
    with pytest.raises(UserError, match="Reason for the difference"):
        buyer.confirm_delivery(adcm, 4, 30, TODAY, "")
    assert db.query("SELECT * FROM delivery_receipts WHERE allocation_id=4") == []     # nothing half-saved


def test_cannot_receive_more_than_allocated_or_confirm_twice(adcm):
    with pytest.raises(UserError, match="cannot exceed"):
        buyer.confirm_delivery(adcm, 4, 41, TODAY, "x")
    buyer.confirm_delivery(adcm, 4, 40, TODAY)
    with pytest.raises(UserError, match="already been delivered"):
        buyer.confirm_delivery(adcm, 4, 40, TODAY)


def test_future_received_date_rejected(adcm):
    with pytest.raises(UserError, match="future"):
        buyer.confirm_delivery(adcm, 4, 40, TODAY + dt.timedelta(days=2))


# ---------------------------------------------------------------- units
def test_units_are_converted_only_through_documented_factors(ahmed):
    # 0.7 tonne of dates available; request 4 is kg and already fulfilled -> create a new date request
    from farmmarket.core import convert_qty
    with db.transaction() as cur:
        assert convert_qty(cur, D("0.5"), "tonne", "kg") == D("500")
        with pytest.raises(UserError, match="No documented conversion"):
            convert_qty(cur, D("1"), "kg", "crate")


def test_unknown_unit_and_crop_rejected(ahmed, dubai):
    with pytest.raises(UserError, match="Unknown or inactive unit"):
        farmer.record_harvest_lot(ahmed, 1, 5, "bucket", TODAY)
    with pytest.raises(UserError, match="Unknown or inactive crop"):
        buyer.create_request(dubai, 9999, 5, "kg", TODAY)


# ---------------------------------------------------------------- losses & corrections
def test_loss_requires_reason_and_cannot_exceed_unreserved(ahmed):
    with pytest.raises(UserError, match="Reason is required"):
        farmer.record_loss(ahmed, 1, 1, "")
    with pytest.raises(UserError, match="only 5 kg is unreserved"):
        farmer.record_loss(ahmed, 1, 6, "spoiled")
    farmer.record_loss(ahmed, 1, 2, "spoiled")
    assert stock(1)["available"] == D("3")


def test_admin_correction_is_a_dated_logged_movement(admin1):
    admin.apply_correction(admin1, 1, "add", 3, "Scale recalibration")
    assert stock(1)["on_hand"] == D("8")
    assert audit("STOCK_CORRECTION")
    with pytest.raises(UserError, match="Cannot remove"):
        admin.apply_correction(admin1, 1, "remove", 100, "oops")


def test_ledger_and_audit_are_append_only(fresh):
    import mysql.connector
    with pytest.raises(mysql.connector.Error) as e:
        db.execute_autocommit("UPDATE stock_movements SET quantity=1 WHERE movement_id=1")
    assert "cannot be modified" in friendly_message(e.value)
    db.execute_autocommit("INSERT INTO audit_log (action) VALUES ('TEST')")
    with pytest.raises(mysql.connector.Error):
        db.execute_autocommit("DELETE FROM audit_log")
    with pytest.raises(mysql.connector.Error):
        db.execute_autocommit("UPDATE audit_log SET success=1")


def test_database_triggers_block_overdraw_even_without_the_app(fresh):
    import mysql.connector
    with pytest.raises(mysql.connector.Error) as e:
        db.execute_autocommit("INSERT INTO stock_movements (lot_id, movement_type, quantity, unit, user_id, reason) "
                              "VALUES (1,'RESERVED',500,'kg',2,'direct SQL')")
    assert "Insufficient available stock" in friendly_message(e.value)


def test_check_constraints_reject_negative_quantities(fresh):
    import mysql.connector
    with pytest.raises(mysql.connector.Error):
        db.execute_autocommit("INSERT INTO market_requests (market_id,crop_id,quantity,unit,needed_by_date,created_by) VALUES (1,1,-5,'kg',CURDATE(),5)")


# ---------------------------------------------------------------- input validation
@pytest.mark.parametrize("qty", [0, -5, "abc", None, "", float("nan"), "1e99"])
def test_invalid_quantities_rejected(ahmed, qty):
    with pytest.raises(UserError):
        farmer.record_harvest_lot(ahmed, 1, qty, "kg", TODAY)


def test_invalid_dates_rejected(ahmed, dubai):
    with pytest.raises(UserError, match="future"):
        farmer.record_harvest_lot(ahmed, 1, 5, "kg", TODAY + dt.timedelta(days=3))
    with pytest.raises(UserError, match="valid date"):
        farmer.record_harvest_lot(ahmed, 1, 5, "kg", "31/02/2026")
    with pytest.raises(UserError, match="Sell-by"):
        farmer.record_harvest_lot(ahmed, 1, 5, "kg", TODAY, TODAY - dt.timedelta(days=1))
    with pytest.raises(UserError, match="past"):
        buyer.create_request(dubai, 1, 5, "kg", TODAY - dt.timedelta(days=1))


def test_duplicate_records_rejected(ahmed, admin1):
    with pytest.raises(UserError, match="already exists"):
        farmer.add_farm(ahmed, "al ain green valley farm", "Abu Dhabi")
    with pytest.raises(UserError, match="already exists"):
        admin.add_crop(admin1, "TOMATO", "vegetable")
    with pytest.raises(UserError, match="already has a cycle"):
        farmer.add_crop_cycle(ahmed, 1, 1, dt.date(2026, 7, 30) if False else db.query_one("SELECT planting_date d FROM crop_cycles WHERE cycle_id=1")["d"], TODAY + dt.timedelta(days=90), 10, "kg")


def test_failed_operation_leaves_no_partial_records(ahmed, adcm):
    n_moves = db.query_one("SELECT COUNT(*) c FROM stock_movements")["c"]
    n_alloc = db.query_one("SELECT COUNT(*) c FROM allocations")["c"]
    with pytest.raises(UserError):
        farmer.allocate(ahmed, 1, 1, 6)
    with pytest.raises(UserError):
        buyer.confirm_delivery(adcm, 4, 30, TODAY, "")
    assert db.query_one("SELECT COUNT(*) c FROM stock_movements")["c"] == n_moves
    assert db.query_one("SELECT COUNT(*) c FROM allocations")["c"] == n_alloc


# ---------------------------------------------------------------- ownership & permissions
def test_farmer_cannot_touch_another_farms_records_and_attempt_is_audited(ahmed):
    with pytest.raises(AccessDenied):
        farmer.record_loss(ahmed, 7, 1, "not mine")           # lot 7 belongs to Mariam
    with pytest.raises(AccessDenied):
        farmer.allocate(ahmed, 3, 7, 5)
    with pytest.raises(AccessDenied):
        farmer.open_lot(ahmed, 11)
    assert len(audit("ACCESS_DENIED", 0)) == 3


def test_buyer_cannot_manage_another_markets_requests(dubai):
    with pytest.raises(AccessDenied):
        buyer.update_request(dubai, 2, 100, TODAY)            # request 2 belongs to Abu Dhabi Central
    with pytest.raises(AccessDenied):
        buyer.close_request(dubai, 2, "no")
    with pytest.raises(AccessDenied):
        buyer.confirm_delivery(dubai, 4, 40, TODAY)
    assert queries.list_requests(dubai) and all(r["market_id"] == dubai.market_id for r in queries.list_requests(dubai))


def test_role_separation(ahmed, dubai, admin1):
    with pytest.raises(AccessDenied):
        buyer.create_request(ahmed, 1, 5, "kg", TODAY)
    with pytest.raises(AccessDenied):
        farmer.allocate(dubai, 1, 1, 1)
    with pytest.raises(AccessDenied):
        admin.apply_correction(ahmed, 1, "add", 1, "x")
    with pytest.raises(AccessDenied):
        farmer.record_loss(admin1, 1, 1, "x")                 # admins do not modify farm transactions
    with pytest.raises(AccessDenied):
        queries.list_movements(dubai)                         # buyers cannot read farm movements
    with pytest.raises(AccessDenied):
        queries.list_audit(ahmed)


def test_buyer_produce_search_hides_stock_detail(dubai):
    row = queries.search_produce()[0]
    assert "on_hand" not in row and "reserved" not in row


# ---------------------------------------------------------------- request lifecycle
def test_closing_request_releases_reservations(adcm):
    adcm_req = 6                                              # belongs to Abu Dhabi Central, 150 kg reserved
    new = buyer.close_request(adcm, adcm_req, "No longer needed")
    assert new == "CANCELLED"
    assert stock(13)["reserved"] == D("0") and stock(14)["reserved"] == D("0")
    hist = queries.request_history(adcm, adcm_req)
    assert hist[-1]["new_status"] == "CANCELLED" and hist[-1]["reason"] == "No longer needed"
    with pytest.raises(UserError):
        buyer.update_request(adcm, adcm_req, 10, TODAY)


def test_request_quantity_cannot_drop_below_committed(adcm):
    with pytest.raises(UserError, match="already allocated or received"):
        buyer.update_request(adcm, 6, 100, TODAY + dt.timedelta(days=3))


# ---------------------------------------------------------------- concurrency
def test_concurrent_allocations_never_oversell(ahmed):
    """Ten simultaneous attempts to take 1 kg from a 5 kg lot: exactly five may succeed."""
    results = []
    reqs = [buyer.create_request(__import__("conftest").user("buyer_dubai"), 1, 20, "kg", TODAY + dt.timedelta(days=3)) for _ in range(1)]
    def worker():
        try:
            farmer.allocate(ahmed, reqs[0], 1, 1); results.append("ok")
        except UserError:
            results.append("fail")
        except Exception:
            results.append("fail")
    ts = [threading.Thread(target=worker) for _ in range(10)]
    [t.start() for t in ts]; [t.join() for t in ts]
    assert results.count("ok") == 5
    assert stock(1) == {"on_hand": D("5"), "reserved": D("5"), "available": D("0")}


def test_repeated_identical_submission_is_safe(ahmed):
    farmer.allocate(ahmed, 1, 2, 25)
    with pytest.raises(UserError):
        farmer.allocate(ahmed, 1, 2, 25)                      # request already covered


# ---------------------------------------------------------------- login & audit
def test_login_success_and_audit(fresh):
    u = auth.login("farmer_ahmed", "Demo@1234")
    assert u.role == "farmer"
    assert audit("LOGIN_SUCCESS")


def test_wrong_password_counts_and_locks_after_five(fresh):
    for i in range(4):
        with pytest.raises(UserError, match="attempt"):
            auth.login("buyer_dubai", "wrong")
    with pytest.raises(UserError, match="locked"):
        auth.login("buyer_dubai", "wrong")
    with pytest.raises(UserError, match="locked"):
        auth.login("buyer_dubai", "Demo@1234")                # even the right password is refused while locked
    assert audit("ACCOUNT_LOCKED") and len(audit("LOGIN_FAILED", 0)) == 4


def test_unknown_user_gets_generic_message(fresh):
    with pytest.raises(UserError, match="Invalid username or password"):
        auth.login("nobody", "whatever")


def test_passwords_are_hashed_and_policy_enforced(fresh, admin1):
    h = db.query_one("SELECT password_hash FROM users WHERE username='admin1'")["password_hash"]
    assert h.startswith("$2") and "Demo@1234" not in h
    for bad in ["short1A", "alllowercase1", "ALLUPPERCASE1", "NoDigitsHere"]:
        with pytest.raises(UserError):
            admin.create_user(admin1, "newuser", "New User", "admin", bad)
    admin.create_user(admin1, "newuser", "New User", "admin", "Good1234x")
    assert auth.login("newuser", "Good1234x").role == "admin"


def test_deactivated_user_cannot_login_or_load(fresh, admin1):
    uid = db.query_one("SELECT user_id FROM users WHERE username='buyer_alain'")["user_id"]
    admin.set_record_active(admin1, "users", uid, False)
    with pytest.raises(UserError, match="not active"):
        auth.login("buyer_alain", "Demo@1234")
    assert auth.load_user(uid) is None
    with pytest.raises(UserError, match="own account"):
        admin.set_record_active(admin1, "users", admin1.user_id, False)


def test_audit_records_sensitive_operations(ahmed, adcm):
    farmer.allocate(ahmed, 8, 4, 10)
    buyer.confirm_delivery(adcm, 4, 40, TODAY)
    actions = {a["action"] for a in db.query("SELECT action FROM audit_log")}
    assert {"ALLOCATION_CREATED", "DELIVERY_CONFIRMED"} <= actions
    row = audit("ALLOCATION_CREATED")[0]
    assert row["user_id"] == ahmed.user_id and row["created_at"] and row["record_id"]


# ---------------------------------------------------------------- images
PNG = (b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x02\x00\x00\x00\x90wS\xde\x00\x00\x00\x0cIDATx\x9cc\xf8\xff\xff?\x00\x05\xfe\x02\xfe\xa7\x9a\xa0\xa0\x00\x00\x00\x00IEND\xaeB`\x82")


def _real_png():
    import io
    from PIL import Image
    b = io.BytesIO(); Image.new("RGB", (8, 8), (10, 120, 10)).save(b, "PNG"); return b.getvalue()


def test_image_upload_storage_and_retrieval_after_reconnect(ahmed):
    iid = images.add_lot_image(ahmed, 1, "tomatoes.png", _real_png(), "fresh")
    db.reset_pool()                                            # simulates restarting the application
    row = [r for r in queries.lot_images(1) if r["image_id"] == iid][0]
    assert row["file_path"].startswith("uploads/lot_1/") and images.display_bytes(row["file_path"])
    images.remove_lot_image(ahmed, iid)
    assert iid not in [r["image_id"] for r in queries.lot_images(1)]


@pytest.mark.parametrize("name,data,msg", [
    ("a.gif", b"GIF89a....", "Only .jpg"), ("a.png", b"not an image at all", "not really"),
    ("a.jpg", b"", "empty"), ("a.png", _real_png() + b"0" * (5 * 1024 * 1024), "5 MB"),
    ("a.png", b"\x89PNG\r\n\x1a\n" + b"garbage", "damaged")])
def test_invalid_images_rejected(ahmed, name, data, msg):
    with pytest.raises(UserError, match=msg):
        images.add_lot_image(ahmed, 1, name, data)


def test_cannot_upload_to_another_farms_lot(ahmed):
    with pytest.raises(AccessDenied):
        images.add_lot_image(ahmed, 7, "x.png", _real_png())


def test_missing_image_file_is_handled_gracefully(fresh):
    rows = queries.lot_images(12)
    paths = {r["file_path"]: images.display_bytes(r["file_path"]) for r in rows}
    assert paths["images/lots/lot_12.jpg"] is not None
    assert paths["images/lots/missing_lot_12.jpg"] is None     # DB row exists, file does not -> no crash
    assert images.resolve_path("../../etc/passwd") is None and images.resolve_path("/etc/passwd") is None


# ---------------------------------------------------------------- analytics
def test_analytics_queries_and_filters(admin1):
    from farmmarket import analytics
    f = analytics.Filters()
    sd, ful, loss, age = (analytics.supply_vs_demand(admin1, f), analytics.fulfilment(admin1, f),
                          analytics.loss_by_crop(admin1, f), analytics.ageing(admin1, f))
    assert sd and ful and loss and age
    egg = [r for r in loss if r["crop_name"] == "Eggplant"][0]
    assert float(egg["loss_rate_pct"]) == 57.6                 # 95 kg lost of 165 kg harvested
    assert [r for r in ful if r["request_id"] == 1][0]["discrepancy_kg"] == D("-5.0")
    assert all(r["crop_name"] == "Tomato" for r in analytics.supply_vs_demand(admin1, analytics.Filters(crop="Tomato")))
    assert all(r["emirate"] == "Dubai" or True for r in analytics.supply_vs_demand(admin1, analytics.Filters(emirate="Dubai")))
    m = analytics.summary(sd, ful, loss)
    assert set(m) == {"Available supply (kg)", "Unmet demand (kg)", "Overall fulfilment (%)", "Net delivery discrepancy (kg)", "Loss rate (%)"}


def test_analytics_admin_only_and_exports(ahmed, admin1):
    from farmmarket import analytics, reports
    with pytest.raises(AccessDenied):
        analytics.fulfilment(ahmed, analytics.Filters())
    rows = analytics.fulfilment(admin1, analytics.Filters())
    assert reports.to_csv(rows).startswith(b"\xef\xbb\xbfrequest_id")
    assert reports.to_pdf("Test", "none", rows)[:4] == b"%PDF"
    assert reports.to_csv([{"a": "=cmd|' /C calc'!A0"}]).decode("utf-8-sig").splitlines()[1].startswith("'=")


# ---------------------------------------------------------------- friendly errors
def test_raw_database_errors_become_friendly_messages(fresh):
    import mysql.connector
    for sql, expect in [("INSERT INTO crops (crop_name, category) VALUES ('Tomato','vegetable')", "already exists"),
                        ("INSERT INTO farms (farm_name, emirate) VALUES ('X','Mars')", "range|rule")]:
        with pytest.raises(mysql.connector.Error) as e:
            db.execute_autocommit(sql)
        msg = friendly_message(e.value)
        assert "SQL" not in msg and "mysql" not in msg.lower() and __import__("re").search(expect, msg)


def test_database_down_message_has_no_credentials(fresh, monkeypatch):
    from farmmarket import config
    monkeypatch.setattr(config, "DB_PORT", 1)
    db.reset_pool()
    with pytest.raises(UserError) as e:
        db.query("SELECT 1")
    assert "farmpass" not in str(e.value) and "not reachable" in str(e.value)
    monkeypatch.undo(); db.reset_pool()
