"""
Strategy Team - Project Registry
================================
A browsable catalogue of every project the strategy team has run: who owns it, and on
click, what it is about / how it was built / why it was built.

Run it:   streamlit run app.py --server.port 8503

Reads `My Tasks_Projects.xlsx` live - add a row in Excel, hit Refresh, it appears.

Layout: no sidebar, no top bar. A dark hero panel carries the title and the headline
numbers; below it a left-aligned toolbar and a dense numbered index of projects. Each
index row is a keyed container with a transparent full-size Streamlit button laid over
it, which is what makes the whole row clickable while the visuals stay ours.

Two constraints worth remembering:
  * No web fonts and no icon fonts - Google Fonts is blocked on the team's network,
    which made st.expander render its Material ligature as the literal text
    "keyboard_arrow_right". Hence no expanders anywhere and no @import in theme.py.
  * theme.py is an imported module, so Streamlit does NOT pick up edits to it on a
    rerun - restart `streamlit run` after changing the palette or CSS.
"""

from __future__ import annotations

import datetime as dt
import html
import time
from pathlib import Path

import pandas as pd
import streamlit as st

import theme
from data_loader import (
    DEFAULT_SOURCE,
    OVERRIDES_PATH,
    Project,
    is_google_sheet,
    load_with_fallback,
    status_sort_key,
)

st.set_page_config(
    page_title="Strategy Team - Project Registry",
    page_icon="\N{WHITE MEDIUM STAR}",
    layout="wide",
    initial_sidebar_state="collapsed",  # there is no sidebar; see theme.py
)
st.markdown(theme.css(), unsafe_allow_html=True)

# Nothing about statuses, verticals or columns is fixed in code. Statuses come from the
# sheet's Lists tab, verticals from the data, and any column the team adds shows up under
# "Also recorded" on the detail page. See data_loader.load_projects.

CARDS_PER_ROW = 3


# ---------------------------------------------------------------------------
# Render helpers
# ---------------------------------------------------------------------------
def esc(text: str) -> str:
    return html.escape(str(text or ""))


def plural(n: int, word: str) -> str:
    return f"{n} {word}" if n == 1 else f"{n} {word}s"


def initials(name: str) -> str:
    parts = [p for p in str(name).split() if p]
    if not parts:
        return "?"
    return (parts[0][:2] if len(parts) == 1 else parts[0][0] + parts[-1][0]).upper()


# No status_tag helper any more. Status is delivery-tracking detail: it stays in the sheet
# and appears only as plain text under "Delivery detail" on a build page. A catalogue for
# the whole organisation should not lead with how the team is performing.


def vertical_tag(vertical: str) -> str:
    return f'<span class="vert">{esc(vertical)}</span>'


def person_chip(name: str) -> str:
    return (
        f'<span class="person"><span class="person-avatar">{esc(initials(name))}</span>'
        f"{esc(name)}</span>"
    )


def people_row(names: list[str], empty: str = "Not recorded") -> str:
    if not names:
        return f'<span style="color:{theme.BRAND["ink_200"]};font-size:.79rem">{esc(empty)}</span>'
    return (
        '<span style="display:inline-flex;flex-wrap:wrap;gap:6px 14px">'
        + "".join(person_chip(n) for n in names)
        + "</span>"
    )


def fmt_date(ts) -> str:
    return "-" if ts is None or pd.isna(ts) else pd.Timestamp(ts).strftime("%d %b %Y")


def spacer(px: int) -> None:
    st.markdown(f"<div style='height:{px}px'></div>", unsafe_allow_html=True)


# ---------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------
# How often the page re-reads the sheet when "Keep in sync" is on. Google Sheets have no
# modification time to key a cache on, so this interval IS the staleness window.
SYNC_SECONDS = 30


@st.cache_data(show_spinner="Reading the sheet...", ttl=SYNC_SECONDS)
def get_projects(source: str, mtime: float, overrides_mtime: float):
    """`mtime` args are cache keys only - touching either file invalidates the cache.

    The `ttl` is what covers Google Sheets, which have no mtime: an edit shows up on the
    next rerun after the ttl lapses, or immediately via Refresh.
    """
    return load_with_fallback(source)


