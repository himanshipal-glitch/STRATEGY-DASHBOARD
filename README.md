# Strategy Team — Project Registry

A browsable catalogue of every project the strategy team has run. The landing page lists
each project with its **point of contact**; clicking one opens a detail page answering
**what it is about**, **how it was built** and **why it was built**.

Reads `Projects.xlsx` live — add a row in Excel, hit **Refresh from Excel**, and the
project appears. No rebuild, no code change.

## Run it

```bash
pip install -r requirements.txt
streamlit run app.py --server.port 8503
```

Then open <http://localhost:8503>. On Windows you can just double-click `run.bat`.

Every path in the code resolves relative to this folder, so the whole directory can be
moved or copied without editing anything. It reads `Projects.xlsx` from here if present,
otherwise falls back to `~/Downloads/My Tasks_Projects.xlsx`. To point it somewhere else,
put the path in **Data source** at the foot of the page.

This folder lives inside OneDrive, so `Projects.xlsx` syncs — handy for letting the team
fill it in, but it also means edits can arrive from other machines while the app is open.
Press **Refresh from Excel** to pick them up.

## Navigating it

No sidebar and no top bar. A dark hero panel carries the title and the headline numbers;
below it sits a left-aligned toolbar and then the index:

- **search** on the right of the toolbar
- **status segmented control** — All / Active / Completed / Needs attention
- **category links** with live counts (`All 27 · Product 7 · Marketing 6 …`)
- **refine row** — priority, person, and the missing-write-up filter
- **Data source** at the foot for the workbook path and Refresh

Projects are a dense numbered index rather than a grid of cards. Each row is fully
clickable and shows the title, a two-line description, the point of contact, the
vertical, checklist progress and status at a glance.

## Design

Restrained and near-monochrome — the Apple product-page register. The dark hero panel
has a fine bright top edge and a radial sheen so it reads as a material rather than a
flat rectangle; everything below is white with hairline rules, large tight-tracked
headings and tabular numerals.

Colour is only ever information, never decoration:

- **status** is a 6px dot beside plain text — accent green for done, near-black for
  active now, greys for dormant, muted red for blocked. No coloured pills. There is a
  second dot palette (`STATUS_DOTS_DARK`) so the same states read on the dark panel.
- **priority** is small grey uppercase text.
- **one accent** (`BRAND["accent"]`, a muted green) for links, progress and ticks. Swap
  it for `#0071E3` for pure Apple blue, or `BRAND["ink"]` to go fully monochrome — one
  line in `theme.py`.

### Two constraints baked into the code

**No web fonts, no icon fonts.** Google Fonts is blocked on the team's network. That
broke Streamlit's own Material Symbols ligatures, so `st.expander` rendered the literal
text `keyboard_arrow_right` on screen. There are therefore no expanders anywhere, no
`@import` in `theme.py`, and the chevrons are drawn in CSS. Use the system font stack.

**Clickable rows.** Each index row is a keyed container holding the row markup plus a
Streamlit button that is stretched over it at `opacity: 0`. The *element container*
(`st-key-go_*`) is what gets positioned — Streamlit's `stElementContainer` is itself
`position: relative`, so absolutely positioning the inner `.stButton` resolves against
that collapsed 0-height box instead of the row.

## Files

| File | What it is |
| --- | --- |
| `Projects.xlsx` | **The intake sheet.** What the team fills in, and what the app reads |
| `build_template.py` | Regenerates `Projects.xlsx` (seeded from the old tracker) |
| `app.py` | Pages, layout, filters, index and detail views |
| `theme.py` | **Every colour, radius and font.** Change a hex here and the whole dashboard follows |
| `data_loader.py` | Reads the workbook (either format), derives the write-ups |
| `overrides.json` | Optional hand-written write-ups that replace the sheet's text |
| `.streamlit/config.toml` | Base theme for Streamlit's own widgets |

## The intake sheet

`Projects.xlsx` is one file doing two jobs: the form people fill in, and the app's data
source. Share it (a shared drive works fine), let people add rows, then press **Refresh
from Excel**. Nothing needs rebuilding.

It has three sheets: **Read me first** (instructions), **Projects** (the table), and
**Lists** (the dropdown options — add a row there to add a new status or vertical).

