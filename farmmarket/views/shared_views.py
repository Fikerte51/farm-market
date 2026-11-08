"""Pages used by every role: search & status filters, the LangChain assistant, change password."""
import streamlit as st

from .. import assistant, auth, config, queries
from . import ui


def records(user):
    st.header("Operational records" if user.role == "admin" else "Search & status")
    st.caption("Read-only views limited to the records you are allowed to see. Use the filters, then open a tab.")
    is_buyer = user.role == "buyer"
    r1 = st.columns(4)
    crop = r1[0].selectbox("Crop", [None] + queries.crops(False), format_func=lambda c: "All crops" if c is None else c["crop_name"], key="rc_crop")
    emirate = r1[1].selectbox("Emirate", [None] + config.EMIRATES, format_func=lambda e: "All emirates" if e is None else e, key="rc_em")
    farm = None if is_buyer else r1[2].selectbox("Farm", [None] + (queries.my_farms(user) if user.role == "farmer" else queries.farms(False)),
                                                  format_func=lambda f: "All farms" if f is None else f["farm_name"], key="rc_farm")
    market = None if is_buyer else r1[3].selectbox("Market", [None] + queries.markets(False),
                                                    format_func=lambda m: "All markets" if m is None else m["market_name"], key="rc_mk")
    r2 = st.columns(4)
    status = r2[0].selectbox("Request status", [None] + config.REQUEST_STATUSES, format_func=lambda s: "All statuses" if s is None else s, key="rc_st")
    avail = r2[1].checkbox("Only lots with available stock", key="rc_av")
    with r2[2]:
        d_from = ui.optional_date("From date", "rc_from")
    with r2[3]:
        d_to = ui.optional_date("To date", "rc_to")
    cid = crop["crop_id"] if crop else None
    fid = farm["farm_id"] if farm else None
    mid = market["market_id"] if market else None

    names = ["Harvest lots", "Requests", "Allocations", "Receipts", "Crop cycles"] + ([] if is_buyer else ["Stock movements"])
    tabs = st.tabs(names)
    with tabs[0]:
        if is_buyer:
            rows = queries.search_produce(cid, emirate)
            ui.table(rows, ["lot_id", "crop_name", "farm_name", "emirate", "harvest_date", "sell_by_date", "available", "unit"])
        else:
            ui.table(queries.list_lots(user, cid, fid, emirate, avail, d_from, d_to, include_inactive=True))
    with tabs[1]:
        ui.table(queries.list_requests(user, market_id=mid, crop_id=cid, emirate=emirate, status=status, created_from=d_from, created_to=d_to),
                 ["request_id", "market_name", "market_emirate", "crop_name", "requested", "unit", "needed_by_date", "status",
                  "allocated_open", "received", "remaining_need"])
    with tabs[2]:
        ui.table(queries.list_allocations(user, farm_id=fid, crop_id=cid, market_id=mid))
    with tabs[3]:
        ui.table(queries.list_receipts(user, market_id=mid, farm_id=fid, crop_id=cid, date_from=d_from, date_to=d_to))
    with tabs[4]:
        ui.table(queries.list_cycles(user, crop_id=cid, farm_id=fid, emirate=emirate, expected_from=d_from, expected_to=d_to))
    if not is_buyer:
        with tabs[5]:
            ui.table(queries.list_movements(user, farm_id=fid, crop_id=cid, date_from=d_from, date_to=d_to))


EXAMPLES = ["Which tomato lots are available right now?", "What is the status of request 6?",
            "Which deliveries had a discrepancy?", "What harvests are expected before next month?"]


def assistant_page(user):
    st.header("Data assistant")
    st.caption("Ask questions about produce, stock, forecasts, requests and deliveries in plain English. "
               "The assistant (LangChain + Google Gemini) is read-only: it only uses approved, role-scoped queries and cannot change any record.")
    hist = st.session_state.setdefault("chat", [])
    ex = st.columns(len(EXAMPLES))
    clicked = None
    for col, q in zip(ex, EXAMPLES):
        if col.button(q, key="ex_" + q[:12], width="stretch"):
            clicked = q
    for m in hist:
        with st.chat_message(m["role"]):
            st.markdown(m["text"])
            for rec in m.get("records", []):
                if rec["rows"]:
                    with st.expander(f"Supporting records — {rec['tool'].replace('_', ' ')} ({len(rec['rows'])})"):
                        ui.table(rec["rows"])
    question = st.chat_input("Ask a question…", max_chars=assistant.MAX_QUESTION_CHARS) or clicked
    if question:
        hist.append({"role": "user", "text": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Looking at the records…"):
                reply = assistant.ask(user, question)
            st.markdown(reply.answer)
            for rec in reply.records:
                if rec["rows"]:
                    with st.expander(f"Supporting records — {rec['tool'].replace('_', ' ')} ({len(rec['rows'])})"):
                        ui.table(rec["rows"])
        hist.append({"role": "assistant", "text": reply.answer, "records": reply.records})


def change_password(user):
    with st.form("chg_pw", clear_on_submit=True):
        old = st.text_input("Current password", type="password")
        new = st.text_input("New password", type="password")
        if st.form_submit_button("Change password"):
            ui.run(auth.change_password, user, old, new, success="Password changed.")
