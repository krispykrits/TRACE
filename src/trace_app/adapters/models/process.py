"""One model call in a bounded worker; no fallback and no implicit retries."""

from __future__ import annotations

import json
import logging
import multiprocessing
import os
import sys
import threading
import time
from multiprocessing.connection import Connection

from trace_app.investigation.provider import (
    AdmissionGuard,
    ModelCapabilities,
    ModelConfiguration,
    ModelErrorCode,
    ModelProviderError,
    ModelReply,
    ModelRequest,
    ModelResult,
    ModelTransport,
    ModelUsage,
    validate_model_readiness,
    validate_model_reply,
)


def _worker(
    connection: Connection, transport: ModelTransport, request: ModelRequest
) -> None:
    # Third-party stdout/stderr and exception messages cannot enter parent logs.
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
        sys.stdout = sink
        sys.stderr = sink
        logging.disable(logging.CRITICAL)
        try:
            reply = validate_model_reply(request, transport.generate(request)).reply
            envelope = {
                "structured_json": reply.structured_json,
                "operation_id": reply.operation_id,
                "usage": reply.usage.to_dict(),
                "reported_model": reply.reported_model,
            }
        except ModelProviderError as error:
            envelope = {
                "error": error.code.value,
                "usage": error.usage.to_dict() if error.usage is not None else None,
                "diagnostics": error.diagnostics,
            }
        except Exception:
            envelope = {"error": ModelErrorCode.DEPENDENCY.value}
        try:
            connection.send_bytes(json.dumps(envelope, allow_nan=False).encode())
        finally:
            connection.close()


class ProcessModelProvider:
    """Transport is trusted composition code, never a caller-selected import."""

    def __init__(
        self,
        configuration: ModelConfiguration,
        capabilities: ModelCapabilities,
        transport: ModelTransport,
        *,
        credential_present: bool,
        admission_guard: AdmissionGuard | None = None,
    ) -> None:
        self.readiness = validate_model_readiness(
            configuration, capabilities, credential_present=credential_present
        )
        self._configuration = configuration
        self._transport = transport
        self._admission_guard = admission_guard
        if configuration.mode == "live" and admission_guard is None:
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)

    def generate(self, request: ModelRequest) -> ModelResult:
        if not isinstance(request, ModelRequest) or (
            request.configuration != self._configuration
        ):
            raise ModelProviderError(ModelErrorCode.CONFIGURATION)
        if self._configuration.mode == "live":
            assert self._admission_guard is not None
            self._admission_guard.verify(request)
        started = time.monotonic()
        deadline = started + request.bounds.timeout_ms / 1000
        context = multiprocessing.get_context("spawn")
        receiver, sender = context.Pipe(duplex=False)
        worker = context.Process(
            target=_worker, args=(sender, self._transport, request), daemon=True
        )
        expired = threading.Event()
        watchdog: threading.Timer | None = None

        def expire() -> None:
            # poll() only covers initial readability; recv_bytes() can also stall.
            expired.set()
            try:
                if worker.is_alive():
                    worker.kill()
            except ProcessLookupError:
                # The worker exited between the liveness check and signal.
                pass

        status = ModelErrorCode.DEPENDENCY.value
        try:
            worker.start()
            sender.close()
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise ModelProviderError(ModelErrorCode.TIMEOUT)
            watchdog = threading.Timer(remaining, expire)
            watchdog.daemon = True
            watchdog.start()
            if not receiver.poll(remaining):
                raise ModelProviderError(ModelErrorCode.TIMEOUT)
            # Worst case JSON escaping is six bytes per original byte plus metadata.
            encoded = receiver.recv_bytes(request.bounds.max_response_bytes * 6 + 4096)
            if time.monotonic() >= deadline:
                raise ModelProviderError(ModelErrorCode.TIMEOUT)
            envelope = json.loads(encoded)
            if "error" in envelope:
                failed_usage = envelope.get("usage")
                raise ModelProviderError(
                    ModelErrorCode(envelope["error"]),
                    usage=(
                        ModelUsage(
                            failed_usage["input_tokens"], failed_usage["output_tokens"]
                        )
                        if isinstance(failed_usage, dict)
                        else None
                    ),
                    diagnostics=envelope.get("diagnostics"),
                )
            usage = envelope["usage"]
            reply = ModelReply(
                envelope["structured_json"],
                envelope["operation_id"],
                ModelUsage(usage["input_tokens"], usage["output_tokens"]),
                reported_model=envelope.get("reported_model"),
            )
            result = validate_model_reply(request, reply)
            if time.monotonic() >= deadline:
                raise ModelProviderError(ModelErrorCode.TIMEOUT)
            status = "structured_response_received"
            return result
        except ModelProviderError as error:
            status = error.code.value
            raise
        except Exception:
            if expired.is_set() or time.monotonic() >= deadline:
                status = ModelErrorCode.TIMEOUT.value
                raise ModelProviderError(ModelErrorCode.TIMEOUT) from None
            raise ModelProviderError(ModelErrorCode.DEPENDENCY) from None
        finally:
            if watchdog is not None:
                watchdog.cancel()
                watchdog.join()
            receiver.close()
            sender.close()
            if worker.pid is not None:
                if worker.is_alive():
                    worker.kill()
                worker.join()
                worker.close()
            logging.getLogger("trace_app.models").info(
                "Model call completed.",
                extra={
                    "event": "models.call.completed",
                    **request.metadata(),
                    "outcome": status,
                    "elapsed_ms": max(0, int((time.monotonic() - started) * 1000)),
                },
            )
