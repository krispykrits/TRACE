"""Composition roots: only this boundary selects application adapters."""

from __future__ import annotations

from trace_app.adapters.retrieval.exact_scoring import LocalExactScorer
from trace_app.demo.fixtures import CustomerFixture, NotificationFixture, PaymentFixture
from trace_app.demo.order_workflow import OrderWorkflow
from trace_app.knowledge.index import IndexGeneration
from trace_app.knowledge.ports import CorpusReader, Encoder
from trace_app.knowledge.search import SearchService


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
