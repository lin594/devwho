#!/usr/bin/env python3
"""Collect verified CI distributions into one collision-checked release directory."""

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil

import tomllib

ROOT = Path(__file__).resolve().parents[1]
PACKAGE_VERSION = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))["project"][
    "version"
]


def collect(sources, output, commit, ci_runs=()):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("release commit must be a full Git SHA")
    assets = {}
    for source in sources:
        source = Path(source)
        for line in (source / "SHA256SUMS").read_text(encoding="ascii").splitlines():
            checksum, name = line.split("  ", 1)
            if not re.fullmatch(r"[0-9a-f]{64}", checksum) or Path(name).name != name:
                raise ValueError("invalid checksum entry")
            if not name.startswith(f"devwho-{PACKAGE_VERSION}") or not name.endswith(
                (".tar.gz", ".whl", ".pyz")
            ):
                raise ValueError("unexpected release artifact: " + name)
            artifact = source / name
            if artifact.is_symlink() or not artifact.is_file():
                raise ValueError("missing or unsafe artifact: " + name)
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != checksum:
                raise ValueError("checksum mismatch: " + name)
            if name in assets and assets[name][1] != checksum:
                raise ValueError("conflicting release artifact: " + name)
            assets[name] = artifact, checksum
    if not assets:
        raise ValueError("no release artifacts")
    output = Path(output)
    # Fail before creating output on corrupt inputs; never replace an existing release set.
    output.mkdir(parents=True, exist_ok=False)
    for name, (artifact, _) in sorted(assets.items()):
        shutil.copy2(artifact, output / name)
    manifest = {
        "package_version": PACKAGE_VERSION,
        "commit": commit,
        "ci_runs": list(ci_runs),
        "assets": [
            {"name": name, "sha256": checksum} for name, (_, checksum) in sorted(assets.items())
        ],
    }
    (output / "RELEASE-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    sums = []
    for artifact in sorted(output.iterdir()):
        sums.append(f"{hashlib.sha256(artifact.read_bytes()).hexdigest()}  {artifact.name}\n")
    (output / "SHA256SUMS").write_text("".join(sums), encoding="ascii")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("sources", nargs="+", type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run", action="append", default=[])
    args = parser.parse_args()
    manifest = collect(args.sources, args.output, args.commit, args.ci_run)
    print(f"Verified {len(manifest['assets'])} release artifacts")


if __name__ == "__main__":
    main()
