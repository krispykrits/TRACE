"""Framework-independent validation of normalized embedding vectors."""

from __future__ import annotations

import math

from trace_app.knowledge.ports import EncoderFailure


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
