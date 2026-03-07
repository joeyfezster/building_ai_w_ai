# Review Pack v2 — "Mission Control" Design Spec

## Design Intent

Reduce review friction for a human operator of a dark factory by introducing **persistent health context** (sidebar), **zone-anchored filtering** (architecture as the cross-cutting lens), and **explicit information tiers** (verdict → context → evidence → code).

The reviewer's workflow: **glance at verdict → check if anything needs attention → drill into anomalies → merge or reject**.

## Layout: Sidebar + Main Pane

```
┌──────────────────────┬─────────────────────────────────────────────┐
│                      │                                             │
│   SIDEBAR (fixed)    │           MAIN PANE (scrollable)            │
│   ~260px wide        │           ~840px wide                       │
│                      │                                             │
│   Always visible.    │   Content sections, each expandable         │
│   Never scrolls      │   in-place. Filtered by active zone.        │
│   off screen.        │                                             │
│                      │                                             │
└──────────────────────┴─────────────────────────────────────────────┘
```

### Sidebar (Persistent, Fixed Left)

The sidebar answers: **"What's the overall health?"** and **"Where do I look?"**

```
┌──────────────────────┐
│ PR #10               │
│ Decision persistence │
│ +338/-7 · 6 files    │
│                      │
│ ┌──────────────────┐ │
│ │  ✓  READY        │ │  ← Verdict badge: green/yellow/red
│ └──────────────────┘ │     background fills the full width
│                      │
│ ── Gates ──────────  │
│ G0 Adversarial  ✓    │  ← Each gate is a row: name + icon
│ G1 Deterministic ✓   │     Click → scrolls main pane to
│ G2 NFR           —   │     Convergence section
│ G3 Scenarios     —   │
│                      │
│ ── Metrics ────────  │
│ CI        4/4   ✓    │  ← Click → scrolls to CI Performance
│ Scenarios  N/A  —    │
│ Comments  2/2   ✓    │
│ Findings    0   ✓    │  ← "0" = no critical/warning from agents
│                      │
│ ── Zones ──────────  │
│ ┌────────────────┐   │
│ │ ■ Factory  (5) │   │  ← Mini zone map: colored squares
│ │ □ Env          │   │     ■ = modified (has files in diff)
│ │ □ RL Core      │   │     □ = unmodified
│ │ □ Agent        │   │     Click zone → filters main pane
│ │ □ Training     │   │     Click again → clears filter
│ │ □ Observ.      │   │
│ │ □ Dashboard    │   │     Synced with full architecture
│ │ □ Tests        │   │     diagram in main pane. Clicking
│ │ ■ Config   (1) │   │     either one updates both.
│ │ □ Docker       │   │
│ └────────────────┘   │
│  Active: (none)      │  ← Shows "Factory" when filtered
│  [Clear filter]      │
│                      │
│ ── Sections ───────  │
│ ● Architecture       │  ← ● = dot indicator
│ ● What Changed       │     Blue dot = has content
│ ● Agent Reviews      │     Red dot = has findings
│   Key Decisions      │     No dot = empty/N/A
│ ● Convergence        │
│   Post-Merge (2)     │  ← Count badge for items
│   ─────────────      │
│   Code Diffs (6)     │  ← Below the line = low tier
│   Factory History    │
│                      │
│ HEAD: babed4d        │
│ 2026-02-27           │
└──────────────────────┘
```

**Sidebar behaviors:**
- Fixed position, does not scroll with main pane
- Clicking a gate row scrolls main pane to Convergence section
- Clicking a metric row scrolls main pane to that section (CI, Scenarios, etc.)
- Clicking a zone in the mini-map filters ALL main pane sections to that zone
- Clicking a section name scrolls main pane to that section
- Section dots indicate: blue (has content), red (has findings/warnings), none (empty)
- On viewport < 1200px: sidebar collapses to a top bar (verdict + gates + zone pills)
- On viewport < 768px: top bar collapses further to just verdict badge + hamburger

### Main Pane (Scrollable Content)

The main pane is where drill-down happens. Sections are ordered by tier:

