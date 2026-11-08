"""Farmer pages: inventory overview, farms & crop cycles, harvest & stock, lot images, requests & allocation."""
import datetime as dt
from decimal import Decimal

import pandas as pd
import streamlit as st

from .. import config, farmer, images, queries
from ..core import today
from . import theme, ui


def _kg_factors() -> dict:
    return {u["unit_code"]: float(u["to_base_factor"]) for u in queries.units(False) if u["category"] == "mass"}


# =============================================================================== overview
def home(user):
    ui.show_flash()
    st.header("Inventory overview")
    st.caption("Saleable stock is calculated from stock movements. Expected harvest is a forecast and never counted as stock.")
    f = _kg_factors()
    lots = queries.list_lots(user)
    stock, forecast = queries.inventory_overview(user)
    kg = lambda rows, key, ukey="unit": sum(float(r[key]) * f[r[ukey]] for r in rows if r[ukey] in f)
    theme.metric_cards([("On hand (kg)", kg(stock, "on_hand")), ("Reserved (kg)", kg(stock, "reserved")),
                        ("Available (kg)", kg(stock, "available")),
                        ("Expected harvest - forecast (kg)", kg(forecast, "expected_quantity"))])

    st.subheader("Harvest lots (saleable stock)")
    st.caption("Totals above cover mass units converted to kg.")
    ui.table(lots, ["lot_id", "crop_name", "farm_name", "harvest_date", "sell_by_date", "unit", "on_hand", "reserved", "available"],
             empty="No stock recorded yet.")

    soon = [l for l in lots if l["sell_by_date"] and Decimal(l["available"]) > 0 and l["sell_by_date"] <= today() + dt.timedelta(days=3)]
    needing = queries.list_requests(user, needs_supply=True)
    if soon or needing:
        c1, c2 = st.columns(2)
        c1.markdown(f'<div class="note">⏳ {len(soon)} lot(s) reach their sell-by date within 3 days.</div>', unsafe_allow_html=True)
        c2.markdown(f'<div class="note">📨 {len(needing)} market request(s) still need supply (see Requests &amp; allocation).</div>', unsafe_allow_html=True)

    left, right = st.columns(2)
    with left:
        st.subheader("Stock by crop")
        ui.table(stock, empty="No stock recorded yet.")
    with right:
        st.subheader("Expected harvest (forecast only)")
        ui.table(forecast, empty="No open crop cycles.")

    chart = {}
    for l in lots:
        if l["unit"] in f:
            c = chart.setdefault(l["crop_name"], {"Available (kg)": 0.0, "Reserved (kg)": 0.0})
            c["Available (kg)"] += float(l["available"]) * f[l["unit"]]
            c["Reserved (kg)"] += float(l["reserved"]) * f[l["unit"]]
    if chart:
        st.subheader("Available vs reserved by crop (kg)")
        st.bar_chart(pd.DataFrame(chart).T, color=["#25603f", "#d2763a"])
    if soon:
        st.subheader("Lots close to their sell-by date")
        ui.table(soon, ["lot_id", "crop_name", "farm_name", "sell_by_date", "available", "unit"])


