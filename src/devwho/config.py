"""Strict, local TOML configuration for developer environments."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import tomllib
from typing import Mapping


class ConfigError(ValueError):
    """Configuration cannot be used safely."""


PROFILE_NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]*\Z")
ENV_NAME = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
RUNTIME_NAME = re.compile(r"GIT_CONFIG_(?:COUNT|KEY_[0-9]+|VALUE_[0-9]+)\Z")
# These affect shell parsing/startup or collide with DevWho's internal state.
UNSAFE_ENV = frozenset(
    {
        "BASH_ENV",
        "ENV",
        "BASHOPTS",
        "SHELLOPTS",
        "IFS",
        "CDPATH",
        "ZDOTDIR",
        "PS4",
        "PROMPT_COMMAND",
        "GIT_AUTHOR_NAME",
        "GIT_AUTHOR_EMAIL",
        "GIT_COMMITTER_NAME",
        "GIT_COMMITTER_EMAIL",
    }
)


def validate_env_key(key: str, *, internal: bool = False) -> None:
    if not isinstance(key, str) or not ENV_NAME.fullmatch(key):
        raise ConfigError("Invalid environment variable name")
    if key in UNSAFE_ENV or key.startswith(("__DEVWHO", "__devwho")):
        raise ConfigError(f"Reserved environment variable: {key}")
    if key.startswith("DEVWHO_") and not (internal and key == "DEVWHO_PROFILE"):
        raise ConfigError(f"Reserved environment variable: {key}")
    if key == "GIT_CONFIG_COUNT" or key.startswith(("GIT_CONFIG_KEY_", "GIT_CONFIG_VALUE_")):
        if not (internal and RUNTIME_NAME.fullmatch(key)):
            raise ConfigError(f"Reserved environment variable: {key}")


def _string(value: object, field: str, *, nonempty: bool = False) -> str:
    if not isinstance(value, str) or "\0" in value or (nonempty and not value.strip()):
        raise ConfigError(f"{field} must be {'a nonempty' if nonempty else 'a'} string without NUL")
    return value


def _table(value: object, field: str, allowed: set[str] | None = None) -> dict:
    if not isinstance(value, dict):
        raise ConfigError(f"{field} must be a table")
    if allowed is not None and set(value) - allowed:
        raise ConfigError(f"Unknown field in {field}: {sorted(set(value) - allowed)[0]}")
    return value


def expand_path(value: str, environ: Mapping[str, str]) -> str:
    """Expand only a leading ~, never shell expressions or environment values."""
    _string(value, "path", nonempty=True)
    if value == "~" or value.startswith("~/"):
        home = environ.get("HOME") or os.path.expanduser("~")
        return home + value[1:]
    return os.path.expanduser(value) if value.startswith("~") else value


@dataclass(frozen=True)
class Profile:
    name: str
    git: dict
    git_ssh: dict
    github: dict
    env: dict[str, str]
    unset_env: tuple[str, ...]


@dataclass(frozen=True)
class Config:
    path: Path
    profiles: dict[str, Profile]
    default_profile: str | None = None
    shortcut_profile: str | None = None
    handoff_warning: bool = False


def config_path(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    if env.get("DEVWHO_CONFIG"):
        return Path(expand_path(env["DEVWHO_CONFIG"], env))
    root = env.get("XDG_CONFIG_HOME") or str(Path(expand_path("~", env)) / ".config")
    return Path(root) / "devwho" / "config.toml"


def parse_profile(name: str, raw: object) -> Profile:
    if not isinstance(name, str) or not PROFILE_NAME.fullmatch(name):
        raise ConfigError("Invalid profile name")
    data = _table(raw, f"profiles.{name}", {"git", "git_ssh", "github", "env", "unset_env"})
    git = _table(
        data.get("git", {}),
        "git",
        {"name", "email", "signing_key", "signing_format", "sign_commits", "config"},
    )
    if ("name" in git) != ("email" in git):
        raise ConfigError("git.name and git.email must be provided together")
    for key in ("name", "email", "signing_key", "signing_format"):
        if key in git:
            _string(git[key], f"git.{key}", nonempty=True)
    for key in ("name", "email"):
        if key in git and (
            git[key] != git[key].strip() or any(char in git[key] for char in "\r\n<>")
        ):
            raise ConfigError(
                f"git.{key} must not contain identity delimiters or surrounding whitespace"
            )
    if "signing_format" in git and git["signing_format"] not in {"ssh", "openpgp", "x509"}:
        raise ConfigError("Unsupported git.signing_format")
    if "sign_commits" in git and type(git["sign_commits"]) is not bool:
        raise ConfigError("git.sign_commits must be a boolean")
    runtime = _table(git.get("config", {}), "git.config")
    for key, value in runtime.items():
        if not isinstance(key, str) or not re.fullmatch(
            r"[A-Za-z][A-Za-z0-9-]*\.(?:[^\n\r\0]+\.)?[A-Za-z][A-Za-z0-9-]*", key
        ):
            raise ConfigError("Invalid Git runtime configuration key")
        values = value if isinstance(value, list) else [value]
        if not values:
            raise ConfigError("git.config lists must not be empty")
        for item in values:
            _string(item, "git.config value")
    ssh = _table(data.get("git_ssh", {}), "git_ssh", {"identity_file", "identities_only"})
    if ssh:
        _string(ssh.get("identity_file"), "git_ssh.identity_file", nonempty=True)
        if "identities_only" in ssh and type(ssh["identities_only"]) is not bool:
            raise ConfigError("git_ssh.identities_only must be a boolean")
    github = _table(data.get("github", {}), "github", {"hostname", "expected_user", "config_dir"})
    if github:
        _string(github.get("config_dir"), "github.config_dir", nonempty=True)
        expected = _string(github.get("expected_user"), "github.expected_user", nonempty=True)
        # Underscores also support Enterprise Managed User login suffixes.
        if not re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9_-]{0,98}[A-Za-z0-9])?", expected):
            raise ConfigError("Invalid github.expected_user")
        for key in ("hostname", "expected_user"):
            if key in github:
                _string(github[key], f"github.{key}", nonempty=True)
        if "hostname" in github and not re.fullmatch(
            r"[A-Za-z0-9][A-Za-z0-9.-]*", github["hostname"]
        ):
            raise ConfigError("Invalid github.hostname")
    env = _table(data.get("env", {}), "env")
    for key, value in env.items():
        validate_env_key(key)
        _string(value, f"env.{key}")
    unset = data.get("unset_env", [])
    if not isinstance(unset, list) or not all(isinstance(key, str) for key in unset):
        raise ConfigError("unset_env must be an array of environment variable names")
    for key in unset:
        validate_env_key(key)
    if set(env) & set(unset):
        raise ConfigError("An environment variable cannot be both set and unset")
    semantic = set()
    if ssh:
        semantic.add("GIT_SSH_COMMAND")
    if github:
        semantic.update(("GH_CONFIG_DIR", "GH_HOST"))
    if semantic & (set(env) | set(unset)):
        raise ConfigError("Generic environment conflicts with semantic configuration")
    return Profile(name, dict(git), dict(ssh), dict(github), dict(env), tuple(dict.fromkeys(unset)))


def load_config(path: str | Path | None = None, environ: Mapping[str, str] | None = None) -> Config:
    env = os.environ if environ is None else environ
    selected = (config_path(env) if path is None else Path(expand_path(str(path), env))).resolve()
    try:
        with selected.open("rb") as source:
            data = tomllib.load(source)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError("Invalid TOML configuration") from exc
    except OSError as exc:
        raise ConfigError(f"Cannot read configuration: {selected}") from exc
    _table(data, "configuration", {"version", "settings", "profiles"})
    if type(data.get("version")) is not int or data["version"] != 1:
        raise ConfigError("Configuration version must be 1")
    profiles_raw = _table(data.get("profiles", {}), "profiles")
    if not profiles_raw:
        raise ConfigError("Configuration must contain at least one profile")
    profiles = {name: parse_profile(name, raw) for name, raw in profiles_raw.items()}
    settings = _table(
        data.get("settings", {}),
        "settings",
        {"default_profile", "shortcut_profile", "handoff_warning"},
    )
    if "handoff_warning" in settings and type(settings["handoff_warning"]) is not bool:
        raise ConfigError("settings.handoff_warning must be a boolean")
    for key, value in settings.items():
        if key == "handoff_warning":
            continue
        if not isinstance(value, str) or value not in profiles:
            raise ConfigError(f"settings.{key} must name an existing profile")
    return Config(
        selected,
        profiles,
        settings.get("default_profile"),
        settings.get("shortcut_profile"),
        settings.get("handoff_warning", False),
    )
