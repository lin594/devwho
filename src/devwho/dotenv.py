"""Explicit, literal dotenv input. Never execute or interpolate file contents."""

import json
from pathlib import Path
import re

from .config import Config, ConfigError, ENV_NAME, PROFILE_NAME, expand_path, parse_profile


def parse_dotenv(text: str) -> dict[str, str]:
    text = text.replace("\r\n", "\n")
    if "\r" in text or "\0" in text:
        raise ConfigError("dotenv contains a forbidden control character")
    values = {}
    for number, raw in enumerate(text.split("\n"), 1):
        line = raw.strip(" \t")
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].lstrip(" \t")
        key, separator, value = line.partition("=")
        key = key.strip(" \t")
        if not separator or not ENV_NAME.fullmatch(key) or key in values:
            raise ConfigError(f"Invalid or duplicate dotenv assignment on line {number}")
        untrimmed = value
        value = value.lstrip(" \t")
        try:
            if value.startswith('"'):
                parsed, end = json.JSONDecoder().raw_decode(value)
                tail = value[end:].lstrip(" \t")
                if tail and not tail.startswith("#"):
                    raise ValueError()
                if not isinstance(parsed, str) or any(
                    0xD800 <= ord(char) <= 0xDFFF for char in parsed
                ):
                    raise ValueError()
            elif value.startswith("'"):
                end = value.index("'", 1)
                parsed = value[1:end]
                tail = value[end + 1 :].lstrip(" \t")
                if tail and not tail.startswith("#"):
                    raise ValueError()
            else:
                parsed = re.split(r"[ \t]#", untrimmed, maxsplit=1)[0].strip(" \t")
            if "\0" in parsed:
                raise ValueError()
        except (ValueError, IndexError):
            raise ConfigError(f"Invalid dotenv value on line {number}") from None
        values[key] = parsed
    return values


def load_dotenv(path: Path, profile: str | None, environ: dict[str, str]) -> Config:
    selected = Path(expand_path(str(path), environ)).resolve()
    try:
        text = selected.read_bytes().decode("utf-8")
    except (OSError, UnicodeError):
        raise ConfigError(f"Cannot read UTF-8 dotenv input: {selected}") from None
    values = parse_dotenv(text)
    marker = values.pop("DEVWHO_PROFILE", None)
    for name in (profile, marker):
        if name is not None and not PROFILE_NAME.fullmatch(name):
            raise ConfigError("Invalid dotenv profile name")
    if profile is not None and marker is not None and profile != marker:
        raise ConfigError("dotenv profile marker does not match --env-profile")
    name = profile if profile is not None else marker
    if name is None:
        raise ConfigError("dotenv input needs DEVWHO_PROFILE or --env-profile")
    parsed = parse_profile(name, {"env": values})
    return Config(selected, {name: parsed}, shortcut_profile=name, source_format="dotenv")


def export_dotenv(profile) -> str:
    if profile.git or profile.git_ssh or profile.github or profile.unset_env:
        raise ConfigError("dotenv export requires an env-only profile without unset_env")
    values = {"DEVWHO_PROFILE": profile.name, **profile.env}
    return "".join(
        key + "=" + json.dumps(value, ensure_ascii=False) + "\n" for key, value in values.items()
    )
