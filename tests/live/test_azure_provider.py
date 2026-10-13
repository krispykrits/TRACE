"""One explicitly authorized paid synthetic call through TRACE's actual adapter."""

from __future__ import annotations

import json
import os
import time
import unittest
from pathlib import Path

from trace_app.bootstrap import create_azure_model_provider_from_files
from trace_app.investigation.provider import ModelCallBounds
from trace_app.investigation.provider_policy import (
    AuthorizedEvidence,
    EvidenceField,
    EvidenceSelection,
    PromptTemplate,
    ProviderCall,
    ProviderScope,
    Sensitivity,
    SourceKind,
)


class SyntheticSmokeAuthority:
    """Test-only authority for owner-authorized synthetic evidence; no source handles."""

    def __init__(self, scope: ProviderScope) -> None:
        self.scope = scope
        self.evidence = AuthorizedEvidence(
            "azure-smoke-1",
            "trace-synthetic-smoke",
            "smoke.v1",
            SourceKind.SYNTHETIC,
            (
                EvidenceField(
                    "observation",
                    "Synthetic connector health check.",
                    Sensitivity.PUBLIC,
                    True,
                ),
            ),
            access_allowed=True,
            transmission_allowed=True,
            source_owner_allowed=True,
            identifiers_reviewed=True,
            expires_at=time.time() + 120,
        )

    def resolve(
        self, scope: ProviderScope, evidence_id: str
    ) -> AuthorizedEvidence | None:
        return (
            self.evidence
            if scope == self.scope and evidence_id == self.evidence.evidence_id
            else None
        )


@unittest.skipUnless(
    os.environ.get("TRACE_ALLOW_PAID_LIVE") == "1", "paid call requires explicit opt-in"
)
class AzureLiveProviderTests(unittest.TestCase):
    def test_one_policy_gated_synthetic_response(self) -> None:
        destination = Path(os.environ["TRACE_PROVIDER_REPORT_PATH"])
        if (
            not destination.parent.is_dir()
            or destination.is_symlink()
            or (destination.exists() and destination.stat().st_mode & 0o077)
        ):
            self.fail("Report destination must be private and locally writable.")
        scope = ProviderScope("local-smoke-owner", "azure-connector-live")
        provider = create_azure_model_provider_from_files(
            Path(os.environ["TRACE_AZURE_SETUP_PATH"]),
            Path(os.environ["TRACE_AZURE_SECRETS_PATH"]),
            authority=SyntheticSmokeAuthority(scope),
            scope=scope,
            prompts={
                "azure-health.v1": PromptTemplate(
                    'Return JSON only with status "ok" and citation_id "azure-smoke-1" after reading the admitted synthetic evidence.',
                    "azure-health-json.v1",
                )
            },
            journal_path=Path(os.environ["TRACE_PROVIDER_JOURNAL_PATH"]),
            monthly_limit_nusd=20_000_000_000,
            initial_spend_nusd=int(os.environ["TRACE_INITIAL_SPEND_NUSD"]),
        )
        started = time.monotonic()
        result = provider.generate(
            ProviderCall(
                "azure-health.v1",
                (EvidenceSelection("azure-smoke-1", "smoke.v1", ("observation",)),),
                ModelCallBounds(
                    timeout_ms=30_000, max_output_tokens=256, max_response_bytes=65_536
                ),
            )
        )
        body = result.structured_response(scope)
        self.assertTrue(body.get("status") == "ok", "Unexpected health status.")
        self.assertTrue(
            body.get("citation_id") == "azure-smoke-1", "Missing admitted citation."
        )
        metadata = result.metadata()
        self.assertTrue(
            isinstance(metadata.get("provider_operation_id"), str),
            "Missing operation metadata.",
        )
        usage = metadata.get("usage")
        self.assertTrue(
            isinstance(usage, dict) and usage.get("availability") == "available",
            "Missing measured usage.",
        )
        report = {
            **metadata,
            "policy_version": "trace-provider-data-policy.v1",
            "evidence_ids": ["azure-smoke-1"],
            "attempts": 1,
            "automatic_retries": 0,
            "elapsed_ms": int((time.monotonic() - started) * 1000),
            "checked_at_utc_epoch": time.time(),
            "model_version_verification": "date_not_independently_verified",
        }
        descriptor = os.open(
            destination, os.O_WRONLY | os.O_CREAT | os.O_TRUNC | os.O_NOFOLLOW, 0o600
        )
        with os.fdopen(descriptor, "w") as output:
            json.dump(report, output, sort_keys=True)
            output.write("\n")
