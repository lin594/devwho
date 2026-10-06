#!/usr/bin/env python3
"""Package already-built cores with their own runtime files and license notices."""

import argparse
import hashlib
from pathlib import Path
import platform
import shutil
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--go", required=True, type=Path)
    parser.add_argument("--setup", required=True, type=Path)
    parser.add_argument("--rust", required=True, type=Path)
    parser.add_argument("--output", type=Path, default=ROOT / "dist/cores")
    parser.add_argument("--staging", type=Path, default=ROOT / "build/core-packages")
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=True)
    args.staging.mkdir(parents=True, exist_ok=True)
    target = platform.system().lower() + "-" + platform.machine().lower()
    sums = []
    for language in ("go", "rust", "bash"):
        source = ROOT / "implementations" / language
        dest = args.staging / language
        # Do not erase an arbitrary caller-supplied directory. Fresh packaging
        # fails visibly if the stage already exists.
        dest.mkdir()
        shutil.copy2(ROOT / "LICENSE", dest / "LICENSE")
        if language == "bash":
            shutil.copytree(
                source,
                dest,
                dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("tests", "__pycache__", "*.pyc"),
            )
        else:
            binary = args.go if language == "go" else args.rust
            shutil.copy2(binary, dest / "devwho")
            (dest / "devwho").chmod(0o755)
            if language == "go":
                shutil.copy2(args.setup, dest / "devwho-setup")
                (dest / "devwho-setup").chmod(0o755)
            for doc in source.glob("*.md"):
                shutil.copy2(doc, dest / doc.name)
            if (source / "licenses").is_dir():
                shutil.copytree(source / "licenses", dest / "licenses")
        suffix = "unix-source" if language == "bash" else target
        archive = args.output / f"devwho-{language}-{suffix}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(dest, arcname=archive.name.removesuffix(".tar.gz"))
        sums.append(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
        print(archive)
    (args.output / "SHA256SUMS").write_text("".join(sums), encoding="ascii")


if __name__ == "__main__":
    main()
