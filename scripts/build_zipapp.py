#!/usr/bin/env python3
"""Build a dependency-free, relocatable DevWho zipapp and SHA256SUMS."""

from __future__ import annotations

import hashlib
import shutil
import tempfile
import tomllib
import zipapp
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "version"
]
ARCHIVE_NAME = f"devwho-{PACKAGE_VERSION}.pyz"


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

    sums = output / "SHA256SUMS"
    stem = ARCHIVE_NAME.removesuffix(".pyz")
    artifacts = [archive, output / (stem + ".tar.gz"), *output.glob(stem + "-*.whl")]
    sums.write_text(
        "".join(
            f"{hashlib.sha256(item.read_bytes()).hexdigest()}  {item.name}\n"
            for item in sorted(artifacts)
            if item.is_file()
        ),
        encoding="ascii",
    )
    return archive


if __name__ == "__main__":
    print(build())
