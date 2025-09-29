# FAILED
# --- file: semantic_search.py
"""SemanticSearch: load multiple CSVs (or DataFrames) and run semantic search across *all* text columns.

Usage example
-------------
>>> from semantic_search import SemanticSearch
>>> searcher = SemanticSearch(["offers.csv", "grants.csv"])  # or list of DataFrames
>>> hits = searcher.search("program officer tunisia", top_k=5)
>>> print(hits[["title_en", "score"]])

Dependencies: `pandas`, `numpy`, `sentence-transformers` (and its Torch deps).
"""

# from __future__ import annotations

import io
from typing import List, Union

import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer


class SemanticSearch:
    """Load CSVs ➜ build embeddings ➜ cosine‑similarity search."""

    def __init__(
        self,
        csv_sources: List[Union[str, pd.DataFrame]],
        model_name: str = "sentence-transformers/all-MiniLM-L6-v2",
    ) -> None:
        """Create the search index.

        Parameters
        ----------
        csv_sources
            A list containing either file *paths* to CSVs **or** pre‑loaded
            ``pandas.DataFrame`` objects.
        model_name
            The Sentence‑Transformers model to use (defaults to the small but
            effective *all‑MiniLM‑L6‑v2*).
        """
        self.model = SentenceTransformer(model_name)

        # -------- load & concatenate --------
        dfs: List[pd.DataFrame] = []
        for src in csv_sources:
            if isinstance(src, pd.DataFrame):
                dfs.append(src.copy())
            elif isinstance(src, str):
                dfs.append(pd.read_csv(src))
            else:
                raise TypeError(
                    f"Unsupported CSV source type {type(src)}. Provide a file path or a DataFrame."
                )

        if not dfs:
            raise ValueError("No CSV data provided.")

        self.df = pd.concat(dfs, ignore_index=True).fillna("")

        # -------- combine text columns --------
        self.text_columns: List[str] = (
            self.df.select_dtypes(include="object").columns.tolist()
        )
        self._corpus: List[str] = (
            self.df[self.text_columns].astype(str).agg(" ".join, axis=1).tolist()
        )

        # -------- pre‑compute embeddings --------
        self._embeddings: np.ndarray = self.model.encode(
            self._corpus,
            convert_to_numpy=True,
            normalize_embeddings=True,  # L2‑normalize so dot = cosine
            show_progress_bar=False,
        )

    # ---------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------
    def search(self, query: str, top_k: int = 10) -> pd.DataFrame:
        """Return *top_k* most similar rows to *query* (highest cosine score)."""
        if not query:
            raise ValueError("Query string is empty.")

        query_vec: np.ndarray = self.model.encode(
            query, convert_to_numpy=True, normalize_embeddings=True
        )

        scores: np.ndarray = np.dot(self._embeddings, query_vec)

        k = min(top_k, len(scores))
        idx = np.argpartition(-scores, range(k))[:k]

        hits = self.df.iloc[idx].copy()
        hits["score"] = scores[idx]
        return hits.sort_values("score", ascending=False).reset_index(drop=True)
