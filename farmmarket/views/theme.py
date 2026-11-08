"""Visual theme: sand surfaces, date-palm green, terracotta accents; Fraunces headings + Work Sans body.
All styling lives here so pages stay free of presentation code."""
import base64
from functools import lru_cache
from urllib.parse import quote

import streamlit as st

from .. import config

GREEN, GREEN_DK, SAND, CARD, BORDER, MUTED, INK = "#25603f", "#1d4a31", "#f6f5f0", "#ffffff", "#e4e1d6", "#6b7a70", "#1d3b2a"

# lucide-style line icons (stroke only) -> used as CSS background images
ICONS = {
    "sprout": '<path d="M7 20h10"/><path d="M10 20c5.5-2.5.8-6.4 3-10"/><path d="M9.5 9.4c1.1.8 1.8 2.2 2.3 3.7-2 .4-3.5.4-4.8-.3-1.2-.6-2.3-1.9-3-4.2 2.8-.5 4.4 0 5.5.8z"/><path d="M14.1 6a7 7 0 0 0-1.1 4c1.9-.1 3.3-.6 4.3-1.4 1-1 1.6-2.3 1.7-4.6-2.7.1-4 1-4.9 2z"/>',
    "bars": '<path d="M3 3v16a2 2 0 0 0 2 2h16"/><path d="M18 17V9"/><path d="M13 17V5"/><path d="M8 17v-3"/>',
    "arrow": '<path d="M5 12h14"/><path d="m12 5 7 7-7 7"/>',
    "arrow_up_right": '<path d="M7 17 17 7"/><path d="M7 7h10v10"/>',
}


