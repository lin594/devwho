"""Core regression tests use only artificial profiles and credentials."""

from copy import deepcopy
import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

from devwho.config import Config, ConfigError, config_path, load_config, parse_profile
from devwho.engine import TransitionError, compile_profile, transition


def profile(name, **kwargs):
    return parse_profile(name, kwargs)


def config(*profiles):
    return Config(Path("/unused/config.toml"), {item.name: item for item in profiles})


def activate(cfg, name, env, state=None):
    patch, next_state = transition(cfg, name, env, state)
    return patch.apply(env), next_state


def runtime(env):
    return [
        (env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"])
        for i in range(int(env.get("GIT_CONFIG_COUNT", "0")))
    ]


class ConfigTests(unittest.TestCase):
    def load(self, content):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text(content)
            return load_config(path)

    def test_settings_and_profiles(self):
        cfg = self.load("""version = 1
[settings]
default_profile = "a"
shortcut_profile = "b"
handoff_warning = true
[profiles.a.env]
VALUE = "a"
[profiles.b.env]
VALUE = "b"
""")
        self.assertEqual(
            (cfg.default_profile, cfg.shortcut_profile, cfg.handoff_warning), ("a", "b", True)
        )

    def test_invalid_configs(self):
        for content in (
            "version = true\n[profiles.a]",
            "version = 2\n[profiles.a]",
            "version = 1\n[profiles.a]\nunknown = true",
            'version = 1\n[settings]\ndefault_profile = "missing"\n[profiles.a]',
            'version = 1\n[settings]\nhandoff_warning = "yes"\n[profiles.a]',
            'version = 1\n[profiles.a.git]\nname = "Jane"',
            "version = 1\n[profiles.a.env]\nVALUE = 1",
            "bad = [",
        ):
            with self.subTest(content=content), self.assertRaises(ConfigError):
                self.load(content)

    def test_reserved_keys(self):
        for key in (
            "DEVWHO_PROFILE",
            "DEVWHO_OTHER",
            "__DEVWHO_STATE",
            "__devwho_data",
            "GIT_CONFIG_COUNT",
            "GIT_CONFIG_KEY_0",
            "GIT_CONFIG_VALUE_0",
            "GIT_CONFIG_KEY_x",
            "BASH_ENV",
            "ENV",
            "IFS",
            "ZDOTDIR",
            "PROMPT_COMMAND",
            "GIT_AUTHOR_NAME",
            "INVALID-KEY",
        ):
            for kind in ("env", "unset_env"):
                with self.subTest(key=key, kind=kind), self.assertRaises(ConfigError):
                    profile("a", **{kind: {key: "value"} if kind == "env" else [key]})

    def test_bad_values_and_semantic_conflicts(self):
        for data in (
            {"env": {"VALUE": "\0"}},
            {"env": {"VALUE": "x"}, "unset_env": ["VALUE"]},
            {"git_ssh": {"identity_file": "key"}, "env": {"GIT_SSH_COMMAND": "ssh"}},
            {
                "github": {"config_dir": "dir", "expected_user": "jane-work"},
                "unset_env": ["GH_HOST"],
            },
            {"git": {"config": {"credential.helper": []}}},
        ):
            with self.subTest(data=data), self.assertRaises(ConfigError):
                profile("a", **data)

    def test_git_identity_validation(self):
        for key in ("name", "email"):
            for value in (" leading", "trailing ", "a\rb", "a\nb", "a<b", "a>b"):
                git = {"name": "Jane O'Example", "email": "jane@example.com"}
                git[key] = value
                with self.subTest(key=key, value=value), self.assertRaises(ConfigError) as raised:
                    profile("a", git=git)
                self.assertIn("git." + key, str(raised.exception))
                self.assertNotIn(value, str(raised.exception))
        profile("a", git={"name": "Jane O'Example 王", "email": "jane@example.com"})

    def test_github_expected_user_required_and_validated(self):
        for github in (
            {"config_dir": "dir"},
            {"config_dir": "dir", "expected_user": ""},
            {"config_dir": "dir", "expected_user": "bad user"},
            {"config_dir": "dir", "expected_user": "-bad"},
            {"config_dir": "dir", "expected_user": "bad\nuser"},
        ):
            with self.subTest(github=github), self.assertRaises(ConfigError) as raised:
                profile("a", github=github)
            self.assertIn("github.expected_user", str(raised.exception))
        profile("a", github={"config_dir": "dir", "expected_user": "jane-work"})
        profile("a", github={"config_dir": "dir", "expected_user": "jane_shortcode"})

    def test_config_path_resolved_absolutely(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.toml"
            path.write_text("version = 1\n[profiles.a]\n")
            relative = os.path.relpath(path)
            cfg = load_config(relative)
            self.assertTrue(cfg.path.is_absolute())
            self.assertEqual(cfg.path, path.resolve())

    def test_path_resolution(self):
        self.assertEqual(
            config_path({"HOME": "/example"}), Path("/example/.config/devwho/config.toml")
        )
        self.assertEqual(config_path({"XDG_CONFIG_HOME": "/xdg"}), Path("/xdg/devwho/config.toml"))
        self.assertEqual(
            config_path({"HOME": "/example", "DEVWHO_CONFIG": "~/custom"}), Path("/example/custom")
        )


class TransitionTests(unittest.TestCase):
    def test_missing_empty_and_nonempty_baseline(self):
        cfg = config(profile("a", env={"ABSENT": "a", "EMPTY": "a", "PRESENT": "a"}))
        base = {"EMPTY": "", "PRESENT": "old", "HTTP_PROXY": "proxy"}
        env, state = activate(cfg, "a", base)
        restored, state = activate(cfg, None, env, json.loads(json.dumps(state)))
        self.assertEqual(restored, base)
        self.assertIsNone(state)

    def test_switching_sets_restore_a_only_and_unset(self):
        cfg = config(
            profile("a", env={"FOO": "a", "BAR": "a"}, unset_env=["DELETE"]),
            profile("b", env={"BAR": "b", "BAZ": "b"}),
        )
        base = {"FOO": "", "DELETE": "old"}
        env, state = activate(cfg, "a", base)
        self.assertNotIn("DELETE", env)
        env, state = activate(cfg, "b", env, state)
        self.assertEqual(env["FOO"], "")
        self.assertEqual(env["DELETE"], "old")
        self.assertEqual((env["BAR"], env["BAZ"]), ("b", "b"))
        self.assertEqual(activate(cfg, None, env, state)[0], base)

    def test_idempotence(self):
        cfg = config(
            profile("a", git={"name": "Jane Doe", "email": "jane@example.com"}, env={"VALUE": "a"})
        )
        env, state = activate(cfg, "a", {})
        patch, next_state = transition(cfg, "a", env, state)
        self.assertEqual(patch.set, {})
        self.assertEqual(patch.unset, ())
        self.assertEqual(next_state, state)
        self.assertEqual(env["GIT_CONFIG_COUNT"], "6")

    def test_preserve_runtime_config_and_proxy(self):
        base = {
            "GIT_CONFIG_COUNT": "1",
            "GIT_CONFIG_KEY_0": "http.proxy",
            "GIT_CONFIG_VALUE_0": "proxy",
            "GIT_CONFIG_KEY_12": "orphan",
            "GIT_CONFIG_VALUE_12": "unused",
            "HTTPS_PROXY": "proxy",
        }
        cfg = config(
            profile("a", git={"name": "Jane", "email": "jane@example.com"}),
            profile("b", git={"name": "Other", "email": "other@example.com"}),
        )
        env, state = activate(cfg, "a", base)
        self.assertEqual(runtime(env)[0], ("http.proxy", "proxy"))
        env, state = activate(cfg, "b", env, state)
        self.assertEqual(len(runtime(env)), 7)
        self.assertEqual(env["HTTPS_PROXY"], "proxy")
        self.assertEqual(activate(cfg, None, env, state)[0], base)

    def test_preserve_user_appended_pairs(self):
        cfg = config(
            profile("a", git={"name": "Jane", "email": "jane@example.com"}),
            profile("b", env={"VALUE": "b"}),
        )
        env, state = activate(cfg, "a", {})
        env.update(
            GIT_CONFIG_COUNT="7", GIT_CONFIG_KEY_6="credential.helper", GIT_CONFIG_VALUE_6="custom"
        )
        env, state = activate(cfg, "b", env, state)
        self.assertEqual(runtime(env), [("credential.helper", "custom")])
        env, state = activate(cfg, "a", env, state)
        self.assertEqual(runtime(env)[0], ("credential.helper", "custom"))
        restored, _ = activate(cfg, None, env, state)
        self.assertEqual(runtime(restored), [("credential.helper", "custom")])
        self.assertNotIn("GIT_CONFIG_KEY_6", restored)

    def test_orphan_vars_and_zero_count_restore(self):
        cfg = config(profile("a", git={"name": "Jane", "email": "jane@example.com"}))
        for base in (
            {"GIT_CONFIG_KEY_0": "orphan", "GIT_CONFIG_VALUE_0": "unused"},
            {"GIT_CONFIG_COUNT": "000"},
        ):
            with self.subTest(base=base):
                env, state = activate(cfg, "a", base)
                self.assertEqual(activate(cfg, None, env, state)[0], base)

    def test_unmanaged_orphan_changes_are_preserved(self):
        cfg = config(profile("a", git={"name": "Jane", "email": "jane@example.com"}))
        env, state = activate(
            cfg, "a", {"GIT_CONFIG_KEY_12": "orphan", "GIT_CONFIG_VALUE_12": "old"}
        )
        env["GIT_CONFIG_VALUE_12"] = "user-change"
        env, state = activate(cfg, "a", env, state)
        self.assertEqual(env["GIT_CONFIG_VALUE_12"], "user-change")
        env, _ = activate(cfg, None, env, state)
        self.assertEqual(env["GIT_CONFIG_VALUE_12"], "user-change")

    def test_modified_runtime_atomic_failure(self):
        cfg = config(profile("a", git={"name": "Jane", "email": "jane@example.com"}))
        env, state = activate(cfg, "a", {})
        env["GIT_CONFIG_VALUE_0"] = "changed"
        saved_env, saved_state = deepcopy(env), deepcopy(state)
        with self.assertRaises(TransitionError):
            transition(cfg, None, env, state)
        self.assertEqual((env, state), (saved_env, saved_state))

    def test_changed_prefix_fails_without_removing_configuration(self):
        cfg = config(profile("a", git={"name": "Jane", "email": "jane@example.com"}))
        env, state = activate(
            cfg,
            "a",
            {
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.proxy",
                "GIT_CONFIG_VALUE_0": "proxy",
            },
        )
        env["GIT_CONFIG_VALUE_0"] = "different"
        with self.assertRaises(TransitionError):
            transition(cfg, None, env, state)

    def test_invalid_runtime_atomic_failure(self):
        cfg = config(profile("a", git={"name": "Jane", "email": "jane@example.com"}))
        for base in (
            {"GIT_CONFIG_COUNT": ""},
            {"GIT_CONFIG_COUNT": "-1"},
            {"GIT_CONFIG_COUNT": "1"},
            {"GIT_CONFIG_COUNT": "999999999"},
        ):
            with self.subTest(base=base), self.assertRaises(TransitionError):
                transition(cfg, "a", base)

    def test_conflicts_report_names_only(self):
        cfg = config(
            profile(
                "a",
                github={"config_dir": "~/github", "expected_user": "jane-work"},
                git={"name": "Jane", "email": "jane@example.com"},
            )
        )
        for key in (
            "GH_TOKEN",
            "GITHUB_TOKEN",
            "GIT_AUTHOR_NAME",
            "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME",
            "GIT_COMMITTER_EMAIL",
        ):
            env = {key: "private-value"}
            with self.subTest(key=key), self.assertRaises(TransitionError) as raised:
                transition(cfg, "a", env)
            self.assertIn(key, str(raised.exception))
            self.assertNotIn("private-value", str(raised.exception))
        transition(cfg, "a", {"GH_TOKEN": "", "GIT_AUTHOR_NAME": "", "HOME": "/example"})

    def test_unknown_profile_and_invalid_state_atomic(self):
        cfg = config(profile("a", env={"VALUE": "a"}))
        env, state = activate(cfg, "a", {})
        original = deepcopy(state)
        with self.assertRaises(TransitionError):
            transition(cfg, "missing", env, state)
        self.assertEqual(state, original)
        for broken in ({}, {"version": 1}, {**state, "baseline": {"BASH_ENV": "x"}}):
            with self.subTest(broken=broken), self.assertRaises(ValueError):
                transition(cfg, "a", env, broken)

    def test_inherited_context_becomes_new_baseline(self):
        cfg = config(
            profile("a", git={"name": "Jane", "email": "jane@example.com"}),
            profile("b", env={"VALUE": "b"}),
        )
        inherited, _ = activate(cfg, "a", {})
        env, state = activate(cfg, "b", inherited)
        self.assertEqual(activate(cfg, None, env, state)[0], inherited)
        self.assertEqual(transition(cfg, None, inherited)[0].set, {})

    def test_compile_values_literal_and_paths_quoted(self):
        with tempfile.TemporaryDirectory() as directory:
            identity = Path(directory) / "key 'quoted' $(false)"
            identity.touch()
            item = profile(
                "a",
                env={"VALUE": "$(touch /tmp/never)\n`false` $HOME"},
                git_ssh={"identity_file": "~/key 'quoted' $(false)", "identities_only": True},
                github={
                    "config_dir": "~/github/$HOME",
                    "hostname": "example.com",
                    "expected_user": "jane_work",
                },
            )
            compiled = compile_profile(item, {"HOME": directory})
            self.assertEqual(compiled.values["VALUE"], "$(touch /tmp/never)\n`false` $HOME")
            self.assertEqual(
                shlex.split(compiled.values["GIT_SSH_COMMAND"]),
                ["ssh", "-i", str(identity), "-o", "IdentitiesOnly=yes"],
            )
            self.assertEqual(compiled.values["GH_CONFIG_DIR"], directory + "/github/$HOME")
            self.assertEqual(compiled.values["GH_HOST"], "example.com")

    def test_semantic_paths_reject_relative_paths_atomically(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = config(
                profile("good", env={"VALUE": "good"}),
                profile("ssh", git_ssh={"identity_file": "relative-key"}),
                profile(
                    "github", github={"config_dir": "relative-gh", "expected_user": "jane-work"}
                ),
            )
            env, state = activate(cfg, "good", {"HOME": directory})
            saved_env, saved_state = deepcopy(env), deepcopy(state)
            for name, field in (("ssh", "git_ssh.identity_file"), ("github", "github.config_dir")):
                with self.subTest(name=name), self.assertRaises(TransitionError) as raised:
                    transition(cfg, name, env, state)
                self.assertIn(field, str(raised.exception))
                self.assertNotIn("relative-", str(raised.exception))
                self.assertEqual((env, state), (saved_env, saved_state))

    def test_semantic_paths_use_restored_and_destination_home(self):
        with tempfile.TemporaryDirectory() as directory:
            homes = [Path(directory) / name for name in ("original", "previous", "destination")]
            for home in homes:
                (home / ".ssh").mkdir(parents=True)
                (home / ".ssh" / "key").touch()
            original, previous, destination = map(str, homes)
            cfg = config(
                profile("a", env={"HOME": previous}),
                profile(
                    "b",
                    git_ssh={"identity_file": "~/.ssh/key"},
                    github={"config_dir": "~/github", "expected_user": "jane-work"},
                ),
                profile(
                    "c",
                    env={"HOME": destination},
                    git_ssh={"identity_file": "~/.ssh/key"},
                    github={"config_dir": "~/github", "expected_user": "jane-work"},
                ),
            )
            env, state = activate(cfg, "a", {"HOME": original})
            env, state = activate(cfg, "b", env, state)
            self.assertEqual(env["HOME"], original)
            self.assertEqual(shlex.split(env["GIT_SSH_COMMAND"])[2], original + "/.ssh/key")
            self.assertEqual(env["GH_CONFIG_DIR"], original + "/github")
            env, state = activate(cfg, "c", env, state)
            self.assertEqual(env["HOME"], destination)
            self.assertEqual(shlex.split(env["GIT_SSH_COMMAND"])[2], destination + "/.ssh/key")
            self.assertEqual(env["GH_CONFIG_DIR"], destination + "/github")
            self.assertEqual(activate(cfg, None, env, state)[0], {"HOME": original})

    def test_single_tilde_uses_effective_home(self):
        compiled = compile_profile(
            profile("a", github={"config_dir": "~", "expected_user": "jane-work"}),
            {"HOME": "/example"},
        )
        self.assertEqual(compiled.values["GH_CONFIG_DIR"], "/example")

    def test_tilde_path_with_unset_or_relative_effective_home_fails(self):
        for values in ({"unset_env": ["HOME"]}, {"env": {"HOME": "relative-home"}}):
            cfg = config(
                profile(
                    "a", github={"config_dir": "~/github", "expected_user": "jane-work"}, **values
                )
            )
            with self.subTest(values=values), self.assertRaises(TransitionError):
                transition(cfg, "a", {"HOME": "/original"})

    def test_previous_profile_token_is_not_removed_to_avoid_conflict(self):
        cfg = config(
            profile("a", env={"GH_TOKEN": "fictional-token"}),
            profile("b", github={"config_dir": "/fictional/github", "expected_user": "jane-work"}),
        )
        env, state = activate(cfg, "a", {})
        before = deepcopy(state)
        with self.assertRaises(TransitionError) as raised:
            transition(cfg, "b", env, state)
        self.assertEqual(str(raised.exception), "Conflicting environment variable: GH_TOKEN")
        self.assertEqual(state, before)
        self.assertEqual(env["GH_TOKEN"], "fictional-token")

    def test_missing_ssh_identity_is_atomic_and_does_not_leak_path(self):
        with tempfile.TemporaryDirectory() as directory:
            cfg = config(
                profile("good", env={"VALUE": "a"}),
                profile(
                    "missing", git_ssh={"identity_file": str(Path(directory) / "private-name")}
                ),
                profile("directory", git_ssh={"identity_file": directory}),
            )
            env, state = activate(cfg, "good", {})
            saved_env, saved_state = deepcopy(env), deepcopy(state)
            for name in ("missing", "directory"):
                with self.subTest(name=name), self.assertRaises(TransitionError) as raised:
                    transition(cfg, name, env, state)
                self.assertIn("git_ssh.identity_file", str(raised.exception))
                self.assertNotIn(directory, str(raised.exception))
                self.assertEqual((env, state), (saved_env, saved_state))

    def test_a_only_restored_then_user_modified_is_external(self):
        cfg = config(profile("a", env={"A_ONLY": "a"}), profile("b", env={"B_ONLY": "b"}))
        env, state = activate(cfg, "a", {"A_ONLY": "original"})
        env, state = activate(cfg, "b", env, state)
        self.assertEqual(env["A_ONLY"], "original")
        env["A_ONLY"] = "external-change"
        env, _ = activate(cfg, None, env, state)
        self.assertEqual(env["A_ONLY"], "external-change")

    def test_runtime_multivalued_helper_reset_and_signing(self):
        item = profile(
            "a",
            git={
                "config": {"credential.helper": ["", "custom"]},
                "signing_key": "key",
                "signing_format": "ssh",
                "sign_commits": True,
            },
        )
        compiled = compile_profile(item, {})
        self.assertEqual(
            compiled.runtime[:2], (("credential.helper", ""), ("credential.helper", "custom"))
        )
        self.assertIn(("commit.gpgSign", "true"), compiled.runtime)
        self.assertNotIn("GIT_AUTHOR_NAME", compiled.values)

    def test_real_git_explicit_author_survives_cherry_pick_and_rebase(self):
        cfg = config(
            profile("a", git={"name": "Work User", "email": "work@example.com"}),
            profile("b", git={"name": "Personal User", "email": "personal@example.com"}),
        )
        for operation in ("cherry-pick", "rebase"):
            with self.subTest(operation=operation), tempfile.TemporaryDirectory() as directory:
                base = {
                    key: value
                    for key, value in os.environ.items()
                    if not key.startswith(("GIT_", "DEVWHO_"))
                }
                base.update(HOME=directory, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
                env, state = activate(cfg, "a", base)

                def git(*args):
                    return subprocess.check_output(
                        ["git", *args], cwd=directory, env=env, text=True, stderr=subprocess.STDOUT
                    ).strip()

                git("init", "-q")
                git("checkout", "-qb", "main")
                git("commit", "--allow-empty", "-qm", "base")
                git("checkout", "-qb", "source")
                Path(directory, "source.txt").write_text("source change")
                git("add", "source.txt")
                git("commit", "--author=Original Author <original@example.com>", "-qm", "source")
                # Assert the fixture really has a different author before replay.
                self.assertEqual(
                    git("log", "-1", "--format=%an <%ae>|%cn <%ce>"),
                    "Original Author <original@example.com>|Work User <work@example.com>",
                )
                commit = git("rev-parse", "HEAD")
                git("checkout", "-q", "main")
                env, state = activate(cfg, "b", env, state)
                Path(directory, "main.txt").write_text("unrelated main change")
                git("add", "main.txt")
                git("commit", "-qm", "main diverged")
                if operation == "cherry-pick":
                    git("cherry-pick", commit)
                else:
                    git("rebase", "main", "source")
                self.assertEqual(
                    git("log", "-1", "--format=%an <%ae>|%cn <%ce>"),
                    "Original Author <original@example.com>|Personal User <personal@example.com>",
                )
                self.assertEqual(Path(directory, "source.txt").read_text(), "source change")

    def test_real_git_identity_and_replay_author(self):
        cfg = config(
            profile("a", git={"name": "Jane Doe", "email": "jane@example.com"}),
            profile("b", git={"name": "Other User", "email": "other@example.com"}),
        )
        with tempfile.TemporaryDirectory() as directory:
            base = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith(("GIT_", "DEVWHO_"))
            }
            base.update(HOME=directory, GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull)
            env, state = activate(cfg, "a", base)

            def git(*args):
                return subprocess.check_output(
                    ["git", *args], cwd=directory, env=env, text=True, stderr=subprocess.STDOUT
                ).strip()

            git("init", "-q")
            git("checkout", "-q", "-b", "source")
            git("commit", "-q", "--allow-empty", "-m", "original")
            commit = git("rev-parse", "HEAD")
            git("checkout", "-q", "--orphan", "replayed")
            env, state = activate(cfg, "b", env, state)
            self.assertIn("Other User <other@example.com>", git("var", "GIT_AUTHOR_IDENT"))
            git("cherry-pick", "--allow-empty", commit)
            self.assertEqual(
                git("log", "-1", "--format=%an <%ae>|%cn <%ce>"),
                "Jane Doe <jane@example.com>|Other User <other@example.com>",
            )
            env, _ = activate(cfg, None, env, state)
            self.assertNotIn("GIT_CONFIG_COUNT", env)


if __name__ == "__main__":
    unittest.main()
