"""Real Bash and Zsh integration tests for DevWho shell functions.

Every test uses an isolated HOME, XDG config directory, DevWho config and Git
repository. No user startup files or network services are involved.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import selectors
import shutil
import subprocess
import tempfile
import unittest


REPO = Path(__file__).resolve().parents[1]
DEVWHO = Path(os.environ.get("DEVWHO_TEST_EXECUTABLE", REPO / "bin" / "devwho")).resolve()
SHELLS = ("bash", "zsh")
SHELL_EXES = {
    name: os.environ.get("DEVWHO_TEST_" + name.upper())
    or ("/bin/" + name if Path("/bin/" + name).exists() else shutil.which(name))
    for name in SHELLS
}
TRACKED_ENV = (
    "DEVWHO_PROFILE",
    "GH_CONFIG_DIR",
    "GIT_AUTHOR_NAME",
    "GIT_AUTHOR_EMAIL",
    "GIT_COMMITTER_NAME",
    "GIT_COMMITTER_EMAIL",
    "GIT_CONFIG_COUNT",
    "GIT_CONFIG_KEY_0",
    "GIT_CONFIG_VALUE_0",
    "GIT_SSH_COMMAND",
    "HTTPS_PROXY",
    "HTTP_PROXY",
    "ALL_PROXY",
)


class ShellCase(unittest.TestCase):
    shell = None

    def setUp(self):
        if not DEVWHO.exists():
            self.skipTest("bin/devwho has not been created yet")
        if not self.executable or not Path(self.executable).exists():
            self.skipTest(
                f"{self.shell} executable not available; set DEVWHO_TEST_{self.shell.upper()}"
            )
        self.tmp = tempfile.TemporaryDirectory(prefix="devwho-shell-test-")
        self.root = Path(self.tmp.name)
        self.home = self.root / "home"
        self.home.mkdir()
        self.xdg = self.root / "xdg"
        self.xdg.mkdir()
        self.config = self.root / "devwho.toml"
        self.write_config()
        self.launchers = self.root / "launchers"
        self.launchers.mkdir()
        (self.launchers / "devwho").symlink_to(DEVWHO)
        self.repo = self.root / "repo"
        self.repo.mkdir()
        self.git(["init", "-q", "-b", "main"], cwd=self.repo)
        self.git(["config", "user.name", "Wrong Local User"], cwd=self.repo)
        self.git(["config", "user.email", "wrong@example.invalid"], cwd=self.repo)
        self.base_env = self.clean_env()
        self.base_env.update(
            {
                "HOME": str(self.home),
                "XDG_CONFIG_HOME": str(self.xdg),
                "DEVWHO_CONFIG": str(self.config),
                "GIT_CONFIG_NOSYSTEM": "1",
                "GIT_CONFIG_GLOBAL": os.devnull,
                "PATH": str(self.launchers) + os.pathsep + os.environ.get("PATH", ""),
            }
        )

    def tearDown(self):
        self.tmp.cleanup()

    @staticmethod
    def clean_env():
        env = dict(os.environ)
        for key in list(env):
            if (
                key.startswith(("DEVWHO_", "__DEVWHO", "GIT_"))
                or key in TRACKED_ENV
                or key in {"GH_TOKEN", "GITHUB_TOKEN", "GH_HOST", "ZDOTDIR", "BASH_ENV", "ENV"}
            ):
                env.pop(key, None)
        return env

    def write_config(self, *, defaults=True, profiles=None):
        profiles = profiles or {
            "personal": {
                "name": "Personal User",
                "email": "personal@example.invalid",
                "env": {"GH_CONFIG_DIR": str(self.root / "gh-personal"), "PERSONAL_ONLY": "p"},
                "unset_env": ["GIT_SSH_COMMAND"],
            },
            "work": {
                "name": "Work User",
                "email": "work@example.invalid",
                "env": {"GH_CONFIG_DIR": str(self.root / "gh-work"), "WORK_ONLY": "w"},
            },
        }
        lines = ["version = 1"]
        if defaults:
            lines += ["[settings]", 'default_profile = "personal"', 'shortcut_profile = "work"']
        for profile, data in profiles.items():
            if data.get("unset_env"):
                lines += [
                    f"[profiles.{profile}]",
                    "unset_env = " + json.dumps(data["unset_env"], ensure_ascii=False),
                ]
            lines += [
                f"[profiles.{profile}.git]",
                f"name = {json.dumps(data['name'])}",
                f"email = {json.dumps(data['email'])}",
                f"[profiles.{profile}.env]",
            ]
            for key, value in data.get("env", {}).items():
                lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
            if data.get("git_ssh"):
                lines.append(f"[profiles.{profile}.git_ssh]")
                for key, value in data["git_ssh"].items():
                    lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
        self.config.write_text("\n".join(lines) + "\n", encoding="utf-8")

    def git(self, args, *, cwd=None, env=None):
        return subprocess.run(
            ["git", *args], cwd=cwd, env=env, check=True, text=True, capture_output=True
        ).stdout.strip()

    def cli(self, *args, env=None, check=True):
        return subprocess.run(
            [str(DEVWHO), "--config", str(self.config), *args],
            env=env or self.base_env,
            check=check,
            text=True,
            capture_output=True,
        )

    def shell_command(self, script, *, env=None, check=True):
        script = "set -e\n" + script
        args = (
            [self.executable, "-f", "-c", script]
            if self.shell == "zsh"
            else [self.executable, "--noprofile", "--norc", "-c", script]
        )
        result = subprocess.run(
            args,
            env=env or self.base_env,
            cwd=self.repo,
            check=False,
            text=True,
            capture_output=True,
        )
        if check and result.returncode:
            self.fail(
                f"{self.shell} exited {result.returncode}\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
            )
        return result

    def init_code(self):
        return self.cli("init", self.shell).stdout

    def initialized_script(self, body):
        # eval is the documented shell integration boundary; init output itself
        # must consist solely of shell code.
        return 'eval "$(devwho --config "$DEVWHO_CONFIG" init ' + self.shell + ')"\n' + body

    def initialized_env(self):
        env = dict(self.base_env)
        env["DEVWHO"] = str(DEVWHO)
        return env

    def start_shell(self):
        return PersistentShell(self.executable, self.shell, self.base_env, self.config)


def make_shell_case(shell):
    return type(
        f"{shell.title()}IntegrationTests",
        (ShellCase,),
        {"shell": shell, "executable": SHELL_EXES[shell]},
    )


class ShellIntegrationMixin:
    def test_init_output_is_sourceable_and_current_prints_one_value(self):
        result = self.cli("init", self.shell)
        self.assertEqual(result.stderr, "")
        env = self.initialized_env()
        sourced = self.shell_command(
            'eval "$(' + str(DEVWHO) + ' --config "$DEVWHO_CONFIG" init ' + self.shell + ')"\n'
            'devwho --config "$DEVWHO_CONFIG" current\nprintf "sentinel\\n"\n',
            env=env,
        )
        self.assertEqual(sourced.stdout.splitlines(), ["personal", "sentinel"])
        self.assertEqual(self.cli("current").stdout.strip(), "none")

    def test_two_live_shells_keep_independent_profiles(self):
        a, b = self.start_shell(), self.start_shell()
        try:
            a.command("setdev work")
            b.command("setdev personal")
            self.assertIn(
                "A:work:" + str(self.root / "gh-work"),
                a.command('printf "A:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"'),
            )
            self.assertIn(
                "B:personal:" + str(self.root / "gh-personal"),
                b.command('printf "B:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"'),
            )
            self.assertIn(
                "A-still:work:" + str(self.root / "gh-work"),
                a.command('printf "A-still:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"'),
            )
        finally:
            a.close()
            b.close()

    def test_repeated_same_profile_is_idempotent(self):
        result = self.shell_command(
            self.initialized_script(
                'setdev work\nfirst="$(env | grep "^GIT_CONFIG_" | sort)"\n'
                'setdev work\nsecond="$(env | grep "^GIT_CONFIG_" | sort)"\n'
                'printf "idempotent:%s\\n" "$([ "$first" = "$second" ] && echo yes || echo no)"\n'
            ),
            env=self.initialized_env(),
        )
        self.assertIn("idempotent:yes", result.stdout)

    def test_readonly_environment_failure_does_not_partially_activate(self):
        result = self.shell_command(
            self.initialized_script(
                'readonly WORK_ONLY=locked\nbefore="$(devwho current)|$GH_CONFIG_DIR|$GIT_CONFIG_COUNT"\n'
                'setdev work 2>/dev/null || :\nafter="$(devwho current)|$GH_CONFIG_DIR|$GIT_CONFIG_COUNT"\n'
                'printf "readonly-unchanged:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=self.initialized_env(),
        )
        self.assertIn("readonly-unchanged:yes", result.stdout)

    def test_typed_variable_is_rejected_before_literal_can_be_evaluated(self):
        marker = self.root / "arithmetic-marker"
        self.write_config(
            profiles={
                "personal": {
                    "name": "Personal User",
                    "email": "personal@example.invalid",
                    "env": {},
                },
                "work": {
                    "name": "Work User",
                    "email": "work@example.invalid",
                    "env": {"INJECTION_TARGET": "$(touch " + str(marker) + ")"},
                },
            }
        )
        declaration = (
            "declare -i INJECTION_TARGET" if self.shell == "bash" else "typeset -i INJECTION_TARGET"
        )
        result = self.shell_command(
            self.initialized_script(
                declaration
                + '\nbefore="$(devwho current)|${INJECTION_TARGET-unset}|$GIT_CONFIG_COUNT"\n'
                "setdev work 2>/dev/null || :\n"
                'after="$(devwho current)|${INJECTION_TARGET-unset}|$GIT_CONFIG_COUNT"\n'
                'printf "typed-unchanged:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=self.initialized_env(),
        )
        self.assertIn("typed-unchanged:yes", result.stdout)
        self.assertFalse(marker.exists())

    def test_zsh_string_transform_attributes_are_rejected_atomically(self):
        if self.shell != "zsh":
            self.skipTest("Zsh-only scalar transformation attributes")
        profile_values = {
            "VALUE_LOWER": "Mixed Case",
            "VALUE_UPPER": "Mixed Case",
            "VALUE_LEFT": "Mixed Case",
            "VALUE_RIGHT": "Mixed Case",
            "VALUE_ZERO": "Mixed Case",
        }
        self.write_config(
            profiles={
                "personal": {
                    "name": "Personal User",
                    "email": "personal@example.invalid",
                    "env": {"GH_CONFIG_DIR": str(self.root / "gh-personal")},
                },
                "work": {
                    "name": "Work User",
                    "email": "work@example.invalid",
                    "env": profile_values,
                },
            }
        )
        declarations = (
            "typeset -l VALUE_LOWER",
            "typeset -u VALUE_UPPER",
            "typeset -L 20 VALUE_LEFT",
            "typeset -R 20 VALUE_RIGHT",
            "typeset -Z 20 VALUE_ZERO",
        )
        commands = []
        for declaration in declarations:
            commands.extend(
                (
                    declaration,
                    'before="$(devwho current)|$GH_CONFIG_DIR|$GIT_CONFIG_COUNT"',
                    "setdev work 2>/dev/null || :",
                    'after="$(devwho current)|$GH_CONFIG_DIR|$GIT_CONFIG_COUNT"',
                    '[ "$before" = "$after" ] || exit 19',
                )
            )
        commands.append("printf 'zsh-transform-unchanged:yes\\n'")
        result = self.shell_command(
            self.initialized_script("\n".join(commands) + "\n"), env=self.initialized_env()
        )
        self.assertIn("zsh-transform-unchanged:yes", result.stdout)

    def test_doctor_does_not_switch_the_current_shell(self):
        result = self.shell_command(
            self.initialized_script(
                'before="$(devwho current)|$GH_CONFIG_DIR"\n'
                'devwho --config "$DEVWHO_CONFIG" doctor work --offline >/dev/null 2>&1 || :\n'
                'after="$(devwho current)|$GH_CONFIG_DIR"\n'
                'printf "doctor-readonly:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=self.initialized_env(),
        )
        self.assertIn("doctor-readonly:yes", result.stdout)

    def test_init_bootstraps_default_and_shortcut_restores_baseline(self):
        env = self.initialized_env()
        result = self.shell_command(
            self.initialized_script(
                'printf "init:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
                'setdev\nprintf "shortcut:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
                'unsetdev\nprintf "restored:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
            ),
            env=env,
        )
        self.assertIn(f"init:personal:{self.root / 'gh-personal'}", result.stdout)
        self.assertIn(f"shortcut:work:{self.root / 'gh-work'}", result.stdout)
        self.assertIn(f"restored:personal:{self.root / 'gh-personal'}", result.stdout)

    def test_setdev_is_shell_local_and_child_inherits_active_patch(self):
        script = self.initialized_script(
            'setdev work\nprintf "parent:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
            'env | sort > "$HOME/child-env"\n'
            'sh -c \'printf "child:%s:%s\\n" "$WORK_ONLY" "$GH_CONFIG_DIR"\'\n'
            'bash --noprofile --norc -c \'eval "$("$DEVWHO" --config "$DEVWHO_CONFIG" init bash)"; printf "grandchild:%s:%s\\n" "$("$DEVWHO" --config "$DEVWHO_CONFIG" current)" "$GH_CONFIG_DIR"\'\n'
            'printf "parent-after:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
        )
        result = self.shell_command(script, env=self.initialized_env())
        self.assertIn(f"parent:work:{self.root / 'gh-work'}", result.stdout)
        self.assertIn(f"child:w:{self.root / 'gh-work'}", result.stdout)
        self.assertIn(f"grandchild:work:{self.root / 'gh-work'}", result.stdout)
        self.assertIn(f"parent-after:work:{self.root / 'gh-work'}", result.stdout)
        exported = (self.home / "child-env").read_text(encoding="utf-8")
        self.assertNotIn("__DEVWHO_STATE=", exported)

    def test_git_consumers_use_profile_over_local_user_and_preserve_replay_author(self):
        env = self.initialized_env()
        script = self.initialized_script(
            "setdev work\nprintf test > tracked.txt\ngit add tracked.txt\n"
            'git commit -qm work\ngit log -1 --format="commit:%an|%ae|%cn|%ce"\n'
            "git checkout -qb feature\nprintf feature > feature.txt\ngit add feature.txt\n"
            "git commit -qm feature\n"
            "printf source > authored.txt\ngit add authored.txt\n"
            'GIT_AUTHOR_NAME="Original Author" GIT_AUTHOR_EMAIL=author@example.invalid '
            "git commit -qm authored-by-other\n"
            'git log -1 --format="source:%an|%ae|%cn|%ce"\n'
            "sha=$(git rev-parse HEAD)\ngit checkout -q main\n"
            'setdev personal\ngit cherry-pick "$sha"\n'
            'git log -1 --format="replay:%an|%ae|%cn|%ce"\n'
        )
        result = self.shell_command(script, env=env)
        self.assertIn(
            "commit:Work User|work@example.invalid|Work User|work@example.invalid", result.stdout
        )
        self.assertIn(
            "source:Original Author|author@example.invalid|Work User|work@example.invalid",
            result.stdout,
        )
        self.assertIn(
            "replay:Original Author|author@example.invalid|Personal User|personal@example.invalid",
            result.stdout,
        )

    def test_env_patch_is_literal_and_preserves_proxy_and_runtime_git_config(self):
        evil = (
            "quote' \" $HOME `touch "
            + str(self.root / "marker3")
            + "` ; & | \\ touch "
            + str(self.root / "marker")
            + " $(touch "
            + str(self.root / "marker2")
            + ")\nline 雪\x01"
        )
        self.write_config(
            profiles={
                "personal": {
                    "name": "Personal User",
                    "email": "personal@example.invalid",
                    "env": {},
                },
                "work": {
                    "name": "Work User",
                    "email": "work@example.invalid",
                    "env": {
                        "EVIL_VALUE": evil,
                        "WORK_ONLY": "present",
                        "GIT_SSH_COMMAND": "ssh -F /missing/devwho-test-ssh-config",
                    },
                },
            }
        )
        env = self.initialized_env()
        env.update(
            {
                "HTTP_PROXY": "http://127.0.0.1:8899",
                "GIT_CONFIG_COUNT": "1",
                "GIT_CONFIG_KEY_0": "http.proxy",
                "GIT_CONFIG_VALUE_0": "http://127.0.0.1:8899",
            }
        )
        script = self.initialized_script(
            'setdev work\nprintf "value-begin\\n%s\\nvalue-end\\n" "$EVIL_VALUE"\n'
            'printf "proxy:%s:%s:%s:%s:%s\\n" "$HTTP_PROXY" "$GIT_CONFIG_COUNT" "$GIT_CONFIG_KEY_0" "$GIT_CONFIG_KEY_1" "$GIT_CONFIG_KEY_2"\n'
            "append_index=$GIT_CONFIG_COUNT\n"
            'eval "export GIT_CONFIG_KEY_${append_index}=http.sslVerify"\n'
            'eval "export GIT_CONFIG_VALUE_${append_index}=true"\n'
            "GIT_CONFIG_COUNT=$((append_index + 1)); export GIT_CONFIG_COUNT\n"
            'setdev personal\nprintf "after:%s:%s\\n" "$GIT_CONFIG_COUNT" "${WORK_ONLY-unset}"\n'
            'printf "appended-consumer:%s\\n" "$(git config --get http.sslVerify)"\n'
        )
        result = self.shell_command(script, env=env)
        self.assertIn("value-begin\n" + evil + "\nvalue-end", result.stdout)
        self.assertIn("proxy:http://127.0.0.1:8899:", result.stdout)
        self.assertIn("http.proxy", result.stdout)
        self.assertIn("after:", result.stdout)
        self.assertIn("appended-consumer:true", result.stdout)
        self.assertEqual(list(self.root.glob("marker*")), [])

    def test_relative_config_is_pinned_across_directory_change(self):
        env = self.initialized_env()
        env["DEVWHO_REL_CONFIG"] = os.path.relpath(self.config, self.repo)
        script = (
            'eval "$("$DEVWHO" --config "$DEVWHO_REL_CONFIG" init ' + self.shell + ')"\n'
            'cd "$HOME"\nsetdev work\nprintf "relative:%s:%s\\n" "$(devwho current)" "$GH_CONFIG_DIR"\n'
        )
        result = self.shell_command(script, env=env)
        self.assertIn(f"relative:work:{self.root / 'gh-work'}", result.stdout)

    def test_profile_switches_do_not_write_repository_or_global_git_files(self):
        global_config = self.home / ".gitconfig"
        original_global = b"[user]\n    name = Global Wrong\n    email = global@example.invalid\n"
        global_config.write_bytes(original_global)
        original_repo = (self.repo / ".git" / "config").read_bytes()
        env = self.initialized_env()
        env["GIT_CONFIG_GLOBAL"] = str(global_config)
        result = self.shell_command(
            self.initialized_script(
                'setdev work\nprintf "work:%s\\n" "$(git config --get user.name)"\n'
                'setdev personal\nprintf "personal:%s\\n" "$(git config --get user.name)"\n'
                "unsetdev\n"
            ),
            env=env,
        )
        self.assertIn("work:Work User", result.stdout)
        self.assertIn("personal:Personal User", result.stdout)
        self.assertEqual((self.repo / ".git" / "config").read_bytes(), original_repo)
        self.assertEqual(global_config.read_bytes(), original_global)

    def test_switch_restores_variables_to_original_unset_empty_and_nonempty_values(self):
        self.write_config(
            profiles={
                "personal": {
                    "name": "Personal User",
                    "email": "personal@example.invalid",
                    "env": {
                        "GH_CONFIG_DIR": str(self.root / "gh-personal"),
                        "PERSONAL_ONLY": "p",
                        "ORIGINAL_TAG": "personal",
                    },
                    "unset_env": ["GIT_SSH_COMMAND"],
                },
                "work": {
                    "name": "Work User",
                    "email": "work@example.invalid",
                    "env": {
                        "GH_CONFIG_DIR": str(self.root / "gh-work"),
                        "WORK_ONLY": "w",
                        "ORIGINAL_TAG": "work",
                        "GIT_SSH_COMMAND": "ssh -F /tmp/work-config",
                    },
                },
            },
            defaults=False,
        )
        env = self.initialized_env()
        env.pop("GH_CONFIG_DIR", None)
        env["GIT_SSH_COMMAND"] = ""
        env["ORIGINAL_TAG"] = "outer"
        script = self.initialized_script(
            'setdev work\nprintf "active:%s:%s:%s:%s\\n" "$GH_CONFIG_DIR" '
            '"${GIT_SSH_COMMAND-unset}" "${ORIGINAL_TAG-unset}" "${PERSONAL_ONLY-unset}"\n'
            'setdev personal\nprintf "personal:%s:%s:%s:%s\\n" "$GH_CONFIG_DIR" '
            '"${GIT_SSH_COMMAND-unset}" "$ORIGINAL_TAG" "$PERSONAL_ONLY"\n'
            'unsetdev\nprintf "baseline:%s:%s:%s\\n" "${GH_CONFIG_DIR-unset}" '
            '"${GIT_SSH_COMMAND-unset}" "$ORIGINAL_TAG"\n'
        )
        result = self.shell_command(script, env=env)
        self.assertIn(
            f"active:{self.root / 'gh-work'}:ssh -F /tmp/work-config:work:unset", result.stdout
        )
        self.assertIn(f"personal:{self.root / 'gh-personal'}:unset:personal:p", result.stdout)
        self.assertIn("baseline:unset::outer", result.stdout)

    def test_invalid_profile_and_missing_ssh_value_fail_without_changing_shell(self):
        env = self.initialized_env()
        result = self.shell_command(
            self.initialized_script(
                'setdev work\nbefore="$GH_CONFIG_DIR|$GIT_CONFIG_COUNT|$WORK_ONLY"\n'
                "setdev missing 2>/dev/null || :\n"
                'after="$GH_CONFIG_DIR|$GIT_CONFIG_COUNT|$WORK_ONLY"\n'
                'printf "unchanged:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=env,
        )
        self.assertIn("unchanged:yes", result.stdout)
        result = self.shell_command(
            self.initialized_script(
                'before="$GH_CONFIG_DIR|${WORK_ONLY-unset}"\n'
                "export GIT_CONFIG_COUNT=1 GIT_CONFIG_KEY_0=http.proxy\nunset GIT_CONFIG_VALUE_0\n"
                "setdev work 2>/dev/null || :\n"
                'after="$GH_CONFIG_DIR|${WORK_ONLY-unset}"\n'
                'printf "malformed-unchanged:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=env,
        )
        self.assertIn("malformed-unchanged:yes", result.stdout)
        missing_ssh = self.root / "not-created-ssh-config"
        self.write_config(
            profiles={
                "personal": {
                    "name": "Personal User",
                    "email": "personal@example.invalid",
                    "env": {},
                },
                "work": {
                    "name": "Work User",
                    "email": "work@example.invalid",
                    "git_ssh": {"identity_file": str(missing_ssh)},
                },
            }
        )
        result = self.shell_command(
            self.initialized_script(
                'before="$(devwho current)|${GIT_SSH_COMMAND-unset}|${GIT_CONFIG_COUNT-unset}"\n'
                "setdev work 2>/dev/null || :\n"
                'after="$(devwho current)|${GIT_SSH_COMMAND-unset}|${GIT_CONFIG_COUNT-unset}"\n'
                'printf "missing-ssh-unchanged:%s\\n" "$([ "$before" = "$after" ] && echo yes || echo no)"\n'
            ),
            env=self.initialized_env(),
        )
        self.assertIn("missing-ssh-unchanged:yes", result.stdout)

    def test_exec_child_and_grandchild_inherit_profile_parent_and_exit_status_survive(self):
        env = self.initialized_env()
        script = self.initialized_script(
            "before=$(devwho current)\n"
            "set +e\n"
            'devwho --config "$DEVWHO_CONFIG" exec work -- sh -c '
            '\'printf "exec:%s:%s\\n" "$WORK_ONLY" "$GH_CONFIG_DIR"; '
            'sh -c "printf grandchild:%s:%s\\\\n $WORK_ONLY $GH_CONFIG_DIR"; exit 23\'\n'
            'rc=$?\nset -e\nprintf "parent:%s:%s:%s\\n" "$before" "$(devwho current)" "$rc"\n'
        )
        result = self.shell_command(script, env=env, check=False)
        self.assertEqual(result.returncode, 0)
        self.assertIn(f"exec:w:{self.root / 'gh-work'}", result.stdout)
        self.assertIn(f"grandchild:w:{self.root / 'gh-work'}", result.stdout)
        self.assertIn("parent:personal:personal:23", result.stdout)


for _shell in SHELLS:
    _cls = make_shell_case(_shell)
    for _name, _method in ShellIntegrationMixin.__dict__.items():
        if _name.startswith("test_"):
            setattr(_cls, _name, _method)
    globals()[_cls.__name__] = _cls

del _cls, _name, _method


class PersistentShell:
    """A live shell driven through stdin; responses are delimited by sentinels."""

    def __init__(self, executable, shell, env, config):
        self.shell = shell
        args = [executable, "-f"] if shell == "zsh" else [executable, "--noprofile", "--norc"]
        self.process = subprocess.Popen(
            args,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=False,
            env=env,
            bufsize=0,
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = b""

        def quote(value):
            return "'" + str(value).replace("'", "'\\''") + "'"

        init = 'eval "$(' + quote(DEVWHO) + " --config " + quote(config) + " init " + shell + ')"'
        self.command(init)

    def command(self, command):
        if self.process.poll() is not None:
            raise AssertionError(
                "shell exited unexpectedly: " + self.process.stderr.read().decode(errors="replace")
            )
        marker = ("__DEVWHO_END_" + str(id(command)) + "__").encode()
        self.process.stdin.write(command.encode() + b"\nprintf '%s\\n' '" + marker + b"'\n")
        self.process.stdin.flush()
        while marker + b"\n" not in self.buffer:
            ready = self.selector.select(timeout=10)
            if not ready:
                raise AssertionError("timed out waiting for shell output")
            chunk = os.read(self.process.stdout.fileno(), 4096)
            if not chunk:
                raise AssertionError("shell closed stdout before response marker")
            self.buffer += chunk
        output, self.buffer = self.buffer.split(marker + b"\n", 1)
        return output.decode(errors="replace")

    def close(self):
        if self.process.poll() is None:
            self.process.stdin.write(b"exit\n")
            self.process.stdin.flush()
            self.process.wait(timeout=5)
        self.selector.close()
        self.process.stdin.close()
        self.process.stdout.close()
        self.process.stderr.close()


if __name__ == "__main__":
    unittest.main()
