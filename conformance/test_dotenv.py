"""One literal dotenv contract for every compatibility core."""

import json
from pathlib import Path
import shlex
import shutil
import subprocess

from .support import ContractCase, EXECUTABLE


class DotenvContract(ContractCase):
    def setUp(self):
        super().setUp()
        self.dotenv = self.root / "profile.env"

    def run_env(self, *args, options=(), env=None):
        result = subprocess.run(
            [str(EXECUTABLE), "--env-file", str(self.dotenv), *options, *args],
            cwd=self.root,
            env=self.env if env is None else env,
            capture_output=True,
            timeout=30,
        )
        # Preserve literal CR in environment values; universal-newline text mode
        # would turn it into LF and conceal the producer's actual bytes.
        result.stdout = result.stdout.decode()
        result.stderr = result.stderr.decode()
        return result

    def test_literal_fixtures_and_export_roundtrip(self):
        fixtures = json.loads((Path(__file__).parent / "fixtures/dotenv.json").read_text())
        for case in fixtures["valid"]:
            with self.subTest(case=case["id"]):
                self.dotenv.write_bytes(case["text"].encode())
                exported = self.run_env("config", "export-env", "demo")
                self.assertEqual(exported.returncode, 0, exported.stderr)
                for content in (case["text"], exported.stdout):
                    self.dotenv.write_bytes(content.encode())
                    result = self.run_env("exec", "demo", "--", "/usr/bin/env", "-0")
                    self.assertEqual(result.returncode, 0, result.stderr)
                    active = dict(part.split("=", 1) for part in result.stdout.split("\0") if part)
                    self.assertEqual(active["DEVWHO_PROFILE"], "demo")
                    for key, value in case["env"].items():
                        self.assertEqual(active[key], value)
                    self.assertFalse((self.root / "sentinel").exists())
        for case in fixtures["invalid"]:
            with self.subTest(case=case["id"]):
                self.dotenv.write_bytes(case["text"].encode())
                result = self.run_env(
                    "internal", "transition", "--shell", "bash", "--activate", "demo"
                )
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")

    def test_explicit_selection_and_source_conflicts(self):
        self.dotenv.write_text("A=value\n")
        self.assertEqual(self.run_env("list", options=("--env-profile", "demo")).stdout, "demo\n")
        self.dotenv.write_text("DEVWHO_PROFILE=demo\n")
        self.assertNotEqual(self.run_env("list", options=("--env-profile", "other")).returncode, 0)
        self.assertNotEqual(
            self.run_env("list", options=("--config", str(self.config))).returncode, 0
        )
        original = self.dotenv.read_bytes()
        self.assertNotEqual(self.run_env("config", "init").returncode, 0)
        self.assertEqual(self.dotenv.read_bytes(), original)
        self.dotenv.write_bytes(b"DEVWHO_PROFILE=demo\nA=\xff")
        self.assertNotEqual(self.run_env("list").returncode, 0)

    def test_shell_shortcut_restore_and_pinned_source(self):
        self.dotenv.write_text("DEVWHO_PROFILE=demo\nAPP_ACCOUNT=second\nEMPTY=\n")
        self.config.write_text('version=1\n[profiles.other.env]\nAPP_ACCOUNT="wrong"\n')
        for shell in ("bash", "zsh"):
            if not shutil.which(shell):
                continue
            with self.subTest(shell=shell):
                init = self.run_env("init", shell)
                self.assertEqual(init.returncode, 0, init.stderr)
                script = (
                    init.stdout
                    + "\n"
                    + (
                        'test -z "${DEVWHO_PROFILE-}" || exit 10\n'
                        f"export DEVWHO_CONFIG={shlex.quote(str(self.config))}\n"
                        "setdev || exit 11\n"
                        'test "$APP_ACCOUNT" = second && test "$DEVWHO_PROFILE" = demo || exit 12\n'
                        'test "${EMPTY+x}:$EMPTY" = x: || exit 13\n'
                        "unsetdev || exit 14\n"
                        'test "$APP_ACCOUNT" = original && test -z "${DEVWHO_PROFILE+x}" || exit 15\n'
                        'test -z "${EMPTY+x}" || exit 16\n'
                    )
                )
                result = subprocess.run(
                    [shell, "-c", script],
                    cwd=self.root,
                    env={**self.env, "APP_ACCOUNT": "original"},
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_export_rejects_loss_and_preflight_retained(self):
        for profile in (
            '[profiles.demo.git]\nname="Demo"\nemail="demo@example.com"\n',
            '[profiles.demo]\nunset_env=["APP_ACCOUNT"]\n',
            '[profiles.demo.github]\nconfig_dir="~/gh"\nexpected_user="demo"\n',
            '[profiles.demo.git_ssh]\nidentity_file="~/key"\n',
        ):
            with self.subTest(profile=profile):
                self.config.write_text("version=1\n" + profile)
                result = self.invoke("config", "export-env", "demo")
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
        self.dotenv.write_text("DEVWHO_PROFILE=demo\nAPP_ACCOUNT=second\n")
        result = self.run_env(
            "exec",
            "demo",
            "--",
            "/bin/true",
            env={**self.env, "GIT_AUTHOR_NAME": "conflicting author"},
        )
        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("conflicting author", result.stderr)


if __name__ == "__main__":
    import unittest

    unittest.main()
