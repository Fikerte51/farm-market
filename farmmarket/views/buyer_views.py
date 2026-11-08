"""Market-buyer pages: search local produce, my requests, confirm deliveries."""
import datetime as dt

import streamlit as st

from .. import buyer, config, queries
from ..core import today
from . import ui


def search(user):
    ui.show_flash()
    st.header("Search local produce")
    st.caption("Only available quantities are shown (not reserved, not past the sell-by date). Expected harvests are forecasts and are listed separately.")
    c1, c2, c3 = st.columns(3)
    crop = c1.selectbox("Crop", [None] + queries.crops(), format_func=lambda c: "Any crop" if c is None else c["crop_name"], key="bs_crop")
    emirate = c2.selectbox("Farm location (emirate)", [None] + config.EMIRATES, format_func=lambda e: "Any emirate" if e is None else e, key="bs_em")
    needed = c3.date_input("Still sellable on", value=today(), min_value=None, key="bs_date", format="YYYY-MM-DD")
    c4, c5 = st.columns(2)
    min_qty = c4.number_input("Minimum available quantity (0 = any)", min_value=0.0, value=0.0, step=10.0, key="bs_qty", format="%.3f")
    unit = c5.selectbox("Unit for the minimum", queries.units(), format_func=lambda u: u["unit_code"], key="bs_unit")
    rows = queries.search_produce(crop["crop_id"] if crop else None, emirate, needed, min_qty or None, unit["unit_code"] if unit else None)
    st.subheader(f"{len(rows)} lot(s) available")
    ui.table(rows, ["lot_id", "crop_name", "farm_name", "emirate", "harvest_date", "sell_by_date", "available", "unit", "image_count"],
             empty="No produce matches these filters. Try another crop, emirate or date, or create a request so farmers can supply it.")
    if rows:
        sel = st.selectbox("View photos of a lot", rows, key="bs_lot", format_func=lambda l: f"Lot #{l['lot_id']} · {l['crop_name']} · {l['farm_name']}")
        ui.show_lot_images(sel["lot_id"], key_prefix="bs")
    with st.expander("Expected harvests (forecast, NOT available stock)"):
        fc = [c for c in queries.list_cycles(user, crop_id=crop["crop_id"] if crop else None, emirate=emirate)
              if c["status"] in ("PLANNED", "GROWING", "HARVESTING")]
        ui.table(fc, ["crop_name", "emirate", "expected_harvest_date", "expected_quantity", "expected_unit", "status"],
                 empty="No expected harvests match.")


