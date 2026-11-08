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
    "dashboard": '<rect x="3" y="3" width="6" height="8" rx="1"/><rect x="15" y="3" width="6" height="5" rx="1"/><rect x="3" y="15" width="6" height="6" rx="1"/><rect x="15" y="12" width="6" height="9" rx="1"/>',
    "location_on": '<path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0z"/><circle cx="12" cy="10" r="3"/>',
    "agriculture": '<path d="m3 21 18-18M7 17c-5 0-5-5-5-5 5 0 5 5 5 5zM11 13c-5 0-5-5-5-5 5 0 5 5 5 5zM15 9c-5 0-5-5-5-5 5 0 5 5 5 5zM7 17c0 5 5 5 5 5 0-5-5-5-5-5zM11 13c0 5 5 5 5 5 0-5-5-5-5-5zM15 9c0 5 5 5 5 5 0-5-5-5-5-5z"/>',
    "image": '<rect x="3" y="3" width="18" height="18" rx="2"/><circle cx="8" cy="8" r="1.5"/><path d="m21 15-5-5L5 21"/>',
    "alt_route": '<circle cx="6" cy="19" r="3"/><circle cx="18" cy="5" r="3"/><path d="M6 16V3M6 13c0-5 5-8 9-8"/>',
    "search": '<circle cx="10.5" cy="10.5" r="7.5"/><path d="m16 16 5 5"/>',
    "auto_awesome": '<path d="m12 3 2.5 6.5L21 12l-6.5 2.5L12 21l-2.5-6.5L3 12l6.5-2.5L12 3zM20 2v4M18 4h4M4 18v4M2 20h4"/>',
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
[data-testid="stSidebar"] {{ background: {CARD}; border-right: 1px solid #d9e0dc; border-radius: 18px 0 0 0; }}
[data-testid="stSidebar"] > div:first-child {{ padding-top: .5rem; }}
.brand {{ display: flex; align-items: center; gap: .9rem; margin: .4rem .6rem 2rem; }}
.brand .logo {{ width: 46px; height: 46px; border-radius: 12px; background: #00643d url({icon_uri('sprout', '#ffffff')}) center/28px no-repeat; flex: none; }}
.brand .name {{ font-family: 'Fraunces', serif; font-weight: 600; font-size: 1.5rem; color: #005a36; line-height: 1.15; }}
.wslabel {{ font-size: .8rem; letter-spacing: .11em; font-weight: 600; color: #5c6862; margin: 0 .9rem .7rem; text-transform: uppercase; }}
[data-testid="stSidebar"] [data-testid="stElementContainer"]:has(> [data-testid="stRadio"]),
[data-testid="stSidebar"] [data-testid="stRadio"] {{ width: 100%; }}
[data-testid="stSidebar"] [data-testid="stRadio"] [role="radiogroup"] {{ gap: .3rem; min-height: calc(100dvh - 12rem); justify-content: flex-start; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] {{ box-sizing: border-box; width: 100%; margin: 0; min-height: 54px; padding: .85rem 1rem; border-radius: 9px; cursor: pointer; transition: background .15s; align-items: center; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:hover {{ background: #eef5f1; }}
/* Keep native radio inputs accessible; hide only their decorative circles. */
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:first-child {{ display: none; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] > div:last-child {{ margin: 0; padding: 0; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"] p {{ display: flex; align-items: center; gap: .9rem; margin: 0; font-size: 1rem; line-height: 1.4; color: #606c65; font-weight: 500; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) {{ background: #ddf1e8; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:checked) p {{ color: #004c30; font-weight: 600; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label[data-baseweb="radio"]:has(input:focus-visible) {{ outline: 2px solid #00643d; outline-offset: 2px; }}
[data-testid="stSidebar"] [data-testid="stRadio"] span[role="img"] {{ width: 20px; height: 20px; flex: none; font-size: 20px; line-height: 1; }}
{''.join(f'''[data-testid="stSidebar"] [data-testid="stRadio"] span[aria-label="{name} icon"] {{ font-size: 0 !important; background: url({icon_uri(name, '#606c65')}) center/20px no-repeat; }}
[data-testid="stSidebar"] [data-testid="stRadio"] label:has(input:checked) span[aria-label="{name} icon"] {{ background-image: url({icon_uri(name, '#004c30')}); }}
''' for name in ('dashboard', 'location_on', 'agriculture', 'image', 'alt_route', 'search', 'auto_awesome'))}
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
