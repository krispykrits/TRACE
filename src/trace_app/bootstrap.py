"""Composition roots: only this boundary selects application adapters."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Callable

from trace_app.adapters.retrieval.exact_scoring import LocalExactScorer
from trace_app.adapters.tools.local import (
    LocalToolBackend,
    LocalToolSources,
    LoggingToolAudit,
)
from trace_app.demo.fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.demo.order_workflow import OrderWorkflow
from trace_app.investigation.tools import ToolPolicy, ToolScope, ToolSession
from trace_app.knowledge.index import IndexGeneration
from trace_app.knowledge.ports import CorpusReader, Encoder
from trace_app.knowledge.search import SearchService


def create_tool_session(
    *,
    evidence_db: Path,
    corpus_db: Path,
    index_root: Path,
    scope: ToolScope,
    policy: ToolPolicy = ToolPolicy(),
    read_clock: Callable[[], datetime] | None = None,
) -> ToolSession:
    return ToolSession(
        LocalToolBackend(
            LocalToolSources(evidence_db, corpus_db, index_root), read_clock=read_clock
        ),
        scope,
        LoggingToolAudit(),
        policy,
    )


def create_search_service(
    reader: CorpusReader, index: IndexGeneration, encoder: Encoder | None = None
) -> SearchService:
    return SearchService(reader, index, encoder, scorer=LocalExactScorer())


def create_demo_order_workflow() -> OrderWorkflow:
    return OrderWorkflow(
        customers=CustomerFixture(),
        payments=PaymentFixture(),
        notifications=NotificationFixture(),
    )
