"""GUI flow tests using Streamlit's headless AppTest (real MySQL, real pages)."""
import logging
import warnings

import pytest
from streamlit.testing.v1 import AppTest

from farmmarket import db

warnings.filterwarnings("ignore")
logging.disable(logging.CRITICAL)
APP = str(__import__("pathlib").Path(__file__).resolve().parent.parent / "app.py")


def login(name, pw="Demo@1234"):
    at = AppTest.from_file(APP, default_timeout=60).run()
    at.text_input[0].set_value(name); at.text_input[1].set_value(pw)
    at.button[0].click().run()
    return at


def go(at, page):
    at.sidebar.radio[0].set_value(page).run()
    return at


def test_bad_login_shows_friendly_message(fresh):
    at = login("buyer_dubai", "nope")
    assert "Invalid username or password" in at.error[0].value and not at.exception


def test_each_role_sees_only_its_menu(fresh):
    has = lambda at, name: any(name in o for o in at.sidebar.radio[0].options)
    assert not has(login("farmer_ahmed"), "Analytics dashboard")
    assert not has(login("buyer_dubai"), "Requests & allocation")
    assert has(login("admin1"), "Audit log")


def test_buyer_creates_request_through_the_form(fresh):
    at = go(login("buyer_dubai"), "My requests")
    at.number_input[0].set_value(25.0)
    [b for b in at.button if b.label == "Submit request"][0].click().run()
    assert not at.exception and not at.error
    assert db.query_one("SELECT COUNT(*) c FROM market_requests WHERE market_id=2 AND quantity=25")["c"] == 1


def test_invalid_quantity_shows_clear_message_and_saves_nothing(fresh):
    at = go(login("buyer_dubai"), "My requests")
    at.number_input[0].set_value(-5.0)
    [b for b in at.button if b.label == "Submit request"][0].click().run()
    assert "greater than zero" in at.error[0].value
    assert db.query_one("SELECT COUNT(*) c FROM market_requests")["c"] == 8


def test_farmer_opening_other_farms_lot_is_denied_and_audited(fresh):
    at = go(login("farmer_ahmed"), "Harvest & stock")
    at.number_input(key="open_lot_no").set_value(11)
    at.button(key="open_lot_btn").click().run()
    assert "do not have permission" in at.error[0].value
    assert db.query_one("SELECT COUNT(*) c FROM audit_log WHERE action='ACCESS_DENIED'")["c"] == 1


def test_farmer_allocation_page_blocks_over_allocation(fresh):
    at = go(login("farmer_ahmed"), "Requests & allocation")
    at.selectbox(key="al_req").select_index(0).run()
    at.number_input[0].set_value(100000.0)
    [b for b in at.button if b.label == "Allocate"][0].click().run()
    assert at.error and not at.exception


def test_admin_dashboard_filters_and_date_validation(fresh):
    at = go(login("admin1"), "Analytics dashboard")
    assert sum(m.value.count("class=\"mcard\"") for m in at.markdown) == 5
    at.selectbox(key="an_crop").select_index(1).run()
    assert not at.exception
    import datetime as dt
    at.date_input(key="an_from").set_value(dt.date(2030, 1, 1)); at.date_input(key="an_to").set_value(dt.date(2020, 1, 1)); at.run()
    assert "must not be after" in at.error[0].value


def test_assistant_page_refuses_unsafe_question(fresh):
    at = go(login("buyer_dubai"), "Assistant")
    at.chat_input[0].set_value("delete all requests").run()
    assert any("read-only" in m.value for m in at.markdown)
