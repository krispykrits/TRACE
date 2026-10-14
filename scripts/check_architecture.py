"""Check TRACE's import boundaries without importing application code."""

from __future__ import annotations

import ast
import importlib.util
import sys
from pathlib import Path

CORE = frozenset({"evidence", "knowledge", "investigation"})
PACKAGES = CORE | {"adapters", "cli", "runtime", "demo"}
ROOT_MODULES = frozenset({"__init__", "bootstrap"})
FORBIDDEN_RUNTIME_ROOTS = frozenset({"evaluation", "tests", "scripts"})
NETWORK_ROOTS = frozenset({"http", "urllib", "socket", "ssl"})


def imported_modules(source: str, module: str, *, package: bool = False) -> list[str]:
    """Resolve static/relative imports and literal dynamic import calls."""
    imports: list[str] = []
    dynamic_names = {"__import__", "importlib.import_module"}
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(alias.name for alias in node.names)
            for alias in node.names:
                if alias.name == "importlib":
                    dynamic_names.add((alias.asname or alias.name) + ".import_module")
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level:
                owner = module if package else module.rpartition(".")[0]
                base = importlib.util.resolve_name("." * node.level + base, owner)
            imports.append(base)
            imports.extend(base + "." + alias.name for alias in node.names)
            if base == "importlib":
                dynamic_names.update(
                    alias.asname or alias.name
                    for alias in node.names
                    if alias.name == "import_module"
                )
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        name = ast.unparse(node.func)
        if name not in dynamic_names:
            continue
        if (
            node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            imports.append(node.args[0].value)
        else:
            imports.append("<dynamic-import>")
    return imports


def collect_violations(root: Path) -> list[str]:
    violations: list[str] = []
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        layer = relative.parts[0] if len(relative.parts) > 1 else path.stem
        if layer not in PACKAGES | ROOT_MODULES:
            violations.append(
                f"{relative}: unknown runtime package/module; record a reviewed boundary decision"
            )
        module = "trace_app." + ".".join(relative.with_suffix("").parts)
        is_package = path.name == "__init__.py"
        if is_package:
            module = module.removesuffix(".__init__")
        for dependency in imported_modules(
            path.read_text(), module, package=is_package
        ):
            top = dependency.split(".")[0]
            forbidden = (
                top in FORBIDDEN_RUNTIME_ROOTS or dependency == "<dynamic-import>"
            )
            # External network execution belongs to explicitly selected adapters.
            forbidden |= (
                top in NETWORK_ROOTS
                and dependency != "urllib.parse"
                and not dependency.startswith("urllib.parse.")
                and layer != "adapters"
            )
            target = (
                dependency.split(".")[1]
                if dependency.startswith("trace_app.")
                else None
            )
            if layer in CORE:
                forbidden |= (target is not None and target not in CORE) or (
                    top != "trace_app" and top not in sys.stdlib_module_names
                )
            elif layer == "runtime":
                forbidden |= target not in (None, "runtime") or (
                    top != "trace_app" and top not in sys.stdlib_module_names
                )
            elif layer == "adapters":
                forbidden |= target in {"bootstrap", "cli", "demo"}
                if relative.parts[:2] == ("adapters", "models"):
                    # Model transports receive prepared text, not citation readers,
                    # assessment acceptance/reviews, or source/tool handles.
                    forbidden |= target not in (None, "investigation", "runtime")
                    if target == "investigation":
                        forbidden |= not (
                            dependency == "trace_app.investigation.provider"
                            or dependency == "trace_app.investigation.provider_policy"
                            or dependency.startswith(
                                "trace_app.investigation.provider."
                            )
                            or dependency.startswith(
                                "trace_app.investigation.provider_policy."
                            )
                        )
            elif layer == "demo":
                forbidden |= target in {"adapters", "bootstrap", "cli"}
            elif layer == "cli":
                forbidden |= target == "adapters"
            if forbidden:
                violations.append(f"{relative}: forbidden dependency {dependency}")
    return sorted(set(violations))


def main() -> int:
    root = Path(__file__).resolve().parents[1] / "src/trace_app"
    violations = collect_violations(root)
    for violation in violations:
        print(violation, file=sys.stderr)
    if not violations:
        print("TRACE architecture boundaries passed.")
    return int(bool(violations))


if __name__ == "__main__":
    raise SystemExit(main())