@st.fragment(run_every=SYNC_SECONDS)
def sync_ticker() -> None:
    """Re-runs the whole app on a timer so the page keeps up with the live sheet.

    Streamlit only re-reads data when the script re-runs, and a page nobody is clicking
    never re-runs. This fragment is the heartbeat that makes it self-updating.

    The elapsed-time guard is essential: a fragment executes IMMEDIATELY when it is
    called, not only on its timer, so an unguarded st.rerun() here fires on the first
    pass and every pass after it - an infinite rerun loop in which the page never
    finishes drawing. main() stamps `_last_sync` just before calling this, so the
    immediate pass is a no-op and only genuine timer ticks trigger a rerun.
    """
    if time.monotonic() - st.session_state.get("_last_sync", 0.0) >= SYNC_SECONDS - 2:
        st.session_state["_last_sync"] = time.monotonic()
        st.rerun(scope="app")


def file_mtime(path_or_url: str) -> float:
    if is_google_sheet(path_or_url):
        return 0.0  # no mtime for a URL; the cache ttl handles freshness
    try:
        return Path(path_or_url).stat().st_mtime
    except OSError:
        return 0.0


def data_source() -> str:
    """The workbook path or Google Sheets URL currently in use.

    The configured source (Streamlit secrets, or a local file) wins unless someone types
    an override in the footer. The override is deliberately a separate, empty-by-default
    field so the real URL is never rendered back to the page - this app is public.
    """
    override = str(st.session_state.get("source_override", "")).strip().strip('"')
    return override or DEFAULT_SOURCE


def source_exists(source: str) -> bool:
    return True if is_google_sheet(source) else Path(source).exists()


def source_stamp(source: str) -> str:
    now = dt.datetime.now().strftime("%H:%M")
    if is_google_sheet(source):
        live = st.session_state.get("sync_on", True)
        return (f"Live from Google Sheets · checked {now}" if live
                else f"From Google Sheets · read {now}")
    mt = file_mtime(source)
    return ("Source updated " + dt.datetime.fromtimestamp(mt).strftime("%d %b %Y")
            if mt else "Source date unknown")


