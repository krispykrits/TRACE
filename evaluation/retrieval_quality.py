"""Independent development passage ranking, review records and acceptance protocol.

Gold relevance/claim judgments stay evaluator-only. No generated answer is scored.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import sys
import tempfile
from contextlib import ExitStack
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from evaluation.scoring import SupportReview
from trace_app.corpus_sources import CorpusBatch, CuratedFileSource
from trace_app.corpus_store import SQLiteCorpusStore
from trace_app.evidence import _parse_utc, format_utc
from trace_app.knowledge import (
    CorpusAccessError,
    CorpusDependencyError,
    CorpusReadContext,
    _object,
    _text,
    canonical,
    chunk_document,
    digest,
    parse_json,
)
from trace_app.knowledge_context import CONTEXT_VERSION, ContextAssembler, ContextBudget
from trace_app.retrieval import SearchService
from trace_app.retrieval_backends import LocalSentenceEncoder
from trace_app.retrieval_contracts import EncoderFailure, SearchMode, SearchRequest
from trace_app.retrieval_index import build_index, load_index
from trace_app.structured_logging import configure_logging

SCORER_VERSION = "passage-retrieval-scorer.v3"
_ROOT = Path(__file__).resolve().parents[1]
_INPUT = _ROOT / "evaluation/retrieval"
_REVIEW_PATH = _INPUT / "reviews_v4.json"
_AT = datetime(2026, 10, 12, 12, tzinfo=UTC)
_READ_AT = _AT + timedelta(minutes=10)
_CONTEXT = CorpusReadContext(
    "local:knowledge-development",
    "test",
    ("order", "payment"),
    "development_reference",
    "2026-10-12T12:00:00Z",
)
_MODES: tuple[SearchMode, ...] = ("lexical", "semantic", "hybrid")


def read_json(path: Path, *, max_bytes: int = 2_000_000) -> Any:
    if path.is_symlink() or not path.is_file():
        raise ValueError("Evaluation inputs must be regular nonsymlink files.")
    with path.open("rb") as stream:
        value = stream.read(max_bytes + 1)
    if len(value) > max_bytes:
        raise ValueError("Evaluation input exceeds its byte bound.")
    return parse_json(value.decode("utf-8"))


def validate_suite(value: object) -> dict[str, Any]:
    suite: dict[str, Any] = _object(
        value,
        {
            "schema_version",
            "suite_version",
            "cohort",
            "judgment_kind",
            "corpus_version",
            "relevance_scope",
            "queries",
        },
        "retrieval suite",
    )
    if (
        suite["schema_version"] != "3"
        or suite["cohort"] != "development"
        or suite["judgment_kind"] != "agent_authored_proposal"
        or suite["relevance_scope"] != "eligible_passage_content"
    ):
        raise ValueError(
            "Only version 3 eligible-passage development proposals are supported."
        )
    _text(suite["suite_version"], "suite_version")
    _text(suite["corpus_version"], "corpus_version")
    queries = suite["queries"]
    if not isinstance(queries, list) or not 1 <= len(queries) <= 200:
        raise ValueError("Suite requires 1–200 development queries.")
    identities, texts = set(), set()
    for query in queries:
        _object(
            query,
            {
                "id",
                "family",
                "category",
                "query",
                "service",
                "stale_document_ids",
                "claim",
                "judgments",
            },
            "query",
        )
        for field in ("id", "family"):
            _text(query[field], field)
        SearchRequest(query["query"], service=query["service"])
        if query["service"] not in (None, "order", "payment"):
            raise ValueError("Query service must be inside fixed development grants.")
        if query["category"] not in (
            "answerable",
            "exact_code",
            "negation",
            "misleading",
            "service_ambiguity",
            "absent_knowledge",
            "stale_source",
        ):
            raise ValueError("Query category is unsupported.")
        if query["id"] in identities or query["query"] in texts:
            raise ValueError("Query IDs and text must be unique.")
        identities.add(query["id"])
        texts.add(query["query"])
        stale = query["stale_document_ids"]
        if (
            not isinstance(stale, list)
            or len(stale) > 6
            or len(set(stale)) != len(stale)
        ):
            raise ValueError("Stale source selection is invalid.")
        for identity in stale:
            _text(identity, "stale_document_id")
        if query["claim"] is not None:
            _text(query["claim"], "claim", 2_000)
        judgments = query["judgments"]
        if not isinstance(judgments, list) or len(judgments) > 20:
            raise ValueError("Passage judgments exceed their bound.")
        ids = set()
        for judgment in judgments:
            _object(
                judgment,
                {"chunk_id", "document_id", "section", "proposed_support", "claim"},
                "judgment",
            )
            if not isinstance(judgment["chunk_id"], str) or not re.fullmatch(
                r"chunk-[0-9a-f]{64}", judgment["chunk_id"]
            ):
                raise ValueError("Judgment chunk identity is invalid.")
            if judgment["chunk_id"] in ids:
                raise ValueError("Duplicate passage judgment.")
            ids.add(judgment["chunk_id"])
            for field in ("document_id", "section", "claim"):
                _text(judgment[field], field, 2_000)
            if judgment["proposed_support"] not in (
                "supported",
                "unsupported",
                "indeterminate",
            ):
                raise ValueError("Proposed claim-support verdict is invalid.")
    return suite


def review_targets(suite: dict[str, Any]) -> dict[str, str]:
    targets = {}
    for query in suite["queries"]:
        targets["relevance:" + query["id"]] = "relevance"
        for judgment in query["judgments"]:
            targets["support:" + query["id"] + ":" + judgment["chunk_id"]] = "support"
    return targets


def review_summary(suite: dict[str, Any], value: object) -> dict[str, Any]:
    data = _object(value, {"schema_version", "suite_sha256", "reviews"}, "reviews")
    if data["schema_version"] != "1" or data["suite_sha256"] != digest(
        canonical(suite)
    ):
        raise ValueError("Review version or suite hash differs.")
    if not isinstance(data["reviews"], list) or len(data["reviews"]) > 2_000:
        raise ValueError("Review list exceeds its bound.")
    targets = review_targets(suite)
    decisions: dict[str, set[str]] = {}
    unique = set()
    fixture_count = 0
    for value in data["reviews"]:
        review = SupportReview.from_dict(value)
        if review.claim_id not in targets:
            raise ValueError("Review references an unknown target.")
        key = (review.claim_id, review.reviewer_id, review.kind)
        if key in unique:
            raise ValueError("Duplicate reviewer decision.")
        unique.add(key)
        if review.kind == "fixture_expectation":
            fixture_count += 1
            continue
        decisions.setdefault(review.claim_id, set()).add(review.verdict)
    disagreements = sorted(
        target for target, verdicts in decisions.items() if len(verdicts) > 1
    )
    unreviewed = sorted(set(targets) - set(decisions))
    rejected_gold = sorted(
        target
        for target, kind in targets.items()
        if kind == "relevance"
        and target in decisions
        and decisions[target] != {"supported"}
    )
    determinate, unsupported = 0, 0
    for target, verdicts in decisions.items():
        if (
            targets[target] == "support"
            and len(verdicts) == 1
            and verdicts != {"indeterminate"}
        ):
            determinate += 1
            unsupported += verdicts == {"unsupported"}
    return {
        "required_targets": len(targets),
        "human_reviewed_targets": len(decisions),
        "unreviewed_targets": unreviewed,
        "disagreements": disagreements,
        "rejected_relevance_targets": rejected_gold,
        "fixture_review_records": fixture_count,
        "human_unsupported_claim_rate": {
            "numerator": unsupported,
            "denominator": determinate,
            "value": unsupported / determinate if determinate else None,
        },
        "complete": not unreviewed and not disagreements and not rejected_gold,
    }


def validate_protocol(
    value: object, suite: dict[str, Any], *, run_at: datetime
) -> dict[str, Any]:
    protocol: dict[str, Any] = _object(
        value,
        {
            "schema_version",
            "protocol_version",
            "suite_sha256",
            "approved_by",
            "approved_at",
            "candidate_k",
            "rerank_top_k",
            "primary_k",
            "secondary_k",
            "mode",
            "acceptance",
        },
        "protocol",
    )
    if (
        protocol["schema_version"] != "1"
        or protocol["protocol_version"] != "retrieval-acceptance.v3"
        or protocol["suite_sha256"] != digest(canonical(suite))
    ):
        raise ValueError("Protocol version or frozen suite hash differs.")
    _text(protocol["approved_by"], "approved_by")
    if _parse_utc(_text(protocol["approved_at"], "approved_at")) > run_at:
        raise ValueError("Threshold approval must precede the run.")
    if protocol["mode"] not in _MODES:
        raise ValueError("Acceptance mode is invalid.")
    for field in ("candidate_k", "rerank_top_k", "primary_k", "secondary_k"):
        if type(protocol[field]) is not int or not 1 <= protocol[field] <= 20:
            raise ValueError("Protocol K values must be integers from 1 to 20.")
    if (
        not protocol["rerank_top_k"]
        <= protocol["primary_k"]
        <= protocol["secondary_k"]
        <= protocol["candidate_k"]
    ):
        raise ValueError("Protocol K values are inconsistent.")
    thresholds: dict[str, Any] = _object(
        protocol["acceptance"],
        {"recall_at_5", "mrr_at_5", "recall_at_10", "minimum_evaluation_queries"},
        "acceptance",
    )
    if protocol["primary_k"] != 5 or protocol["secondary_k"] != 10:
        raise ValueError("This protocol's named thresholds require K=5 and K=10.")
    for field in ("recall_at_5", "mrr_at_5", "recall_at_10"):
        if (
            type(thresholds[field]) not in (int, float)
            or not math.isfinite(thresholds[field])
            or not 0 <= thresholds[field] <= 1
        ):
            raise ValueError("Acceptance thresholds require finite rates in [0,1].")
    if (
        type(thresholds["minimum_evaluation_queries"]) is not int
        or not 1 <= thresholds["minimum_evaluation_queries"] <= 200
    ):
        raise ValueError("Minimum evaluation query count is invalid.")
    return protocol


def _rate(numerator: float, denominator: int) -> dict[str, Any]:
    return {
        "numerator": numerator,
        "denominator": denominator,
        "value": numerator / denominator if denominator else None,
    }


def _verified_policy_exclusions(row: dict[str, Any], query: dict[str, Any]) -> int:
    checks = row.get("policy_checks", [])
    expected = set(query.get("stale_document_ids", []))
    if (
        not isinstance(checks, list)
        or len(checks) != len(expected)
        or {check["document_id"] for check in checks} != expected
    ):
        raise ValueError("Every expected source exclusion requires one policy check.")
    verified = 0
    for check in checks:
        ids = check["excluded_chunk_ids"]
        if (
            not isinstance(ids, list)
            or not ids
            or any(not isinstance(identity, str) for identity in ids)
            or len(set(ids)) != len(ids)
            or type(check["eligible_at_query_chunks"]) is not int
            or type(check["saved_citations_denied"]) is not int
        ):
            raise ValueError("Source-policy check observations are malformed.")
        verified += (
            check["reason"] == "freshness_expired"
            and _parse_utc(check["before_at"])
            < _parse_utc(check["fresh_until"])
            <= _parse_utc(check["query_at"])
            and check["eligible_at_query_chunks"] == 0
            and check["saved_citations_denied"] == len(ids)
            and not set(ids).intersection(row["chunk_ids"])
            and not set(ids).intersection(row.get("context_chunk_ids", []))
        )
    return verified


def score(
    suite: dict[str, Any],
    attempts: list[dict[str, Any]],
    *,
    modes: tuple[SearchMode, ...],
    ks: tuple[int, ...],
    candidate_k: int,
) -> dict[str, Any]:
    if (
        not modes
        or len(set(modes)) != len(modes)
        or any(mode not in _MODES for mode in modes)
    ):
        raise ValueError("Evaluation modes must be unique existing branches.")
    if (
        not ks
        or len(set(ks)) != len(ks)
        or any(type(k) is not int or not 1 <= k <= candidate_k <= 20 for k in ks)
    ):
        raise ValueError("Metric K values must lie within candidate K.")
    queries = {query["id"]: query for query in suite["queries"]}
    expected = {(mode, identity) for mode in modes for identity in queries}
    pairs = [(row["mode"], row["query_id"]) for row in attempts]
    if len(pairs) != len(set(pairs)) or set(pairs) != expected:
        raise ValueError("Every scheduled mode/query needs exactly one attempt.")
    output: dict[str, Any] = {}
    for mode in modes:
        rows = [row for row in attempts if row["mode"] == mode]
        policy_counts = {
            row["query_id"]: _verified_policy_exclusions(row, queries[row["query_id"]])
            for row in rows
        }
        by_k = {}
        for k in ks:
            recalls, reciprocal, absent_with_results, no_relevant, failures = (
                [],
                [],
                0,
                0,
                0,
            )
            for row in rows:
                ranks = row["chunk_ids"]
                if (
                    not isinstance(ranks, list)
                    or len(ranks) > candidate_k
                    or any(not isinstance(identity, str) for identity in ranks)
                    or len(set(ranks)) != len(ranks)
                ):
                    raise ValueError(
                        "Attempt ranks violate candidate bounds or uniqueness."
                    )
                if row["failure_code"] is not None:
                    _text(row["failure_code"], "failure_code")
                failed = (
                    row["failure_code"] is not None
                    or row["search_status"] not in ("ok", "no_results")
                    or row["context_status"] not in ("ok", "empty")
                    or policy_counts[row["query_id"]]
                    != len(queries[row["query_id"]].get("stale_document_ids", []))
                )
                failures += failed
                ranked = [] if failed else ranks[:k]
                relevant = {
                    judgment["chunk_id"]
                    for judgment in queries[row["query_id"]]["judgments"]
                }
                if relevant:
                    recalls.append(len(set(ranked) & relevant) / len(relevant))
                    reciprocal.append(
                        next(
                            (
                                1 / rank
                                for rank, identity in enumerate(ranked, 1)
                                if identity in relevant
                            ),
                            0.0,
                        )
                    )
                else:
                    no_relevant += 1
                    absent_with_results += bool(ranked)
            by_k[str(k)] = {
                "k": k,
                "passage_recall": _rate(sum(recalls), len(recalls)),
                "mrr": _rate(sum(reciprocal), len(reciprocal)),
                "no_relevant_queries": no_relevant,
                "no_relevant_queries_returning_candidates": absent_with_results,
            }
        output[mode] = {
            "attempts": len(rows),
            "failures": failures,
            "by_k": by_k,
            "policy_exclusions": {
                "expected": sum(
                    len(q.get("stale_document_ids", [])) for q in queries.values()
                ),
                "verified": sum(policy_counts.values()),
            },
        }
    return output


def acceptance_checks(
    protocol: dict[str, Any], metrics: dict[str, Any], count: int
) -> dict[str, bool]:
    rates = metrics[protocol["mode"]]["by_k"]
    thresholds = protocol["acceptance"]

    def meets(value, minimum):
        return value is not None and value >= minimum

    return {
        "source_policy_exclusions": metrics[protocol["mode"]]["policy_exclusions"][
            "verified"
        ]
        == metrics[protocol["mode"]]["policy_exclusions"]["expected"],
        "minimum_queries": count >= thresholds["minimum_evaluation_queries"],
        "recall_at_5": meets(
            rates["5"]["passage_recall"]["value"], thresholds["recall_at_5"]
        ),
        "mrr_at_5": meets(rates["5"]["mrr"]["value"], thresholds["mrr_at_5"]),
        "recall_at_10": meets(
            rates["10"]["passage_recall"]["value"], thresholds["recall_at_10"]
        ),
    }


class _FixedSource:
    def __init__(self, batch: CorpusBatch) -> None:
        self.batch = batch

    def load(self) -> CorpusBatch:
        return self.batch


def _validate_sources(suite: dict[str, Any]) -> CorpusBatch:
    batch = CuratedFileSource(_ROOT / "corpus/development").load()
    if suite["corpus_version"] != batch.corpus_version:
        raise ValueError("Query suite corpus version differs.")
    chunks = {
        chunk.chunk_id: chunk
        for document in batch.documents
        for chunk in chunk_document(document)
    }
    documents = {document.metadata.document_id for document in batch.documents}
    for query in suite["queries"]:
        if set(query["stale_document_ids"]) - documents:
            raise ValueError("Stale selection references an unknown source.")
        for judgment in query["judgments"]:
            chunk = chunks.get(judgment["chunk_id"])
            if (
                chunk is None
                or chunk.metadata.document_id != judgment["document_id"]
                or chunk.section != judgment["section"]
            ):
                raise ValueError("Judgment identity does not match the source passage.")
            if chunk.metadata.document_id in query["stale_document_ids"] or query[
                "service"
            ] not in (None, chunk.metadata.service):
                raise ValueError(
                    "Relevant passage is outside the case's allowed source selection."
                )
    return batch


def review_bundle(suite: dict[str, Any], *, reviews_path: Path = _REVIEW_PATH) -> str:
    batch = _validate_sources(suite)
    chunks = {
        chunk.chunk_id: chunk
        for doc in batch.documents
        for chunk in chunk_document(doc)
    }
    # Include nongold passages so reviewers can assess complete relevance sets.
    used = sorted(chunks)
    lines = [
        "# Passage relevance and claim-support review",
        "",
        "This is evaluator-only development material. All judgments below are agent-authored proposals, with no human sign-off yet.",
        "",
        "Suite SHA-256: `" + digest(canonical(suite)) + "`.",
        "",
        "Review every query's proposed relevant set, including empty sets, and each passage/claim verdict against the original quote and metadata. Record supported/unsupported/indeterminate decisions and rationales in "
        + reviews_path.name
        + " using the target IDs below. A relevance verdict of supported endorses the complete proposed relevant set; another verdict records a rejection/uncertainty. Claim verdicts concern the question-specific probe, not a generated answer. AI review findings and requests to revise these proposals do not establish human endorsement; actual human decisions must be recorded separately.",
        "",
        "The 100 requests are variants across 15 related development families over six fictional/curated references. They are not 100 independent incidents. Stale-source cases give the certificate reference a fixture freshness deadline of 12:05 UTC, index it at 12:00 and query at 12:10 on 2026-10-12. No held-out material is supplied.",
        "",
        "Relevance means eligible passage content directly addressing the question, not merely supporting a reused probe. An empty set does not mean policy metadata cannot answer a freshness question. Stale cases separately check before-expiry eligibility, query-time exclusion, the freshness deadline and saved-citation denial. Policy observations are evaluator-only and are not retrieved passage gold.",
        "",
        "## Original passages",
        "",
    ]
    for identity in used:
        chunk = chunks[identity]
        lines += [
            "### " + identity,
            "",
            "Document: `" + chunk.metadata.document_id + "`; section: " + chunk.section,
            "",
            "```json",
            json.dumps(chunk.metadata.to_dict(), indent=2),
            "```",
            "",
            "Original offsets: "
            + str(chunk.start_offset)
            + "–"
            + str(chunk.end_offset)
            + ".",
            "",
        ]
        lines += ["> " + line for line in chunk.text.splitlines()] + [""]
    lines += ["## Review targets", ""]
    for query in suite["queries"]:
        lines += [
            "### " + query["id"],
            "",
            "Query: " + query["query"],
            "",
            "Family/category: "
            + query["family"]
            + " / "
            + query["category"]
            + "; service filter: "
            + str(query["service"])
            + ".",
            "",
            "Relevance target: `relevance:" + query["id"] + "`.",
            "",
            "Policy exclusion expectation: "
            + (
                ", ".join(query["stale_document_ids"])
                + "; freshness_expired at 12:10 UTC after the 12:05 deadline; eligible at 12:04, then excluded and saved citations denied."
                if query["stale_document_ids"]
                else "none"
            ),
            "",
            "Proposed relevant passages: "
            + (
                ", ".join("`" + j["chunk_id"] + "`" for j in query["judgments"])
                or "none"
            )
            + ".",
            "",
        ]
        for judgment in query["judgments"]:
            lines += [
                "Claim target: `support:"
                + query["id"]
                + ":"
                + judgment["chunk_id"]
                + "`.",
                "",
                "Claim: " + judgment["claim"],
                "",
                "Proposed verdict: **" + judgment["proposed_support"] + "**.",
                "",
            ]
    return "\n".join(lines)


def _policy_checks(
    store: SQLiteCorpusStore, generation_id: str, stale_ids: tuple[str, ...]
) -> list[dict[str, Any]]:
    if not stale_ids:
        return []
    before_at = _AT + timedelta(minutes=4)
    before = store.read_chunks(
        context=_CONTEXT, at=before_at, generation_id=generation_id
    )
    current = store.read_chunks(
        context=_CONTEXT, at=_READ_AT, generation_id=generation_id
    )
    checks = []
    for identity in stale_ids:
        chunks = [c for c in before if c.metadata.document_id == identity]
        if not chunks:
            raise ValueError("Expected stale source was not eligible before expiry.")
        denied = 0
        for chunk in chunks:
            try:
                store.resolve(
                    generation_id, chunk.chunk_id, context=_CONTEXT, at=_READ_AT
                )
            except CorpusAccessError:
                denied += 1
        checks.append(
            {
                "document_id": identity,
                "reason": "freshness_expired",
                "before_at": format_utc(before_at),
                "fresh_until": chunks[0].metadata.fresh_until,
                "query_at": format_utc(_READ_AT),
                "excluded_chunk_ids": [c.chunk_id for c in chunks],
                "eligible_at_query_chunks": sum(
                    c.metadata.document_id == identity for c in current
                ),
                "saved_citations_denied": denied,
            }
        )
    return checks


def run(
    suite: dict[str, Any],
    reviews: dict[str, Any],
    protocol: dict[str, Any],
    *,
    modes: tuple[SearchMode, ...],
    acceptance: bool,
    max_chunks_per_document: int = 20,
) -> dict[str, Any]:
    started_at = datetime.now(UTC)
    if (
        not modes
        or len(set(modes)) != len(modes)
        or any(mode not in _MODES for mode in modes)
    ):
        raise ValueError("Evaluation modes must be unique existing branches.")
    SearchRequest(
        "configuration validation",
        protocol["candidate_k"],
        candidate_pool=protocol["candidate_k"],
        max_chunks_per_document=max_chunks_per_document,
    )
    validate_protocol(protocol, suite, run_at=started_at)
    review = review_summary(suite, reviews)
    if acceptance:
        if not review["complete"]:
            raise ValueError(
                "Acceptance requires completed human relevance/claim reviews before execution."
            )
        if (
            len(suite["queries"]) < protocol["acceptance"]["minimum_evaluation_queries"]
            or protocol["mode"] not in modes
        ):
            raise ValueError(
                "Acceptance requires the minimum query count and selected mode."
            )
    batch = _validate_sources(suite)
    encoder = None
    encoder_failure = False
    if any(mode != "lexical" for mode in modes):
        try:
            encoder = LocalSentenceEncoder()
        except EncoderFailure:
            encoder_failure = True
    attempts = []
    with (
        tempfile.TemporaryDirectory(prefix="trace-passage-evaluation-") as directory,
        ExitStack() as stack,
    ):
        root = Path(directory)
        states: dict[tuple[str, ...], tuple[Any, ...]] = {}
        for query in suite["queries"]:
            state_key = tuple(sorted(query["stale_document_ids"]))
            case_batch = CorpusBatch(
                batch.corpus_version,
                tuple(
                    replace(
                        document,
                        metadata=replace(
                            document.metadata,
                            version="1.0.0-stale-fixture",
                            fresh_until="2026-10-12T12:05:00Z",
                        ),
                    )
                    if document.metadata.document_id in query["stale_document_ids"]
                    else document
                    for document in batch.documents
                ),
            )
            if state_key not in states:
                # IDs are bookkeeping, never path components from unchecked external text.
                case_root = root / digest(canonical(state_key))
                case_root.mkdir(mode=0o700)
                store = stack.enter_context(
                    SQLiteCorpusStore(case_root / "corpus.sqlite3")
                )
                corpus, _ = store.ingest(
                    _FixedSource(case_batch),
                    at=_AT,
                    retain_until="2026-10-14T12:00:00Z",
                )
                chunks = store.read_chunks(context=_CONTEXT, at=_AT)
                build_failure = False
                try:
                    build_index(
                        case_root / "index", corpus, chunks, at=_AT, encoder=encoder
                    )
                    index = load_index(case_root / "index", encoder=encoder)
                except (EncoderFailure, ValueError):
                    # Preserve explicit dense failure; an explicit lexical branch can still run.
                    build_failure = True
                    build_index(case_root / "lexical", corpus, chunks, at=_AT)
                    index = load_index(case_root / "lexical")
                states[state_key] = (store, corpus, index, build_failure)
            store, corpus, index, build_failure = states[state_key]
            policy_checks = _policy_checks(store, corpus.generation_id, state_key)
            service = SearchService(store, index, encoder)
            assembler = ContextAssembler(store)
            for mode in modes:
                if mode != "lexical" and (encoder_failure or build_failure):
                    attempts.append(
                        {
                            "mode": mode,
                            "query_id": query["id"],
                            "failure_code": "encoder_unavailable",
                            "chunk_ids": [],
                            "search_status": "provider_failure",
                            "context_status": "retrieval_failed",
                            "policy_checks": policy_checks,
                        }
                    )
                    continue
                response = service.search(
                    SearchRequest(
                        query["query"],
                        protocol["candidate_k"],
                        mode,
                        query["service"],
                        candidate_pool=protocol["candidate_k"],
                        max_chunks_per_document=max_chunks_per_document,
                    ),
                    context=_CONTEXT,
                    at=_READ_AT,
                )
                assembled = assembler.assemble(
                    response,
                    context=_CONTEXT,
                    at=_READ_AT,
                    budget=ContextBudget(max_passages=protocol["rerank_top_k"]),
                )
                details = assembled.to_dict()
                failure = None
                if response.status not in (
                    "ok",
                    "no_results",
                ) or assembled.status not in ("ok", "empty"):
                    failure = response.reason or assembled.status
                attempts.append(
                    {
                        "mode": mode,
                        "query_id": query["id"],
                        "failure_code": failure,
                        "search_status": response.status,
                        "context_status": assembled.status,
                        "policy_checks": policy_checks,
                        "chunk_ids": [
                            result.chunk.chunk_id for result in response.results
                        ],
                        "corpus_generation_id": corpus.generation_id,
                        "index_generation_id": index.index_id,
                        "eligible_chunks": response.eligible_chunks,
                        "context_bytes": assembled.used_bytes,
                        "context_omitted": details["omitted"],
                        "context_chunk_ids": [
                            mapping["chunk_id"]
                            for mapping in json.loads(assembled.serialized_data)[
                                "citations"
                            ].values()
                        ],
                    }
                )
    metrics = score(
        suite,
        attempts,
        modes=modes,
        ks=(protocol["primary_k"], protocol["secondary_k"]),
        candidate_k=protocol["candidate_k"],
    )
    checks = (
        acceptance_checks(protocol, metrics, len(suite["queries"]))
        if protocol["mode"] in modes
        else None
    )
    sources = [
        "evaluation/retrieval_quality.py",
        "evaluation/scoring.py",
        "src/trace_app/knowledge_context.py",
        "src/trace_app/retrieval.py",
        "src/trace_app/retrieval_index.py",
        "src/trace_app/retrieval_contracts.py",
        "src/trace_app/retrieval_backends.py",
        "src/trace_app/knowledge.py",
        "src/trace_app/corpus_store.py",
        "src/trace_app/corpus_sources.py",
        "uv.lock",
        "corpus/development/manifest.json",
    ]
    configuration = {
        "modes": modes,
        "context_version": CONTEXT_VERSION,
        "embedding": encoder.spec.to_dict() if encoder else None,
        "candidate_k": protocol["candidate_k"],
        "primary_k": protocol["primary_k"],
        "secondary_k": protocol["secondary_k"],
        "rerank_top_k": protocol["rerank_top_k"],
        "max_chunks_per_document": max_chunks_per_document,
        "reranker": None,
        "context_max_bytes": 8_192,
        "paid_calls": 0,
    }
    inputs = {
        "suite": suite,
        "reviews": reviews,
        "protocol": protocol,
        "attempts": attempts,
        "configuration": configuration,
    }
    return {
        "schema_version": "1",
        "scorer_version": SCORER_VERSION,
        "created_at": format_utc(started_at),
        "purpose": "acceptance" if acceptance else "exploration",
        **inputs,
        "input_sha256": {
            name: digest(canonical(data)) for name, data in inputs.items()
        },
        "source_sha256": {
            path: hashlib.sha256((_ROOT / path).read_bytes()).hexdigest()
            for path in sources
        },
        "metrics": metrics,
        "human_review": review,
        "threshold_comparison": checks,
        "acceptance_status": ("passed" if checks and all(checks.values()) else "failed")
        if acceptance
        else "not_run",
        "limitations": [
            "Agent-authored proposals require owner passage/claim review.",
            "100 requests span 15 related families, not 100 independent incidents.",
            "Six development documents; top-10 may saturate the one-passage-per-document baseline.",
            "Ranks are not answerability, confidence or causal support; absent/stale matches are reported separately.",
        ],
    }


def rescore(report: dict[str, Any]) -> dict[str, Any]:
    if report["schema_version"] != "1" or report["scorer_version"] != SCORER_VERSION:
        raise ValueError("Saved scorer version differs.")
    if (
        report["source_sha256"]["evaluation/retrieval_quality.py"]
        != hashlib.sha256(Path(__file__).read_bytes()).hexdigest()
    ):
        raise ValueError("Saved scorer implementation differs.")
    for name in ("suite", "reviews", "protocol", "attempts", "configuration"):
        if report["input_sha256"][name] != digest(canonical(report[name])):
            raise ValueError("Saved input hash mismatch.")
    suite = validate_suite(report["suite"])
    protocol = validate_protocol(
        report["protocol"], suite, run_at=_parse_utc(report["created_at"])
    )
    review = review_summary(suite, report["reviews"])
    if report["purpose"] not in ("exploration", "acceptance"):
        raise ValueError("Saved run purpose is invalid.")
    if report["purpose"] == "acceptance" and not review["complete"]:
        raise ValueError("Saved acceptance requires completed human reviews.")
    metrics = score(
        suite,
        report["attempts"],
        modes=tuple(report["configuration"]["modes"]),
        ks=(protocol["primary_k"], protocol["secondary_k"]),
        candidate_k=protocol["candidate_k"],
    )
    if metrics != report["metrics"] or review != report["human_review"]:
        raise ValueError("Saved score or review summary disagrees with inputs.")
    checks = (
        acceptance_checks(protocol, metrics, len(suite["queries"]))
        if protocol["mode"] in metrics
        else None
    )
    expected = (
        "not_run"
        if report["purpose"] == "exploration"
        else (
            "passed"
            if checks and all(checks.values()) and review["complete"]
            else "failed"
        )
    )
    if (
        checks != report["threshold_comparison"]
        or expected != report["acceptance_status"]
    ):
        raise ValueError("Saved acceptance state disagrees with protocol/reviews.")
    return metrics


def _write_new(path: Path, content: str) -> None:
    with os.fdopen(
        os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW, 0o600), "w"
    ) as stream:
        stream.write(content + "\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--suite", type=Path, default=_INPUT / "queries_v4.json")
    parser.add_argument("--reviews", type=Path, default=_REVIEW_PATH)
    parser.add_argument("--protocol", type=Path, default=_INPUT / "acceptance_v3.json")
    parser.add_argument("--modes", nargs="+", choices=_MODES, default=list(_MODES))
    parser.add_argument("--max-chunks-per-document", type=int, default=20)
    operation = parser.add_mutually_exclusive_group()
    operation.add_argument("--acceptance", action="store_true")
    parser.add_argument("--output", type=Path)
    operation.add_argument("--review-bundle", type=Path)
    operation.add_argument("--rescore", type=Path)
    args = parser.parse_args(argv)
    configure_logging()
    try:
        if args.output and (args.rescore or args.review_bundle):
            raise ValueError("--output applies only to a new evaluation run.")
        for path in (args.output, args.review_bundle):
            if path and (path.exists() or path.is_symlink()):
                raise ValueError(
                    "Choose a new artifact path; existing files are never overwritten."
                )
        if args.rescore:
            metrics = rescore(read_json(args.rescore, max_bytes=10_000_000))
            print(json.dumps(metrics, sort_keys=True))
            return 0
        suite = validate_suite(read_json(args.suite))
        reviews, protocol = read_json(args.reviews), read_json(args.protocol)
        validate_protocol(protocol, suite, run_at=datetime.now(UTC))
        review_summary(suite, reviews)
        if args.review_bundle:
            _write_new(
                args.review_bundle, review_bundle(suite, reviews_path=args.reviews)
            )
            print(
                json.dumps(
                    {
                        "status": "review_pending",
                        "suite_sha256": digest(canonical(suite)),
                        "targets": len(review_targets(suite)),
                    }
                )
            )
            return 0
        if args.acceptance and not args.output:
            raise ValueError("Acceptance requires an exclusive saved report path.")
        report = run(
            suite,
            reviews,
            protocol,
            modes=tuple(args.modes),
            acceptance=args.acceptance,
            max_chunks_per_document=args.max_chunks_per_document,
        )
        if args.output:
            _write_new(args.output, json.dumps(report, indent=2, sort_keys=True))
        print(
            json.dumps(
                {
                    "metrics": report["metrics"],
                    "acceptance_status": report["acceptance_status"],
                    "human_review_complete": report["human_review"]["complete"],
                },
                sort_keys=True,
            )
        )
        return (
            2
            if report["acceptance_status"] == "failed"
            or any(row["failures"] for row in report["metrics"].values())
            else 0
        )
    except (
        ValueError,
        OSError,
        KeyError,
        TypeError,
        EncoderFailure,
        CorpusDependencyError,
    ) as error:
        print(json.dumps({"status": "error", "error": str(error)}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