# =============================================================================== farms & cycles
def farms_cycles(user):
    ui.show_flash()
    st.header("Farms & crop cycles")
    my = queries.my_farms(user)
    st.subheader("My farms")
    ui.table(my, ["farm_id", "farm_name", "emirate", "location_desc", "area_hectares", "is_active"], empty="You have no farms yet. Add one below.")

    with st.expander("➕ Add a farm"):
        with st.form(ui.form_key("add_farm")):
            name = st.text_input("Farm name")
            emirate = st.selectbox("Emirate", config.EMIRATES)
            loc = st.text_input("Location description (optional)")
            area = st.number_input("Area in hectares (optional)", min_value=0.0, value=0.0, step=0.5, format="%.3f")
            if st.form_submit_button("Add farm"):
                ok, _ = ui.run(farmer.add_farm, user, name, emirate, loc, area or None, success="Farm added and assigned to you.", rerun=True)

    st.subheader("Crop cycles")
    cycles = queries.list_cycles(user)
    status_f = st.selectbox("Filter by status", ["All"] + config.CYCLE_STATUSES, key="cyc_status")
    shown = [c for c in cycles if status_f == "All" or c["status"] == status_f]
    ui.table(shown, ["cycle_id", "farm_name", "crop_name", "planting_date", "expected_harvest_date", "expected_quantity",
                     "expected_unit", "status"], empty="No crop cycles yet.")

    active_farms = [f for f in my if f["is_active"]]
    with st.expander("➕ Add a crop cycle (record the expected harvest forecast)"):
        if not active_farms:
            st.info("Add a farm first.")
        else:
            crops, units = queries.crops(), queries.units()
            with st.form(ui.form_key("add_cycle")):
                farm = st.selectbox("Farm", active_farms, format_func=lambda f: f["farm_name"])
                crop = st.selectbox("Crop", crops, format_func=lambda c: c["crop_name"])
                c1, c2 = st.columns(2)
                planting = c1.date_input("Planting date", value=today(), format="YYYY-MM-DD")
                expected = c2.date_input("Expected harvest date", value=today() + dt.timedelta(days=60), format="YYYY-MM-DD")
                c3, c4 = st.columns(2)
                qty = c3.number_input("Expected quantity (forecast)", value=0.0, step=10.0, format="%.3f")
                unit = c4.selectbox("Unit", units, format_func=lambda u: f"{u['unit_code']} ({u['unit_name']})")
                notes = st.text_input("Notes (optional)")
                if st.form_submit_button("Add crop cycle"):
                    ui.run(farmer.add_crop_cycle, user, farm["farm_id"], crop["crop_id"], planting, expected, qty,
                           unit["unit_code"], notes, success="Crop cycle added.", rerun=True)

    with st.expander("✏️ Update a forecast"):
        if not cycles:
            st.info("No cycles to update.")
        else:
            with st.form(ui.form_key("upd_cycle")):
                cy = st.selectbox("Crop cycle", cycles, format_func=lambda c: f"#{c['cycle_id']} · {c['crop_name']} · {c['farm_name']} · planted {c['planting_date']}")
                c1, c2, c3 = st.columns(3)
                exp = c1.date_input("Expected harvest date", value=today() + dt.timedelta(days=30), format="YYYY-MM-DD")
                qty = c2.number_input("Expected quantity", value=float(cycles[0]["expected_quantity"]), step=10.0, format="%.3f")
                status = c3.selectbox("Status", config.CYCLE_STATUSES, index=1)
                if st.form_submit_button("Save forecast"):
                    ui.run(farmer.update_cycle_forecast, user, cy["cycle_id"], exp, qty, status,
                           success="Forecast updated (stock is unchanged).", rerun=True)


