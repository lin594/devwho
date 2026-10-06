import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.build_zipapp import PACKAGE_VERSION
from scripts.collect_release_assets import collect


class ReleaseAssetTests(unittest.TestCase):
    def test_corrupt_input_fails_before_output_is_created(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "ci"
            source.mkdir()
            name = f"devwho-{PACKAGE_VERSION}.pyz"
            (source / name).write_bytes(b"corrupted download")
            (source / "SHA256SUMS").write_text("0" * 64 + "  " + name + "\n")
            with self.assertRaisesRegex(ValueError, "checksum mismatch"):
                collect([source], root / "release", "a" * 40)
            self.assertFalse((root / "release").exists())

    def test_different_runner_bytes_cannot_silently_replace_a_same_named_asset(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            sources = []
            name = f"devwho-{PACKAGE_VERSION}.pyz"
            for index, data in enumerate((b"linux", b"macos")):
                source = root / str(index)
                source.mkdir()
                (source / name).write_bytes(data)
                checksum = hashlib.sha256(data).hexdigest()
                (source / "SHA256SUMS").write_text(checksum + "  " + name + "\n")
                sources.append(source)
            with self.assertRaisesRegex(ValueError, "conflicting release artifact"):
                collect(sources, root / "release", "a" * 40)
            self.assertFalse((root / "release").exists())

    def test_identical_duplicate_is_deduplicated_and_manifest_is_checksummed(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            name = f"devwho-{PACKAGE_VERSION}.pyz"
            (root / name).write_bytes(b"same artifact")
            checksum = hashlib.sha256(b"same artifact").hexdigest()
            (root / "SHA256SUMS").write_text(checksum + "  " + name + "\n")
            output = root / "release"
            manifest = collect([root, root], output, "a" * 40)
            self.assertEqual(len(manifest["assets"]), 1)
            sums = (output / "SHA256SUMS").read_text()
            for artifact in (output / name, output / "RELEASE-MANIFEST.json"):
                self.assertIn(
                    hashlib.sha256(artifact.read_bytes()).hexdigest() + "  " + artifact.name, sums
                )
