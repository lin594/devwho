#!/usr/bin/env python3
"""Assemble the complete declared candidate from checksum-verified canonical CI sources."""

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


def release_plan():
    plan = json.loads((ROOT / "release-plan.json").read_text(encoding="utf-8"))
    if plan["schema_version"] != 1 or plan["package_version"] != PACKAGE_VERSION:
        raise ValueError("release plan/version mismatch")
    return plan


def collect(sources, output, commit, ci_runs):
    if not re.fullmatch(r"[0-9a-f]{40}", commit):
        raise ValueError("release commit must be a full Git SHA")
    if not ci_runs or any(
        not re.fullmatch(r"https://github.com/lin594/devwho/actions/runs/[0-9]+", run)
        for run in ci_runs
    ):
        raise ValueError("originating devwho CI run is required")
    plan = release_plan()
    source_ids = {source_id for source_id, _ in sources}
    if source_ids != set(plan["sources"]):
        raise ValueError("required canonical CI sources missing or unexpected")
    assets, provenance = {}, {}
    for source_id, source in sources:
        source = Path(source)
        if source_id not in (source.name, *(parent.name for parent in source.parents)):
            raise ValueError("source directory must retain its CI artifact identity")
        declared = plan["sources"][source_id]
        required = set(declared["assets"])
        checksum_bytes = (source / "SHA256SUMS").read_bytes()
        listed = set()
        for line in checksum_bytes.decode("ascii").splitlines():
            checksum, name = line.split("  ", 1)
            if (
                not re.fullmatch(r"[0-9a-f]{64}", checksum)
                or Path(name).name != name
                or name in listed
            ):
                raise ValueError("invalid or duplicate checksum entry")
            if name not in required:
                raise ValueError("unexpected release artifact: " + name)
            listed.add(name)
            artifact = source / name
            if artifact.is_symlink() or not artifact.is_file():
                raise ValueError("missing or unsafe artifact: " + name)
            if hashlib.sha256(artifact.read_bytes()).hexdigest() != checksum:
                raise ValueError("checksum mismatch: " + name)
            if name in assets and assets[name][1] != checksum:
                raise ValueError("conflicting release artifact: " + name)
            assets[name] = artifact, checksum, source_id
        if listed != required:
            raise ValueError("required release artifact missing from " + source_id)
        actual = {
            path.name
            for path in source.iterdir()
            if path.name.endswith((".tar.gz", ".whl", ".pyz"))
        }
        if actual != required:
            raise ValueError("missing or unexpected distribution in " + source_id)
        provenance[source_id] = {
            "artifact": source_id,
            "job": declared["job"],
            "target": declared["target"],
            "input_checksums_sha256": hashlib.sha256(checksum_bytes).hexdigest(),
        }
    expected = {name for source in plan["sources"].values() for name in source["assets"]}
    if set(assets) != expected:
        raise ValueError("incomplete release asset plan")
    output = Path(output)
    # Validate every source and the complete asset set before creating output.
    output.mkdir(parents=True, exist_ok=False)
    for name, (artifact, _, _) in sorted(assets.items()):
        shutil.copy2(artifact, output / name)
    manifest = {
        "tag": plan["tag"],
        "package_version": PACKAGE_VERSION,
        "commit": commit,
        "ci_runs": list(ci_runs),
        "expected_release_assets": sorted(expected),
        "canonical_python_source": plan["canonical_python_source"],
        "release_plan_sha256": hashlib.sha256(
            (ROOT / "release-plan.json").read_bytes()
        ).hexdigest(),
        "sources": [provenance[key] for key in sorted(provenance)],
        "omitted": plan["omitted"],
        "assets": [
            {"name": name, "sha256": checksum, "source_artifact": source_id}
            for name, (_, checksum, source_id) in sorted(assets.items())
        ],
    }
    (output / "RELEASE-MANIFEST.json").write_text(
        json.dumps(manifest, indent=2) + "\n", encoding="utf-8"
    )
    (output / "SHA256SUMS").write_text(
        "".join(
            f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.name}\n"
            for path in sorted(output.iterdir())
        ),
        encoding="ascii",
    )
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", action="append", required=True, metavar="CI_ARTIFACT=DIR")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--ci-run", action="append", required=True)
    args = parser.parse_args()
    sources = []
    for value in args.source:
        source_id, separator, directory = value.partition("=")
        if not separator or not directory:
            parser.error("--source requires CI_ARTIFACT=DIR")
        sources.append((source_id, Path(directory)))
    manifest = collect(sources, args.output, args.commit, args.ci_run)
    print(f"Verified complete plan: {len(manifest['assets'])} release artifacts")


if __name__ == "__main__":
    main()
