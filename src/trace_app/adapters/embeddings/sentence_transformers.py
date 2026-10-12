"""Pinned cached CPU sentence encoder; no automatic downloads or fallback."""

from __future__ import annotations

import importlib.metadata
from typing import Any

import numpy as np

from trace_app.knowledge.ports import EncoderFailure, EncoderSpec, SearchInputError
from trace_app.knowledge.vectors import validate_vectors

MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
MODEL_REVISION = "ee8519ce6a28a61c9190da0a16e199d262197a1b"


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
