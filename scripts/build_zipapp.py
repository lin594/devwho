#!/usr/bin/env python3
"""Build a dependency-free, relocatable DevWho zipapp and SHA256SUMS."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import zipapp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_NAME = "devwho-0.1.0.pyz"


def build(output_dir: str | Path | None = None) -> Path:
    """Build the release archive in output_dir (dist/ by default)."""
    output = Path(output_dir) if output_dir is not None else ROOT / "dist"
    output.mkdir(parents=True, exist_ok=True)
    output = output.resolve()
    archive = output / ARCHIVE_NAME

    with tempfile.TemporaryDirectory(prefix="devwho-zipapp-") as temporary:
        source = Path(temporary) / "app"
        shutil.copytree(
            ROOT / "src" / "devwho",
            source / "devwho",
            ignore=shutil.ignore_patterns("__pycache__", "*.pyc"),
        )
        (source / "__main__.py").write_text(
            "from devwho.cli import main\nraise SystemExit(main())\n",
            encoding="utf-8",
        )
        shutil.copy2(ROOT / "LICENSE", source / "LICENSE")
        zipapp.create_archive(
            source,
            archive,
            interpreter="/usr/bin/env python3",
            compressed=True,
        )
    archive.chmod(0o755)

    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    sums = output / "SHA256SUMS"
    sums.write_text(f"{digest}  {ARCHIVE_NAME}\n", encoding="ascii")
    return archive


if __name__ == "__main__":
    print(build())
