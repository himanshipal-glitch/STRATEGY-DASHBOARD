"""
Single source of truth for every colour, radius and font in the dashboard.

Design intent — the Apple product-page register, executed properly:
  * one dramatic dark panel carrying the title and the headline numbers, with a fine
    glass edge and a radial sheen, so the page opens with weight instead of empty white;
  * a left-aligned toolbar, not a floating centred form;
  * a dense, beautifully typeset index of numbered rows rather than sparse cards —
    27 projects should read as a considered catalogue, not a pile of tiles;
  * colour is information only: one accent, plus a 6px status dot. Nothing decorative.

Two hard constraints learned from the running app:
  * NO WEB FONTS AND NO ICON FONTS. Google Fonts is blocked on the team's network, which
    made Streamlit's own Material Symbols ligatures render as the literal text
    "keyboard_arrow_right" inside expanders. We use the system font stack and draw our
    own glyphs, and app.py avoids st.expander entirely.
  * Streamlit injects its emotion styles AFTER this sheet, so any property it also sets
    on its own containers needs !important to win.

REDLINE HERE — nothing else in the codebase hardcodes a colour.
"""

# ---------------------------------------------------------------------------
# Palette — greyscale with a single restrained accent.
# Greys and hairlines follow Apple's own values. The accent is a muted green so there
# is still a thread back to Recykal without the page reading as colourful. Swap it for
# "#0071E3" for pure Apple blue, or BRAND["ink"] to go fully monochrome.
# ---------------------------------------------------------------------------
BRAND = {
    "ink": "#1D1D1F",            # primary text, near-black
    "ink_600": "#424245",        # body
    "ink_400": "#6E6E73",        # secondary
    "ink_300": "#86868B",        # captions
    "ink_200": "#A1A1A6",        # dormant
    "hairline": "#D2D2D7",       # control borders
    "hairline_soft": "#E8E8ED",  # row rules
    "bg": "#FFFFFF",
    "bg_alt": "#F5F5F7",         # recessed panels
    "bg_hover": "#FAFAFA",       # row hover
    "surface": "#FFFFFF",
    "dark": "#000000",           # hero base
    "dark_2": "#1A1A1C",         # hero gradient end
    "on_dark": "#F5F5F7",        # text on the dark panel
    "on_dark_dim": "#98989D",
    "accent": "#1D6F42",
    "accent_hover": "#175935",
    "accent_soft": "#EFF4F0",
    "alert": "#B3261E",          # blocked status dot only
}

# Status is a 6px dot beside plain text — no coloured pills. The dot encodes urgency:
# accent = done, ink = active now, greys = dormant, muted red = blocked.
# Status colours are matched by KEYWORD, not by an exact list, so the team can invent any
# status they like on the Lists tab and it still gets a sensible dot. First match wins, so
# the order here matters ("not started" must be tested before "start").
# Each entry is (keywords, light dot, dark-panel dot).
_STATUS_RULES: list[tuple[tuple[str, ...], str, str]] = [
    (("complete", "done", "closed", "shipped", "delivered", "live"),
     BRAND["accent"], "#4CAF7D"),
    (("block", "stuck", "blocker"), BRAND["alert"], "#FF6B60"),
    (("not started", "not begun", "yet to", "backlog", "planned", "queued", "to do",
      "todo", "upcoming"), "#C7C7CC", "#48484A"),
    (("hold", "pause", "parked", "shelved", "dropped", "cancel", "abandon"),
     BRAND["ink_200"], "#636366"),
    (("continuous", "recurring", "ongoing", "bau", "maintenance"),
     BRAND["ink_400"], "#98989D"),
    (("progress", "active", "wip", "doing", "started", "review", "testing"),
     BRAND["ink"], "#FFFFFF"),
]
_STATUS_FALLBACK = (BRAND["ink_300"], "#8E8E93")

RADIUS = {"hero": "28px", "card": "18px", "chip": "980px", "panel": "12px"}

