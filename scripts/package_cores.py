#!/usr/bin/env python3
"""Package already-built cores with their own runtime files and license notices."""

import argparse
import hashlib
from pathlib import Path
import platform
import re
import shutil
import subprocess
import tarfile

ROOT = Path(__file__).resolve().parents[1]


def runtime_requirements(directory, language, target):
    lines = [
        f"DevWho {language} development artifact",
        f"Target: {target}",
        "Test evidence: consult the originating CI run or local build record.",
        "Only the recorded OS/CPU target is validated; this is not a universal binary.",
    ]
    if language == "bash":
        lines += [
            "Bash 3.2+, jq 1.6+, Perl 5.18+ and standard Unix utilities.",
            "See THIRD_PARTY.md for the complete command/module inventory.",
        ]
    else:
        for binary in sorted(directory.glob("devwho*")):
            lines.append("\nExecutable: " + binary.name)
            if platform.system() == "Linux":
                linked = subprocess.run(["ldd", str(binary)], capture_output=True, text=True)
                output = linked.stdout + linked.stderr
                if "not a dynamic executable" in output or "statically linked" in output:
                    lines.append("Static executable; no dynamic libc dependency.")
                else:
                    linked.check_returncode()
                    dependencies = re.findall(r"^\s*(\S+)\s+=>", output, re.M)
                    versions = subprocess.check_output(
                        ["readelf", "--version-info", str(binary)], text=True
                    )
                    glibc = set(re.findall(r"GLIBC_([0-9]+(?:\.[0-9]+)+)", versions))
                    lines.append("Dynamic dependencies: " + ", ".join(sorted(dependencies)))
                    if glibc:
                        minimum = max(glibc, key=lambda v: tuple(map(int, v.split("."))))
                        lines.append("Required glibc symbol version: " + minimum + " or newer.")
                    lines.append("Use a matching glibc system; Alpine/musl is not this target.")
            elif platform.system() == "Darwin":
                output = subprocess.check_output(["otool", "-L", str(binary)], text=True)
                lines.append("macOS system libraries:")
                lines.extend(line.strip() for line in output.splitlines()[1:])
                lines.append("Tested on macOS " + platform.mac_ver()[0] + ".")
            else:
                raise ValueError("Packaging is supported only on tested Linux/macOS hosts")
    lines.append("\nNo Python or language compiler is required to run this artifact.")
    (directory / "RUNTIME.txt").write_text("\n".join(lines) + "\n", encoding="utf-8")


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
            # Package the runtime inventory, never incidental local profiles or
            # ignored files that happen to be beside the script implementation.
            for name in (
                "devwho",
                "devwho.bash",
                "child-exec.pl",
                "core.jq",
                "doctor.bash",
                "toml-json.pl",
                "state-json.pl",
                "dotenv-json.pl",
                "writable.bash",
                "writable.zsh",
                "install.sh",
                "README.md",
                "README.zh-CN.md",
                "THIRD_PARTY.md",
            ):
                shutil.copy2(source / name, dest / name)
            shutil.copytree(source / "vendor", dest / "vendor")
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
        runtime_requirements(dest, language, target)
        suffix = "unix-source" if language == "bash" else target
        archive = args.output / f"devwho-{language}-{suffix}.tar.gz"
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(dest, arcname=archive.name.removesuffix(".tar.gz"))
        sums.append(f"{hashlib.sha256(archive.read_bytes()).hexdigest()}  {archive.name}\n")
        print(archive)
    (args.output / "SHA256SUMS").write_text("".join(sums), encoding="ascii")


if __name__ == "__main__":
    main()
