"""Administrator pages: analytics dashboard, reference data, users & access, stock corrections, audit log."""
import pandas as pd
import streamlit as st

from .. import admin, analytics, config, queries, reports
from ..core import today
from ..errors import friendly_message
from . import ui


# =============================================================================== analytics dashboard
def _chart(rows, x, cols):
    if not rows:
        st.info("No data for these filters.")
        return
    df = pd.DataFrame([{k: (float(v) if k in cols else v) for k, v in r.items()} for r in rows])
    st.bar_chart(df.groupby(x)[cols].sum(), color=["#25603f", "#d2763a"][:len(cols)])


def _exports(user, name, rows, filters_text):
    c1, c2, _ = st.columns([1, 1, 4])

    def log(fmt):
        try:
            admin.log_export(user, name, fmt, len(rows))
        except Exception:  # noqa: BLE001 - logging must never block the download
            pass
    c1.download_button("⬇ CSV", reports.to_csv(rows), f"{name}.csv", "text/csv", key=f"csv_{name}", disabled=not rows,
                       on_click=log, args=("CSV",))
    c2.download_button("⬇ PDF", reports.to_pdf(name.replace("_", " ").title(), filters_text, rows), f"{name}.pdf",
                       "application/pdf", key=f"pdf_{name}", disabled=not rows, on_click=log, args=("PDF",))


def dashboard(user):
    st.header("Analytics dashboard")
    st.caption("Three SQL analyses. Mass units are converted to kg through the units table; crates (count units) cannot be converted and are excluded.")
    c1, c2, c3, c4 = st.columns(4)
    crop = c1.selectbox("Crop", [None] + queries.crops(False), format_func=lambda c: "All crops" if c is None else c["crop_name"], key="an_crop")
    emirate = c2.selectbox("Emirate", [None] + config.EMIRATES, format_func=lambda e: "All emirates" if e is None else e, key="an_em")
    with c3:
        d_from = ui.optional_date("From date", "an_from")
    with c4:
        d_to = ui.optional_date("To date", "an_to")
    if d_from and d_to and d_from > d_to:
        st.error("'From' date must not be after 'To' date.", icon="⚠️")
        return
    f = analytics.Filters(crop["crop_name"] if crop else None, emirate, d_from, d_to)
    ftxt = f"crop={f.crop or 'all'}, emirate={f.emirate or 'all'}, dates={d_from or '-'}..{d_to or '-'}"
    try:
        sd, ful, loss, age = (analytics.supply_vs_demand(user, f), analytics.fulfilment(user, f),
                              analytics.loss_by_crop(user, f), analytics.ageing(user, f))
    except Exception as exc:  # noqa: BLE001
        st.error(friendly_message(exc), icon="⚠️")
        return
    ui.metric_row(analytics.summary(sd, ful, loss))
    t1, t2, t3 = st.tabs(["1. Supply vs demand", "2. Fulfilment & discrepancies", "3. Loss & ageing"])
    with t1:
        st.caption("Unreserved, unexpired stock (by harvest date) versus unmet demand of open requests (by needed-by date), kg.")
        _chart(sd, "crop_name", ["supply_kg", "demand_kg"])
        ui.table(sd)
        _exports(user, "supply_vs_demand", sd, ftxt)
    with t2:
        st.caption("Per request: requested, allocated, received and the delivery discrepancy (received − allocated), kg.")
        _chart(ful, "crop_name", ["requested_kg", "received_kg"])
        ui.table(ful)
        _exports(user, "request_fulfilment", ful, ftxt)
    with t3:
        st.caption("Loss rate per crop from LOSS movements, and ageing of unreserved stock by days to the sell-by date.")
        a, b = st.columns(2)
        with a:
            st.markdown("**Loss rate by crop (%)**")
            _chart(loss, "crop_name", ["loss_rate_pct"])
            ui.table(loss)
        with b:
            st.markdown("**Unreserved stock by ageing bucket (kg)**")
            _chart(age, "bucket", ["stock_kg"])
            ui.table(age)
        _exports(user, "loss_by_crop", loss, ftxt)
        _exports(user, "stock_ageing", age, ftxt)