```
┌─────────────────────────────────────────────────────────────┐
│                                                             │
│  ═══ TIER 1: Architecture & Context ═══                     │
│                                                             │
│  Architecture                                          ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │                                                   │      │
│  │   [Full SVG diagram — same as today]              │      │
│  │   Zones clickable, arrows, file count badges      │      │
│  │   Update / Baseline toggle                        │      │
│  │                                                   │      │
│  └───────────────────────────────────────────────────┘      │
│  Click a zone to filter all sections below ↓                │
│                                                             │
│  What Changed                                          ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ Infrastructure: New decision persistence script..  │      │
│  │ Product: No product code changes.                  │      │
│  │                                                    │      │
│  │ (When zone is active: shows zone-specific detail)  │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Specs & Scenarios                                     ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ Specs: docs/dark_factory.md                        │      │
│  │ Scenarios: N/A (factory internals PR)              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  ═══ TIER 2: Safety & Reasoning ═══                         │
│                                                             │
│  Agent Reviews                              Grade: A   ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ FILE              GRADE  ZONE     NOTABLE          │      │
│  │ persist_dec...py    A    factory  Clean script...   │      │
│  │   └─ [expanded detail if clicked]                  │      │
│  │ decision_log.json   A    factory  Well-structured.. │      │
│  │ SKILL.md            A    factory  Clean addition..  │      │
│  │ factory_fix.md      A    factory  Fixed contradict..│      │
│  │ CLAUDE.md           A    factory  Minimal additions │      │
│  │ Makefile            A    config   Simple target..   │      │
│  │                                                     │      │
│  │ When zone filtered: non-matching rows dim/collapse  │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Key Decisions                                    (3)  ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ 1  Single JSON file > ADRs                         │      │
│  │    Decisions are small machine-generated records... │      │
│  │    └─ [expanded: full body, zone tags, files]      │      │
│  │                                                     │      │
│  │ 2  Codex reads the decision log                    │      │
│  │    Architectural context, not eval criteria...     │      │
│  │                                                     │      │
│  │ 3  Read-only vs prohibited in Codex prompt         │      │
│  │    Pre-existing contradiction fixed...              │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Convergence                                          ▼     │
│  ┌─────────────────────┬─────────────────────┐              │
│  │ G0 Adversarial      │ G1 Deterministic    │              │
│  │ CLEAN               │ ALL PASS            │              │
│  │ 6 files, all A      │ 4/4 CI checks       │              │
│  ├─────────────────────┼─────────────────────┤              │
│  │ G2 NFR              │ G3 Scenarios        │              │
│  │ N/A                 │ N/A                 │              │
│  ├─────────────────────┴─────────────────────┤              │
│  │ Overall: READY                            │              │
│  │ Factory-internal PR. CI green.            │              │
│  └───────────────────────────────────────────┘              │
│                                                             │
│  ═══ TIER 3: Follow-ups & Evidence ═══                      │
│                                                             │
│  CI Performance                                        ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ factory-self-test (push)   pass   17s  normal     │      │
│  │ factory-self-test (PR)     pass   19s  normal     │      │
│  │ validate (push)            pass  5m33  ⚠ watch    │      │
│  │ validate (PR)              pass  5m38  ⚠ watch    │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Post-Merge Items                                 (2)  ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ LOW  Phase 2: Cross-PR context in review packs    │      │
│  │ LOW  Phase 3: Lifecycle management                │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Code Diffs                                      (6)  ▼    │
│  ┌───────────────────────────────────────────────────┐      │
│  │ scripts/persist_decisions.py         +222  added  │      │
│  │ docs/decisions/decision_log.json      +53  added  │      │
│  │ .claude/skills/.../SKILL.md           +29  mod    │      │
│  │ .github/codex/prompts/factory_fix.md   +6  mod    │      │
│  │ CLAUDE.md                              +3  mod    │      │
│  │ Makefile                               +4  mod    │      │
│  │                                                    │      │
│  │ Click file → expands inline diff viewer            │      │
│  │ (side-by-side / unified / raw tabs)                │      │
│  └───────────────────────────────────────────────────┘      │
│                                                             │
│  Factory History                                       ▼    │
│  (null for non-factory PRs)                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Interaction Model

### 1. Zone Filtering (Cross-Component)

**Trigger:** Click a zone in the sidebar mini-map OR in the full architecture diagram.

**Effect on all components:**
- Architecture: clicked zone highlighted, others dimmed (same as today)
- Sidebar mini-map: clicked zone gets bold border, synced with main diagram
- What Changed: switches from default summary to zone-specific detail
- Agent Reviews: non-matching rows collapse/dim (same as today)
- Key Decisions: only decisions tagged with that zone remain visible
- Scenarios: cards for that zone get highlight glow
- CI Performance: no change (CI jobs are cross-zone)
- Code Diffs: only files in that zone's path patterns remain visible
- Sidebar "Active: Factory" label updates, "[Clear filter]" appears

**Clear:** Click the same zone again, click background, or click "[Clear filter]" in sidebar.

### 2. Drill-Down (In-Place Expansion)

Every item in the main pane is expandable:

| Component | Collapsed state | Expanded state |
|-----------|----------------|----------------|
| Agent review row | File, grade, zone, one-line notable | + full detail paragraph, code refs |
| Decision card | Number, title, one-line rationale | + full body, zone tags, file table |
| CI check row | Name, status, time, health tag | + sub-checks, zone coverage, notes |
| Convergence gate | Name, status text, one-line summary | + full detail HTML |
| Post-merge item | Priority tag, title | + description, code snippet, failure/success scenarios |
| Code diff file | Filename, +/- stats, status | + inline diff viewer (side-by-side/unified/raw) |
| Scenario card | Name, category, status | + what/how/result detail |

**Pattern:** Click row → toggles `.open` class → detail section appears below. Multiple items can be open simultaneously. Clicking an open item closes it.

### 3. Sidebar Navigation

Clicking a section name in the sidebar nav smooth-scrolls the main pane to that section. The nav item gets an "active" indicator based on scroll position (intersection observer).

### 4. Section Collapse

Each tier header ("TIER 1: Architecture & Context") and each section within it has a collapse chevron. Collapsing a tier collapses all sections in it. Collapsing an individual section collapses just that section.

## Information Tiers

| Tier | Label | Sections | Purpose |
|------|-------|----------|---------|
| Sidebar | Health dashboard | Verdict, gates, metrics, zone map, nav | Always-visible context — never scroll away from this |
| 1 | Architecture & Context | Architecture, What Changed, Specs & Scenarios | What was this PR about? Where did it touch? |
| 2 | Safety & Reasoning | Agent Reviews, Key Decisions, Convergence | Is it safe? What reasoning supports the changes? |
| 3 | Follow-ups & Evidence | CI Performance, Post-Merge, Code Diffs, Factory History | Supporting evidence and next steps |

## Agent Reviews: Team View (Future)

When the adversarial review becomes a team of agents, the Agent Reviews section evolves:

```
  Agent Reviews                              Grade: A   ▼
  ┌───────────────────────────────────────────────────┐
  │ ── Deterministic Agents ──                         │
  │ 🔧 ruff         ✓ pass   0 findings               │
  │ 🔧 radon        ✓ pass   0 findings               │
  │ 🔧 vulture      ✓ pass   0 findings               │
  │ 🔧 bandit       ✓ pass   0 findings               │
  │ 🔧 test-quality ✓ pass   0 findings               │
  │                                                     │
  │ ── Agentic Reviewers ──                            │
  │ 🤖 semantic-reviewer    Grade: A   (6 files)       │
  │    └─ [expand: per-file grades + findings]         │
  │ 🤖 architecture-reviewer Grade: A  (2 zones)      │
  │    └─ [expand: zone coherence assessment]          │
  │ 🤖 spec-compliance      Grade: A   (1 spec)       │
  │    └─ [expand: spec-to-implementation mapping]     │
  │                                                     │
  │ Combined: 5 tool checks + 3 agentic reviews        │
  │ 0 critical · 0 warnings · 0 nits                   │
  └───────────────────────────────────────────────────┘
