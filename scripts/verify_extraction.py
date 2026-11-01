"""Verify explicitly mapped migration copies without moving or deleting files."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path, PurePosixPath


def _file(root: Path, relative: object) -> Path:
    if not isinstance(relative, str) or not relative or "\\" in relative:
        raise ValueError("paths must be nonempty relative POSIX paths")
    path = PurePosixPath(relative)
    if path.is_absolute() or any(p in ("", ".", "..") for p in relative.split("/")):
        raise ValueError("paths must not be absolute or contain dot segments")
    target = root
    for part in path.parts:
        target = target / part
        if target.is_symlink():
            raise ValueError(f"symlink is not allowed: {relative}")
    if not target.is_file():
        raise ValueError(f"file is missing or not regular: {relative}")
    return target


def _digest(path: Path) -> str:
    with path.open("rb") as file:
        return hashlib.file_digest(file, "sha256").hexdigest()


def verify(source_root: Path, destination_root: Path, manifest: object) -> int:
    if not isinstance(manifest, dict) or set(manifest) != {"version", "files"}:
        raise ValueError("manifest must contain version and files")
    if type(manifest["version"]) is not int or manifest["version"] != 1:
        raise ValueError("unsupported manifest version")
    entries = manifest["files"]
    if not isinstance(entries, list) or not entries:
        raise ValueError("manifest files must be a nonempty list")
    sources: set[str] = set()
    destinations: set[str] = set()
    for entry in entries:
        if not isinstance(entry, dict) or set(entry) != {
            "source",
            "destination",
            "sha256",
        }:
            raise ValueError("each entry requires source, destination, and sha256")
        source, destination, expected = (
            entry[k] for k in ("source", "destination", "sha256")
        )
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected):
            raise ValueError("sha256 must be a lowercase hexadecimal SHA-256")
        source_file = _file(source_root, source)
        destination_file = _file(destination_root, destination)
        assert isinstance(source, str) and isinstance(destination, str)
        if source in sources or destination in destinations:
            raise ValueError("duplicate source or destination")
        sources.add(source)
        destinations.add(destination)
        if _digest(source_file) != expected or _digest(destination_file) != expected:
            raise ValueError(f"SHA-256 mismatch for mapping: {source} -> {destination}")
    return len(entries)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-root", type=Path, required=True)
    parser.add_argument("--destination-root", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    args = parser.parse_args()
    try:
        manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
        count = verify(args.source_root, args.destination_root, manifest)
    except (OSError, ValueError) as error:
        print(f"Verification failed: {error}", file=sys.stderr)
        return 1
    print(f"Verified {count} mapped files against their recorded SHA-256 values.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
