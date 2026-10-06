"""CLI, diagnostics, bootstrap, child-process, and release-archive regressions."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.build_zipapp import ARCHIVE_NAME, build


ROOT = Path(__file__).resolve().parents[1]
DEVWHO = ROOT / "bin" / "devwho"


def toml_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


class CliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="devwho-cli-")
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.config = self.root / "config.toml"
        self.repo = self.root / "repo"
        self.repo.mkdir()
        subprocess.run(["git", "init", "-q", str(self.repo)], check=True)
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.name", "Local Wrong"], check=True
        )
        subprocess.run(
            ["git", "-C", str(self.repo), "config", "user.email", "wrong@example.test"], check=True
        )
        self.write_config()
        self.env = self.clean_env()
        self.env.update(
            {
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.root / "xdg"),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
            }
        )
        Path(self.env["XDG_CONFIG_HOME"]).mkdir()

    @staticmethod
    def clean_env() -> dict[str, str]:
        env = dict(os.environ)
        for key in list(env):
            if key.startswith(("GIT_", "DEVWHO_", "__DEVWHO")) or key in {
                "GH_TOKEN",
                "GITHUB_TOKEN",
                "GH_CONFIG_DIR",
                "GH_HOST",
            }:
                env.pop(key, None)
        return env

    def write_config(self, *, github: bool = False, git: bool = True, secret: bool = False):
        lines = ["version = 1", ""]
        for profile, email in (
            ("personal", "jane.personal@example.test"),
            ("work", "jane.work@example.test"),
        ):
            if git:
                lines.extend(
                    [
                        f"[profiles.{profile}.git]",
                        'name = "Jane Doe"',
                        f"email = {toml_string(email)}",
                    ]
                )
            lines.extend([f"[profiles.{profile}.env]", f"TOOL_PROFILE = {toml_string(profile)}"])
            if secret:
                lines.append(f"TOOL_SECRET = {toml_string('do-not-print-this-secret')}")
            if github:
                lines.extend(
                    [
                        f"[profiles.{profile}.github]",
                        'hostname = "github.com"',
                        'expected_user = "jane-work"'
                        if profile == "work"
                        else 'expected_user = "jane-personal"',
                        f"config_dir = {toml_string(str(self.root / ('gh-' + profile)))}",
                    ]
                )
            lines.append("")
        self.config.write_text("\n".join(lines), encoding="utf-8")

    def cli(
        self,
        *args: str,
        env: dict[str, str] | None = None,
        cwd: Path | None = None,
        input_text: str | None = None,
    ) -> subprocess.CompletedProcess:
        return subprocess.run(
            [str(DEVWHO), "--config", str(self.config), *args],
            env=self.env if env is None else env,
            cwd=cwd,
            input=input_text,
            text=True,
            capture_output=True,
            check=False,
        )

    @staticmethod
    def runtime_identity(name: str, email: str) -> dict[str, str]:
        pairs = [
            ("user.name", name),
            ("user.email", email),
            ("author.name", name),
            ("author.email", email),
            ("committer.name", name),
            ("committer.email", email),
        ]
        env = {"GIT_CONFIG_COUNT": str(len(pairs))}
        for index, (key, value) in enumerate(pairs):
            env[f"GIT_CONFIG_KEY_{index}"] = key
            env[f"GIT_CONFIG_VALUE_{index}"] = value
        return env

    def test_common_read_commands_do_not_print_custom_env_values(self):
        self.write_config(secret=True)
        for args in (("--version",), ("--help",), ("current",), ("list",), ("show", "work")):
            with self.subTest(args=args):
                result = subprocess.run(
                    [str(DEVWHO), "--config", str(self.config), *args],
                    env=self.env,
                    text=True,
                    capture_output=True,
                    check=False,
                )
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertNotIn("do-not-print-this-secret", result.stdout + result.stderr)
        self.assertIn("work", self.cli("list").stdout)
        self.assertIn("TOOL_SECRET", self.cli("show", "work").stdout)

    def test_doctor_checks_real_git_identity_and_reports_metadata_mismatch(self):
        env = dict(self.env)
        env.update(self.runtime_identity("Jane Doe", "jane.work@example.test"))
        env["DEVWHO_PROFILE"] = "work"
        env["TOOL_PROFILE"] = "work"
        good = self.cli("doctor", "work", env=env, cwd=self.repo)
        self.assertEqual(good.returncode, 0, good.stdout + good.stderr)
        self.assertIn("Git author: OK", good.stdout)
        self.assertIn("Jane Doe <jane.work@example.test>", good.stdout)

        env.update(self.runtime_identity("Wrong User", "wrong@example.test"))
        mismatch = self.cli("doctor", "work", env=env, cwd=self.repo)
        self.assertEqual(mismatch.returncode, 1)
        self.assertIn("expected Jane Doe <jane.work@example.test>", mismatch.stdout)
        self.assertIn("actual Wrong User <wrong@example.test>", mismatch.stdout)

    def test_current_verbose_reports_effective_identity_and_cli_directory(self):
        env = dict(self.env, DEVWHO_PROFILE="work", GH_CONFIG_DIR=str(self.root / "gh-work"))
        env.update(self.runtime_identity("Jane Doe", "jane.work@example.test"))
        result = self.cli("current", "--verbose", env=env, cwd=self.repo)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("Git author: Jane Doe <jane.work@example.test>", result.stdout)
        self.assertIn("Git committer: Jane Doe <jane.work@example.test>", result.stdout)
        self.assertIn("GitHub config directory: " + str(self.root / "gh-work"), result.stdout)
        self.assertNotIn("Local Wrong", result.stdout)

    def test_config_only_profile_show_and_doctor_are_supported(self):
        self.write_config(git=False)
        env = dict(self.env, DEVWHO_PROFILE="work", TOOL_PROFILE="work")
        show = self.cli("show", "work", env=env)
        self.assertEqual(show.returncode, 0, show.stderr)
        doctor = self.cli("doctor", env=env)
        self.assertEqual(doctor.returncode, 0, doctor.stdout + doctor.stderr)
        self.assertIn("Environment TOOL_PROFILE: OK", doctor.stdout)

    def test_conflicting_credentials_fail_without_echoing_values_or_shell_patch(self):
        self.write_config(github=True)
        for key, secret in (
            ("GH_TOKEN", "ghp-super-secret"),
            ("GIT_AUTHOR_NAME", "private-author-name"),
        ):
            with self.subTest(key=key):
                env = dict(self.env, DEVWHO_PROFILE="work", **{key: secret})
                result = self.cli(
                    "internal",
                    "transition",
                    "--shell",
                    "bash",
                    "--activate",
                    "work",
                    env=env,
                    input_text="",
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")
                self.assertIn(key, result.stderr)
                self.assertNotIn(secret, result.stdout + result.stderr)

    def test_config_init_is_exclusive_private_and_rejects_symlink(self):
        destination = self.root / "new-config.toml"
        result = subprocess.run(
            [str(DEVWHO), "--config", str(destination), "config", "init"],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(destination.stat().st_mode & 0o777, 0o600)
        original = destination.read_text(encoding="utf-8")
        again = subprocess.run(
            [str(DEVWHO), "--config", str(destination), "config", "init"],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(again.returncode, 1)
        self.assertEqual(destination.read_text(encoding="utf-8"), original)

        target = self.root / "symlink-target.toml"
        target.write_text("preserve me\n", encoding="utf-8")
        link = self.root / "linked-config.toml"
        try:
            link.symlink_to(target)
        except (OSError, NotImplementedError) as exc:
            self.skipTest(f"symlinks unavailable: {exc}")
        linked = subprocess.run(
            [str(DEVWHO), "--config", str(link), "config", "init"],
            env=self.env,
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(linked.returncode, 1)
        self.assertEqual(target.read_text(encoding="utf-8"), "preserve me\n")

    def test_exec_preserves_child_status_and_returns_127_for_missing_command(self):
        command = self.cli("exec", "work", "--", sys.executable, "-c", "raise SystemExit(7)")
        self.assertEqual(command.returncode, 7)
        missing = self.cli("exec", "work", "--", str(self.root / "no-such-command"))
        self.assertEqual(missing.returncode, 127)
        self.assertIn("command not found", missing.stderr)

    def test_doctor_checks_fake_gh_login_and_redacts_failed_tool_stderr(self):
        self.write_config(github=True, git=False)
        fake_bin = self.root / "fake-bin"
        fake_bin.mkdir()
        gh = fake_bin / "gh"
        gh.write_text(
            "#!/bin/sh\nprintf '%s\\n' \"${FAKE_GH_LOGIN:-jane-other}\"\n"
            'if [ "${FAKE_GH_FAIL:-0}" = 1 ]; then echo fake-gh-secret >&2; exit 2; fi\n',
            encoding="utf-8",
        )
        gh.chmod(0o755)
        env = dict(
            self.env,
            PATH=str(fake_bin) + os.pathsep + self.env.get("PATH", ""),
            DEVWHO_PROFILE="work",
            TOOL_PROFILE="work",
            GH_CONFIG_DIR=str(self.root / "gh-work"),
            GH_HOST="github.com",
        )
        mismatch = self.cli("doctor", "work", env=env)
        self.assertEqual(mismatch.returncode, 1)
        self.assertIn("expected jane-work; actual jane-other", mismatch.stdout)

        wrong_host_env = dict(env, GH_HOST="other.example")
        wrong_host = self.cli("doctor", "work", env=wrong_host_env)
        self.assertEqual(wrong_host.returncode, 1)
        self.assertIn("GitHub hostname: FAIL", wrong_host.stdout)

        env["FAKE_GH_FAIL"] = "1"
        failed = self.cli("doctor", "work", env=env)
        self.assertEqual(failed.returncode, 2)
        self.assertIn("GitHub identity: UNVERIFIED", failed.stdout)
        self.assertNotIn("fake-gh-secret", failed.stdout + failed.stderr)
        self.assertNotIn("jane-other", failed.stdout)

    def test_doctor_offline_marks_github_unverified(self):
        self.write_config(github=True, git=False)
        env = dict(
            self.env,
            DEVWHO_PROFILE="work",
            TOOL_PROFILE="work",
            GH_CONFIG_DIR=str(self.root / "gh-work"),
            GH_HOST="github.com",
        )
        result = self.cli("doctor", "work", "--offline", env=env)
        self.assertEqual(result.returncode, 2)
        self.assertIn("GitHub identity: UNVERIFIED", result.stdout)
        self.assertIn("expected jane-work", result.stdout)

    def test_doctor_checks_git_runtime_for_signing_only_profiles(self):
        self.config.write_text(
            'version = 1\n[profiles.signing.git.config]\n"commit.gpgSign" = "true"\n',
            encoding="utf-8",
        )
        metadata_only = dict(self.env, DEVWHO_PROFILE="signing")
        mismatch = self.cli("doctor", env=metadata_only, cwd=self.repo)
        self.assertEqual(mismatch.returncode, 1)
        self.assertIn("Git runtime configuration: FAIL", mismatch.stdout)
        self.assertIn("values hidden", mismatch.stdout)

        activated = self.cli(
            "exec",
            "signing",
            "--",
            str(DEVWHO),
            "--config",
            str(self.config),
            "doctor",
            env=self.env,
            cwd=self.repo,
        )
        self.assertEqual(activated.returncode, 0, activated.stdout + activated.stderr)
        self.assertIn("Git runtime configuration: OK", activated.stdout)

    def test_internal_transition_failure_has_no_partial_shell_output(self):
        malformed = self.root / "bad.toml"
        malformed.write_text(
            'version = 1\n[profiles.work.env]\nBAD-KEY = "nope"\n', encoding="utf-8"
        )
        result = subprocess.run(
            [
                str(DEVWHO),
                "--config",
                str(malformed),
                "internal",
                "transition",
                "--shell",
                "bash",
                "--activate",
                "work",
            ],
            env=self.env,
            input="",
            text=True,
            capture_output=True,
            check=False,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, "")

    def test_relocated_zipapp_supports_version_and_real_bash_zsh_activation(self):
        archive_dir = self.root / "relocated archive 中文"
        archive_dir.mkdir()
        build_dir = self.root / "temporary-build"
        build_dir.mkdir()
        wheel = build_dir / "devwho-0.1.0-py3-none-any.whl"
        wheel.write_bytes(b"wheel fixture")
        built = build(build_dir)
        self.assertIn(
            hashlib.sha256(wheel.read_bytes()).hexdigest() + "  " + wheel.name,
            (build_dir / "SHA256SUMS").read_text(encoding="ascii"),
        )
        with zipfile.ZipFile(built) as archive:
            self.assertEqual(archive.read("LICENSE"), (ROOT / "LICENSE").read_bytes())
        relocated = archive_dir / ARCHIVE_NAME
        shutil.copy2(built, relocated)
        expected = hashlib.sha256(relocated.read_bytes()).hexdigest()
        self.assertEqual(expected, hashlib.sha256(built.read_bytes()).hexdigest())
        self.assertIn(expected, (built.parent / "SHA256SUMS").read_text(encoding="ascii"))

        version = subprocess.run(
            [str(relocated), "--version"], env=self.env, text=True, capture_output=True, check=False
        )
        self.assertEqual(version.returncode, 0, version.stderr)
        self.assertIn("devwho 0.1.0", version.stdout)

        for shell in ("bash", "zsh"):
            executable = shutil.which(shell)
            if not executable:
                with self.subTest(shell=shell):
                    self.skipTest(f"{shell} is not installed")
            script = (
                'eval "$("'
                + str(relocated)
                + '" --config "'
                + str(self.config)
                + '" init '
                + shell
                + ')"\n'
                "setdev work\n"
                'test "$("'
                + str(relocated)
                + '" --config "'
                + str(self.config)
                + '" current)" = work\n'
                "unsetdev\n"
                'test "$("'
                + str(relocated)
                + '" --config "'
                + str(self.config)
                + '" current)" = none\n'
            )
            result = subprocess.run(
                [executable, "-f", "-c", script]
                if shell == "zsh"
                else [executable, "--noprofile", "--norc", "-c", script],
                env=self.env,
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(shell=shell):
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

        renamed = archive_dir / "devwho"
        shutil.copy2(relocated, renamed)
        renamed.chmod(0o755)
        for shell in ("bash", "zsh"):
            executable = shutil.which(shell)
            if not executable:
                continue
            script = (
                'eval "$("'
                + str(renamed)
                + '" --config "'
                + str(self.config)
                + '" init '
                + shell
                + ')"\n'
                "setdev work\n"
                'test "$("'
                + str(renamed)
                + '" --config "'
                + str(self.config)
                + '" current)" = work\n'
                "unsetdev\n"
                'test "$("'
                + str(renamed)
                + '" --config "'
                + str(self.config)
                + '" current)" = none\n'
            )
            result = subprocess.run(
                [executable, "-f", "-c", script]
                if shell == "zsh"
                else [executable, "--noprofile", "--norc", "-c", script],
                env=self.env,
                text=True,
                capture_output=True,
                check=False,
            )
            with self.subTest(shell=shell, launcher="without-extension"):
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == "__main__":
    unittest.main()
