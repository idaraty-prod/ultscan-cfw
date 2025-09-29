# FAILED

# --- file: app.py
"""Streamlit interface for *SemanticSearch*.

Run with:
    streamlit run app.py
"""

# from __future__ import annotations

import io
from typing import List

import pandas as pd
import streamlit as st

from semantic_search import SemanticSearch

st.set_page_config(page_title="CSV Semantic Search", layout="wide")

st.title("🔍 CSV Semantic Search")
st.markdown(
    "Upload **one or more** CSV files, enter a search query, and see the most relevant rows (cosine similarity across all text columns)."
)

uploaded = st.file_uploader(
    "Upload CSV file(s)", type=["csv"], accept_multiple_files=True
)

# uploaded = [
#     'outputs/posts/posts-1752699138.csv'
# ]

if uploaded:
    # Read everything into DataFrames (handle UploadedFile.read → bytes)
    dfs: List[pd.DataFrame] = []
    for f in uploaded:
        # Reset pointer & get bytes
        bytes_data = f.read()
        df = pd.read_csv(io.StringIO(bytes_data.decode("utf-8")))
        dfs.append(df)

    # Build the searcher lazily (outside the loop to avoid re‑encoding)
    if "_searcher" not in st.session_state:
        with st.spinner("Building embeddings… this happens once per session"):
            st.session_state._searcher = SemanticSearch(dfs)
        st.success("Embeddings ready! Enter a query below.")

    query = st.text_input("Search query", placeholder="e.g. program officer tunisia")
    top_k = st.slider("Top‑K results", 1, 50, 10)

    if query:
        results = st.session_state._searcher.search(query, top_k=top_k)
        st.dataframe(results, use_container_width=True)
        st.caption(f"Showing {len(results)} match(es). Cosine‑similarity scores included.")
else:
    st.info("⬆️ Upload at least one CSV file to get started.")
