"""Process behavior and user-data invariants tested through executable APIs."""

import json
import os
import signal
import subprocess

from conformance.support import ContractCase, EXECUTABLE


class ProcessContract(ContractCase):
    def setUp(self):
        super().setUp()
        self.config.write_text('version=1\n[profiles.a.env]\nSELECTED="a"\n')

    def test_config_path_falls_back_to_account_home_without_home_variable(self):
        import pwd

        env = {
            key: value
            for key, value in self.env.items()
            if key not in {"HOME", "XDG_CONFIG_HOME", "DEVWHO_CONFIG"}
        }
        result = subprocess.run(
            [str(EXECUTABLE), "config", "path"], env=env, capture_output=True, text=True, timeout=10
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(
            result.stdout.strip(), pwd.getpwuid(os.getuid()).pw_dir + "/.config/devwho/config.toml"
        )

    def test_argv_is_literal_and_empty_arguments_survive(self):
        values = ["", "space value", "line\n雪", "$(touch bad)", "`touch bad2`", "a'b\"c"]
        result = self.invoke(
            "exec", "a", "--", "/bin/sh", "-c", "printf '%s\\0' \"$@\"", "sh", *values
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.split("\0")[:-1], values)
        self.assertFalse((self.root / "bad").exists())
        self.assertFalse((self.root / "bad2").exists())

    def test_doctor_preserves_trailing_empty_runtime_values(self):
        self.config.write_text(
            'version=1\n[profiles.a.git.config]\n"credential.helper"=["helper", ""]\n'
        )
        result = self.invoke(
            "exec",
            "a",
            "--",
            str(EXECUTABLE),
            "--config",
            str(self.config),
            "doctor",
            "a",
            "--offline",
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("Git runtime configuration: OK", result.stdout)

    def test_exec_preserves_signal_and_nonexecutable_status(self):
        result = self.invoke("exec", "a", "--", "/bin/sh", "-c", "kill -TERM $$")
        self.assertEqual(result.returncode, -signal.SIGTERM)
        script = self.root / "not-executable"
        script.write_text("#!/bin/sh\nexit 0\n")
        script.chmod(0o600)
        self.assertEqual(self.invoke("exec", "a", "--", str(script)).returncode, 126)

    def test_rebase_preserves_original_author_and_selected_committer(self):
        self.config.write_text(
            'version=1\n[profiles.a.git]\nname="Selected"\nemail="selected@example.test"\n'
        )

        def git(*args):
            return subprocess.run(
                ["git", *args],
                cwd=self.root,
                env=self.env,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.strip()

        git("init", "-q", "-b", "main")
        git(
            "-c",
            "user.name=Base",
            "-c",
            "user.email=base@example.test",
            "commit",
            "--allow-empty",
            "-m",
            "base",
        )
        git("branch", "topic")
        (self.root / "main.txt").write_text("main")
        git("add", "main.txt")
        git("-c", "user.name=Base", "-c", "user.email=base@example.test", "commit", "-m", "main")
        git("checkout", "topic")
        (self.root / "topic.txt").write_text("topic")
        git("add", "topic.txt")
        git(
            "-c",
            "user.name=Original",
            "-c",
            "user.email=original@example.test",
            "commit",
            "-m",
            "topic",
        )
        result = self.invoke("exec", "a", "--", "git", "rebase", "main")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(
            git("log", "-1", "--format=%an|%ae|%cn|%ce"),
            "Original|original@example.test|Selected|selected@example.test",
        )

    def test_unset_key_returns_to_baseline_after_becoming_unmanaged(self):
        self.config.write_text('version=1\n[profiles.a.env]\nVALUE="a"\n[profiles.b]\n')
        a, state = self.transition("a", dict(self.env, VALUE="original"))
        b, state = self.transition("b", a, state)
        b["VALUE"] = "edited-after-release"
        restored, _ = self.transition(None, b, state)
        self.assertEqual(restored["VALUE"], "edited-after-release")

    def test_unknown_profile_and_author_overrides_do_not_emit_patch(self):
        for profile, additions in [
            ("missing", {}),
            ("a", {"GIT_AUTHOR_EMAIL": "hidden"}),
            ("a", {"GIT_COMMITTER_NAME": "hidden"}),
        ]:
            result = self.invoke(
                "internal",
                "transition",
                "--shell",
                "bash",
                "--activate",
                profile,
                env=dict(self.env, **additions),
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertNotIn("hidden", result.stderr)

    def test_activation_leaves_dirty_repository_remote_and_branch_unchanged(self):
        subprocess.run(
            ["git", "init", "-q", "-b", "main", str(self.root)],
            check=True,
            env=self.env,
            capture_output=True,
        )
        subprocess.run(
            ["git", "remote", "add", "origin", "git@example.invalid:owner/repo.git"],
            check=True,
            cwd=self.root,
            env=self.env,
        )
        dirty = self.root / "dirty-file"
        dirty.write_text("uncommitted\n")
        before = (self.root / ".git/config").read_bytes()
        env, state = self.transition("a")
        self.transition(None, env, state)
        self.assertEqual((self.root / ".git/config").read_bytes(), before)
        self.assertEqual(dirty.read_text(), "uncommitted\n")
        result = subprocess.run(
            ["git", "symbolic-ref", "HEAD"],
            cwd=self.root,
            env=self.env,
            capture_output=True,
            text=True,
            check=True,
        )
        self.assertEqual(result.stdout.strip(), "refs/heads/main")

    def test_profile_path_uses_effective_home_and_rejects_relative(self):
        other = self.root / "other home"
        other.mkdir()
        self.config.write_text(
            "version=1\n[profiles.a.env]\nHOME=" + json.dumps(str(other)) + "\n"
            '[profiles.a.github]\nconfig_dir="~/gh"\nexpected_user="sample"\n'
        )
        env, state = self.transition("a")
        self.assertEqual(env["GH_CONFIG_DIR"], str(other / "gh"))
        self.assertEqual(self.transition(None, env, state), (self.env, None))
        self.config.write_text(
            'version=1\n[profiles.a.github]\nconfig_dir="relative"\nexpected_user="sample"\n'
        )
        result = self.invoke("exec", "a", "--", "/bin/true")
        self.assertEqual(result.returncode, 1)

    def test_relocated_launcher_is_pinned_after_path_changes(self):
        # Symlinks exercise lookup independently of packaging layout; each
        # artifact's installation test also copies its complete distribution.
        folder = self.root / "launcher space 雪"
        folder.mkdir()
        link = folder / "devwho"
        link.symlink_to(EXECUTABLE)
        fake = self.root / "fake"
        fake.mkdir()
        (fake / "devwho").write_text("#!/bin/sh\nexit 99\n")
        (fake / "devwho").chmod(0o755)
        for shell, options in (("bash", ["--noprofile", "--norc"]), ("zsh", ["-f"])):
            with self.subTest(shell=shell):
                env = dict(self.env, LAUNCH=str(link), CFG=str(self.config), FAKE=str(fake))
                script = 'eval "$("$LAUNCH" --config "$CFG" init ' + shell + ')"\n'
                script += 'export PATH="$FAKE:$PATH"\nsetdev a\n[ "$DEVWHO_PROFILE" = a ]\nunsetdev\n[ -z "${DEVWHO_PROFILE-}" ]\n'
                result = subprocess.run(
                    ["/bin/" + shell, *options, "-c", "set -e\n" + script],
                    cwd=self.root,
                    env=env,
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
