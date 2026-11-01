from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path

from scripts.verify_extraction import verify


class ExtractionVerificationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.source = self.root / "source"
        self.destination = self.root / "destination"
        self.source.mkdir()
        self.destination.mkdir()
        (self.source / "original").write_bytes(b"frozen evidence")
        (self.destination / "copy").write_bytes(b"frozen evidence")
        self.entry = {
            "source": "original",
            "destination": "copy",
            "sha256": hashlib.sha256(b"frozen evidence").hexdigest(),
        }

    def test_matching_renamed_copy(self) -> None:
        self.assertEqual(
            verify(
                self.source, self.destination, {"version": 1, "files": [self.entry]}
            ),
            1,
        )

    def test_changed_or_missing_copy_fails(self) -> None:
        (self.destination / "copy").write_bytes(b"changed")
        with self.assertRaisesRegex(ValueError, "mismatch"):
            verify(self.source, self.destination, {"version": 1, "files": [self.entry]})
        (self.destination / "copy").unlink()
        with self.assertRaisesRegex(ValueError, "missing"):
            verify(self.source, self.destination, {"version": 1, "files": [self.entry]})

    def test_empty_duplicate_and_path_traversal_rejected(self) -> None:
        with self.assertRaises(ValueError):
            verify(self.source, self.destination, {"version": 1, "files": []})
        with self.assertRaisesRegex(ValueError, "duplicate"):
            verify(
                self.source,
                self.destination,
                {"version": 1, "files": [self.entry, self.entry]},
            )
        with self.assertRaisesRegex(ValueError, "dot segments"):
            verify(
                self.source,
                self.destination,
                {"version": 1, "files": [{**self.entry, "source": "../original"}]},
            )

    def test_symlink_rejected(self) -> None:
        (self.destination / "link").symlink_to(self.destination / "copy")
        with self.assertRaisesRegex(ValueError, "symlink"):
            verify(
                self.source,
                self.destination,
                {"version": 1, "files": [{**self.entry, "destination": "link"}]},
            )


if __name__ == "__main__":
    unittest.main()
