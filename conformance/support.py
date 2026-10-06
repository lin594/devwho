"""Subprocess-only helpers; fixtures never read a contributor's profile."""

from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
EXECUTABLE = Path(os.environ.get("DEVWHO_TEST_EXECUTABLE", ROOT / "bin/devwho")).resolve()


class ContractCase(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devwho-contract-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.root / "config.toml"
        self.env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "HOME": str(self.home),
            "XDG_CONFIG_HOME": str(self.home / ".config"),
            "GIT_CONFIG_GLOBAL": os.devnull,
            "GIT_CONFIG_NOSYSTEM": "1",
            "LC_ALL": "C.UTF-8" if sys.platform.startswith("linux") else "en_US.UTF-8",
        }

    def invoke(self, *args, env=None, state="", executable=EXECUTABLE):
        return subprocess.run(
            [str(executable), "--config", str(self.config), *args],
            input=state,
            text=True,
            capture_output=True,
            timeout=30,
            cwd=self.root,
            env=self.env if env is None else env,
        )

    def transition(self, profile, env=None, state=None, executable=EXECUTABLE):
        supplied = self.env if env is None else env
        args = ["internal", "transition", "--shell", "bash"]
        args.extend(["--restore"] if profile is None else ["--activate", profile])
        result = self.invoke(
            *args,
            env=supplied,
            state="" if state is None else json.dumps(state),
            executable=executable,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Scalar-only disposable shell; full integration tests independently
        # exercise the renderer's attribute preflight and atomicity.
        script = (
            "__devwho_writable() { return 0; }\n__apply() {\n"
            + result.stdout
            + "\n}\n__apply || exit $?\nprintf '%s\\0' \"${__DEVWHO_STATE-}\"\nenv -0\n"
        )
        applied = subprocess.run(
            ["/bin/bash", "--noprofile", "--norc", "-c", script],
            env=supplied,
            cwd=self.root,
            capture_output=True,
            timeout=30,
        )
        self.assertEqual(applied.returncode, 0, applied.stderr.decode(errors="replace"))
        raw_state, *entries = applied.stdout.split(b"\0")
        active = {}
        for entry in entries:
            if entry:
                key, value = entry.decode().split("=", 1)
                if key not in {"_", "SHLVL", "PWD", "OLDPWD"}:
                    active[key] = value
        return active, json.loads(raw_state) if raw_state else None
