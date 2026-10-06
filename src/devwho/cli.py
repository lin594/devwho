"""DevWho's offline CLI and explicit consumer diagnostics."""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path

from . import __version__
from .config import config_path, load_config
from .engine import compile_profile, transition


def parser() -> argparse.ArgumentParser:
    root = argparse.ArgumentParser(
        prog="devwho", description="Per-shell developer identity through environment variables."
    )
    root.add_argument("--version", action="version", version="devwho " + __version__)
    root.add_argument("--config", type=Path, help="use this TOML configuration")
    commands = root.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="list profile names")
    show = commands.add_parser("show", help="show metadata; custom env values stay hidden")
    show.add_argument("profile")
    current = commands.add_parser("current", help="print active profile or none")
    current.add_argument("--verbose", action="store_true")
    doctor = commands.add_parser("doctor", help="verify current tool identity, without switching")
    doctor.add_argument("profile", nargs="?")
    doctor.add_argument("--offline", action="store_true", help="skip live GitHub verification")
    execute = commands.add_parser("exec", help="run a command in one profile's child process tree")
    execute.add_argument("profile")
    execute.add_argument("argv", nargs=argparse.REMAINDER)
    config = commands.add_parser("config", help="locate or create configuration")
    config.add_argument("action", choices=["path", "init"])
    init = commands.add_parser("init", help="print shell integration; does not edit startup files")
    init.add_argument("shell", choices=["bash", "zsh"])
    internal = commands.add_parser("internal", help=argparse.SUPPRESS)
    internal.add_argument("action", choices=["transition", "bootstrap", "notice"])
    internal.add_argument("--shell", choices=["bash", "zsh"])
    mode = internal.add_mutually_exclusive_group()
    mode.add_argument("--activate", action="store_true")
    mode.add_argument("--restore", action="store_true")
    internal.add_argument("profile", nargs="?")
    return root


def _run(argv: list[str], timeout: int = 10) -> subprocess.CompletedProcess:
    return subprocess.run(argv, text=True, capture_output=True, timeout=timeout, check=False)