# =============================================================================== harvest & stock
def harvest(user):
    ui.show_flash()
    st.header("Harvest & stock")
    tab_rec, tab_lots, tab_loss, tab_moves, tab_open = st.tabs(
        ["Record harvest", "Lots & stock", "Loss / deactivate", "Stock movements", "Open lot by number"])
    cycles = queries.list_cycles(user)
    units = queries.units()

    with tab_rec:
        if not cycles:
            st.info("Create a crop cycle first (Farms & crop cycles).")
        else:
            with st.form(ui.form_key("harvest")):
                cy = st.selectbox("Crop cycle", cycles, format_func=lambda c: f"#{c['cycle_id']} · {c['crop_name']} · {c['farm_name']} · planted {c['planting_date']}")
                c1, c2 = st.columns(2)
                qty = c1.number_input("Harvested quantity", value=0.0, step=5.0, format="%.3f")
                unit = c2.selectbox("Unit", units, format_func=lambda u: u["unit_code"])
                c3, c4 = st.columns(2)
                hdate = c3.date_input("Harvest date", value=today(), format="YYYY-MM-DD")
                has_sell = c4.checkbox("This lot has a sell-by date", value=True)
                sell = c4.date_input("Sell-by date", value=today() + dt.timedelta(days=10), format="YYYY-MM-DD")
                if st.form_submit_button("Record harvest lot"):
                    ok, lot_id = ui.run(farmer.record_harvest_lot, user, cy["cycle_id"], qty, unit["unit_code"], hdate,
                                        sell if has_sell else None)
                    if ok:
                        ui.reset_form("harvest")
                        st.session_state["_flash"] = f"Harvest lot #{lot_id} recorded. Upload a photo for it under 'Lot images'."
                        st.rerun()

    with tab_lots:
        crops = queries.crops(False)
        c1, c2, c3, c4 = st.columns(4)
        crop = c1.selectbox("Crop", [None] + crops, format_func=lambda c: "All crops" if c is None else c["crop_name"], key="lot_crop")
        farm = c2.selectbox("Farm", [None] + queries.my_farms(user), format_func=lambda f: "All farms" if f is None else f["farm_name"], key="lot_farm")
        avail = c3.checkbox("Only lots with available stock", key="lot_avail")
        inactive = c4.checkbox("Include inactive lots", key="lot_inactive")
        d1, d2 = st.columns(2)
        hf, ht = ui.optional_date("Harvested from", "lot_from"), ui.optional_date("Harvested to", "lot_to")
        lots = queries.list_lots(user, crop["crop_id"] if crop else None, farm["farm_id"] if farm else None, None, avail, hf, ht, inactive)
        ui.table(lots, ["lot_id", "crop_name", "farm_name", "harvest_date", "sell_by_date", "harvested_quantity", "unit",
                        "on_hand", "reserved", "available", "is_active", "image_count"])
        if lots:
            sel = st.selectbox("Show photos of a lot", lots, format_func=ui.lot_label, key="lot_photos")
            ui.show_lot_images(sel["lot_id"], key_prefix="lotpics")

    with tab_loss:
        lots = queries.list_lots(user, include_inactive=True)
        if not lots:
            st.info("No lots yet.")
        else:
            st.subheader("Record a loss")
            with st.form(ui.form_key("loss")):
                lot = st.selectbox("Harvest lot", lots, format_func=ui.lot_label)
                c1, c2 = st.columns([1, 2])
                qty = c1.number_input("Quantity lost", value=0.0, step=1.0, format="%.3f")
                why = c2.text_input("Reason (required)")
                if st.form_submit_button("Record loss"):
                    ok, _ = ui.run(farmer.record_loss, user, lot["lot_id"], qty, why)
                    if ok:
                        ui.reset_form("loss")
                        st.session_state["_flash"] = "Loss recorded as a stock movement."
                        st.rerun()
            st.subheader("Activate / deactivate a lot")
            st.caption("Lots are deactivated (not deleted) so the history is preserved. A lot with reserved stock cannot be deactivated.")
            lot2 = st.selectbox("Lot", lots, format_func=lambda l: ui.lot_label(l) + ("" if l["is_active"] else " [inactive]"), key="lot_toggle")
            if lot2["is_active"]:
                if st.button("Deactivate lot", key="deact_lot"):
                    ui.run(farmer.set_lot_active, user, lot2["lot_id"], False, success="Lot deactivated.", rerun=True)
            elif st.button("Reactivate lot", key="react_lot"):
                ui.run(farmer.set_lot_active, user, lot2["lot_id"], True, success="Lot reactivated.", rerun=True)

    with tab_moves:
        c1, c2, c3 = st.columns(3)
        crop = c1.selectbox("Crop", [None] + queries.crops(False), format_func=lambda c: "All crops" if c is None else c["crop_name"], key="mv_crop")
        mtype = c2.selectbox("Movement type", [None, "HARVEST_ADDED", "RESERVED", "RESERVATION_RELEASED", "DELIVERY", "LOSS",
                                              "CORRECTION_ADD", "CORRECTION_REMOVE"], format_func=lambda t: "All types" if t is None else t, key="mv_type")
        farm = c3.selectbox("Farm", [None] + queries.my_farms(user), format_func=lambda f: "All farms" if f is None else f["farm_name"], key="mv_farm")
        mf, mt = ui.optional_date("From", "mv_from"), ui.optional_date("To", "mv_to")
        rows = queries.list_movements(user, farm_id=farm["farm_id"] if farm else None, crop_id=crop["crop_id"] if crop else None,
                                      movement_type=mtype, date_from=mf, date_to=mt)
        ui.table(rows, ["movement_id", "movement_date", "lot_id", "crop_name", "farm_name", "movement_type", "quantity", "unit", "username", "reason"])

    with tab_open:
        st.caption("Open any lot by its number. Lots of farms that are not assigned to you are refused, and the attempt is written to the audit log.")
        n = st.number_input("Lot number", min_value=1, value=1, step=1, key="open_lot_no")
        if st.button("Open lot", key="open_lot_btn"):
            ok, lot = ui.run(farmer.open_lot, user, int(n))
            if ok:
                ui.table([lot], ["lot_id", "crop_name", "farm_name", "harvest_date", "sell_by_date", "on_hand", "reserved", "available", "unit"])
                ui.show_lot_images(lot["lot_id"], key_prefix="openlot")


