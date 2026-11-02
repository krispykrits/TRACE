"""Build and verify the runtime wheel in an isolated installed environment."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    uv = shutil.which("uv")
    if uv is None:
        raise RuntimeError("The pinned uv executable is required for package checks.")
    with tempfile.TemporaryDirectory(prefix="trace-package-check-") as directory:
        temporary = Path(directory)
        output = temporary / "dist"
        subprocess.run(
            [uv, "build", "--wheel", "--out-dir", str(output)], cwd=root, check=True
        )
        wheels = list(output.glob("*.whl"))
        if len(wheels) != 1:
            raise RuntimeError("Expected exactly one runtime wheel.")
        with zipfile.ZipFile(wheels[0]) as archive:
            names = archive.namelist()
            # Synthetic isolation/disclosure sentinels belong only to external
            # test tooling, never to the installed application or metadata.
            for name in names:
                content = archive.read(name)
                if any(
                    marker in content
                    for marker in (
                        b"TRACE_EVALUATOR_ONLY_CANARY_67_94d7",
                        b"trace_nonfunctional_credential_67_5e12",
                    )
                ):
                    raise RuntimeError("Wheel contains a synthetic isolation canary.")
            if any(
                not (name.startswith("trace_app/") or ".dist-info/" in name)
                for name in names
            ):
                raise RuntimeError(
                    "Wheel contains content outside the runtime package."
                )
            if not {
                "trace_app/knowledge/search.py",
                "trace_app/investigation/tools.py",
                "trace_app/investigation/bundle.py",
                "trace_app/adapters/tools/local.py",
                "trace_app/investigation/provider.py",
                "trace_app/adapters/models/process.py",
                "trace_app/adapters/models/azure.py",
                "trace_app/adapters/models/journal.py",
                "trace_app/investigation/provider_policy.py",
                "trace_app/investigation/assessment_schema.py",
                "trace_app/investigation/assessment_context.py",
                "trace_app/investigation/assessment_validation.py",
                "trace_app/investigation/execution.py",
                "trace_app/adapters/storage/sqlite/execution.py",
                "trace_app/investigation/workflow.py",
                "trace_app/investigation/reports.py",
                "trace_app/investigation/local_service.py",
                "trace_app/adapters/storage/sqlite/reports.py",
                "trace_app/adapters/sources/local_investigator.py",
                "trace_app/investigation/workflow_prompt.py",
                "trace_app/adapters/storage/sqlite/workflow.py",
                "trace_app/adapters/storage/sqlite/workflow_schema.py",
            } <= set(names):
                raise RuntimeError("Wheel is missing nested runtime modules.")
        requirements = temporary / "requirements.txt"
        subprocess.run(
            [
                uv,
                "export",
                "--locked",
                "--no-dev",
                "--no-emit-project",
                "--output-file",
                str(requirements),
            ],
            cwd=root,
            check=True,
            capture_output=True,
        )
        environment = temporary / "venv"
        subprocess.run(
            [uv, "venv", "--python", sys.executable, str(environment)],
            cwd=root,
            check=True,
        )
        python = environment / "bin/python"
        subprocess.run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--require-hashes",
                "-r",
                str(requirements),
            ],
            cwd=root,
            check=True,
        )
        subprocess.run(
            [
                uv,
                "pip",
                "install",
                "--python",
                str(python),
                "--no-deps",
                str(wheels[0]),
            ],
            cwd=root,
            check=True,
        )
        # Only the installed wheel and locked runtime dependencies are available.
        child_env = {"PATH": os.environ.get("PATH", os.defpath)}
        subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import trace_app.adapters.hosted; import trace_app.adapters.http.api",
            ],
            cwd=temporary,
            env=child_env,
            check=True,
        )
        excluded = subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('evaluation') is None; assert importlib.util.find_spec('tests') is None; assert importlib.util.find_spec('scripts') is None",
            ],
            cwd=temporary,
            env=child_env,
            check=True,
        )
        # The deadline worker must also run from the wheel outside the checkout.
        worker = subprocess.run(
            [str(python), "-I", "-m", "trace_app.adapters.tools.local"],
            input="{}",
            cwd=temporary,
            env=child_env,
            check=True,
            capture_output=True,
            text=True,
        )
        if json.loads(worker.stdout)["status"] != "dependency_failure":
            raise RuntimeError(
                "Installed tool worker failed closed-protocol verification."
            )
        print(
            "Built wheel, hosted imports, tool worker and evaluator exclusion passed."
        )
    return excluded.returncode


if __name__ == "__main__":
    raise SystemExit(main())
