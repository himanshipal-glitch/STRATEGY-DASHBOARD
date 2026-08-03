"""
Reads the project workbook and turns it into records for the dashboard.

TWO FORMATS ARE SUPPORTED, detected automatically:

  1. `Projects.xlsx` — the intake sheet built by build_template.py. A single `Projects`
     sheet with explicit "What It Is About" / "How It Was Built" / "Why It Was Built"
     columns. This is the format to use going forward.

  2. `My Tasks_Projects.xlsx` — the original tracker: an `All` master sheet plus a
     `Completed` detail sheet, joined on task name. Kept working so old exports still
     open, but it has no rationale column, which is why format 1 exists.

Design rule, inherited from the wider repo: never invent content. Every sentence the
dashboard shows is either (a) copied verbatim from a column, with that column named on
screen, (b) a factual read of a URL's host (script.google.com -> Apps Script), or (c)
prose written by hand in overrides.json, which is badged "authored". Where the sheet is
silent the dashboard says so instead of filling the space.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlparse

import pandas as pd

HERE = Path(__file__).parent
OVERRIDES_PATH = HERE / "overrides.json"

# The team's live Google Sheet: the source of truth. The local .xlsx below is a fallback
# used only when the sheet cannot be reached (see load_with_fallback).
#
# For this to work the sheet MUST be shared as "Anyone with the link -> Viewer".
# A sheet restricted to named accounts answers the export URL with 401 Unauthorized.
#
# The URL lives ONLY in Streamlit secrets - never in this file. This repo is public, and
# the sheet is shared as "anyone with the link", so a URL committed here would hand the
# whole registry to anyone who finds the repo. Set it in one of two places:
#
#   Streamlit Cloud:  Manage app -> Settings -> Secrets
#   locally:          .streamlit/secrets.toml   (gitignored; see secrets.toml.example)
#
#     [data]
#     sheet_url = "https://docs.google.com/spreadsheets/d/..../edit"
#
# With no secret set, the dashboard falls back to a local Projects.xlsx and says so.
def _sheet_url() -> str | None:
    """Sheet URL from Streamlit secrets, or None if not configured.

    Wrapped defensively: st.secrets raises rather than returning a default when there is
    no secrets file at all, and this module is also imported by scripts (build_template,
    verify_provenance) that run outside Streamlit entirely.
    """
    try:
        import streamlit as st

        return str(st.secrets["data"]["sheet_url"]).strip() or None
    except Exception:
        return None


GOOGLE_SHEET_URL = _sheet_url()

LOCAL_FALLBACKS = [
    HERE / "Projects.xlsx",
    Path.home() / "Downloads" / "My Tasks_Projects.xlsx",
]
# Kept for callers that expect a Path to the local workbook.
DEFAULT_WORKBOOK = next((p for p in LOCAL_FALLBACKS if p.exists()), LOCAL_FALLBACKS[0])
# The live sheet when a secret is configured, otherwise whatever local copy exists.
DEFAULT_SOURCE = GOOGLE_SHEET_URL or str(DEFAULT_WORKBOOK)

NEW_SHEET = "Projects"
LEGACY_MASTER = "All"
LEGACY_DETAIL = "Completed"

# The tracker spells some names more than one way. Merging them keeps one person from
# showing up as two entries in the owner filter. Kept as an explicit, visible map rather
# than a clever fuzzy match, so a wrong merge is easy to spot and fix.
PERSON_ALIASES = {
    "annada": "Annada",
    "namita": "Namitha",
    "namitha": "Namitha",
    "rishica": "Rishica",
    "ayesh": "Ayesha",
    "ayesha": "Ayesha",
    "anoj": "Anoj",
    "abd": "ABD",
}

# Display order in the index. Anything unrecognised sorts last.
PROJECTS_SHEET_ID_RE = re.compile(r"/spreadsheets/d/([a-zA-Z0-9-_]+)")

# Fallback display order, used only for statuses the sheet does not itself order. The
# team's own ordering on the `Lists` tab always wins - see `_status_order`.
FALLBACK_STATUS_ORDER = [
    "In Progress", "Continuous", "Blocked", "On Hold", "Not started", "Completed",
]

# Headers the loader understands. Anything else the team adds becomes a row in
# Project.extras and is displayed automatically, so new columns need no code change.
KNOWN_HEADERS = {
    "id", "projectname", "project", "task", "name",
    "vertical", "team", "status", "priority",
    "pointofcontact", "owner", "answerableto",
    "contributors", "dependencies", "collaborators",
    "whatitisabout", "what", "description",
    "howitwasbuilt", "how", "whyitwasbuilt", "why",
    "impactwhatchanged", "impact", "timesaved", "moneysaved",
    "startdate", "created", "completeddate", "completed",
    "stepschecklist", "steps", "subtasks", "links", "link", "notes",
}
# Without a project name there is no project, so this is the one hard requirement.
REQUIRED_HEADERS = ("Project Name", "Project", "Task", "Name")

ARTIFACT_KINDS = [
    ("script.google.com", "Apps Script web app"),
    ("docs.google.com/spreadsheets", "Google Sheet"),
    ("docs.google.com/document", "Google Doc"),
    ("docs.google.com/presentation", "Google Slides"),
    ("drive.google.com", "Drive file"),
    ("lookerstudio.google.com", "Looker Studio"),
    ("datastudio.google.com", "Looker Studio"),
    ("figma.com", "Figma file"),
    ("notion.so", "Notion page"),
    ("github.com", "GitHub repo"),
]


# ---------------------------------------------------------------------------
# Records
# ---------------------------------------------------------------------------
@dataclass
class Step:
    text: str
    done: bool


@dataclass
class Link:
    url: str
    kind: str


@dataclass
class Project:
    pid: str
    name: str
    vertical: str
    priority: str
    status: str
    owners: list[str] = field(default_factory=list)
    collaborators: list[str] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)
    links: list[Link] = field(default_factory=list)

    # explicit write-up columns (new format only)
    desc_what: str = ""
    desc_how: str = ""
    desc_why: str = ""

    # outcome columns (both formats)
    impact: str = ""
    time_saved: str = ""
    money_saved: str = ""
    process_done: str = ""   # legacy format's "what was done" column

    created: pd.Timestamp | None = None
    completed: pd.Timestamp | None = None
    days: float | None = None
    notes: str = ""

    # Any column the team adds that the loader has no special handling for. Displayed
    # verbatim on the detail page under "Also recorded", so adding a column to the sheet
    # needs no code change at all.
    extras: dict[str, str] = field(default_factory=dict)

    # 1-based row on the Projects sheet, so the UI can send someone straight to the row
    # they need to edit. 0 when unknown (legacy format).
    sheet_row: int = 0

    # authored prose from overrides.json
    authored: dict[str, str] = field(default_factory=dict)

    # ---- derived --------------------------------------------------------
    @property
    def owner_label(self) -> str:
        return ", ".join(self.owners) if self.owners else "Unassigned"

    @property
    def steps_done(self) -> int:
        return sum(1 for s in self.steps if s.done)

    @property
    def progress(self) -> float | None:
        """Fraction of checklist items ticked, or None when there is no checklist."""
        return self.steps_done / len(self.steps) if self.steps else None

    @property
    def artifact_kinds(self) -> list[str]:
        seen: list[str] = []
        for link in self.links:
            if link.kind not in seen:
                seen.append(link.kind)
        return seen

    def what_blocks(self) -> list[tuple[str, str]]:
        """(source label, verbatim text) for 'what this project is about'.

        Preference: hand-written override, then the new sheet's explicit column, then the
        legacy pair. The old tracker used `Process Done` and `Impact` interchangeably —
        some rows describe the work in one, some the other — so both are shown, each
        labelled with the column it came from, rather than guessing which is which.
        """
        if self.authored.get("what"):
            return [("authored", self.authored["what"])]
        if self.desc_what.strip():
            return [("What It Is About column", self.desc_what.strip())]
        blocks = []
        if self.process_done.strip():
            blocks.append(("Process Done column", self.process_done.strip()))
        if self.impact.strip():
            blocks.append(("Impact column", self.impact.strip()))
        return blocks

    def how_blocks(self) -> list[tuple[str, str]]:
        if self.authored.get("how"):
            return [("authored", self.authored["how"])]
        if self.desc_how.strip():
            return [("How It Was Built column", self.desc_how.strip())]
        return []

    def why_blocks(self) -> list[tuple[str, str]]:
        """(source label, verbatim text) for 'why it was built'.

        The legacy tracker had no rationale column — `Impact` records what changed, not
        why the work was commissioned — so for old data this draws only on the savings
        columns and stays empty rather than recycling `Impact`, which is already shown
        under 'what this is about'. The new sheet has a real `Why It Was Built` column.
        """
        if self.authored.get("why"):
            return [("authored", self.authored["why"])]
        if self.desc_why.strip():
            return [("Why It Was Built column", self.desc_why.strip())]
        blocks = []
        if self.time_saved.strip():
            blocks.append(("Time Saved column", self.time_saved.strip()))
        if self.money_saved.strip():
            blocks.append(("Money Saved column", self.money_saved.strip()))
        return blocks

    def impact_blocks(self) -> list[tuple[str, str]]:
        """Outcome text, shown only when it is not already serving as the description."""
        if self.desc_what.strip() and self.impact.strip():
            return [("Impact / What Changed column", self.impact.strip())]
        return []

    def has_how(self) -> bool:
        return bool(self.how_blocks() or self.steps or self.links)

    @property
    def has_description(self) -> bool:
        return bool(self.what_blocks())

    @property
    def doc_gaps(self) -> list[str]:
        """Which of the three questions this project cannot yet answer."""
        gaps = []
        if not self.what_blocks():
            gaps.append("What it is about")
        if not self.has_how():
            gaps.append("How it was built")
        if not self.why_blocks():
            gaps.append("Why it was built")
        return gaps

    @property
    def doc_score(self) -> int:
        return 3 - len(self.doc_gaps)


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------
def _text(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    s = str(value).strip()
    return "" if s.lower() in {"nan", "none", "nat"} else s


def _join_key(name: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", _text(name).lower()).strip()


def _people(value) -> list[str]:
    raw = _text(value)
    if not raw:
        return []
    out: list[str] = []
    for part in re.split(r"[,/&]| and ", raw):
        part = part.strip(" .")
        if not part:
            continue
        canon = PERSON_ALIASES.get(part.lower(), part[:1].upper() + part[1:])
        if canon not in out:
            out.append(canon)
    return out


def _steps(value) -> list[Step]:
    """Parse the '[x] did a thing\\n[ ] todo' checklist format."""
    raw = _text(value)
    if not raw:
        return []
    steps = []
    for line in raw.splitlines():
        line = line.strip()
        if not line:
            continue
        m = re.match(r"^[-*]?\s*\[\s*([xX✓])?\s*\]\s*(.+)$", line)
        if m:
            steps.append(Step(text=m.group(2).strip(), done=bool(m.group(1))))
        else:
            # A bare line with no checkbox: keep the text, don't guess at its state.
            steps.append(Step(text=line.lstrip("-* "), done=False))
    return steps


def _artifact_kind(url: str) -> str:
    lowered = url.lower()
    for needle, label in ARTIFACT_KINDS:
        if needle in lowered:
            return label
    return urlparse(url).netloc or "Link"


def _links(*values) -> list[Link]:
    found: list[Link] = []
    seen: set[str] = set()
    for value in values:
        for url in re.findall(r"https?://[^\s,;)\]]+", _text(value)):
            url = url.rstrip(".,;")
            if url not in seen:
                seen.add(url)
                found.append(Link(url=url, kind=_artifact_kind(url)))
    return found


def _strip_urls(value) -> str:
    return re.sub(r"\s*https?://[^\s,;)\]]+\s*,?", " ", _text(value)).strip(" ,")


def _timestamp(value):
    if not _text(value):
        return None
    ts = pd.to_datetime(value, errors="coerce", dayfirst=True)
    return None if pd.isna(ts) else ts


def _days(created, completed):
    if created is None or completed is None:
        return None
    return max(0.0, (completed - created).total_seconds() / 86400.0)


def _load_overrides() -> dict:
    """Optional hand-written What/How/Why, keyed by project ID or exact project name."""
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    entries = raw.get("projects", raw) if isinstance(raw, dict) else {}
    return {str(k).strip(): v for k, v in entries.items() if isinstance(v, dict)}


def is_google_sheet(source: str) -> bool:
    return "docs.google.com/spreadsheets" in str(source)


def _google_export_url(source: str) -> str:
    """Turn a Google Sheets page URL into its .xlsx export URL."""
    m = PROJECTS_SHEET_ID_RE.search(str(source))
    if not m:
        raise ValueError(
            "That looks like a Google Sheets link but no document ID could be read from "
            "it. Copy the URL straight from the browser address bar."
        )
    return f"https://docs.google.com/spreadsheets/d/{m.group(1)}/export?format=xlsx"


def _read_workbook(source: str | Path) -> dict[str, pd.DataFrame]:
    """Read every sheet of an .xlsx file OR a Google Sheet, keyed by sheet name."""
    if is_google_sheet(source):
        url = _google_export_url(str(source))
        try:
            return pd.read_excel(url, sheet_name=None, dtype=object)
        except Exception as exc:
            # By far the commonest cause is link sharing being off, in which case Google
            # answers with 401/403 or an HTML sign-in page rather than a workbook.
            detail = f"{type(exc).__name__}: {exc}"
            if any(code in detail for code in ("401", "403", "Unauthorized", "Forbidden")):
                raise PermissionError(
                    "Google refused access to that sheet.\n\n"
                    "Open it, press Share, and under 'General access' choose "
                    "'Anyone with the link' with the role set to Viewer. A sheet "
                    "restricted to named accounts cannot be read by the dashboard, "
                    "because the dashboard is not signed in as you.\n\n"
                    f"({detail})"
                ) from exc
            raise ValueError(
                f"Could not download that Google Sheet.\n\n{detail}"
            ) from exc
    return pd.read_excel(Path(source), sheet_name=None, dtype=object)


def _status_order(sheets: dict[str, pd.DataFrame], seen: list[str]) -> list[str]:
    """Status values in the order the TEAM chose.

    The `Lists` tab's Status column is authoritative, so reordering, renaming, adding or
    deleting a status there changes the dashboard's filters with no code change. Statuses
    that appear in the data but not on `Lists` are appended, so nothing is ever hidden
    just because someone forgot to register it.
    """
    ordered: list[str] = []
    lookup = {re.sub(r"[^a-z0-9]+", "", str(k).lower()): k for k in sheets}
    if "lists" in lookup:
        lists = sheets[lookup["lists"]]
        for col in lists.columns:
            if re.sub(r"[^a-z0-9]+", "", str(col).lower()) == "status":
                for v in lists[col].tolist():
                    label = _text(v)
                    if label and label not in ordered:
                        ordered.append(label)
                break
    for label in FALLBACK_STATUS_ORDER:
        if label in seen and label not in ordered:
            ordered.append(label)
    for label in seen:  # anything the team invented on the fly
        if label and label not in ordered:
            ordered.append(label)
    return [s for s in ordered if s in seen] or seen


def _row_number(index_value) -> int:
    """Sheet row for a pandas index value: +2 for the header and the 0-based index."""
    try:
        return int(index_value) + 2
    except (TypeError, ValueError):
        return 0


def _norm_cols(df: pd.DataFrame) -> dict[str, str]:
    """Map normalised column name -> actual column name, so headers can drift a little."""
    return {re.sub(r"[^a-z0-9]+", "", str(c).lower()): c for c in df.columns}


def _pick(row: dict, cols: dict[str, str], *names: str):
    """First present value among several candidate header spellings."""
    for n in names:
        actual = cols.get(re.sub(r"[^a-z0-9]+", "", n.lower()))
        if actual is not None and _text(row.get(actual)):
            return row.get(actual)
    return None


# ---------------------------------------------------------------------------
# Format 1: the Projects intake sheet
# ---------------------------------------------------------------------------
def _load_new_format(df: pd.DataFrame, overrides: dict) -> tuple[list[Project], list[str]]:
    warnings: list[str] = []
    cols = _norm_cols(df)
    projects: list[Project] = []
    seen_names: set[str] = set()

    for n, (_, raw) in enumerate(df.iterrows(), start=1):
        row = raw.to_dict()
        name = _text(_pick(row, cols, "Project Name", "Project", "Task", "Name"))
        if not name:
            continue

        key = _join_key(name)
        if key in seen_names:
            warnings.append(
                f"'{name}' appears more than once on the '{NEW_SHEET}' sheet. "
                f"Both rows are shown — delete or rename one."
            )
        seen_names.add(key)

        raw_id = _text(_pick(row, cols, "ID"))
        if raw_id.endswith(".0"):
            raw_id = raw_id[:-2]
        created = _timestamp(_pick(row, cols, "Start Date", "Created"))
        completed = _timestamp(_pick(row, cols, "Completed Date", "Completed"))

        # Any status string is accepted. It gets its own filter chip and a dot colour
        # matched on keywords, so the team can add or rename statuses freely.
        status = _text(_pick(row, cols, "Status")) or "Not recorded"

        notes = _pick(row, cols, "Notes")
        links_cell = _pick(row, cols, "Links", "Link")

        p = Project(
            pid=raw_id or str(n),
            name=name,
            vertical=_text(_pick(row, cols, "Vertical", "Team")) or "Unassigned",
            priority=_text(_pick(row, cols, "Priority")),
            status=status,
            owners=_people(_pick(row, cols, "Point of Contact", "Owner", "Answerable To")),
            collaborators=_people(
                _pick(row, cols, "Contributors", "Dependencies", "Collaborators")
            ),
            steps=_steps(_pick(row, cols, "Steps / Checklist", "Steps", "Subtasks")),
            links=_links(links_cell, notes),
            desc_what=_strip_urls(_pick(row, cols, "What It Is About", "What", "Description")),
            desc_how=_strip_urls(_pick(row, cols, "How It Was Built", "How")),
            desc_why=_strip_urls(_pick(row, cols, "Why It Was Built", "Why")),
            impact=_text(_pick(row, cols, "Impact / What Changed", "Impact")),
            time_saved=_text(_pick(row, cols, "Time Saved")),
            money_saved=_text(_pick(row, cols, "Money Saved")),
            created=created,
            completed=completed,
            days=_days(created, completed),
            notes=_strip_urls(notes),
            # dropna(how="all") keeps the original index, so this stays true to the
            # sheet even when blank rows sit between projects. +2 for the header row
            # and pandas' 0-based index. Converted with a try rather than an isinstance
            # check: the index is a numpy.int64, which is NOT a Python int on Windows.
            sheet_row=_row_number(raw.name),
        )
        # Columns the team invented: kept verbatim and shown on the detail page.
        for norm_name, actual in cols.items():
            if norm_name not in KNOWN_HEADERS and not norm_name.startswith("unnamed"):
                value = _text(row.get(actual))
                if value:
                    p.extras[str(actual).strip()] = value

        p.authored = overrides.get(p.pid) or overrides.get(name) or {}
        if p.authored.get("owners"):
            p.owners = _people(", ".join(p.authored["owners"]))
        projects.append(p)

    return projects, warnings


# ---------------------------------------------------------------------------
# Format 2: the legacy All + Completed tracker
# ---------------------------------------------------------------------------
def _load_legacy(sheets: dict[str, pd.DataFrame], overrides: dict
                 ) -> tuple[list[Project], list[str]]:
    warnings: list[str] = []
    master = sheets[LEGACY_MASTER].dropna(how="all")
    detail = sheets.get(LEGACY_DETAIL, pd.DataFrame()).dropna(how="all")

    detail_by_key: dict[str, dict] = {}
    for _, row in detail.iterrows():
        key = _join_key(row.get("Task"))
        if not key:
            continue
        if key in detail_by_key:
            warnings.append(
                f"'{_text(row.get('Task'))}' appears more than once on the "
                f"'{LEGACY_DETAIL}' sheet — the first row was used."
            )
            continue
        detail_by_key[key] = row.to_dict()

    projects: list[Project] = []
    used: set[str] = set()

    def build(row: dict, pid: str, dkey: str) -> Project:
        d = detail_by_key.get(dkey, {})
        if dkey in detail_by_key:
            used.add(dkey)
        name = _text(row.get("Task"))
        created = _timestamp(d.get("Created"))
        completed = _timestamp(d.get("Completed"))
        p = Project(
            pid=pid,
            name=name,
            vertical=_text(row.get("Vertical")) or "Unassigned",
            priority=_text(row.get("Priority")),
            status=_text(row.get("Status")) or _text(d.get("Status")) or "Unspecified",
            owners=_people(row.get("Answerable To") or d.get("Answerable To")),
            collaborators=_people(row.get("Dependencies") or d.get("Dependencies")),
            steps=_steps(row.get("Subtasks") or d.get("Subtasks")),
            impact=_text(d.get("Impact")),
            time_saved=_text(d.get("Time Saved")),
            money_saved=_text(d.get("Money Saved")),
            # `Process Done` sometimes holds only URLs; those become link rows.
            process_done=_strip_urls(d.get("Process Done")),
            created=created,
            completed=completed,
            days=_days(created, completed),
            notes=_strip_urls(row.get("Notes")),
        )
        p.links = _links(row.get("Notes"), d.get("Notes"), d.get("Process Done"))
        p.authored = overrides.get(pid) or overrides.get(name) or {}
        if p.authored.get("owners"):
            p.owners = _people(", ".join(p.authored["owners"]))
        return p

    for _, row in master.iterrows():
        row = row.to_dict()
        name = _text(row.get("Task"))
        if not name:
            continue
        raw_id = _text(row.get("ID"))
        pid = raw_id[:-2] if raw_id.endswith(".0") else (raw_id or _join_key(name))
        projects.append(build(row, pid, _join_key(name)))

    # Anything on the detail sheet but missing from the master still deserves a row -
    # losing a project silently would be worse than an odd ID.
    for key, drow in detail_by_key.items():
        if key in used:
            continue
        warnings.append(
            f"'{_text(drow.get('Task'))}' is on '{LEGACY_DETAIL}' but not "
            f"'{LEGACY_MASTER}'. It is shown, with no ID."
        )
        drow.setdefault("Status", "Completed")
        projects.append(build(drow, f"c-{key[:24]}", key))

    return projects, warnings


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def _best_projects_tab(sheets: dict[str, pd.DataFrame], lookup: dict[str, str]):
    """The tab that most looks like the intake sheet, by columns rather than by name.

    Returns (tab name, dataframe) or (None, None) when no tab has a project-name column.
    A tab called "Projects" always wins if it qualifies; otherwise the tab with the most
    recognised intake columns does, so an import that landed on the wrong tab still works.
    """
    required = {re.sub(r"[^a-z0-9]+", "", h.lower()) for h in REQUIRED_HEADERS}
    # Columns that mark a sheet as the NEW format rather than the legacy tracker.
    signals = {
        "whatitisabout", "howitwasbuilt", "whyitwasbuilt", "pointofcontact",
        "contributors", "stepschecklist", "impactwhatchanged", "links",
    }

    best = (None, None, -1)
    for name, raw in sheets.items():
        frame = raw.dropna(how="all")
        cols = set(_norm_cols(frame))
        if not (cols & required):
            continue                      # no project-name column: not a candidate
        score = len(cols & signals)
        if score == 0:
            continue                      # looks like the legacy tracker, not the intake
        if lookup.get("projects") == name:
            score += 100                  # an explicitly named tab always wins
        if score > best[2]:
            best = (name, frame, score)
    return best[0], best[1]


def load_projects(workbook: str | Path) -> tuple[list[Project], list[str], list[str]]:
    """Return (projects, warnings, status_order).

    `workbook` may be a local .xlsx path or a Google Sheets URL. `status_order` is the
    team's own status ordering, read from the Lists tab — the UI builds its filters from
    it, so nothing about statuses is fixed in code.
    """
    label = str(workbook) if is_google_sheet(workbook) else Path(workbook).name
    sheets = _read_workbook(workbook)
    overrides = _load_overrides()
    warnings: list[str] = []

    # Match sheet names loosely so "projects" / "Projects " still resolve.
    lookup = {re.sub(r"[^a-z0-9]+", "", str(k).lower()): k for k in sheets}

    # Find the intake table by its COLUMNS, not by its tab name. Importing the template
    # into Google Sheets with "Replace current sheet" lands the new columns on whatever
    # tab happened to be selected, so keying off the name alone made the dashboard fall
    # back to legacy mode and show 27 blank write-ups. Whichever tab looks most like the
    # intake sheet wins.
    tab_name, df = _best_projects_tab(sheets, lookup)

    if tab_name is not None:
        if tab_name != lookup.get("projects"):
            warnings.append(
                f"Reading projects from the '{tab_name}' tab — it has the intake columns "
                f"even though it is not called '{NEW_SHEET}'. Renaming that tab to "
                f"'{NEW_SHEET}' would make this unambiguous."
            )
        projects, more = _load_new_format(df, overrides)
        warnings.extend(more)
        source = str(tab_name)
    elif "all" in lookup:
        sheets = {LEGACY_MASTER: sheets[lookup["all"]],
                  **({LEGACY_DETAIL: sheets[lookup["completed"]]}
                     if "completed" in lookup else {})}
        projects, more = _load_legacy(sheets, overrides)
        warnings.extend(more)
        source = f"{LEGACY_MASTER} + {LEGACY_DETAIL}"
    else:
        raise ValueError(
            f"{label} has no '{NEW_SHEET}' sheet and no '{LEGACY_MASTER}' sheet. "
            f"Sheets found: {', '.join(map(str, sheets))}. "
            f"Run build_template.py to create a Projects.xlsx in the right shape."
        )

    if not projects:
        warnings.append(
            f"Read the '{source}' sheet of {label} but found no rows with a project "
            f"name in them."
        )

    known = {p.pid for p in projects} | {p.name for p in projects}
    unknown = [k for k in overrides if k not in known]
    if unknown:
        warnings.append(
            "overrides.json has entries that match no project: " + ", ".join(unknown)
        )

    seen_statuses = list(dict.fromkeys(p.status for p in projects if p.status))
    return projects, warnings, _status_order(sheets, seen_statuses)


def load_with_fallback(source: str) -> tuple[list[Project], list[str], list[str], str]:
    """Load `source`; if a Google Sheet is unreachable, fall back to the local copy.

    Returns the usual triple plus the source actually used, so the UI can say which one
    it is showing. A dashboard that quietly shows stale local data while the team edits
    the sheet would be worse than useless, so the fallback is always announced loudly.
    """
    try:
        projects, warnings, statuses = load_projects(source)
        return projects, warnings, statuses, source
    except Exception as exc:
        local = next((p for p in LOCAL_FALLBACKS if p.exists()), None)
        if not (is_google_sheet(source) and local):
            raise
        projects, warnings, statuses = load_projects(local)
        warnings.insert(0, (
            f"**Showing the local copy `{local.name}`, not the live Google Sheet.** "
            f"Anything the team has typed into the sheet is NOT on this page.\n\n{exc}"
        ))
        return projects, warnings, statuses, str(local)


def status_sort_key(status: str, order: list[str] | None = None) -> int:
    """Index of `status` in the team's ordering; unknown values sort last."""
    table = order or FALLBACK_STATUS_ORDER
    return table.index(status) if status in table else len(table)
