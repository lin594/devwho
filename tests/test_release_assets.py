import hashlib
from pathlib import Path
import tempfile
import unittest

from scripts.collect_release_assets import collect, release_plan

CI_RUNS = ["https://github.com/lin594/devwho/actions/runs/123"]


class ReleaseAssetTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.sources = []
        for source_id, source in release_plan()["sources"].items():
            directory = self.root / source_id
            directory.mkdir()
            for name in source["assets"]:
                (directory / name).write_bytes(name.encode())
            self.write_checksums(directory)
            self.sources.append((source_id, directory))
        self.output = self.root / "release"

    def write_checksums(self, directory):
        (directory / "SHA256SUMS").write_text(
            "".join(
                f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
                for path in sorted(directory.iterdir())
                if path.name != "SHA256SUMS"
            )
        )

    def assemble(self, sources=None):
        return collect(self.sources if sources is None else sources, self.output, "a" * 40, CI_RUNS)

    def test_corrupt_input_fails_before_output_is_created(self):
        name = release_plan()["sources"][self.sources[0][0]]["assets"][0]
        (self.sources[0][1] / name).write_bytes(b"corrupted download")
        with self.assertRaisesRegex(ValueError, "checksum mismatch"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_one_valid_pyz_cannot_be_presented_as_a_complete_release(self):
        directory = self.sources[-1][1]
        for path in directory.iterdir():
            if path.name != "SHA256SUMS" and not path.name.endswith(".pyz"):
                path.unlink()
        self.write_checksums(directory)
        with self.assertRaisesRegex(ValueError, "canonical CI sources"):
            self.assemble([self.sources[-1]])
        self.assertFalse(self.output.exists())

    def test_omitting_one_required_asset_fails_before_output_is_created(self):
        source_id, directory = self.sources[0]
        (directory / release_plan()["sources"][source_id]["assets"][0]).unlink()
        self.write_checksums(directory)
        with self.assertRaisesRegex(ValueError, "required release artifact missing"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_unexpected_checksumming_correct_asset_is_rejected(self):
        directory = self.sources[0][1]
        (directory / "devwho-0.1.0rc1-rust-linux-x86_64.tar.gz").write_bytes(b"omitted Rust target")
        self.write_checksums(directory)
        with self.assertRaisesRegex(ValueError, "unexpected release artifact"):
            self.assemble()
        self.assertFalse(self.output.exists())

    def test_noncanonical_python_source_is_rejected(self):
        sources = [*self.sources[:-1], ("devwho-macos-latest-py3.13", self.sources[-1][1])]
        with self.assertRaisesRegex(ValueError, "canonical CI sources"):
            self.assemble(sources)
        self.assertFalse(self.output.exists())

    def test_differing_same_named_bytes_cannot_replace_a_verified_source(self):
        source_id, original = self.sources[-1]
        duplicate = self.root / "duplicate" / source_id
        duplicate.mkdir(parents=True)
        for path in original.iterdir():
            if path.name != "SHA256SUMS":
                (duplicate / path.name).write_bytes(path.read_bytes() + b"different runner bytes")
        self.write_checksums(duplicate)
        with self.assertRaisesRegex(ValueError, "conflicting release artifact"):
            self.assemble([*self.sources, (source_id, duplicate)])
        self.assertFalse(self.output.exists())

    def test_complete_plan_with_identical_duplicate_records_canonical_provenance(self):
        manifest = self.assemble([*self.sources, self.sources[0]])
        self.assertEqual(len(manifest["assets"]), 8)
        self.assertEqual(manifest["canonical_python_source"], "devwho-ubuntu-latest-py3.11")
        self.assertEqual(len(manifest["sources"]), 3)
        self.assertEqual(
            set(manifest["expected_release_assets"]), {item["name"] for item in manifest["assets"]}
        )
        sums = (self.output / "SHA256SUMS").read_text()
        for artifact in self.output.iterdir():
            if artifact.name != "SHA256SUMS":
                self.assertIn(
                    hashlib.sha256(artifact.read_bytes()).hexdigest() + "  " + artifact.name, sums
                )