# ---------------------------------------------------------------------------
# Hero
# ---------------------------------------------------------------------------
def render_hero(projects: list[Project], source: str, statuses: list[str]) -> None:
    """Headline facts about the LIBRARY, not about the team's performance.

    Deliberately no completion counts, no 'needs attention', no progress. This is a
    catalogue of what the strategy team has built for anyone in the organisation to look
    things up in - not a scorecard for the team that built them. Status and priority stay
    in the sheet but never drive this page.
    """
    verticals = len({p.vertical for p in projects})
    people = len({n for p in projects for n in (p.owners + p.collaborators)})
    tools = len({k for p in projects for k in p.artifact_kinds})
    described = sum(1 for p in projects if p.has_description)
    stamp = source_stamp(source)

    stats = [
        (len(projects), "Builds"),
        (verticals, "Verticals"),
        (people, "People"),
        (tools, "Built with"),
        (described, f"Written up <em>of {len(projects)}</em>"),
    ]
    # data-run carries the epoch second of this render. Invisible, but it makes "did the
    # page actually re-read the sheet?" answerable at a glance in devtools.
    st.markdown(
        f"""
<div class="hero" data-run="{int(time.time())}">
  <div class="hero-eyebrow">Strategy &middot; Build Library</div>
  <h1>Everything the strategy team has built.</h1>
  <div class="hero-lede">What each build is about, how it was put together, why it exists,
    and who to talk to. Open to anyone in the organisation.</div>
  <div class="hero-stats">"""
        + "".join(
            f'<div class="hstat"><div class="n">{n}</div><div class="k">{k}</div></div>'
            for n, k in stats
        )
        + f"""</div>
</div>
<div style="display:flex;justify-content:space-between;font-size:.74rem;
            color:{theme.BRAND['ink_200']};padding:12px 6px 0">
  <span>{verticals} verticals &nbsp;·&nbsp; {people} people involved</span>
  <span>{esc(stamp)}</span>
</div>""",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Toolbar
# ---------------------------------------------------------------------------
def render_toolbar(projects: list[Project], statuses: list[str]) -> list[Project]:
    """Browse by subject and by medium - the two questions a stranger actually asks.

    Note what is NOT here: no status chips, no priority filter. Those are delivery-
    tracking concerns and this is a catalogue, so they stay in the sheet and off the page.
    """
    spacer(34)
    head, find = st.columns([1.45, 1], vertical_alignment="bottom")
    head.markdown(
        '<div class="tool-head"><span class="tool-title">The library</span>'
        f'<span class="tool-sub">{plural(len(projects), "build")}</span></div>',
        unsafe_allow_html=True,
    )
    with find.container(key="find"):
        query = st.text_input(
            "Search", key="q", label_visibility="collapsed",
            placeholder="Search builds, people, what they do",
        ) or ""

    counts: dict[str, int] = {}
    for p in projects:
        counts[p.vertical] = counts.get(p.vertical, 0) + 1
    order = ["All"] + sorted(counts, key=lambda v: (-counts[v], v))
    spacer(18)
    with st.container(key="cats"):
        vertical = st.pills(
            "Vertical", order, default="All", label_visibility="collapsed",
            format_func=lambda v: f"{v} {len(projects) if v == 'All' else counts[v]}",
        ) or "All"

    # "Built with" is derived from the linked file's host, so it needs no new column.
    tool_counts: dict[str, int] = {}
    for p in projects:
        for kind in p.artifact_kinds:
            tool_counts[kind] = tool_counts.get(kind, 0) + 1

    spacer(6)
    with st.container(key="refine"):
        c1, c2, c3 = st.columns([1.15, 1, 1], vertical_alignment="bottom")
        tools = c1.multiselect(
            "Built with", sorted(tool_counts, key=lambda k: (-tool_counts[k], k)),
            placeholder="Anything",
        )
        people = c2.multiselect(
            "Person involved",
            sorted({n for p in projects for n in (p.owners + p.collaborators)}),
            placeholder="Anyone",
        )
        only_gaps = c3.checkbox("Only builds missing a write-up")

    out = []
    for p in projects:
        if vertical != "All" and p.vertical != vertical:
            continue
        if tools and not (set(tools) & set(p.artifact_kinds)):
            continue
        if people and not (set(people) & set(p.owners + p.collaborators)):
            continue
        if only_gaps and not p.doc_gaps:
            continue
        if query:
            haystack = " ".join([
                p.name, p.vertical, p.status, p.priority, p.impact, p.process_done,
                p.time_saved, p.money_saved,
                " ".join(p.owners), " ".join(p.collaborators),
                " ".join(s.text for s in p.steps),
                " ".join(str(v) for v in p.authored.values()),
            ]).lower()
            if query.lower() not in haystack:
                continue
        out.append(p)
    return out


# ---------------------------------------------------------------------------
# The index
# ---------------------------------------------------------------------------
def built_with_tag(p: Project) -> str:
    """What the thing actually IS - read from the linked file's host, never guessed."""
    if not p.artifact_kinds:
        return ""
    return f'<span class="builtwith">{esc(", ".join(p.artifact_kinds))}</span>'


def row_summary(p: Project) -> tuple[str, bool]:
    """Blurb for the row, plus whether it is a real description.

    Where the tracker filled both description columns, lead with the longer one - it is
    reliably the more informative (some rows have a one-word `Process Done` beside a
    full sentence in `Impact`).
    """
    blocks = p.what_blocks()
    if blocks:
        one_line = " ".join(max((t for _, t in blocks), key=len).split())
        return (one_line[:210] + "\N{HORIZONTAL ELLIPSIS}"
                if len(one_line) > 210 else one_line), True
    return "No write-up yet.", False


def card_facts(p: Project) -> str:
    """Small factual chips shown when a build has no write-up.

    Every one of these is read straight from the sheet - step counts, linked files,
    dates, savings. Nothing is invented; the point is to fill an otherwise empty card
    with things we genuinely know rather than dead space.
    """
    bits: list[str] = []
    if p.steps:
        bits.append(f"{p.steps_done}/{len(p.steps)} steps done")
    if p.links:
        bits.append(plural(len(p.links), "linked file"))
    if p.collaborators:
        bits.append(f"{plural(len(p.collaborators), 'contributor')}")
    if p.completed is not None:
        bits.append(f"done {fmt_date(p.completed)}")
    elif p.created is not None:
        bits.append(f"started {fmt_date(p.created)}")
    if p.time_saved:
        bits.append(f"saves {p.time_saved}")
    if not bits:
        return ""
    return ('<div class="idx-facts">'
            + "".join(f"<span>{esc(b)}</span>" for b in bits[:3])
            + "</div>")


def render_row(p: Project, n: int, spine: str = "") -> None:
    """One card: what it is, what it was built as, and who to ask.

    No status, no priority, no progress bar - see render_toolbar for why. The `--spine`
    custom property colours the card's left bar and its vertical label.
    """
    summary, is_real = row_summary(p)
    spine = spine or theme.BRAND["accent"]

    with st.container(key=f"row_{p.pid}"):
        st.markdown(
            f'<div class="idx" style="--spine:{spine}">'
            # Vertical and "built with" share the top row. Keeping the built-with chip
            # out of the footer stops it wrapping into a tall blob in a narrow card.
            f'<div class="idx-head"><span class="idx-vert">{esc(p.vertical)}</span>'
            f"{built_with_tag(p)}</div>"
            f'<div class="idx-title">{esc(p.name)}</div>'
            f'<div class="idx-desc{"" if is_real else " is-empty"}">{esc(summary)}</div>'
            f'{"" if is_real else card_facts(p)}'
            f'<div class="idx-foot">{people_row(p.owners, "No POC recorded")}'
            f'<div class="idx-chev"></div></div>'
            f"</div>",
            unsafe_allow_html=True,
        )
        # Transparent full-row hit target, positioned over the markup by theme.py.
        if st.button(f"Open {p.name}", key=f"go_{p.pid}"):
            st.session_state["selected"] = p.pid
            st.query_params["project"] = p.pid
            st.rerun()


def render_index(projects: list[Project], all_projects: list[Project],
                 statuses: list[str]) -> None:
    spacer(22)
    if len(projects) != len(all_projects):
        st.markdown(
            f'<div style="font-size:.76rem;color:{theme.BRAND["ink_300"]};'
            f'padding-bottom:10px">Showing {len(projects)} of {len(all_projects)}</div>',
            unsafe_allow_html=True,
        )
    st.markdown('<div class="idx-rule"></div>', unsafe_allow_html=True)

    if not projects:
        st.markdown(
            '<div class="empty-state">Nothing matches those filters.<br>'
            "Widen the category or status above.</div>",
            unsafe_allow_html=True,
        )
        return

    ordered = sorted(
        projects,
        key=lambda p: (status_sort_key(p.status, statuses), p.priority or "ZZ",
                       p.name.lower()),
    )
    # Colours come from the FULL project set, so a vertical keeps its hue when filtered.
    spines = theme.spine_map(p.vertical for p in all_projects)
    for start in range(0, len(ordered), CARDS_PER_ROW):
        cols = st.columns(CARDS_PER_ROW, gap="medium")
        for col, project in zip(cols, ordered[start:start + CARDS_PER_ROW]):
            with col:
                render_row(project, start + 1, spines.get(project.vertical, ""))


# ---------------------------------------------------------------------------
# Detail page
# ---------------------------------------------------------------------------
def qa_section(title: str, blocks: list[tuple[str, str]], empty_msg: str,
               extra_html: str = "", show_empty: bool | None = None) -> None:
    """`show_empty` defaults to 'nothing to show at all'; pass it explicitly when
    supporting detail exists but the question itself is still unanswered."""
    if show_empty is None:
        show_empty = not blocks and not extra_html
    authored = any(src == "authored" for src, _ in blocks)

    body = ""
    for source, text in blocks:
        if source != "authored":
            body += f'<div class="qa-source">From the {esc(source)}</div>'
        body += f'<div class="qa-body">{esc(text)}</div>'
    if show_empty:
        body += f'<div class="qa-empty">{esc(empty_msg)}</div>'

    tag = '<span class="authored-tag">written up</span>' if authored else ""
    st.markdown(
        f'<div class="qa"><h3>{esc(title)}{tag}</h3>{body}{extra_html}</div>',
        unsafe_allow_html=True,
    )


def how_extra_html(p: Project) -> str:
    """Checklist + artefact type + collaborators - the factual 'how' evidence."""
    parts = ""
    if p.steps:
        parts += (
            f'<div class="qa-source">Steps taken ({p.steps_done} of {len(p.steps)} '
            f"complete) — from the Subtasks column</div><ul class='steps'>"
        )
        for s in p.steps:
            box = ('<span class="step-box step-done">\N{CHECK MARK}</span>' if s.done
                   else '<span class="step-box step-open"></span>')
            parts += (f'<li class="{"" if s.done else "is-open"}">{box}'
                      f"<span>{esc(s.text)}</span></li>")
        parts += "</ul>"
    if p.links:
        parts += (
            f'<div class="qa-source">Built as: {esc(", ".join(p.artifact_kinds))} '
            f"— read from the linked file's address</div>"
        )
        for link in p.links:
            parts += (
                f'<div class="linkrow"><span class="linkrow-kind">{esc(link.kind)}</span>'
                f'<a href="{esc(link.url)}" target="_blank">{esc(link.url)}</a></div>'
            )
    if p.collaborators:
        parts += ('<div class="qa-source">Built with — from the Dependencies column</div>'
                  f"{people_row(p.collaborators)}")
    return parts


def edit_link_html(p: Project, source: str) -> str:
    """Link to the sheet so editing is one click away.

    The dashboard is deliberately read-only - it reads Google's one-way xlsx export - so
    the honest affordance is to send people to where the data actually lives rather than
    fake an editable control.
    """
    if not is_google_sheet(source):
        return ""
    where = f" &middot; row {p.sheet_row}" if p.sheet_row else ""
    return (
        f'<a class="edit-link" href="{esc(source)}" target="_blank" rel="noopener">'
        f"Edit this project in the sheet{where} \N{RIGHTWARDS ARROW}</a>"
    )


def render_detail(p: Project, all_projects: list[Project], source: str = "") -> None:
    with st.container(key="back"):
        if st.button("\N{LEFTWARDS ARROW}  All projects", key="back_btn"):
            st.session_state.pop("selected", None)
            st.query_params.clear()
            st.rerun()

    timeline = "Not recorded"
    if p.created is not None or p.completed is not None:
        timeline = f"{fmt_date(p.created)} \N{EN DASH} {fmt_date(p.completed)}"
        if p.days is not None:
            timeline += f" ({plural(int(p.days), 'day')})"

    # Catalogue facts only. Status, priority and dates are delivery-tracking detail and
    # live in the quiet footer strip further down, not in the headline.
    meta = [
        ("Point of contact", people_row(p.owners, "No POC recorded")),
        ("Vertical", vertical_tag(p.vertical)),
    ]
    if p.artifact_kinds:
        meta.append(("Built as", esc(", ".join(p.artifact_kinds))))
    if p.collaborators:
        meta.append(("Built with", people_row(p.collaborators)))

    st.markdown(
        '<div class="dhero">'
        '<div class="kicker">Build</div>'
        f"<h1>{esc(p.name)}</h1>"
        '<div class="dmeta">'
        + "".join(
            f'<div><div class="dmeta-label">{esc(label)}</div>'
            f'<div class="dmeta-value">{value}</div></div>'
            for label, value in meta
        )
        + f"</div>{edit_link_html(p, source)}</div>",
        unsafe_allow_html=True,
    )

    # "Why" is missing for almost everything because the sheet has no rationale column;
    # the Why section says so itself, so banner only the gaps Excel can actually fix.
    fixable = [g for g in p.doc_gaps if g != "Why it was built"]
    if fixable:
        spacer(24)
        st.markdown(
            f'<div class="gap-note">Not recorded in the tracker: '
            f"<b>{esc(', '.join(fixable))}</b>. Nothing is invented to fill the space, so "
            f"{'those sections read' if len(fixable) > 1 else 'that section reads'} as "
            f"blank below.</div>",
            unsafe_allow_html=True,
        )

    qa_section(
        "What this build is about",
        p.what_blocks(),
        "Nobody has written a description of this build yet. Fill in the "
        "'What It Is About' column of the Projects sheet.",
    )
    qa_section(
        "How it was built",
        p.how_blocks(),
        "Nothing recorded about how this was put together. Fill in the "
        "'How It Was Built' column of the Projects sheet.",
        extra_html=how_extra_html(p),
        # Knowing who was involved isn't the same as knowing how it was built, so the
        # empty note still shows when only collaborators are on record.
        show_empty=not p.has_how(),
    )
    qa_section(
        "Why it was built",
        p.why_blocks(),
        "No rationale recorded. Fill in the 'Why It Was Built' column of the Projects "
        "sheet — and note it is not the same as Impact: why is the problem that started "
        "the work, Impact is what changed once it shipped.",
    )
    impact = p.impact_blocks()
    if impact:
        qa_section("What changed", impact, "")

    # Delivery detail, deliberately last and deliberately quiet: useful if you go looking,
    # never the headline. This is where status/priority/dates live now.
    facts = [(k, v) for k, v in (
        ("Status", esc(p.status)),
        ("Priority", esc(p.priority)),
        ("Timeline", esc(timeline) if timeline != "Not recorded" else ""),
    ) if v]
    if facts:
        st.markdown(
            '<div class="qa"><h3>Delivery detail</h3><div class="meta-grid">'
            + "".join(
                f'<div class="meta-item"><div class="meta-label">{esc(k)}</div>'
                f'<div class="meta-value">{v}</div></div>' for k, v in facts
            )
            + "</div></div>",
            unsafe_allow_html=True,
        )

    # Whatever extra columns the team has added to the sheet, shown verbatim. No code
    # change is needed to surface a new column.
    if p.extras:
        st.markdown(
            '<div class="qa"><h3>Also recorded</h3>'
            + "".join(
                f'<div class="qa-source">{esc(label)}</div>'
                f'<div class="qa-body">{esc(value)}</div>'
                for label, value in p.extras.items()
            )
            + "</div>",
            unsafe_allow_html=True,
        )

    related = [
        q for q in all_projects
        if q.pid != p.pid and (q.vertical == p.vertical or set(q.owners) & set(p.owners))
    ][:6]
    if related:
        st.markdown('<div class="qa"><h3>Related work</h3></div>', unsafe_allow_html=True)
        spines = theme.spine_map(x.vertical for x in all_projects)
        for start in range(0, len(related), CARDS_PER_ROW):
            cols = st.columns(CARDS_PER_ROW, gap="medium")
            for col, q in zip(cols, related[start:start + CARDS_PER_ROW]):
                with col:
                    render_row(q, start + 1, spines.get(q.vertical, ""))


# ---------------------------------------------------------------------------
# Footer: data source
# ---------------------------------------------------------------------------
def render_footer(source: str) -> None:
    spacer(46)
    st.markdown('<div class="idx-rule"></div>', unsafe_allow_html=True)
    spacer(18)
    left, right = st.columns([2.4, 1], vertical_alignment="bottom")
    with left:
        st.markdown('<div class="foot-label">Data source</div>', unsafe_allow_html=True)
        # NEVER print the sheet URL here. This page is public, and rendering the URL
        # would hand the sheet to every visitor - exactly what moving it into secrets
        # was meant to prevent. Show what kind of source it is; let an override be typed.
        if is_google_sheet(source):
            st.caption("Google Sheet \N{MIDDLE DOT} configured in Streamlit secrets")
        else:
            st.caption(f"Local file \N{MIDDLE DOT} `{Path(source).name}`")
        st.text_input(
            "Point somewhere else", key="source_override",
            placeholder="Paste a different Google Sheets link or .xlsx path",
            label_visibility="collapsed",
            help="Leave blank to use the configured source. For a Google Sheet, set "
                 "link sharing to 'Anyone with the link'.",
        )
    with right:
        spacer(4)
        if st.button("Refresh now", width="stretch"):
            st.cache_data.clear()
            st.rerun()
        st.checkbox(
            f"Keep in sync (every {SYNC_SECONDS}s)", key="sync_on", value=True,
            help="Re-reads the sheet on a timer so the page keeps up with edits the "
                 "team makes. Turn it off if you want the page to hold still.",
        )
    st.markdown(
        f'<div style="font-size:.75rem;color:{theme.BRAND["ink_300"]};line-height:1.6;'
        f'padding-top:12px;max-width:86ch">'
        f"<b>Nothing here is fixed.</b> Add or delete rows, add or rename verticals, "
        f"invent new statuses on the <code>Lists</code> tab, or add your own columns — "
        f"the dashboard follows the sheet. New columns appear under "
        f"<i>Also recorded</i> on each project page. The only required column is "
        f"<code>Project Name</code>. &nbsp; <b>Richer write-up</b> — add an entry to "
        f"<code>{OVERRIDES_PATH.name}</code> to replace a project's text with your own "
        f"prose.</div>",
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    st.session_state.setdefault("source_override", "")

    # Deep links: ?project=<id> survives a refresh and can be shared.
    if "project" in st.query_params and "selected" not in st.session_state:
        st.session_state["selected"] = st.query_params["project"]
    on_detail = bool(st.session_state.get("selected"))
    source = data_source()

    if not source_exists(source):
        st.error(
            f"Can't find a workbook at `{source}`.\n\n"
            "Set the correct path under **Data source** below — a local `.xlsx` file, or "
            "a Google Sheets link pasted from the address bar."
        )
        render_footer(source)
        return

    try:
        projects, warnings, statuses, used = get_projects(
            source, file_mtime(source), file_mtime(str(OVERRIDES_PATH))
        )
    except Exception as exc:  # surface the real problem instead of a blank page
        st.error(f"Could not read the sheet.\n\n{exc}")
        render_footer(source)
        return

    for warning in warnings:
        st.warning(warning, icon="\N{WARNING SIGN}")

    # The heartbeat that keeps the page level with the live sheet. Declared after the
    # data loads so a broken source cannot leave a timer re-running a failing script.
    # Stamping the time first makes the fragment's immediate pass a no-op - see
    # sync_ticker for why that guard is load-bearing.
    if st.session_state.get("sync_on", True):
        st.session_state["_last_sync"] = time.monotonic()
        sync_ticker()

    selected = next(
        (p for p in projects if p.pid == st.session_state.get("selected")), None
    )
    if selected is not None:
        render_detail(selected, projects, used)
        render_footer(source)
        return

    # A stale ?project= id that matches nothing: fall back to the index.
    if on_detail:
        st.session_state.pop("selected", None)
        st.query_params.clear()

    # `used` may differ from `source` when a Google Sheet was unreachable and the local
    # copy was loaded instead - the stamp must name what is actually on screen.
    render_hero(projects, used, statuses)
    shown = render_toolbar(projects, statuses)
    render_gap_banner_slot(projects)
    render_index(shown, projects, statuses)
    render_footer(source)


def render_gap_banner_slot(all_projects: list[Project]) -> None:
    undescribed = [p for p in all_projects if not p.has_description]
    no_why = [p for p in all_projects if not p.why_blocks()]
    if not (undescribed or no_why):
        return
    bits = []
    if undescribed:
        bits.append(
            f"<b>{len(undescribed)} of {len(all_projects)} builds have no description "
            f"yet</b> — nothing on record to say what they are."
        )
    if no_why:
        bits.append(
            f"<b>{len(no_why)} have no stated rationale</b> — nothing on record for why "
            f"the work was picked up."
        )
    spacer(20)
    st.markdown(
        '<div class="gap-note">' + " ".join(bits)
        + " Nothing is invented to cover for that, so those sections read as blank. "
          "Fill in <i>What It Is About</i>, <i>How It Was Built</i> and <i>Why It Was "
          "Built</i> on the sheet and they fill themselves in here.</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
