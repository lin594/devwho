"""Compile profiles and calculate reversible, process-local transitions."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping
from pathlib import Path
import re
import shlex

from .config import Config, Profile, RUNTIME_NAME, expand_path, parse_profile, validate_env_key


class TransitionError(ValueError):
    """A transition failed without changing the supplied environment or state."""


@dataclass(frozen=True)
class Compiled:
    values: dict[str, str]
    unset: tuple[str, ...]
    runtime: tuple[tuple[str, str], ...]


@dataclass(frozen=True)
class EnvironmentPatch:
    set: dict[str, str]
    unset: tuple[str, ...]

    def apply(self, environ: Mapping[str, str]) -> dict[str, str]:
        result = dict(environ)
        for key in self.unset:
            result.pop(key, None)
        result.update(self.set)
        return result


def _check_conflicts(profile: Profile, environ: Mapping[str, str]) -> None:
    overrides = ("GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL", "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL")
    for key in overrides:
        if environ.get(key):
            raise TransitionError(f"Conflicting environment variable: {key}")
    if profile.github:
        for key in ("GH_TOKEN", "GITHUB_TOKEN"):
            if environ.get(key) or profile.env.get(key):
                raise TransitionError(f"Conflicting environment variable: {key}")


def _semantic_path(value: str, environ: Mapping[str, str], field: str) -> str:
    if value == "~" or value.startswith("~/"):
        if not environ.get("HOME"):
            raise TransitionError(f"{field} requires a nonempty effective HOME for ~ paths")
        expanded = expand_path(value, environ)
    elif Path(value).is_absolute():
        expanded = value
    else:
        raise TransitionError(f"{field} must be an absolute path, ~, or start with ~/")
    if not Path(expanded).is_absolute():
        raise TransitionError(f"{field} must expand to an absolute path")
    return expanded


def compile_profile(profile: Profile, environ: Mapping[str, str]) -> Compiled:
    # Validate programmatically constructed profiles as strictly as TOML ones.
    profile = parse_profile(
        profile.name,
        {
            "git": profile.git,
            "git_ssh": profile.git_ssh,
            "github": profile.github,
            "env": profile.env,
            "unset_env": list(profile.unset_env),
        },
    )
    _check_conflicts(profile, environ)
    values = dict(profile.env)
    values["DEVWHO_PROFILE"] = profile.name
    runtime: list[tuple[str, str]] = []
    for key, value in profile.git.get("config", {}).items():
        runtime.extend((key, item) for item in (value if isinstance(value, list) else [value]))
    if "name" in profile.git:
        for kind in ("user", "author", "committer"):
            runtime.append((f"{kind}.name", profile.git["name"]))
            runtime.append((f"{kind}.email", profile.git["email"]))
    for field, key in (("signing_key", "user.signingKey"), ("signing_format", "gpg.format")):
        if field in profile.git:
            runtime.append((key, profile.git[field]))
    if "sign_commits" in profile.git:
        runtime.append(("commit.gpgSign", str(profile.git["sign_commits"]).lower()))
    path_environ = dict(environ)
    for key in profile.unset_env:
        path_environ.pop(key, None)
    path_environ.update(profile.env)
    if profile.git_ssh:
        identity = _semantic_path(
            profile.git_ssh["identity_file"], path_environ, "git_ssh.identity_file"
        )
        try:
            available = Path(identity).is_file()
        except (OSError, ValueError):
            available = False
        if not available:
            raise TransitionError("git_ssh.identity_file must identify an existing file")
        command = "ssh -i " + shlex.quote(identity)
        if profile.git_ssh.get("identities_only", True):
            command += " -o IdentitiesOnly=yes"
        values["GIT_SSH_COMMAND"] = command
    if profile.github:
        values["GH_CONFIG_DIR"] = _semantic_path(
            profile.github["config_dir"], path_environ, "github.config_dir"
        )
        values["GH_HOST"] = profile.github.get("hostname", "github.com")
    for key, value in values.items():
        validate_env_key(key, internal=True)
        if not isinstance(value, str) or "\0" in value:
            raise TransitionError(f"Invalid environment value: {key}")
    return Compiled(values, profile.unset_env, tuple(runtime))


def _pairs(environ: Mapping[str, str]) -> list[list[str]]:
    count = environ.get("GIT_CONFIG_COUNT")
    if count is None:
        return []
    if (
        not isinstance(count, str)
        or not re.fullmatch(r"[0-9]+", count)
        or len(count) > 6
        or int(count) > 4096
    ):
        raise TransitionError("Invalid GIT_CONFIG_COUNT")
    pairs = []
    for index in range(int(count)):
        key_name, value_name = f"GIT_CONFIG_KEY_{index}", f"GIT_CONFIG_VALUE_{index}"
        if key_name not in environ or value_name not in environ:
            raise TransitionError(f"Missing runtime configuration variable at index {index}")
        key, value = environ[key_name], environ[value_name]
        if (
            not isinstance(key, str)
            or not key
            or "\0" in key
            or not isinstance(value, str)
            or "\0" in value
        ):
            raise TransitionError(f"Invalid runtime configuration variable at index {index}")
        pairs.append([key, value])
    return pairs


def _validate_state(state: object) -> dict:
    if not isinstance(state, dict) or set(state) != {
        "version",
        "profile",
        "baseline",
        "managed",
        "runtime",
    }:
        raise TransitionError("Invalid DevWho shell state")
    if type(state["version"]) is not int or state["version"] != 1:
        raise TransitionError("Unsupported DevWho shell state")
    if not isinstance(state["profile"], str) or not re.fullmatch(
        r"[A-Za-z0-9][A-Za-z0-9_.-]*", state["profile"]
    ):
        raise TransitionError("Invalid DevWho shell state")
    baseline, managed = state["baseline"], state["managed"]
    if (
        not isinstance(baseline, dict)
        or not isinstance(managed, list)
        or not all(isinstance(key, str) for key in managed)
    ):
        raise TransitionError("Invalid DevWho shell state")
    for key, value in baseline.items():
        validate_env_key(key, internal=True)
        if RUNTIME_NAME.fullmatch(key) or (
            value is not None and (not isinstance(value, str) or "\0" in value)
        ):
            raise TransitionError("Invalid DevWho baseline")
    if (
        len(set(managed)) != len(managed)
        or not set(managed) <= set(baseline)
        or "DEVWHO_PROFILE" not in managed
    ):
        raise TransitionError("Invalid DevWho managed variables")
    runtime = state["runtime"]
    if runtime is not None:
        if not isinstance(runtime, dict) or set(runtime) != {"baseline", "before", "owned"}:
            raise TransitionError("Invalid DevWho runtime state")
        if not isinstance(runtime["baseline"], dict):
            raise TransitionError("Invalid DevWho runtime baseline")
        for key, value in runtime["baseline"].items():
            if (
                not isinstance(key, str)
                or not RUNTIME_NAME.fullmatch(key)
                or not isinstance(value, str)
                or "\0" in value
            ):
                raise TransitionError("Invalid DevWho runtime baseline")
        _pairs(runtime["baseline"])
        for field in ("before", "owned"):
            pairs = runtime[field]
            if not isinstance(pairs, list) or len(pairs) > 4096:
                raise TransitionError("Invalid DevWho runtime pairs")
            for pair in pairs:
                if (
                    not isinstance(pair, list)
                    or len(pair) != 2
                    or not all(isinstance(item, str) and "\0" not in item for item in pair)
                    or not pair[0]
                ):
                    raise TransitionError("Invalid DevWho runtime pairs")
    # Explicit copies keep caller state immutable, even on later failures.
    return {
        "version": 1,
        "profile": state["profile"],
        "baseline": dict(baseline),
        "managed": list(managed),
        "runtime": None
        if runtime is None
        else {
            "baseline": dict(runtime["baseline"]),
            "before": [list(pair) for pair in runtime["before"]],
            "owned": [list(pair) for pair in runtime["owned"]],
        },
    }


def _runtime_transition(
    target: dict[str, str], runtime: dict | None, owned: tuple[tuple[str, str], ...]
) -> dict | None:
    if runtime is None and not owned:
        return None
    current = _pairs(target)
    if runtime is None:
        runtime = {
            "baseline": {
                key: value for key, value in target.items() if RUNTIME_NAME.fullmatch(key)
            },
            "before": [list(pair) for pair in current],
            "owned": [],
        }
    before, previous = runtime["before"], runtime["owned"]
    boundary = len(before)
    if current[:boundary] != before or current[boundary : boundary + len(previous)] != previous:
        raise TransitionError(
            "Managed Git runtime configuration was changed; refusing to remove unrelated configuration"
        )
    retained = current[:boundary] + current[boundary + len(previous) :]
    desired_pairs = retained + [list(pair) for pair in owned]
    if len(desired_pairs) > 4096:
        raise TransitionError("Too many Git runtime configuration entries")
    desired = dict(runtime["baseline"])
    original = _pairs(runtime["baseline"])
    if owned or retained != original:
        desired["GIT_CONFIG_COUNT"] = str(len(desired_pairs))
        for index, (key, value) in enumerate(desired_pairs):
            desired[f"GIT_CONFIG_KEY_{index}"] = key
            desired[f"GIT_CONFIG_VALUE_{index}"] = value
    # Preserve unrelated orphan variables, but restore those overwritten by our
    # indexed output and remove stale entries created by reindexing appendages.
    touched = {"GIT_CONFIG_COUNT"}
    for index in range(max(len(current), len(desired_pairs))):
        touched.update((f"GIT_CONFIG_KEY_{index}", f"GIT_CONFIG_VALUE_{index}"))
    for key in touched:
        if key in desired:
            target[key] = desired[key]
        else:
            target.pop(key, None)
    return {
        "baseline": dict(runtime["baseline"]),
        "before": retained,
        "owned": [list(pair) for pair in owned],
    }


def transition(
    config: Config,
    profile_or_none: str | None,
    environ: Mapping[str, str],
    state_or_none: dict | None = None,
) -> tuple[EnvironmentPatch, dict | None]:
    """Calculate an atomic activation/restoration, without I/O or mutation."""
    old = None if state_or_none is None else _validate_state(state_or_none)
    if profile_or_none is not None and profile_or_none not in config.profiles:
        raise TransitionError("Unknown profile")
    profile = None if profile_or_none is None else config.profiles[profile_or_none]
    # Check the inherited environment before restoring prior managed keys; an
    # earlier profile must not silently erase a conflicting inherited token.
    if profile is not None:
        _check_conflicts(profile, environ)
    target = dict(environ)
    baseline = {} if old is None else dict(old["baseline"])
    if old:
        for key in old["managed"]:
            if baseline[key] is None:
                target.pop(key, None)
            else:
                target[key] = baseline[key]
    compiled = None if profile is None else compile_profile(profile, target)
    runtime = _runtime_transition(
        target,
        None if old is None else old["runtime"],
        () if compiled is None else compiled.runtime,
    )
    new_state = None
    if compiled is not None:
        managed = sorted(set(compiled.values) | set(compiled.unset))
        for key in managed:
            if key not in baseline:
                baseline[key] = target.get(key)
        for key in compiled.unset:
            target.pop(key, None)
        target.update(compiled.values)
        new_state = {
            "version": 1,
            "profile": profile_or_none,
            "baseline": baseline,
            "managed": managed,
            "runtime": runtime,
        }
    patch_set = {
        key: value
        for key, value in target.items()
        if environ.get(key) != value or key not in environ
    }
    patch_unset = tuple(sorted(set(environ) - set(target)))
    return EnvironmentPatch(patch_set, patch_unset), new_state