# =============================================================================== reference data
def reference(user):
    ui.show_flash()
    st.header("Reference data")
    t_crops, t_units, t_markets, t_farms = st.tabs(["Crops", "Units", "Markets", "Farms"])

    with t_crops:
        rows = queries.crops(False)
        ui.table(rows, ["crop_id", "crop_name", "category", "is_active"])
        with st.form(ui.form_key("add_crop")):
            c1, c2 = st.columns(2)
            name, cat = c1.text_input("New crop name"), c2.selectbox("Category", config.CROP_CATEGORIES)
            if st.form_submit_button("Add crop"):
                ui.run(admin.add_crop, user, name, cat, success="Crop added.", rerun=True)
        _toggle(user, "crops", rows, "crop_id", "crop_name")

    with t_units:
        rows = queries.units(False)
        ui.table(rows, ["unit_code", "unit_name", "category", "to_base_factor", "is_active"])
        st.caption("Quantities in different units are only compared through these documented factors (mass → kg). Mass and count units are never converted into each other.")
        with st.form(ui.form_key("add_unit")):
            c1, c2, c3, c4 = st.columns(4)
            code, nm = c1.text_input("Code (e.g. lb)"), c2.text_input("Name")
            cat = c3.selectbox("Category", ["mass", "count"])
            fac = c4.number_input("Factor to base unit (kg for mass)", value=1.0, format="%.6f")
            if st.form_submit_button("Add unit"):
                ui.run(admin.add_unit, user, code, nm, cat, fac, success="Unit added.", rerun=True)

    with t_markets:
        rows = queries.markets(False)
        ui.table(rows, ["market_id", "market_name", "emirate", "address", "is_active"])
        with st.form(ui.form_key("add_market")):
            c1, c2, c3 = st.columns(3)
            nm, em, ad = c1.text_input("Market name"), c2.selectbox("Emirate", config.EMIRATES), c3.text_input("Address (optional)")
            if st.form_submit_button("Add market"):
                ui.run(admin.add_market, user, nm, em, ad, success="Market added.", rerun=True)
        _toggle(user, "markets", rows, "market_id", "market_name")

    with t_farms:
        rows = queries.farms(False)
        ui.table(rows, ["farm_id", "farm_name", "emirate", "location_desc", "area_hectares", "is_active"])
        st.caption("Farms are created by farmers; administrators can only activate or deactivate them.")
        _toggle(user, "farms", rows, "farm_id", "farm_name")


def _toggle(user, table, rows, id_key, name_key):
    if not rows:
        return
    r = st.selectbox(f"Activate / deactivate ({table})", rows, key=f"tg_{table}",
                     format_func=lambda x: f"{x[name_key]} — {'active' if x['is_active'] else 'inactive'}")
    label = "Deactivate" if r["is_active"] else "Activate"
    if st.button(label, key=f"tgb_{table}"):
        ui.run(admin.set_record_active, user, table, r[id_key], not r["is_active"], success=f"{label}d.", rerun=True)


