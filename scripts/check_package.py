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
            if any(
                not (name.startswith("trace_app/") or ".dist-info/" in name)
                for name in names
            ):
                raise RuntimeError(
                    "Wheel contains content outside the runtime package."
                )
            if not {
                "trace_app/cli/__main__.py",
                "trace_app/knowledge/search.py",
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
        version = subprocess.run(
            [str(python), "-I", "-m", "trace_app.cli", "--version"],
            cwd=temporary,
            env=child_env,
            check=True,
            capture_output=True,
            text=True,
        )
        if not version.stdout.startswith("trace-app "):
            raise RuntimeError(
                "Installed module entry point did not report its version."
            )
        console = subprocess.run(
            [str(environment / "bin/trace-app"), "--version"],
            cwd=temporary,
            env=child_env,
            check=True,
            capture_output=True,
            text=True,
        )
        if console.stdout != version.stdout:
            raise RuntimeError("Console and module entry points disagree.")
        env_file = temporary / "settings.env"
        env_file.write_text("TRACE_ENVIRONMENT=test\n")
        demo = subprocess.run(
            [
                str(python),
                "-I",
                "-m",
                "trace_app.cli",
                "demo-order",
                "--env-file",
                str(env_file),
                "--order-id",
                "order-package",
                "--customer-id",
                "customer-001",
                "--amount-cents",
                "1250",
            ],
            cwd=temporary,
            env=child_env,
            check=True,
            capture_output=True,
            text=True,
        )
        if json.loads(demo.stdout)["status"] != "accepted":
            raise RuntimeError("Installed synthetic workflow did not complete.")
        excluded = subprocess.run(
            [
                str(python),
                "-I",
                "-c",
                "import importlib.util; assert importlib.util.find_spec('evaluation') is None; assert importlib.util.find_spec('tests') is None",
            ],
            cwd=temporary,
            env=child_env,
            check=True,
        )
        print(
            "Built wheel, installed entry points, synthetic workflow and evaluator exclusion passed."
        )
    return excluded.returncode


if __name__ == "__main__":
    raise SystemExit(main())
