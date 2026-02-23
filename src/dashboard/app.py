from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(page_title="MiniPong RL Dashboard", layout="wide")
st.title("MiniPong RL Learning Dashboard")

base = Path("artifacts")
runs = sorted([p.name for p in base.glob("*") if p.is_dir()])
if not runs:
    st.warning("No runs found under artifacts/")
    st.stop()
run_id = st.selectbox("Run", runs)
run_dir = base / run_id

log_path = run_dir / "logs.jsonl"
if log_path.exists():
    rows = [
        json.loads(line)
        for line in log_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    df = pd.DataFrame(rows)
    st.subheader("Training metrics")
    cols = st.columns(3)
    with cols[0]:
        if "train/episode_return" in df:
            st.line_chart(df[["step", "train/episode_return"]].dropna().set_index("step"))
    with cols[1]:
        if "eval/mean_return" in df:
            st.line_chart(df[["step", "eval/mean_return"]].dropna().set_index("step"))
    with cols[2]:
        if "train/loss" in df:
            st.line_chart(df[["step", "train/loss"]].dropna().set_index("step"))
    if "train/epsilon" in df:
        st.subheader("Epsilon")
        st.line_chart(df[["step", "train/epsilon"]].dropna().set_index("step"))


st.subheader("Eval summaries")
eval_files = sorted((run_dir / "eval").glob("metrics_*.json"))
if eval_files:
    eval_rows = []
    for f in eval_files:
        d = json.loads(f.read_text(encoding="utf-8"))
        d["file"] = f.name
        eval_rows.append(d)
    edf = pd.DataFrame(eval_rows)
    st.dataframe(edf)
    if {"mean_hits", "mean_return"}.issubset(edf.columns):
        st.scatter_chart(edf[["mean_hits", "mean_return"]])

st.subheader("Videos")
for v in sorted((run_dir / "videos").glob("*.mp4")):
    st.write(v.name)
    st.video(str(v))