def icon_uri(name: str, color: str, width: float = 2) -> str:
    svg = (f'<svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="{color}" '
           f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{ICONS[name]}</svg>')
    return "data:image/svg+xml;base64," + base64.b64encode(svg.encode()).decode()


@lru_cache(maxsize=1)
def hero_uri() -> str:
    path = config.BASE_DIR / "assets" / "farm-hero.jpg"
    try:
        return "data:image/jpeg;base64," + base64.b64encode(path.read_bytes()).decode()
    except OSError:
        return ""          # no photo: the gradient below is used instead


BASE_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Fraunces:opsz,wght@9..144,500;9..144,600;9..144,700&family=Work+Sans:wght@400;500;600&display=swap');
html, body, [class*="css"], .stApp, [data-testid="stAppViewContainer"] {{ font-family: 'Work Sans', system-ui, sans-serif; }}
.stApp {{ background: {SAND}; color: {INK}; }}
#MainMenu, footer, [data-testid="stToolbar"], [data-testid="stDecoration"] {{ display: none !important; }}
[data-testid="stHeader"] {{ background: transparent; }}
.block-container {{ padding-top: 3.2rem; padding-bottom: 4rem; max-width: 1240px; }}

/* headings */
h1, h2, h3, [data-testid="stHeading"] h1, [data-testid="stHeading"] h2, [data-testid="stHeading"] h3 {{
  font-family: 'Fraunces', Georgia, serif !important; color: {INK}; letter-spacing: -0.01em; font-weight: 600; }}
[data-testid="stHeading"] h2 {{ font-size: 2.5rem; line-height: 1.15; padding-bottom: .2rem; }}
[data-testid="stHeading"] h3 {{ font-size: 1.55rem; margin-top: .6rem; }}
[data-testid="stCaptionContainer"], .stCaption {{ color: #55645a !important; opacity: 1 !important; font-size: .98rem; }}
[data-testid="stCaptionContainer"] p {{ color: #55645a !important; opacity: 1 !important; }}
.block-container > div > div > [data-testid="stCaptionContainer"]:first-of-type {{ margin-bottom: 1.2rem; padding-bottom: 1.2rem; border-bottom: 1px solid {BORDER}; }}

/* sidebar */
[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid {BORDER}; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: .5rem; }}
.brand {{ display: flex; align-items: center; gap: .8rem; margin: .4rem 0 1.8rem; }}
.brand .logo {{ width: 46px; height: 46px; border-radius: 12px; background: {GREEN} url({icon_uri('sprout', '#ffffff')}) center/26px no-repeat; flex: none; }}
.brand .name {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.35rem; color: {GREEN_DK}; line-height: 1.05; }}
.wslabel {{ font-size: .74rem; letter-spacing: .14em; font-weight: 600; color: {MUTED}; margin: 0 0 .5rem .3rem; text-transform: uppercase; }}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{ gap: .15rem; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] {{ width: 100%; padding: .62rem .8rem; border-radius: 10px; cursor: pointer; transition: background .15s; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"]:hover {{ background: #eef3ee; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] > div > div:first-child:not([data-testid]) {{ display: none; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"] p {{ font-size: 1rem; color: #3c4a41; font-weight: 500; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] {{ background: #e1efe6; }}
[data-testid="stSidebar"] [data-testid="stRadioOption"][data-selected="true"] p {{ color: {GREEN_DK}; font-weight: 600; }}
.note {{ background: #fbf4df; border: 1px solid #efe0ae; color: #5b4a12; border-radius: 12px; padding: .85rem 1.1rem; font-size: .95rem; }}
.userbox {{ border-top: 1px solid {BORDER}; margin-top: 1.6rem; padding-top: 1rem; }}
.userbox .n {{ font-weight: 600; font-size: 1.05rem; }}
.userbox .u {{ color: {MUTED}; font-size: .9rem; }}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"] {{ border: none; background: transparent; color: {GREEN}; font-weight: 600; justify-content: flex-start; padding-left: .4rem; }}
[data-testid="stSidebar"] [data-testid="stBaseButton-secondary"]:hover {{ background: #eef3ee; color: {GREEN_DK}; }}

/* metric cards */
.mgrid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(195px, 1fr)); gap: 1.1rem; margin: .4rem 0 1.6rem; }}
.mcard {{ background: {CARD}; border: 1px solid {BORDER}; border-top: 4px solid var(--c); border-radius: 14px; padding: 1.15rem 1.3rem 1.2rem;
  box-shadow: 0 1px 2px rgba(40,60,45,.05), 0 8px 24px -14px rgba(40,60,45,.25); }}
.mcard .top {{ display: flex; justify-content: space-between; align-items: flex-start; gap: .6rem; color: #55645a; font-size: .95rem; font-weight: 500; }}
.mcard .ico {{ width: 40px; height: 40px; border-radius: 10px; background-color: var(--t); background-position: center; background-repeat: no-repeat; background-size: 20px; flex: none; }}
.mcard .val {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 2.6rem; color: var(--c); margin-top: .9rem; line-height: 1.05; }}
.mcard .sub {{ color: {MUTED}; font-size: .85rem; margin-top: .25rem; }}

/* inputs, buttons, tabs, containers */
[data-baseweb="input"], [data-baseweb="select"] > div, [data-baseweb="textarea"], [data-testid="stNumberInputContainer"], [data-testid="stDateInputField"] {{
  border-radius: 10px !important; border-color: #d9d5c6 !important; background: #fff; }}
[data-testid="stTextInput"] label p, [data-testid="stSelectbox"] label p, [data-testid="stNumberInput"] label p, [data-testid="stDateInput"] label p {{ font-weight: 500; color: #34443a; }}
.stButton > button, [data-testid="stFormSubmitButton"] > button, [data-testid="stDownloadButton"] > button {{ border-radius: 10px; font-weight: 600; padding: .6rem 1.1rem; }}
[data-testid="stBaseButton-primary"], [data-testid="stBaseButton-primaryFormSubmit"] {{ background: {GREEN}; border-color: {GREEN}; color: #fff; box-shadow: 0 1px 2px rgba(0,0,0,.08); }}
[data-testid="stBaseButton-primary"]:hover, [data-testid="stBaseButton-primaryFormSubmit"]:hover {{ background: {GREEN_DK}; border-color: {GREEN_DK}; }}
[data-testid="stBaseButton-secondaryFormSubmit"] {{ background: {GREEN}; color: #fff; border-color: {GREEN}; }}
[data-testid="stBaseButton-secondaryFormSubmit"]:hover {{ background: {GREEN_DK}; border-color: {GREEN_DK}; color: #fff; }}
[data-testid="stForm"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; padding: 1.3rem 1.4rem; box-shadow: 0 1px 2px rgba(40,60,45,.04); }}
[data-testid="stExpander"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; overflow: hidden; }}
[data-testid="stExpander"] summary {{ font-weight: 500; }}
[data-testid="stDataFrame"] {{ border: 1px solid {BORDER}; border-radius: 12px; overflow: hidden; background: #fff; }}
[data-testid="stAlert"] {{ border-radius: 12px; border: 1px solid {BORDER}; }}
button[data-baseweb="tab"] {{ font-weight: 500; }}
button[data-baseweb="tab"][aria-selected="true"] {{ color: {GREEN_DK}; font-weight: 600; }}
[data-baseweb="tab-highlight"] {{ background-color: {GREEN} !important; }}
[data-testid="stChatMessage"] {{ background: {CARD}; border: 1px solid {BORDER}; border-radius: 14px; }}
hr {{ border-color: {BORDER}; }}
"""

LOGIN_CSS = f"""
[data-testid="stHeader"], [data-testid="stSidebar"], [data-testid="collapsedControl"] {{ display: none !important; }}
.block-container {{ padding: 0 !important; max-width: 100% !important; }}
.stApp {{ background: #fff; }}
[data-testid="stHorizontalBlock"] {{ gap: 0 !important; }}
[data-testid="stFormSubmitButton"] {{ width: 100%; }}
[data-testid="stFormSubmitButton"] > button {{ width: 100%; }}
.hero {{ position: fixed; top: 0; left: 0; width: 55vw; height: 100vh; z-index: 0; overflow: hidden;
  background: linear-gradient(135deg, #24593a, #4b7a3d 55%, #c0702f); }}
.hero .photo {{ position: absolute; inset: 0; background: url({hero_uri()}) center/cover no-repeat; }}
.hero .shade {{ position: absolute; inset: 0; background: linear-gradient(180deg, rgba(20,30,15,.38) 0%, rgba(20,30,15,.05) 35%, rgba(15,25,12,.72) 100%); }}
.hero .tag {{ position: absolute; top: 44px; left: 48px; right: 48px; display: flex; justify-content: space-between; align-items: center; color: #fff; font-weight: 500; font-size: 1.05rem; }}
.hero .tag .s {{ display: inline-block; width: 24px; height: 24px; vertical-align: -5px; margin-right: 12px; background: url({icon_uri('sprout', '#ffffff')}) center/24px no-repeat; }}
.hero .tag .a {{ width: 22px; height: 22px; background: url({icon_uri('arrow_up_right', '#ffffff')}) center/22px no-repeat; }}
.hero .copy {{ position: absolute; left: 48px; bottom: 56px; right: 48px; color: #fff; }}
.hero .copy .bar {{ width: 56px; height: 4px; background: #e0b34a; margin-bottom: 26px; border-radius: 2px; }}
.hero .copy h1 {{ font-family: 'Fraunces', serif !important; color: #fff !important; font-size: clamp(2.8rem, 5vw, 4.6rem); line-height: 1.02; margin: 0 0 18px; font-weight: 600; }}
.hero .copy p {{ font-size: 1.2rem; margin: 0; opacity: .95; }}
.loginbrand {{ display: flex; align-items: center; gap: .7rem; color: {GREEN}; font-weight: 600; letter-spacing: .16em; font-size: .92rem; margin: 0 0 3rem; }}
.loginbrand i {{ width: 28px; height: 28px; background: url({icon_uri('sprout', GREEN)}) center/28px no-repeat; }}
.loginh {{ font-family: 'Fraunces', serif; font-size: 3.3rem; font-weight: 600; line-height: 1.05; margin: 0 0 .5rem; color: {INK}; }}
.loginsub {{ color: {MUTED}; font-size: 1.1rem; margin-bottom: 1.6rem; }}
[data-testid="stColumn"]:nth-of-type(2) {{ padding: 14vh 5vw 4rem 4vw; background: #fff; min-height: 100vh; }}
[data-testid="stForm"] {{ border: none; padding: 0; background: transparent; box-shadow: none; }}
[data-testid="stBaseButton-secondaryFormSubmit"], [data-testid="stBaseButton-primaryFormSubmit"] {{ width: 100%; padding: .85rem 1rem; font-size: 1.05rem; justify-content: space-between; }}
@media (max-width: 900px) {{ .hero {{ display: none; }} [data-testid="stColumn"]:nth-of-type(2) {{ padding: 6vh 6vw; }} }}
"""


def inject(login: bool = False) -> None:
    css = BASE_CSS + (LOGIN_CSS if login else "")
    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


def hero_html() -> str:
    return ('<div class="hero"><div class="photo"></div><div class="shade"></div>'
            '<div class="tag"><span><i class="s"></i>UAE grown. Locally shared.</span><span class="a"></span></div>'
            '<div class="copy"><div class="bar"></div><h1>Farm &amp;<br>Market</h1><p>Fresh harvests. Connected markets.</p></div></div>')


def brand_html() -> str:
    return '<div class="brand"><div class="logo"></div><div class="name">Farm &amp;<br>Market</div></div>'


PALETTE = [("#25603f", "#e3f0e8"), ("#2b6ea8", "#e4eef8"), ("#b94a3c", "#fbe7e4"), ("#8a6d12", "#fbf0cf"), ("#6d4fa3", "#eee8f8")]


def metric_cards(items: list, ) -> None:
    """items: list of (label, value) or (label, value, subtitle). Coloured top border + tinted icon, as in the design."""
    cards = []
    for i, it in enumerate(items):
        label, value = it[0], it[1]
        sub = it[2] if len(it) > 2 else ""
        c, t = PALETTE[i % len(PALETTE)]
        if isinstance(value, (int, float)):
            value = f"{value:,.0f}" if float(value).is_integer() else f"{value:,.1f}"
        cards.append(f'<div class="mcard" style="--c:{c};--t:{t}"><div class="top"><span>{label}</span>'
                     f'<i class="ico" style="background-image:url({icon_uri("bars", c)})"></i></div>'
                     f'<div class="val">{value}</div>' + (f'<div class="sub">{sub}</div>' if sub else "") + '</div>')
    st.markdown('<div class="mgrid">' + "".join(cards) + "</div>", unsafe_allow_html=True)