def doctor(config, name: str | None, offline: bool) -> int:
    name = name or os.environ.get("DEVWHO_PROFILE")
    if not name:
        print("FAIL: no active profile; use setdev PROFILE or name a profile to diagnose")
        return 1
    if name not in config.profiles:
        raise ValueError(f'Unknown profile "{name}"; run devwho list')
    profile = config.profiles[name]
    print("Profile: " + name)
    failed, unverified = False, False

    def report(label, status, detail=""):
        nonlocal failed, unverified
        print(f"{label}: {status}" + (" — " + detail if detail else ""))
        failed |= status == "FAIL"
        unverified |= status == "UNVERIFIED"

    report(
        "Context",
        "OK" if os.environ.get("DEVWHO_PROFILE") == name else "FAIL",
        "metadata is not proof of authentication",
    )
    try:
        desired = compile_profile(profile, os.environ)
    except ValueError as exc:
        report("Configuration/environment", "FAIL", str(exc))
        return 1
    if "name" in profile.git:
        expected = f"{profile.git['name']} <{profile.git['email']}>"
        for label, variable in [
            ("Git author", "GIT_AUTHOR_IDENT"),
            ("Git committer", "GIT_COMMITTER_IDENT"),
        ]:
            try:
                result = _run(["git", "var", variable])
                actual = result.stdout.strip()
                if result.returncode:
                    report(label, "UNVERIFIED", "Git cannot resolve identity in this context")
                elif actual.startswith(expected + " "):
                    report(label, "OK", expected)
                else:
                    # Only expose Git identity metadata, never subprocess stderr.
                    match = re.match(r"([^\r\n]*<[^\r\n]*>) [0-9]+ [+-][0-9]+$", actual)
                    safe = match.group(1) if match else "unrecognized identity output"
                    report(label, "FAIL", f"expected {expected}; actual {safe}")
            except (OSError, subprocess.TimeoutExpired):
                report(label, "UNVERIFIED", "Git unavailable or timed out")
    runtime_groups = {}
    for key, value in desired.runtime:
        runtime_groups.setdefault(key, []).append(value)
    runtime_mismatch = False
    runtime_unavailable = False
    for key, expected_values in runtime_groups.items():
        try:
            result = _run(["git", "config", "--null", "--get-all", key])
            actual_values = result.stdout.split("\0")
            if actual_values and actual_values[-1] == "":
                actual_values.pop()
            runtime_mismatch |= (
                result.returncode != 0 or actual_values[-len(expected_values) :] != expected_values
            )
        except (OSError, subprocess.TimeoutExpired):
            runtime_unavailable = True
    if runtime_groups:
        report(
            "Git runtime configuration",
            "FAIL" if runtime_mismatch else "UNVERIFIED" if runtime_unavailable else "OK",
            "values hidden",
        )
    if profile.git_ssh:
        matches = os.environ.get("GIT_SSH_COMMAND") == desired.values.get("GIT_SSH_COMMAND")
        report(
            "Git SSH command",
            "OK" if matches else "FAIL",
            "local command/key check only; remote authentication is unverified",
        )
    for key, value in profile.env.items():
        report(
            "Environment " + key, "OK" if os.environ.get(key) == value else "FAIL", "value hidden"
        )
    for key in profile.unset_env:
        report("Unset " + key, "OK" if key not in os.environ else "FAIL")
    if profile.github:
        expected = profile.github.get("expected_user")
        report(
            "GitHub config directory",
            "OK"
            if os.environ.get("GH_CONFIG_DIR") == desired.values.get("GH_CONFIG_DIR")
            else "FAIL",
        )
        report(
            "GitHub hostname",
            "OK" if os.environ.get("GH_HOST") == desired.values.get("GH_HOST") else "FAIL",
        )
        if offline:
            report("GitHub identity", "UNVERIFIED", "offline mode; expected " + expected)
        elif not shutil.which("gh"):
            report("GitHub identity", "UNVERIFIED", "install GitHub CLI; expected " + expected)
        else:
            host = profile.github.get("hostname", "github.com")
            try:
                result = _run(["gh", "api", "--hostname", host, "user", "--jq", ".login"], 15)
                actual = result.stdout.strip()
                if result.returncode or not re.fullmatch(r"[A-Za-z0-9_.-]{1,100}", actual):
                    report(
                        "GitHub identity",
                        "UNVERIFIED",
                        "API/login unavailable; expected " + expected,
                    )
                else:
                    report(
                        "GitHub identity",
                        "OK" if actual == expected else "FAIL",
                        f"expected {expected}; actual {actual}",
                    )
            except (OSError, subprocess.TimeoutExpired):
                report("GitHub identity", "UNVERIFIED", "API unavailable; expected " + expected)
    return 1 if failed else 2 if unverified else 0