# =============================================================================== users & access
def users(user):
    ui.show_flash()
    st.header("Users & access")
    rows = queries.list_users(user)
    ui.table(rows, ["user_id", "username", "full_name", "role", "market_name", "farms", "is_active", "failed_attempts", "locked_until"])
    t_new, t_farm, t_state = st.tabs(["Create user", "Assign farms", "Activate / reset password"])

    with t_new:
        farms = queries.farms(True)
        role = st.selectbox("Role", ["farmer", "buyer", "admin"], key="nu_role")
        with st.form(ui.form_key("new_user")):
            c1, c2 = st.columns(2)
            un, fn = c1.text_input("Username"), c2.text_input("Full name")
            pw = st.text_input("Initial password (8+ chars, upper, lower, digit)", type="password")
            market = st.selectbox("Market (buyers only)", queries.markets(), format_func=lambda m: m["market_name"]) if role == "buyer" else None
            fsel = st.multiselect("Farms (farmers only)", farms, format_func=lambda f: f["farm_name"]) if role == "farmer" else []
            if st.form_submit_button("Create user"):
                ui.run(admin.create_user, user, un, fn, role, pw, market["market_id"] if market else None,
                       [f["farm_id"] for f in fsel], success="User created.", rerun=True)

    with t_farm:
        farmers = [r for r in rows if r["role"] == "farmer"]
        if farmers:
            with st.form(ui.form_key("assign")):
                u = st.selectbox("Farmer", farmers, format_func=lambda r: f"{r['username']} ({r['farms'] or 'no farms'})")
                farm = st.selectbox("Farm", queries.farms(True), format_func=lambda f: f["farm_name"])
                c1, c2 = st.columns(2)
                if c1.form_submit_button("Assign farm"):
                    ui.run(admin.assign_farm, user, u["user_id"], farm["farm_id"], True, success="Farm assigned.", rerun=True)
                if c2.form_submit_button("Remove farm"):
                    ui.run(admin.assign_farm, user, u["user_id"], farm["farm_id"], False, success="Farm removed.", rerun=True)

    with t_state:
        u = st.selectbox("User", rows, key="us_sel", format_func=lambda r: f"{r['username']} ({r['role']}) — {'active' if r['is_active'] else 'inactive'}")
        label = "Deactivate" if u["is_active"] else "Activate"
        if st.button(label + " account", key="us_toggle"):
            ui.run(admin.set_record_active, user, "users", u["user_id"], not u["is_active"], success=f"Account {label.lower()}d.", rerun=True)
        with st.form(ui.form_key("reset_pw")):
            pw = st.text_input("New password", type="password")
            if st.form_submit_button("Reset password (also unlocks the account)"):
                ui.run(admin.reset_password, user, u["user_id"], pw, success="Password reset.", rerun=True)


# =============================================================================== stock corrections
def corrections(user):
    ui.show_flash()
    st.header("Stock corrections")
    st.caption("Administrators do not edit farm or market transactions. The only way to change stock is an approved correction, which is written as a dated movement with a reason and your user name.")
    lots = queries.list_lots(user, include_inactive=True)
    if lots:
        with st.form(ui.form_key("corr")):
            lot = st.selectbox("Harvest lot", lots, format_func=ui.lot_label)
            c1, c2 = st.columns(2)
            direction = c1.radio("Correction", ["add", "remove"], horizontal=True)
            qty = c2.number_input("Quantity (in the lot's unit)", value=0.0, step=1.0, format="%.3f")
            why = st.text_input("Reason / approval reference (required)")
            if st.form_submit_button("Apply correction"):
                ok, _ = ui.run(admin.apply_correction, user, lot["lot_id"], direction, qty, why)
                if ok:
                    ui.reset_form("corr")
                    st.session_state["_flash"] = "Correction recorded."
                    st.rerun()
    st.subheader("Recent corrections")
    rows = [m for m in queries.list_movements(user) if m["movement_type"].startswith("CORRECTION")]
    ui.table(rows, ["movement_id", "movement_date", "lot_id", "crop_name", "movement_type", "quantity", "unit", "username", "reason"],
             empty="No corrections recorded.")


# =============================================================================== audit log
def audit(user):
    st.header("Audit log")
    st.caption("Append-only: audit rows cannot be edited or deleted (enforced by database triggers). Includes sign-ins, denied access, stock and request changes and report exports.")
    c1, c2, c3 = st.columns(3)
    action = c1.selectbox("Action", [None] + queries.audit_actions(), format_func=lambda a: "All actions" if a is None else a, key="au_act")
    outcome = c2.selectbox("Outcome", [None, True, False], format_func=lambda v: "All" if v is None else ("Succeeded" if v else "Failed / denied"), key="au_ok")
    uname = c3.text_input("User name contains", key="au_user")
    d1, d2 = ui.optional_date("From", "au_from"), ui.optional_date("To", "au_to")
    ui.table(queries.list_audit(user, action, outcome, uname or None, d1, d2),
             ["audit_id", "created_at", "username", "action", "table_name", "record_id", "details", "success"])