def requests(user):
    ui.show_flash()
    st.header(f"My requests — {user.market_name}")
    with st.expander("➕ Create a request", expanded=False):
        with st.form(ui.form_key("new_req")):
            crop = st.selectbox("Crop", queries.crops(), format_func=lambda c: c["crop_name"])
            c1, c2, c3 = st.columns(3)
            qty = c1.number_input("Quantity", value=0.0, step=10.0, format="%.3f")
            unit = c2.selectbox("Unit", queries.units(), format_func=lambda u: u["unit_code"])
            needed = c3.date_input("Needed by", value=today() + dt.timedelta(days=7), format="YYYY-MM-DD")
            notes = st.text_input("Notes (optional)")
            if st.form_submit_button("Submit request"):
                ok, rid = ui.run(buyer.create_request, user, crop["crop_id"], qty, unit["unit_code"], needed, notes)
                if ok:
                    ui.reset_form("new_req")
                    st.session_state["_flash"] = f"Request #{rid} submitted."
                    st.rerun()

    c1, c2 = st.columns(2)
    status = c1.selectbox("Status", [None] + config.REQUEST_STATUSES, format_func=lambda s: "All statuses" if s is None else s, key="mr_status")
    crop_f = c2.selectbox("Crop", [None] + queries.crops(False), format_func=lambda c: "All crops" if c is None else c["crop_name"], key="mr_crop")
    reqs = queries.list_requests(user, status=status, crop_id=crop_f["crop_id"] if crop_f else None)
    ui.table(reqs, ["request_id", "crop_name", "requested", "unit", "needed_by_date", "status", "allocated_open", "received", "remaining_need", "notes"],
             empty="You have no requests yet.")
    if not reqs:
        return
    req = st.selectbox("Select a request to view, change or close", reqs, key="mr_sel",
                       format_func=lambda r: f"#{r['request_id']} · {r['crop_name']} · {ui._fmt(r['requested'])} {r['unit']} · {r['status']}")
    with st.expander("Status history"):
        ui.table(queries.request_history(user, req["request_id"]))
    with st.expander("Allocations for this request"):
        ui.table(queries.list_allocations(user, request_id=req["request_id"]),
                 ["allocation_id", "lot_id", "farm_name", "quantity", "unit", "status", "allocated_at"])
    if req["status"] in ("FULFILLED", "CLOSED", "CANCELLED"):
        st.info("This request is finished and can no longer be changed.")
        return
    with st.form(ui.form_key("upd_req")):
        st.markdown("**Change quantity / date**")
        c1, c2 = st.columns(2)
        qty = c1.number_input("Quantity", value=float(req["requested"]), step=10.0, format="%.3f")
        needed = c2.date_input("Needed by", value=max(req["needed_by_date"], today()), format="YYYY-MM-DD")
        notes = st.text_input("Notes", value=req["notes"] or "")
        if st.form_submit_button("Save changes"):
            ui.run(buyer.update_request, user, req["request_id"], qty, needed, notes, success="Request updated.", rerun=True)
    with st.form(ui.form_key("close_req")):
        st.markdown("**Close / cancel this request** (reserved produce is released back to the farms)")
        why = st.text_input("Reason (required)")
        if st.form_submit_button("Close request"):
            ok, new = ui.run(buyer.close_request, user, req["request_id"], why)
            if ok:
                ui.reset_form("close_req")
                st.session_state["_flash"] = f"Request #{req['request_id']} is now {new}."
                st.rerun()


def deliveries(user):
    ui.show_flash()
    st.header("Confirm deliveries")
    st.caption("Record the quantity you actually received. If it differs from the allocation, give a reason; the difference is stored on the receipt.")
    active = queries.list_allocations(user, status="ACTIVE")
    ui.table(active, ["allocation_id", "request_id", "crop_name", "farm_name", "quantity", "unit", "allocated_at"],
             empty="Nothing is waiting for delivery confirmation.")
    if active:
        a = st.selectbox("Allocation to confirm", active, key="dl_sel",
                         format_func=lambda a: f"Allocation #{a['allocation_id']} · request #{a['request_id']} · {a['crop_name']} from {a['farm_name']} · {ui._fmt(a['quantity'])} {a['unit']} allocated")
        with st.form(ui.form_key("deliver")):
            c1, c2 = st.columns(2)
            recv = c1.number_input(f"Quantity received ({a['unit']})", value=float(a["quantity"]), step=1.0, format="%.3f")
            rdate = c2.date_input("Received on", value=today(), format="YYYY-MM-DD")
            why = st.text_input("Reason for the difference (required if received ≠ allocated)")
            if st.form_submit_button("Confirm delivery"):
                ok, rid = ui.run(buyer.confirm_delivery, user, a["allocation_id"], recv, rdate, why)
                if ok:
                    ui.reset_form("deliver")
                    st.session_state["_flash"] = f"Delivery confirmed (receipt #{rid})."
                    st.rerun()
    st.subheader("My delivery receipts")
    c1, c2 = st.columns(2)
    only = c1.checkbox("Only deliveries with a discrepancy", key="dl_only")
    ui.table(queries.list_receipts(user, only_discrepancies=only),
             ["receipt_id", "request_id", "crop_name", "farm_name", "allocated_quantity", "received_quantity", "discrepancy", "unit",
              "discrepancy_reason", "received_date"])
