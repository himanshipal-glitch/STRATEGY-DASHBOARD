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
    "ink": "#1A1614",            # primary text, warm near-black
    "ink_600": "#3D352F",        # body
    "ink_400": "#6B5F56",        # secondary
    "ink_300": "#8C7F74",        # captions
    "ink_200": "#AEA298",        # dormant
    "hairline": "#DDD3C6",       # control borders, warm
    "hairline_soft": "#EBE3D8",  # inner rules
    "bg": "#FAF7F2",             # cream page
    "bg_alt": "#F2ECE3",         # recessed panels
    "bg_hover": "#F6F1E9",
    "surface": "#FFFFFF",        # cards sit brighter than the page
    "dark": "#1A1614",           # hero base, warm not pure black
    "dark_2": "#2A231E",         # hero gradient end
    "on_dark": "#F7F2EA",
    "on_dark_dim": "#B3A698",
    "accent": "#C2603D",         # terracotta
    "accent_hover": "#A44E2F",
    "accent_soft": "#F7EBE4",
    "gold": "#D4A24C",           # secondary warm accent
    "alert": "#B3261E",
}

# One spine colour per vertical. Warm-family hues only, so a page full of them still
# reads as one palette rather than a pie chart.
SPINE_COLOURS = [
    "#C2603D",  # terracotta
    "#D4A24C",  # gold
    "#7D8C5C",  # olive
    "#8C6A8E",  # mauve
    "#5F7F80",  # teal-grey
    "#9C6B4E",  # umber
    "#B5745E",  # clay
    "#A08A5B",  # brass
    "#6E7BA0",  # slate blue
    "#A85F6A",  # rosewood
]


def spine_map(verticals) -> dict[str, str]:
    """Assign a colour to each vertical BY SORTED POSITION, not by hashing the name.

    Hashing looked tidy but collided badly - Finance, Operations and OPM all landed on
    the same hue. Position-based assignment guarantees distinct colours until the palette
    runs out, and sorting keeps them stable as projects are added or removed.
    """
    return {
        v: SPINE_COLOURS[i % len(SPINE_COLOURS)]
        for i, v in enumerate(sorted({str(x) for x in verticals}))
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

RADIUS = {"hero": "24px", "card": "20px", "chip": "980px", "panel": "14px"}

# System stack only — deliberately no @import (Google Fonts is blocked on this network).
FONT_STACK = (
    "-apple-system, BlinkMacSystemFont, 'SF Pro Display', 'SF Pro Text', "
    "'Segoe UI Variable Display', 'Segoe UI Variable', 'Segoe UI', "
    "Roboto, Helvetica, Arial, sans-serif"
)
# Display face for headings — the editorial note. All of these ship with Windows or
# macOS, so it degrades to a real serif everywhere rather than falling back to sans.
SERIF_STACK = (
    "'Iowan Old Style', 'Palatino Linotype', Palatino, 'Book Antiqua', "
    "Georgia, 'Times New Roman', serif"
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
  color: {b['gold']}; margin-bottom: 22px;
}}
.hero h1 {{
  font-family: {SERIF_STACK};
  font-size: clamp(2.4rem, 5.1vw, 3.9rem); font-weight: 400; color: {b['on_dark']};
  letter-spacing: -.018em; line-height: 1.06; margin: 0 0 20px;
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
  font-family: {SERIF_STACK};
  font-size: 2.3rem; font-weight: 400; color: {b['on_dark']}; letter-spacing: -.01em;
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
  font-family: {SERIF_STACK};
  font-size: 1.6rem; font-weight: 400; color: {b['ink']}; letter-spacing: -.01em;
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

/* ==== the card grid ================================================== */
.idx-rule {{ border-top: 1px solid {b['hairline']}; margin: 0; }}

/* Each card is a keyed container with an invisible full-size button laid over it.
   The left spine is a coloured bar keyed to the vertical - set inline per card. */
div[class*="st-key-row_"] {{
  position: relative; height: 100%;
  background: {b['surface']};
  border: 1px solid {b['hairline_soft']};
  border-radius: {r['card']};
  padding: 22px 24px 20px 26px !important;
  box-shadow: 0 1px 2px rgba(60,45,32,.04), 0 6px 16px -10px rgba(60,45,32,.10);
  transition: box-shadow .2s ease, transform .2s ease, border-color .2s ease;
  overflow: hidden;
}}
div[class*="st-key-row_"]:hover {{
  border-color: {b['hairline']};
  box-shadow: 0 2px 4px rgba(60,45,32,.05), 0 16px 34px -14px rgba(60,45,32,.20);
  transform: translateY(-3px);
}}
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
/* card interior: vertical label on top, serif title, blurb, then a footer rule */
.idx {{
  position: relative; display: flex; flex-direction: column;
  height: 100%; min-height: 210px;
}}
/* The coloured spine. It lives on .idx rather than on the card container because the
   inline --spine custom property is set here, and custom properties inherit downwards
   only - a rule on the parent container could never see it. The negative offsets cancel
   the container's padding (22/24/20/26) so the bar still reaches the card's edges. */
.idx::before {{
  content: ""; position: absolute; left: -26px; top: -22px; bottom: -20px; width: 5px;
  background: var(--spine, {b['accent']}); border-radius: 0;
}}
.idx-vert {{
  font-size: .645rem; font-weight: 700; letter-spacing: .13em; text-transform: uppercase;
  color: var(--spine, {b['accent']}); margin-bottom: 12px;
}}
.idx-title {{
  font-family: {SERIF_STACK};
  font-size: 1.22rem; font-weight: 400; color: {b['ink']};
  letter-spacing: -.008em; line-height: 1.26; margin-bottom: 10px;
}}
.idx-desc {{
  font-size: .85rem; color: {b['ink_400']}; line-height: 1.55; margin-bottom: 18px;
  display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden;
}}
.idx-desc.is-empty {{ color: {b['ink_200']}; font-style: italic; }}
.idx-foot {{
  margin-top: auto; padding-top: 14px; border-top: 1px solid {b['hairline_soft']};
  display: flex; align-items: center; justify-content: space-between; gap: 10px;
}}
/* our own chevron - no icon font (Google Fonts is blocked on this network) */
.idx-chev {{
  width: 8px; height: 8px; flex: none;
  border-right: 1.7px solid {b['ink_200']}; border-top: 1.7px solid {b['ink_200']};
  transform: rotate(45deg); transition: transform .18s ease, border-color .18s ease;
}}
div[class*="st-key-row_"]:hover .idx-chev {{
  border-color: {b['accent']}; transform: rotate(45deg) translate(3px, -3px);
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
  font-family: {SERIF_STACK};
  font-size: clamp(1.9rem, 3.7vw, 2.7rem); font-weight: 400; color: {b['on_dark']};
  letter-spacing: -.012em; line-height: 1.12; margin: 0 0 30px;
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
.qa h3 span.authored-tag {{ font-family: {FONT_STACK}; }}
.qa-body {{
  font-family: {SERIF_STACK};
  font-size: 1.06rem; color: {b['ink_600']}; line-height: 1.68; white-space: pre-wrap;
  max-width: 66ch;
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