```

The deterministic agents (ruff, vulture, etc.) show as simple pass/fail rows.
The agentic reviewers (LLM-based) show as expandable cards with their own grading.
Both feed into the same combined findings count in the sidebar.

## Responsive Behavior

| Viewport | Sidebar | Main pane | Architecture |
|----------|---------|-----------|--------------|
| ≥1200px | Full sidebar (260px fixed left) | Remaining width, scrollable | Full SVG in main pane + mini-map in sidebar |
| 900-1199px | Collapsed sidebar (verdict + gates + zone pills as top bar) | Full width below top bar | Full SVG in main pane, no mini-map |
| <900px | Verdict badge + hamburger menu (opens overlay sidebar) | Full width | Compact SVG, no mini-map |

## Key Differences from v1

| Aspect | v1 (Current) | v2 (Mission Control) |
|--------|-------------|---------------------|
| Health visibility | Header badges (scroll away) | Persistent sidebar (always visible) |
| Navigation | Scroll + collapsible sections | Sidebar nav + smooth scroll + tiers |
| Architecture | First section, floats when scrolled | Full in main pane + mini-map in sidebar (always visible) |
| Zone filtering | Click zone in diagram | Click zone in sidebar OR diagram (synced) |
| Information hierarchy | Flat (all sections equal weight) | 3 explicit tiers with labeled dividers |
| Code diffs | File modal (overlay) | Inline expansion in Tier 3 (de-prioritized but accessible) |
| Agent reviews | Single adversarial review table | Split: deterministic tools + agentic reviewers |
| Verdict | Inferred from badges | Explicit computed verdict badge in sidebar |
| Drill-down | Mixed (modals, toggles, expandable rows) | Consistent: always expand in-place |
