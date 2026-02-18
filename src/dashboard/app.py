from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
st.title("MiniPong Learning Dashboard")

runs = sorted((Path("artifacts")).glob("*"))
if not runs:
    st.warning("No runs found in artifacts/")
    st.stop()

run_id = st.selectbox("Run", [r.name for r in runs])
run_dir = Path("artifacts") / run_id

logs_path = run_dir / "logs.jsonl"
rows = (
    [json.loads(line) for line in logs_path.read_text(encoding="utf-8").splitlines()]
    if logs_path.exists()
    else []
)
df = pd.DataFrame(rows)

if not df.empty:
    train_df = df[df["event"] == "train"]
    eval_df = df[df["event"] == "eval"]
    c1, c2 = st.columns(2)
    with c1:
        st.subheader("Loss")
        st.line_chart(train_df.set_index("step")["loss"])
        st.subheader("Epsilon")
        st.line_chart(train_df.set_index("step")["epsilon"])
    with c2:
        st.subheader("Eval Mean Return")
        st.line_chart(eval_df.set_index("step")["mean_return"])
        st.subheader("Hit Rate")
        st.line_chart(eval_df.set_index("step")["mean_hits"])
        st.subheader("Strategy proxy: rally vs return")
        st.scatter_chart(eval_df[["mean_rally_length", "mean_return"]])

st.subheader("Checkpoint Videos")
videos = sorted((run_dir / "videos").glob("*.mp4"))
for v in videos:
    st.write(v.name)
    st.video(str(v))