# System stack only — deliberately no @import. Segoe UI Variable is what Windows 11
# resolves to here and it is a good match for SF Pro's metrics.
FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', "
    "'Segoe UI Variable Display', 'Segoe UI Variable', 'Segoe UI', "
    "Roboto, Helvetica, Arial, sans-serif"
)
MONO_STACK = "'SF Mono', 'Cascadia Mono', 'Segoe UI Mono', ui-monospace, monospace"


def status_dot(status: str, on_dark: bool = False) -> str:
    """A dot colour for ANY status string the team invents.

    Nothing is hardcoded to a fixed list: statuses are matched on keywords, and anything
    unrecognised gets a neutral grey rather than breaking or being dropped.
    """
    s = str(status or "").strip().lower()
    for keywords, light, dark in _STATUS_RULES:
        if any(k in s for k in keywords):
            return dark if on_dark else light
    return _STATUS_FALLBACK[1] if on_dark else _STATUS_FALLBACK[0]


def css() -> str:
    b, r = BRAND, RADIUS
    return f"""
<style>
/* ---- shell ---------------------------------------------------------- */
html, body, [class*="st-"], .stApp {{
  font-family: {FONT_STACK};
  -webkit-font-smoothing: antialiased; -moz-osx-font-smoothing: grayscale;
}}
.stApp {{ background: {b['bg']}; }}
.block-container {{
  padding-top: 1.5rem !important; padding-bottom: 6rem !important; max-width: 1120px;
}}
#MainMenu, footer, header[data-testid="stHeader"] {{ visibility: hidden; height: 0; }}
section[data-testid="stSidebar"], div[data-testid="stSidebarCollapsedControl"] {{
  display: none !important;
}}
a {{ color: {b['accent']}; text-decoration: none; }}
a:hover {{ text-decoration: underline; }}
.tnum {{ font-variant-numeric: tabular-nums; }}

/* ==== the dark hero panel ============================================ */
.hero {{
  position: relative; overflow: hidden;
  border-radius: {r['hero']};
  background:
    radial-gradient(1100px 420px at 78% -12%, rgba(120,190,150,.16), transparent 62%),
    radial-gradient(700px 300px at 12% 108%, rgba(255,255,255,.055), transparent 70%),
    linear-gradient(176deg, {b['dark']} 0%, {b['dark_2']} 100%);
  padding: 68px 60px 0;
  box-shadow: 0 30px 60px -30px rgba(0,0,0,.45);
}}
/* the fine bright edge along the top - the detail that makes it read as a material */
.hero::before {{
  content: ""; position: absolute; inset: 0; border-radius: {r['hero']};
  border: 1px solid rgba(255,255,255,.10);
  border-bottom-color: rgba(255,255,255,.03); pointer-events: none;
}}
.hero-eyebrow {{
  font-size: .69rem; font-weight: 600; letter-spacing: .18em; text-transform: uppercase;
  color: {b['on_dark_dim']}; margin-bottom: 22px;
}}
.hero h1 {{
  font-size: clamp(2.3rem, 4.9vw, 3.7rem); font-weight: 600; color: #fff;
  letter-spacing: -.038em; line-height: 1.03; margin: 0 0 20px;
  max-width: 21ch; text-wrap: balance;
}}
.hero-lede {{
  font-size: 1.07rem; color: {b['on_dark_dim']}; line-height: 1.52;
  max-width: 56ch; margin: 0 0 52px; font-weight: 400;
}}
/* headline numbers, inside the panel, on a hairline */
.hero-stats {{
  display: grid; grid-template-columns: repeat(5, 1fr);
  border-top: 1px solid rgba(255,255,255,.13);
}}
.hstat {{ padding: 26px 0 30px; position: relative; }}
.hstat + .hstat::before {{
  content: ""; position: absolute; left: 0; top: 26px; bottom: 30px;
  width: 1px; background: rgba(255,255,255,.09);
}}
.hstat .n {{
  font-size: 2.1rem; font-weight: 600; color: #fff; letter-spacing: -.035em;
  line-height: 1; font-variant-numeric: tabular-nums;
}}
.hstat .k {{
  font-size: .715rem; font-weight: 500; color: {b['on_dark_dim']};
  margin-top: 9px; letter-spacing: .04em;
}}
.hstat .k em {{ font-style: normal; color: #fff; }}

/* ==== toolbar ======================================================== */
.tool-head {{ display: flex; align-items: flex-end; gap: 14px; }}
.tool-title {{
  font-size: 1.42rem; font-weight: 600; color: {b['ink']}; letter-spacing: -.025em;
  line-height: 1;
}}
.tool-sub {{ font-size: .82rem; color: {b['ink_300']}; padding-bottom: 2px; }}

/* search: quiet until focused */
div[class*="st-key-find"] div[data-testid="stTextInput"] input {{
  border-radius: {r['chip']} !important; border: 1px solid {b['hairline']} !important;
  background: {b['bg_alt']} !important; font-size: .87rem !important;
  padding: .42rem 1rem !important; color: {b['ink']} !important;
  transition: background .18s ease, border-color .18s ease, box-shadow .18s ease;
}}
div[class*="st-key-find"] div[data-testid="stTextInput"] input:focus {{
  background: {b['surface']} !important; border-color: {b['ink_200']} !important;
  box-shadow: 0 0 0 4px rgba(29,29,31,.05) !important;
}}
div[class*="st-key-find"] input::placeholder {{ color: {b['ink_300']} !important; }}

/* status segmented control - Apple's white-pill-on-grey-track */
div[class*="st-key-status"] div[data-baseweb="button-group"] {{
  background: {b['bg_alt']}; border-radius: {r['chip']}; padding: 3px; gap: 2px !important;
}}
div[class*="st-key-status"] button {{
  border-radius: {r['chip']} !important; border: 1px solid transparent !important;
  background: transparent !important; color: {b['ink_400']} !important;
  font-size: .79rem !important; font-weight: 500 !important;
  padding: .28rem 1rem !important; min-height: 0 !important; box-shadow: none !important;
  transition: none !important;
}}
div[class*="st-key-status"] button:hover {{ color: {b['ink']} !important; }}
div[class*="st-key-status"] button[kind="segmented_controlActive"],
div[class*="st-key-status"] button[data-testid="stBaseButton-segmented_controlActive"] {{
  background: {b['surface']} !important; color: {b['ink']} !important;
  font-weight: 600 !important;
  box-shadow: 0 1px 3px rgba(0,0,0,.11), 0 0 0 .5px rgba(0,0,0,.04) !important;
}}
div[class*="st-key-status"] button p {{ font-size: .79rem !important; }}

/* category links - typography, not a nav bar */
div[class*="st-key-cats"] div[data-baseweb="button-group"],
div[class*="st-key-cats"] > div > div {{ flex-wrap: wrap; gap: .1rem 1.4rem !important; }}
div[class*="st-key-cats"] button {{
  background: transparent !important; border: 0 !important; border-radius: 0 !important;
  box-shadow: none !important; min-height: 0 !important;
  color: {b['ink_300']} !important; font-size: .81rem !important; font-weight: 500 !important;
  padding: .26rem 0 !important; margin: 0 !important;
}}
div[class*="st-key-cats"] button:hover {{ color: {b['ink']} !important; }}
div[class*="st-key-cats"] button[kind="pillsActive"],
div[class*="st-key-cats"] button[data-testid="stBaseButton-pillsActive"] {{
  color: {b['ink']} !important; font-weight: 600 !important;
}}
div[class*="st-key-cats"] button p {{ font-size: .81rem !important; }}

/* compact refine selects (always visible - st.expander needs an icon font) */
div[class*="st-key-refine"] label {{
  font-size: .68rem !important; font-weight: 600 !important; letter-spacing: .07em;
  text-transform: uppercase; color: {b['ink_200']} !important;
}}
div[class*="st-key-refine"] div[data-baseweb="select"] > div {{
  border-radius: 10px !important; border-color: {b['hairline_soft']} !important;
  background: {b['bg_alt']} !important; font-size: .82rem !important; min-height: 34px;
}}

/* ==== the index ====================================================== */
.idx-rule {{ border-top: 1px solid {b['hairline']}; margin: 0; }}

/* each row is a keyed container with an invisible full-bleed button on top */
div[class*="st-key-row_"] {{
  position: relative; border-bottom: 1px solid {b['hairline_soft']};
  transition: background .16s ease;
}}
div[class*="st-key-row_"]:hover {{ background: {b['bg_hover']}; }}
/* The transparent hit target covering the whole row.
   It is the *element container* that must be positioned, not the inner .stButton:
   Streamlit's stElementContainer is itself position:relative, so absolutely positioning
   anything inside it resolves against that collapsed 0-height box instead of the row. */
div[class*="st-key-go_"] {{
  position: absolute !important;
  top: 0 !important; left: 0 !important; right: 0 !important; bottom: 0 !important;
  width: auto !important; height: auto !important; margin: 0 !important; z-index: 3;
}}
div[class*="st-key-go_"] .stButton,
div[class*="st-key-go_"] div[data-testid="stButton"] {{
  width: 100% !important; height: 100% !important; margin: 0 !important;
}}
div[class*="st-key-go_"] button {{
  width: 100% !important; height: 100% !important; opacity: 0 !important;
  border: 0 !important; background: transparent !important; cursor: pointer !important;
  padding: 0 !important; min-height: 0 !important; box-shadow: none !important;
}}
.idx {{
  display: grid; grid-template-columns: 46px 1fr 156px 22px;
  align-items: center; gap: 20px; padding: 19px 8px 19px 4px;
}}
.idx-num {{
  font-family: {MONO_STACK}; font-size: .76rem; color: {b['ink_200']};
  font-variant-numeric: tabular-nums; letter-spacing: .02em;
}}
.idx-title {{
  font-size: 1.04rem; font-weight: 600; color: {b['ink']};
  letter-spacing: -.018em; line-height: 1.32; margin-bottom: 6px;
}}
.idx-desc {{
  font-size: .845rem; color: {b['ink_400']}; line-height: 1.45; margin-bottom: 9px;
  display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden;
}}
.idx-desc.is-empty {{ color: {b['ink_200']}; }}
.idx-meta {{
  display: flex; align-items: center; flex-wrap: wrap; gap: 6px 14px;
  font-size: .785rem; color: {b['ink_300']};
}}
.idx-meta .sep {{ color: {b['hairline']}; }}
.idx-right {{ text-align: right; }}
.idx-pri {{
  font-size: .655rem; font-weight: 600; letter-spacing: .08em; text-transform: uppercase;
  color: {b['ink_200']}; margin-top: 7px;
}}
/* our own chevron - no icon font */
.idx-chev {{
  width: 8px; height: 8px; border-right: 1.6px solid {b['ink_200']};
  border-top: 1.6px solid {b['ink_200']}; transform: rotate(45deg);
  transition: transform .18s ease, border-color .18s ease; justify-self: end;
}}
div[class*="st-key-row_"]:hover .idx-chev {{
  border-color: {b['ink']}; transform: rotate(45deg) translate(2px, -2px);
}}

/* "built with" - what the thing actually is, read from the linked file's host */
.builtwith {{
  display: inline-block; font-size: .705rem; font-weight: 500; color: {b['ink_400']};
  background: {b['bg_alt']}; border: 1px solid {b['hairline_soft']};
  border-radius: {r['chip']}; padding: 3px 10px; line-height: 1.35;
}}

/* delivery detail: a quiet grid at the foot of a build page, never the headline */
.meta-grid {{ display: flex; flex-wrap: wrap; gap: 16px 40px; }}
.meta-item .meta-label {{
  font-size: .62rem; font-weight: 600; letter-spacing: .09em; text-transform: uppercase;
  color: {b['ink_200']}; margin-bottom: 6px;
}}
.meta-item .meta-value {{ font-size: .85rem; color: {b['ink_400']}; font-weight: 500; }}

/* progress: a hairline that fills */
.pbar {{
  height: 2px; background: {b['hairline_soft']}; border-radius: 2px;
  width: 74px; display: inline-block; vertical-align: middle;
}}
.pbar-fill {{ height: 100%; background: {b['ink_300']}; border-radius: 2px; display: block; }}

/* ---- shared small components ---------------------------------------- */
.status {{
  display: inline-flex; align-items: center; gap: 7px; white-space: nowrap;
  font-size: .785rem; font-weight: 500; color: {b['ink_600']};
}}
.status .dot {{ width: 6px; height: 6px; border-radius: 50%; flex: none; }}
.vert {{
  display: inline-block; font-size: .715rem; font-weight: 500; color: {b['ink_400']};
  background: {b['bg_alt']}; border-radius: {r['chip']}; padding: 3px 10px;
}}
.person {{
  display: inline-flex; align-items: center; gap: 6px;
  font-size: .785rem; color: {b['ink_600']}; font-weight: 500;
}}
.person-avatar {{
  width: 21px; height: 21px; border-radius: 50%; flex: none;
  background: {b['bg_alt']}; color: {b['ink_400']}; border: .5px solid {b['hairline']};
  display: inline-flex; align-items: center; justify-content: center;
  font-size: .58rem; font-weight: 600;
}}

/* ---- buttons (real ones) -------------------------------------------- */
.stButton > button {{
  border-radius: {r['chip']} !important; font-size: .81rem !important;
  font-weight: 500 !important; border: 1px solid {b['hairline']} !important;
  background: {b['surface']} !important; color: {b['ink']} !important;
  padding: .32rem 1.05rem !important; min-height: 0 !important; box-shadow: none !important;
  transition: background .16s ease, border-color .16s ease;
}}
.stButton > button:hover {{
  background: {b['bg_alt']} !important; border-color: {b['ink_200']} !important;
}}
div[class*="st-key-back"] .stButton > button {{
  border-color: transparent !important; color: {b['ink_400']} !important;
  padding-left: 0 !important;
}}
div[class*="st-key-back"] .stButton > button:hover {{
  background: transparent !important; color: {b['ink']} !important;
}}

/* ==== detail page ==================================================== */
.dhero {{
  position: relative; overflow: hidden; border-radius: {r['hero']};
  background:
    radial-gradient(900px 340px at 84% -18%, rgba(120,190,150,.14), transparent 62%),
    linear-gradient(176deg, {b['dark']} 0%, {b['dark_2']} 100%);
  padding: 44px 52px 40px; margin-bottom: 4px;
  box-shadow: 0 26px 52px -30px rgba(0,0,0,.42);
}}
.dhero::before {{
  content: ""; position: absolute; inset: 0; border-radius: {r['hero']};
  border: 1px solid rgba(255,255,255,.10);
  border-bottom-color: rgba(255,255,255,.03); pointer-events: none;
}}
.dhero .kicker {{
  font-size: .68rem; font-weight: 600; letter-spacing: .16em; text-transform: uppercase;
  color: {b['on_dark_dim']}; margin-bottom: 16px;
}}
.dhero h1 {{
  font-size: clamp(1.75rem, 3.5vw, 2.55rem); font-weight: 600; color: #fff;
  letter-spacing: -.032em; line-height: 1.08; margin: 0 0 30px;
  max-width: 26ch; text-wrap: balance;
}}
.dmeta {{
  display: grid; grid-template-columns: repeat(auto-fit, minmax(132px, 1fr));
  gap: 22px 30px; border-top: 1px solid rgba(255,255,255,.13); padding-top: 24px;
}}
.dmeta-label {{
  font-size: .625rem; font-weight: 600; letter-spacing: .10em; text-transform: uppercase;
  color: #6E6E73; margin-bottom: 8px;
}}
.dmeta-value {{ font-size: .875rem; color: {b['on_dark']}; font-weight: 500; }}
.dmeta .status {{ color: {b['on_dark']}; }}
.dmeta .vert {{ background: rgba(255,255,255,.09); color: {b['on_dark']}; }}
.dmeta .person {{ color: {b['on_dark']}; }}
/* "edit in the sheet" - the dashboard is read-only, so this is the real affordance */
.edit-link {{
  display: inline-block; margin-top: 26px;
  font-size: .82rem; font-weight: 500; color: {b['on_dark']} !important;
  background: rgba(255,255,255,.10); border: 1px solid rgba(255,255,255,.16);
  border-radius: {r['chip']}; padding: .4rem 1rem; text-decoration: none !important;
  transition: background .16s ease, border-color .16s ease;
}}
.edit-link:hover {{
  background: rgba(255,255,255,.17); border-color: rgba(255,255,255,.3);
}}
.dmeta .person-avatar {{
  background: rgba(255,255,255,.11); color: {b['on_dark']}; border-color: rgba(255,255,255,.16);
}}

.qa {{ padding: 38px 0; border-bottom: 1px solid {b['hairline_soft']}; }}
.qa h3 {{
  font-size: .685rem; font-weight: 600; letter-spacing: .14em; text-transform: uppercase;
  color: {b['ink_300']}; margin: 0 0 20px;
}}
.qa-body {{
  font-size: 1.005rem; color: {b['ink_600']}; line-height: 1.63; white-space: pre-wrap;
  max-width: 68ch;
}}
.qa-source {{
  font-size: .655rem; color: {b['ink_200']}; margin: 22px 0 8px;
  font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
}}
.qa-source:first-of-type {{ margin-top: 0; }}
.qa-empty {{
  font-size: .92rem; color: {b['ink_300']}; line-height: 1.6; max-width: 66ch;
  border-left: 2px solid {b['hairline']}; padding: 3px 0 3px 16px;
}}
.authored-tag {{
  display: inline-block; font-size: .575rem; font-weight: 600; letter-spacing: .09em;
  text-transform: uppercase; color: {b['accent']}; background: {b['accent_soft']};
  border-radius: {r['chip']}; padding: 3px 8px; margin-left: 9px; vertical-align: middle;
}}
.steps {{ margin: 0; padding: 0; list-style: none; max-width: 68ch; }}
.steps li {{
  display: flex; gap: 12px; align-items: flex-start; padding: 11px 0;
  border-bottom: 1px solid {b['hairline_soft']}; font-size: .925rem;
  color: {b['ink_600']}; line-height: 1.5;
}}
.steps li:last-child {{ border-bottom: none; }}
.step-box {{
  flex: none; width: 17px; height: 17px; border-radius: 50%; margin-top: 2px;
  display: inline-flex; align-items: center; justify-content: center;
  font-size: .59rem; font-weight: 700;
}}
.step-done {{ background: {b['accent']}; color: #fff; }}
.step-open {{ background: transparent; border: 1.5px solid {b['hairline']}; }}
.steps li.is-open {{ color: {b['ink_300']}; }}
.linkrow {{
  display: flex; align-items: center; gap: 12px; padding: 12px 0;
  border-bottom: 1px solid {b['hairline_soft']};
}}
.linkrow-kind {{
  font-size: .615rem; font-weight: 600; letter-spacing: .06em; text-transform: uppercase;
  color: {b['ink_400']}; background: {b['bg_alt']}; border-radius: {r['chip']};
  padding: 4px 10px; flex: none;
}}
.linkrow a {{ font-size: .845rem; word-break: break-all; }}

/* ---- notes ---------------------------------------------------------- */
.gap-note {{
  border-left: 2px solid {b['hairline']}; padding: 4px 0 4px 16px;
  font-size: .85rem; color: {b['ink_400']}; line-height: 1.6; max-width: 78ch;
}}
.gap-note b {{ color: {b['ink_600']}; font-weight: 600; }}
.gap-note code {{
  background: {b['bg_alt']}; padding: 1px 5px; border-radius: 4px;
  font-size: .81rem; color: {b['ink_600']};
}}
.foot-label {{
  font-size: .655rem; font-weight: 600; letter-spacing: .09em; text-transform: uppercase;
  color: {b['ink_200']}; margin-bottom: 8px;
}}
.empty-state {{
  text-align: center; padding: 62px 0; color: {b['ink_300']}; font-size: .95rem;
}}

div[class*="st-key-card_"] div[data-testid="stVerticalBlock"] {{ gap: .2rem; }}
</style>
"""