def _notice(config) -> int:
    if not getattr(config, "handoff_warning", False):
        return 0
    try:
        result = _run(["git", "status", "--porcelain", "--untracked-files=normal"], 2)
        if result.returncode == 0 and result.stdout:
            print(
                "devwho: this repository has uncommitted changes; confirm the handoff before "
                "editing or committing. Switching identity does not assign those changes.",
                file=sys.stderr,
            )
    except (OSError, subprocess.TimeoutExpired):
        print(
            "devwho: handoff check unavailable; check git status before taking over.",
            file=sys.stderr,
        )
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "current":
            print(os.environ.get("DEVWHO_PROFILE") or "none")
            if args.verbose:
                print("Configuration: " + str(args.config or config_path()))
                print("Use devwho doctor to verify actual tool identity.")
            return 0
        if args.command == "config":
            path = args.config or config_path()
            if args.action == "path":
                print(path)
                return 0
            # Bootstrap is explicit, exclusive, restrictive, and never overwrites.
            path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                stream.write(
                    'version = 1\n\n[profiles.personal.git]\nname = "Jane Doe"\n'
                    'email = "jane@example.com"\n\n[profiles.work.git]\n'
                    'name = "Jane Doe"\nemail = "jane@company.example"\n'
                )
            print("Created " + str(path) + "; edit its example identities before use.")
            return 0
        config = load_config(args.config)
        if args.command == "list":
            for name in sorted(config.profiles):
                print(name)
            return 0
        if args.command == "show":
            if args.profile not in config.profiles:
                raise ValueError(f'Unknown profile "{args.profile}"; run devwho list')
            profile = config.profiles[args.profile]
            print("Profile: " + profile.name)
            if "name" in profile.git:
                print(f"Git: {profile.git['name']} <{profile.git['email']}>")
            if profile.git_ssh:
                print("Git SSH key: " + profile.git_ssh["identity_file"])
            if profile.github:
                print("GitHub expected user: " + profile.github["expected_user"])
                print("GitHub config: " + profile.github["config_dir"])
            print("Custom environment keys: " + ", ".join(sorted(profile.env)))
            print("Unset keys: " + ", ".join(profile.unset_env))
            return 0
        if args.command == "doctor":
            return doctor(config, args.profile, args.offline)
        if args.command == "init":
            from .shell import render_init

            if config.default_profile and not os.environ.get("DEVWHO_PROFILE"):
                compile_profile(config.profiles[config.default_profile], os.environ)
            print(render_init(args.shell, config.path, bool(config.default_profile)), end="")
            return 0
        if args.command == "exec":
            child = args.argv[1:] if args.argv[:1] == ["--"] else args.argv
            if not child:
                raise ValueError("devwho exec needs a command after --")
            if args.profile not in config.profiles:
                raise ValueError(f'Unknown profile "{args.profile}"; run devwho list')
            patch, _ = transition(config, args.profile, os.environ, None)
            env = patch.apply(os.environ)
            try:
                if os.name == "posix":
                    os.execvpe(child[0], child, env)
                result = subprocess.run(child, env=env, check=False)
                return result.returncode
            except FileNotFoundError:
                print("devwho: command not found", file=sys.stderr)
                return 127
            except PermissionError:
                print("devwho: command is not executable", file=sys.stderr)
                return 126
        if args.command == "internal":
            if args.action == "notice":
                return _notice(config)
            if not args.shell:
                raise ValueError("internal transition requires a shell")
            from .shell import render_patch

            if args.action == "bootstrap":
                if not config.default_profile:
                    return 0
                patch, _ = transition(config, config.default_profile, os.environ, None)
                print(render_patch(patch, None, args.shell), end="")
                return 0
            raw_state = sys.stdin.read(1024 * 1024 + 1)
            if len(raw_state) > 1024 * 1024:
                raise ValueError("DevWho shell state exceeds its size limit")
            try:
                state = json.loads(raw_state) if raw_state else None
            except json.JSONDecodeError:
                raise ValueError("Invalid DevWho shell state; open a fresh shell") from None
            profile = None if args.restore else args.profile or config.shortcut_profile
            if not args.restore and not profile:
                raise ValueError("setdev needs PROFILE or settings.shortcut_profile")
            if profile is not None and profile not in config.profiles:
                raise ValueError(f'Unknown profile "{profile}"; run devwho list')
            patch, new_state = transition(config, profile, os.environ, state)
            print(render_patch(patch, new_state, args.shell), end="")
            return 0
        return 1
    except (ValueError, OSError) as exc:
        # Do not emit config values, tool stderr, traceback, or arbitrary env.
        message = (
            str(exc)
            if isinstance(exc, ValueError)
            else f"local operation failed ({type(exc).__name__})"
        )
        print("devwho: " + message, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
