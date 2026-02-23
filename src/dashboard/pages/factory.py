"""Dark Factory — Satisfaction Dashboard.

Provides visibility into the factory convergence loop:
- Current satisfaction score
- Per-scenario pass/fail breakdown
- Convergence trajectory across iterations
- Category-level aggregation
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(
    page_title="Dark Factory — Satisfaction",
    layout="wide",
)
st.title("Dark Factory — Satisfaction Dashboard")

FACTORY_DIR = Path("artifacts/factory")
SCENARIOS_DIR = Path("scenarios")


# ── Helpers ──────────────────────────────────────────────────


def load_scenario_results() -> dict | None:
    """Load the latest scenario results JSON."""
    path = FACTORY_DIR / "scenario_results.json"
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def load_iteration_count() -> int:
    """Load the current iteration count."""
    path = FACTORY_DIR / "iteration_count.txt"
    if not path.exists():
        return 0
    try:
        return int(path.read_text(encoding="utf-8").strip())
    except ValueError:
        return 0


def load_feedback_history() -> list[dict]:
    """Parse satisfaction scores from all feedback files."""
    history = []
    for path in sorted(FACTORY_DIR.glob("feedback_iter_*.md")):
        match = re.search(r"feedback_iter_(\d+)\.md", path.name)
        if not match:
            continue
        iteration = int(match.group(1))
        text = path.read_text(encoding="utf-8")

        # Extract satisfaction score from feedback
        score_match = re.search(
            r"Satisfaction[:\s]+(\d+\.?\d*)%", text
        )
        score = float(score_match.group(1)) / 100 if score_match else 0

        # Extract pass/fail counts
        pass_match = re.search(r"(\d+)\s*/\s*(\d+)\s*pass", text)
        passed = int(pass_match.group(1)) if pass_match else 0
        total = int(pass_match.group(2)) if pass_match else 0

        history.append({
            "iteration": iteration,
            "satisfaction": score,
            "passed": passed,
            "total": total,
        })
    return history


def count_scenarios_by_category() -> dict[str, int]:
    """Count scenario files by category from the scenarios dir."""
    cats: dict[str, int] = {}
    if not SCENARIOS_DIR.exists():
        return cats
    for path in SCENARIOS_DIR.glob("*.md"):
        text = path.read_text(encoding="utf-8")
        cat_match = re.search(
            r"##\s*Category\s*\n+\s*(\w+)", text
        )
        cat = cat_match.group(1) if cat_match else "unknown"
        cats[cat] = cats.get(cat, 0) + 1
    return cats


# ── Main Dashboard ───────────────────────────────────────────


results = load_scenario_results()
iteration = load_iteration_count()
history = load_feedback_history()

if results is None and not history:
    st.info(
        "No factory data yet. Run `make factory-local` "
        "or trigger the factory workflow to generate data."
    )
    st.stop()

# ── Top-Level Metrics ────────────────────────────────────────

st.subheader("Current State")

col1, col2, col3, col4 = st.columns(4)

if results:
    score = results.get("satisfaction_score", 0.0)
    passed = results.get("passed", 0)
    total = results.get("total", 0)
    failed = results.get("failed", 0)

    col1.metric(
        "Satisfaction",
        f"{score:.0%}",
        delta=(
            f"+{score - history[-2]['satisfaction']:.0%}"
            if len(history) >= 2
            else None
        ),
    )
    col2.metric("Passed", f"{passed}/{total}")
    col3.metric("Failed", str(failed))
    col4.metric("Iteration", str(iteration))

    gate1_failed = results.get("gate1_failed", False)
    if gate1_failed:
        st.error(
            "Gate 1 (lint/typecheck/test) failed — "
            "scenarios were not evaluated."
        )
else:
    col1.metric("Satisfaction", "N/A")
    col2.metric("Passed", "N/A")
    col3.metric("Failed", "N/A")
    col4.metric("Iteration", str(iteration))

# ── Convergence Trajectory ───────────────────────────────────

if history:
    st.subheader("Convergence Trajectory")

    df_hist = pd.DataFrame(history)
    df_hist = df_hist.set_index("iteration")

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:
        st.line_chart(
            df_hist[["satisfaction"]],
            y="satisfaction",
            use_container_width=True,
        )
        st.caption("Satisfaction score per iteration")

    with chart_col2:
        st.bar_chart(
            df_hist[["passed", "total"]],
            use_container_width=True,
        )
        st.caption("Scenarios passed vs total per iteration")

# ── Per-Scenario Breakdown ───────────────────────────────────

if results and results.get("results"):
    st.subheader("Scenario Breakdown")

    scenario_data = []
    for r in results["results"]:
        scenario_data.append({
            "Scenario": r.get("name", "unknown"),
            "Category": r.get("category", "unknown"),
            "Status": "✅ Pass" if r.get("passed") else "❌ Fail",
            "Duration (s)": round(r.get("duration", 0), 1),
            "Error": (
                r.get("error", "")[:100]
                if not r.get("passed")
                else ""
            ),
        })

    df_scenarios = pd.DataFrame(scenario_data)

    # Category filter
    categories = ["All"] + sorted(
        df_scenarios["Category"].unique().tolist()
    )
    selected_cat = st.selectbox("Filter by category", categories)
    if selected_cat != "All":
        df_scenarios = df_scenarios[
            df_scenarios["Category"] == selected_cat
        ]

    # Color-code status
    st.dataframe(
        df_scenarios,
        use_container_width=True,
        hide_index=True,
    )

    # ── Category Aggregation ─────────────────────────────────

    st.subheader("Category Summary")

    all_results = results.get("results", [])
    cat_agg: dict[str, dict] = {}
    for r in all_results:
        cat = r.get("category", "unknown")
        if cat not in cat_agg:
            cat_agg[cat] = {"passed": 0, "total": 0}
        cat_agg[cat]["total"] += 1
        if r.get("passed"):
            cat_agg[cat]["passed"] += 1

    cat_rows = []
    for cat, counts in sorted(cat_agg.items()):
        pct = (
            counts["passed"] / counts["total"]
            if counts["total"] > 0
            else 0
        )
        cat_rows.append({
            "Category": cat,
            "Passed": counts["passed"],
            "Total": counts["total"],
            "Score": f"{pct:.0%}",
        })

    st.dataframe(
        pd.DataFrame(cat_rows),
        use_container_width=True,
        hide_index=True,
    )

# ── Scenario Coverage ────────────────────────────────────────

st.subheader("Scenario Coverage")

cat_counts = count_scenarios_by_category()
if cat_counts:
    cov_df = pd.DataFrame(
        [
            {"Category": k, "Scenarios": v}
            for k, v in sorted(cat_counts.items())
        ]
    )
    st.bar_chart(cov_df.set_index("Category"), use_container_width=True)
    st.caption(
        f"Total: {sum(cat_counts.values())} scenarios "
        f"across {len(cat_counts)} categories"
    )
else:
    st.info("No scenario files found in /scenarios/")

# ── Latest Feedback ──────────────────────────────────────────

feedback_files = sorted(FACTORY_DIR.glob("feedback_iter_*.md"))
if feedback_files:
    st.subheader("Latest Feedback")
    latest = feedback_files[-1]
    with st.expander(f"📄 {latest.name}", expanded=False):
        st.markdown(latest.read_text(encoding="utf-8"))
