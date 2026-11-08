"""Local Farm and Market Food Availability System - Streamlit GUI.   Run:  streamlit run app.py"""
import time

import streamlit as st

from farmmarket import auth, config, db
from farmmarket.errors import UserError, friendly_message
from farmmarket.views import admin_views, buyer_views, farmer_views, shared_views, theme, ui

st.set_page_config(page_title="Farm & Market", page_icon="🌱", layout="wide")

ICON = {"Inventory overview": "dashboard", "Farms & crop cycles": "location_on", "Harvest & stock": "agriculture",
        "Lot images": "image", "Requests & allocation": "alt_route", "Search & status": "search", "Assistant": "auto_awesome",
        "Search local produce": "search", "My requests": "list_alt", "Confirm deliveries": "local_shipping",
        "Analytics dashboard": "bar_chart", "Reference data": "database", "Users & access": "group",
        "Stock corrections": "tune", "Operational records": "table_rows", "Audit log": "history"}
WORKSPACE = {"farmer": "Farmer workspace", "buyer": "Market workspace", "admin": "Admin workspace"}

NAV = {
    "farmer": [("Inventory overview", farmer_views.home), ("Farms & crop cycles", farmer_views.farms_cycles),
               ("Harvest & stock", farmer_views.harvest), ("Lot images", farmer_views.lot_images),
               ("Requests & allocation", farmer_views.allocation), ("Search & status", shared_views.records),
               ("Assistant", shared_views.assistant_page)],
    "buyer": [("Search local produce", buyer_views.search), ("My requests", buyer_views.requests),
              ("Confirm deliveries", buyer_views.deliveries), ("Search & status", shared_views.records),
              ("Assistant", shared_views.assistant_page)],
    "admin": [("Analytics dashboard", admin_views.dashboard), ("Reference data", admin_views.reference),
              ("Users & access", admin_views.users), ("Stock corrections", admin_views.corrections),
              ("Operational records", shared_views.records), ("Audit log", admin_views.audit),
              ("Assistant", shared_views.assistant_page)],
}


def login_screen(expired=False):
    theme.inject(login=True)
    left, right = st.columns([11, 9])
    with left:
        st.markdown(theme.hero_html(), unsafe_allow_html=True)
    with right:
        st.markdown('<div class="loginbrand"><i></i>FARM &amp; MARKET</div><div class="loginh">Welcome back.</div>'
                    '<div class="loginsub">Sign in to your farm or market.</div>', unsafe_allow_html=True)
        if expired:
            st.warning("You were signed out after 30 minutes of inactivity.")
        with st.form("login"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            if st.form_submit_button("Sign in  →", type="primary"):
                try:
                    user = auth.login(username, password)
                except Exception as exc:  # noqa: BLE001
                    st.error(friendly_message(exc), icon="🔒")
                else:
                    st.session_state.clear()
                    st.session_state.update(user=user, last_active=time.time())
                    st.rerun()
        st.divider()
        with st.expander("Demo accounts · fictional data"):
            st.markdown("Password for all: `Demo@1234`  \n**Admin:** `admin1`  \n**Farmers:** `farmer_ahmed`, `farmer_mariam`, `farmer_salem`  \n"
                        "**Market buyers:** `buyer_dubai`, `buyer_adcm`, `buyer_sharjah`, `buyer_alain`")


def sign_out(reason="user"):
    user = st.session_state.get("user")
    if user is not None:
        try:
            auth.logout(user, reason)
        except Exception:  # noqa: BLE001
            pass
    st.session_state.clear()
    if reason == "expired":
        st.session_state["_expired"] = True
    st.rerun()


def main():
    if not db.check_connection():
        st.error("🛑 The database is not reachable. Start MySQL and check the DB_* settings in the .env file, then reload this page.")
        if st.button("Try again"):
            db.reset_pool()
            st.rerun()
        return

    user = st.session_state.get("user")
    if user is None:
        login_screen(st.session_state.pop("_expired", False))
        return

    if time.time() - st.session_state.get("last_active", 0) > config.IDLE_TIMEOUT_MINUTES * 60:
        sign_out("expired")
    st.session_state["last_active"] = time.time()
    fresh = auth.load_user(user.user_id)           # picks up deactivation / role changes immediately
    if fresh is None:
        st.session_state.clear()
        st.error("Your account is no longer active.")
        return
    user = st.session_state["user"] = fresh

    theme.inject()
    pages = NAV[user.role]
    with st.sidebar:
        st.markdown(theme.brand_html(), unsafe_allow_html=True)
        st.markdown(f'<div class="wslabel">{WORKSPACE[user.role]}</div>', unsafe_allow_html=True)
        choice = st.radio("Menu", [p[0] for p in pages], key="nav", label_visibility="collapsed",
                          format_func=lambda n: f":material/{ICON.get(n, 'chevron_right')}:  {n}")
        sub = user.market_name if user.market_name else user.role
        st.markdown(f'<div class="userbox"><div class="n">{user.full_name}</div><div class="u">{user.username} · {sub}</div></div>',
                    unsafe_allow_html=True)
        if st.button("Log out", icon=":material/logout:", key="logout_btn"):
            sign_out()
        with st.expander("Change my password"):
            shared_views.change_password(user)

    render = dict(pages)[choice]
    try:
        render(user)
    except UserError as exc:
        st.error(str(exc), icon="⚠️")
    except Exception as exc:  # noqa: BLE001 - never show a traceback to the user
        st.error(friendly_message(exc), icon="⚠️")


main()
