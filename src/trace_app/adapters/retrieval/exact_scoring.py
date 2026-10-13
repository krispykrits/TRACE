"""Adapted Volume 4 technical TF-IDF, normalized dense encoder and exact scores."""

from __future__ import annotations

import re

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

_TOKEN = re.compile(r"/[\w/.-]+|[\w]+(?:[._:-][\w]+)*", re.UNICODE)


def technical_tokens(text: str) -> list[str]:
    return _TOKEN.findall(text.lower())


def lexical_scores(texts: list[str], query: str) -> tuple[float, ...]:
    """Fit only currently authorized passages: denied documents cannot affect IDF."""
    if not any(technical_tokens(text) for text in texts):
        return tuple(0.0 for _ in texts)
    vectorizer = TfidfVectorizer(
        tokenizer=technical_tokens,
        token_pattern=None,
        lowercase=False,
        ngram_range=(1, 2),
        sublinear_tf=True,
        dtype=np.float32,
    )
    matrix = vectorizer.fit_transform(texts)
    q = vectorizer.transform([query])
    return tuple(float(value) for value in (matrix @ q.T).toarray().ravel())


def dense_scores(
    vectors: tuple[tuple[float, ...], ...], query: tuple[float, ...]
) -> tuple[float, ...]:
    return tuple(
        float(value)
        for value in (
            np.asarray(vectors, dtype=np.float32) @ np.asarray(query, dtype=np.float32)
        )
    )


class LocalExactScorer:
    """Numerical implementation of TRACE's score port; preserves existing ranking."""

    def lexical_scores(self, texts: list[str], query: str) -> tuple[float, ...]:
        return lexical_scores(texts, query)

    def dense_scores(
        self, vectors: tuple[tuple[float, ...], ...], query: tuple[float, ...]
    ) -> tuple[float, ...]:
        return dense_scores(vectors, query)
