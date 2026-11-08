"""Small helpers shared by all GUI pages."""
import datetime as dt
from decimal import Decimal

import pandas as pd
import streamlit as st

from .. import images, queries
from ..errors import friendly_message


# ----------------------------------------------------------------------------- feedback
def run(fn, *args, success: str | None = None, rerun: bool = False, **kwargs):
    """Call a service function; show a friendly message on failure. Returns (ok, result)."""
    try:
        result = fn(*args, **kwargs)
    except Exception as exc:  # noqa: BLE001 - every failure becomes a clear message, never a traceback
        st.error(friendly_message(exc), icon="⚠️")
        return False, None
    if success:
        if rerun:
            st.session_state["_flash"] = success
            st.rerun()
        st.success(success, icon="✅")
    elif rerun:
        st.rerun()
    return True, result


def show_flash() -> None:
    msg = st.session_state.pop("_flash", None)
    if msg:
        st.success(msg, icon="✅")


def form_key(name: str) -> str:
    """Changing the key resets every widget inside a form (used after a successful submit)."""
    return f"{name}_{st.session_state.get('_v_' + name, 0)}"


def reset_form(name: str) -> None:
    st.session_state["_v_" + name] = st.session_state.get("_v_" + name, 0) + 1


# ----------------------------------------------------------------------------- tables
def _plain(v):
    if isinstance(v, Decimal):
        return float(v)
    if isinstance(v, (dt.datetime, dt.date)):
        return v
    if isinstance(v, bool):
        return v
    return v


def table(rows: list[dict], cols: list[str] | None = None, empty: str = "No records match.", height: int | None = None):
    if not rows:
        st.info(empty)
        return
    df = pd.DataFrame([{k: _plain(v) for k, v in r.items()} for r in rows])
    if cols:
        df = df[[c for c in cols if c in df.columns]]
    df.columns = [c.replace("_", " ") for c in df.columns]
    kwargs = {"height": height} if height else {}
    st.dataframe(df, width="stretch", hide_index=True, **kwargs)


def metric_row(items: dict) -> None:
    from . import theme
    theme.metric_cards(list(items.items()))


# ----------------------------------------------------------------------------- pickers
def lot_label(l: dict) -> str:
    sell = f", sell-by {l['sell_by_date']}" if l.get("sell_by_date") else ""
    avail = f", {_fmt(l['available'])} {l['unit']} available" if "available" in l else ""
    return f"Lot #{l['lot_id']} · {l['crop_name']} · {l.get('farm_name', '')}{avail}{sell}"


def _fmt(q) -> str:
    s = f"{Decimal(str(q)):f}"
    return s.rstrip("0").rstrip(".") if "." in s else s


def pick(label: str, rows: list[dict], id_key: str, name_fn, key: str, allow_none: str | None = None, **kw):
    """Selectbox returning the chosen row (or None). `allow_none` adds a leading 'All/Choose' option."""
    options = ([None] if allow_none else []) + rows
    chosen = st.selectbox(label, options, key=key, format_func=lambda r: allow_none if r is None else name_fn(r), **kw)
    return chosen


def optional_date(label: str, key: str):
    return st.date_input(label, value=None, key=key, format="YYYY-MM-DD")


# ----------------------------------------------------------------------------- photos
def show_lot_images(lot_id: int, can_remove=None, key_prefix: str = "img") -> None:
    """Show all photos of a lot. A missing / unreadable file is reported politely, never crashes the page."""
    imgs = queries.lot_images(lot_id)
    if not imgs:
        st.caption("No photos for this lot yet.")
        return
    cols = st.columns(min(len(imgs), 3))
    for i, im in enumerate(imgs):
        with cols[i % len(cols)]:
            data = images.display_bytes(im["file_path"])
            if data is None:
                st.warning("Photo file is unavailable (it may have been moved or deleted).", icon="🖼️")
                st.caption(im.get("caption") or "")
            else:
                st.image(data, caption=im.get("caption") or f"Lot #{lot_id}", width="stretch")
            if can_remove:
                if st.button("Remove photo", key=f"{key_prefix}_rm_{im['image_id']}"):
                    can_remove(im["image_id"])