18 columns. Required ones are tinted and every heading carries a hover note explaining
what belongs in it:

| Column | Notes |
| --- | --- |
| ID | Optional; assigned by position if blank |
| **Project Name** | The dashboard headline |
| **Vertical** | Dropdown, but accepts a new value if none fit |
| **Status** | Dropdown, **enforced** — the app groups by these six values |
| Priority | Dropdown, enforced |
| **Point of Contact** | The one person to ask. Shown on every row |
| Contributors | Comma separated; appear under "Built with" |
| **What It Is About** | Two or three sentences a newcomer could follow |
| How It Was Built | Tool, data source, approach, decisions |
| Why It Was Built | The problem that started the work |
| Impact / What Changed | What was different afterwards |
| Time Saved / Money Saved | Free text |
| Start Date / Completed Date | `dd-mm-yyyy`; the app computes elapsed days |
| Steps / Checklist | One per line, `[x]` done or `[ ]` outstanding → progress bar |
| Links | One URL per line; the app reads each host to infer the artefact type |
| Notes | Anything else |

**Why is not Impact.** *Why* is the problem that caused the work to start; *Impact* is what
changed once it shipped. The old tracker only had Impact, which is why 25 of 27 existing
projects show "no stated rationale". That column is the main reason this sheet exists.

Regenerating: `python build_template.py`. It refuses to overwrite an existing
`Projects.xlsx` unless you pass `--force`, because that would discard anything typed in
since. The 27 existing projects are carried over from the old tracker automatically —
but `How It Was Built` and `Why It Was Built` are left **empty** for all of them, because
the old sheet never captured those and inventing them is exactly what we must not do.

### Where the seeded rows came from — and how to check

Every one of the 27 pre-filled rows was copied from
`~/Downloads/My Tasks_Projects.xlsx` (sheet `All`, 27 rows, plus sheet `Completed`,
16 rows, joined on project name). Nothing else was used, and nothing was written by hand.

To verify that yourself rather than take it on trust:

```bash
python verify_provenance.py
```

It normalises every non-empty cell in `Projects.xlsx` and checks it against the pool of
all text in the source workbook, printing anything it cannot trace. It only reads.

Two facts that audit surfaces, both worth knowing before you circulate the sheet:

**The source tracker skips IDs 16–30.** Its IDs run 1–15 then 31–42 — fifteen numbers
missing. Those rows are simply not in the source file, so they could never be copied. If
those projects existed, they are absent from the registry and need re-adding by hand.

**Only 6 of 27 rows have a real description.** `What It Is About` was seeded from the old
`Process Done` column, which was mostly empty. A further 9 rows have nothing there but do
have `Impact` text, which the dashboard falls back on so the row is not blank. The
remaining **12 have no description at all**:

> Re-Express : Research · Overall Marketing Dashboard · Recommerce Expansion of PDMT ·
> RVM bags · In App leads Conversion · Seller vs Funnel Visibility for onboarded Sellers ·
> Seller Rating Campaign · Share the Contacts and List of Vendors for Sellers Service Hub ·
> ScrapTalk Funnel · Take Induction Session for New Peeps · Three Campaign Update ·
> End-End Lead CRM

And `How It Was Built` / `Why It Was Built` are empty for **all 27** — the old sheet never
had those columns. Those are the cells to ask owners to fill in first.

### Nothing is fixed — the sheet is in charge

The team can restructure the sheet freely; the dashboard follows it. No code change is
needed for any of this:

| Change on the sheet | What the dashboard does |
| --- | --- |
| Add / delete a **row** | Project appears or disappears |
| Add a **vertical** (any value, in the sheet or on `Lists`) | New category chip with a count |
| Add / rename / reorder a **status** on the `Lists` tab | Filter chips follow, in *your* order. A dot colour is matched on keywords (done/blocked/hold/progress…), and anything unrecognised gets a neutral grey |
| Add a **column** | Shown verbatim on each project page under *Also recorded* |
| Delete a **column** | That section simply stops appearing |

The **only required column is `Project Name`** — everything else is optional. Delete all
17 other columns and the dashboard still lists 27 projects. Delete `Project Name` and you
get a clear error naming what's missing, rather than a blank page.

Statuses are no longer a fixed list of six. The `Lists` tab's Status column is
authoritative for both the filter order and the hero tiles, and any status used in the
data but missing from `Lists` is still shown rather than silently dropped.

