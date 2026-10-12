"""Adapted Volume 4 technical TF-IDF, normalized dense encoder and exact scores."""

from __future__ import annotations

import importlib.metadata
import math
import re
from typing import Any

import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer

from trace_app.retrieval_contracts import EncoderFailure, EncoderSpec, SearchInputError

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "ee8519ce6a28a61c9190da0a16e199d262197a1b"
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


def validate_vectors(
    values: object, count: int, dimension: int
) -> tuple[tuple[float, ...], ...]:
    if not isinstance(values, (list, tuple)) or len(values) != count:
        raise EncoderFailure("Embedding row count is invalid.")
    vectors: list[tuple[float, ...]] = []
    for row in values:
        if not isinstance(row, (list, tuple)) or len(row) != dimension:
            raise EncoderFailure("Embedding dimension is invalid.")
        if any(
            type(number) not in (int, float) or not math.isfinite(number)
            for number in row
        ):
            raise EncoderFailure("Embedding values must be finite numbers.")
        vector = tuple(float(number) for number in row)
        if not math.isclose(
            math.sqrt(sum(number * number for number in vector)), 1.0, abs_tol=1e-4
        ):
            raise EncoderFailure("Embeddings must be unit normalized.")
        vectors.append(vector)
    return tuple(vectors)


def dense_scores(
    vectors: tuple[tuple[float, ...], ...], query: tuple[float, ...]
) -> tuple[float, ...]:
    return tuple(
        float(value)
        for value in (
            np.asarray(vectors, dtype=np.float32) @ np.asarray(query, dtype=np.float32)
        )
    )


class LocalSentenceEncoder:
    """Pinned CPU model, cached files only, no remote code or implicit truncation."""

    def __init__(self) -> None:
        try:
            import torch
            from sentence_transformers import SentenceTransformer

            torch.set_num_threads(4)
            self._model: Any = SentenceTransformer(
                MODEL_ID,
                revision=MODEL_REVISION,
                device="cpu",
                trust_remote_code=False,
                local_files_only=True,
                token=False,
            )
            self._model.max_seq_length = 256
            self.spec = EncoderSpec(
                MODEL_ID,
                MODEL_REVISION,
                384,
                256,
                "sentence-transformers.cpu.v1",
                tuple(
                    (name, importlib.metadata.version(name))
                    for name in (
                        "sentence-transformers",
                        "torch",
                        "transformers",
                        "tokenizers",
                        "huggingface-hub",
                    )
                ),
            )
            dimension_fn = getattr(self._model, "get_embedding_dimension", None)
            dimension = (
                dimension_fn()
                if dimension_fn
                else self._model.get_sentence_embedding_dimension()
            )
            if dimension != self.spec.dimension:
                raise EncoderFailure("Cached model dimension is incompatible.")
        except EncoderFailure:
            raise
        except Exception as error:
            raise EncoderFailure(
                "Install the locked semantic extra and cache the pinned MiniLM revision; no fallback is available."
            ) from error

    def encode(self, texts: list[str]) -> tuple[tuple[float, ...], ...]:
        if not texts:
            return ()
        try:
            for text in texts:
                encoded = self._model.tokenizer(
                    text, add_special_tokens=True, truncation=False
                )
                if len(encoded["input_ids"]) > self.spec.max_sequence_length:
                    raise SearchInputError(
                        "Text exceeds the pinned encoder context; rechunk or shorten it."
                    )
            values = (
                self._model.encode(
                    texts,
                    batch_size=32,
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                    show_progress_bar=False,
                )
                .astype(np.float32)
                .tolist()
            )
            return validate_vectors(values, len(texts), self.spec.dimension)
        except (EncoderFailure, SearchInputError):
            raise
        except Exception as error:
            raise EncoderFailure("Local embedding operation failed.") from error