# =============================================================================== images
def lot_images(user):
    ui.show_flash()
    st.header("Lot images")
    st.caption("Attach JPG or PNG photos (max 5 MB) to your harvest lots. Photos are saved on disk and linked in the database, so they are still there after the application restarts.")
    lots = queries.list_lots(user, include_inactive=True)
    if not lots:
        st.info("You have no harvest lots yet.")
        return
    lot = st.selectbox("Harvest lot", lots, format_func=ui.lot_label, key="img_lot")
    with st.form(ui.form_key("upload_img")):
        file = st.file_uploader("Image file (JPG or PNG)", type=["jpg", "jpeg", "png"], key=f"up_{st.session_state.get('_v_upload_img', 0)}")
        caption = st.text_input("Caption (optional)")
        if st.form_submit_button("Upload image"):
            if file is None:
                st.error("Please choose an image file first.", icon="⚠️")
            else:
                ok, _ = ui.run(images.add_lot_image, user, lot["lot_id"], file.name, file.getvalue(), caption)
                if ok:
                    ui.reset_form("upload_img")
                    st.session_state["_flash"] = "Image uploaded and linked to the lot."
                    st.rerun()
    st.subheader(f"Photos of lot #{lot['lot_id']}")

    def remove(image_id):
        ui.run(images.remove_lot_image, user, image_id, success="Photo removed.", rerun=True)
    ui.show_lot_images(lot["lot_id"], can_remove=remove, key_prefix="mgr")


# =============================================================================== requests & allocation
def allocation(user):
    ui.show_flash()
    st.header("Requests & allocation")
    st.caption("Reserve produce from lots of your own farms for market requests. A request can be filled partially and from several lots.")
    c1, c2, c3 = st.columns(3)
    crop = c1.selectbox("Crop", [None] + queries.crops(False), format_func=lambda c: "All crops" if c is None else c["crop_name"], key="al_crop")
    market = c2.selectbox("Market", [None] + queries.markets(False), format_func=lambda m: "All markets" if m is None else m["market_name"], key="al_market")
    emirate = c3.selectbox("Market emirate", [None] + config.EMIRATES, format_func=lambda e: "All emirates" if e is None else e, key="al_emirate")
    reqs = queries.list_requests(user, market_id=market["market_id"] if market else None, crop_id=crop["crop_id"] if crop else None,
                                 emirate=emirate, needs_supply=True)
    st.subheader("Requests that still need supply")
    ui.table(reqs, ["request_id", "market_name", "market_emirate", "crop_name", "requested", "unit", "needed_by_date", "status",
                    "allocated_open", "received", "remaining_need"], empty="No open requests need supply right now.")
    if reqs:
        req = st.selectbox("Choose a request", reqs, key="al_req",
                           format_func=lambda r: f"Request #{r['request_id']} · {r['market_name']} · {r['crop_name']} · still needs {ui._fmt(r['remaining_need'])} {r['unit']}")
        with st.expander("Status history of this request"):
            ui.table(queries.request_history(user, req["request_id"]))
        lots = queries.allocatable_lots(user, req["request_id"])
        st.markdown(f"**Still needed:** {ui._fmt(req['remaining_need'])} {req['unit']}")
        if not lots:
            st.warning("None of your farms has available, unexpired stock of this crop.")
        else:
            with st.form(ui.form_key("allocate")):
                lot = st.selectbox("Lot to allocate from (soonest sell-by first)", lots, format_func=ui.lot_label)
                qty = st.number_input("Quantity to allocate (in the lot's unit)", value=0.0, step=5.0, format="%.3f")
                if st.form_submit_button("Allocate"):
                    ok, aid = ui.run(farmer.allocate, user, req["request_id"], lot["lot_id"], qty)
                    if ok:
                        ui.reset_form("allocate")
                        st.session_state["_flash"] = f"Allocation #{aid} created. The quantity is now reserved and unavailable to other requests."
                        st.rerun()

    st.subheader("Active allocations from my farms")
    active = queries.list_allocations(user, status="ACTIVE")
    ui.table(active, ["allocation_id", "request_id", "market_name", "lot_id", "crop_name", "farm_name", "quantity", "unit", "allocated_at"],
             empty="No active allocations.")
    if active:
        with st.form(ui.form_key("release")):
            a = st.selectbox("Allocation to release", active,
                             format_func=lambda a: f"#{a['allocation_id']} · request #{a['request_id']} · {a['crop_name']} · {ui._fmt(a['quantity'])} {a['unit']}")
            why = st.text_input("Reason (required)")
            if st.form_submit_button("Release reservation"):
                ok, _ = ui.run(farmer.release_allocation, user, a["allocation_id"], why)
                if ok:
                    ui.reset_form("release")
                    st.session_state["_flash"] = "Reservation released back to available stock."
                    st.rerun()
    with st.expander("All allocations of my farms"):
        ui.table(queries.list_allocations(user))