### The live Google Sheet

`data_loader.GOOGLE_SHEET_URL` is the default source — the team's shared sheet. The app
converts the URL to an `.xlsx` export and reads all three tabs, so everyone edits one live
document. Paste a different URL (or a local path) into **Data source** to point elsewhere.

**The sheet must be shared as "Anyone with the link → Viewer".** The dashboard is not
signed in as you, so a sheet restricted to named accounts returns `401 Unauthorized`.
When that happens the app does not break: it falls back to the local `Projects.xlsx` and
shows a warning saying, in as many words, that you are looking at a stale local copy and
not the team's edits. Never quietly show old data as if it were live.

### Keeping up with edits

Streamlit only re-reads data when the script re-runs, and a page nobody is clicking never
re-runs. `sync_ticker()` is the heartbeat that fixes that: a `st.fragment(run_every=30)`
that triggers a full app re-run every 30 seconds. The cache `ttl` matches, so each tick
genuinely re-fetches. Toggle it with **Keep in sync** in the footer; **Refresh now**
forces an immediate re-read.

One trap worth knowing if you touch that function: **a fragment executes immediately when
it is called, not only on its timer.** An unguarded `st.rerun()` inside it therefore fires
on the first pass and every pass after — an infinite loop where the page renders the
warning banner and nothing else. The `_last_sync` elapsed-time guard is what prevents
that, and `main()` stamps it just before calling the fragment so the immediate pass is a
no-op. Do not remove it.

### Both formats still load

`data_loader.py` detects the shape of whatever workbook you point it at:

- a **`Projects`** sheet → the new format above;
- an **`All`** sheet (+ optional `Completed`) → the original tracker, joined on task name.

So old exports keep working. Header spellings are matched loosely, and unknown status
values produce a visible warning rather than silently vanishing from the filters.

## Where the content comes from

The spreadsheet has no `what` / `how` / `why` columns, so the dashboard assembles those
three answers out of the columns that do exist — and **names the source column on screen
for every sentence it shows**, so you can always tell where a claim came from.

| Section | Built from |
| --- | --- |
| What this project is about | `Process Done` and `Impact` columns, each labelled |
| How it was built | `Subtasks` checklist, the artefact type read off the linked URL's host, and the `Dependencies` column |
| Why it was built | `Time Saved` / `Money Saved`, or your prose in `overrides.json` |

Two deliberate choices worth knowing about:

- **Nothing is invented.** Where the tracker is silent, the dashboard prints an explicit
  "not recorded" state rather than filler. The counts on the landing page tell you how
  many projects still need a write-up.
- **There is no rationale column in the spreadsheet.** `Impact` records what *changed*,
  not why the work was picked up, so "Why it was built" is genuinely empty for most
  projects rather than being padded out with recycled `Impact` text. That is what
  `overrides.json` is for.

Sheets used: `All` is the master list; `Completed` supplies the extra detail columns and
is joined on task name. A project that appears only on `Completed` still gets a card, with
a warning shown in the UI.

## Adding to it

**A new project** — add a row to the `All` sheet. Fill `Answerable To` so it gets a point
of contact. Hit Refresh.

**A proper write-up** — add an entry to `overrides.json`, keyed by tracker ID or exact
task name:

```json
{
  "projects": {
    "15": {
      "what": "What the project actually is.",
      "how":  "How it was built — stack, data sources, decisions.",
      "why":  "Why it existed and what changed because of it."
    }
  }
}
```

Every field is optional; fill only what you want to override. Overridden text is badged
**written up** on screen to distinguish it from text pulled out of Excel. The dashboard
warns you if a key here matches no project, so typos get caught.

## Notes

- Names are spelled inconsistently in the tracker (`annada`/`Annada`, `namita`/`Namitha`).
  `PERSON_ALIASES` in `data_loader.py` merges them so one person is not listed twice in
  the owner filter. It is an explicit map — add to it as new spellings turn up.
- Project pages are deep-linkable: `?project=15` opens that project directly, so you can
  paste a link to one project in Slack.
- The theme is a read of recykal.market's look — deep circular-economy green, lime accent,
  warm off-white. Everything is in `theme.py` if it needs to move closer to the real site.
