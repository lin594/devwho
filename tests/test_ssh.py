"""Observe Git's actual SSH argv without networking or real credentials."""

import json
import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parent.parent
DEVWHO = Path(os.environ.get("DEVWHO_TEST_EXECUTABLE", ROOT / "bin" / "devwho")).resolve()


class GitSSHTests(unittest.TestCase):
    def test_git_invokes_selected_key_as_literal_argument(self):
        with tempfile.TemporaryDirectory(prefix="devwho-ssh-") as directory:
            home = Path(directory)
            marker = home / "should-not-exist"
            identity = home / ("身份 key ' $(touch " + str(marker).replace("/", "_") + ")")
            identity.write_text("dummy fixture; not a private key")
            fake_bin = home / "bin"
            fake_bin.mkdir()
            log = home / "ssh-argv.nul"
            (fake_bin / "ssh").write_text(
                "#!/bin/sh\nprintf '%s\\0' \"$@\" > " + shlex.quote(str(log)) + "\nexit 1\n"
            )
            (fake_bin / "ssh").chmod(0o700)
            config = home / "config.toml"
            config.write_text(
                "version = 1\n[profiles.work.git_ssh]\nidentity_file = "
                + json.dumps(str(identity), ensure_ascii=False)
                + '\nidentities_only = true\n[profiles.work.env]\nGIT_SSH_VARIANT = "ssh"\n'
            )
            env = {
                key: value
                for key, value in os.environ.items()
                if not key.startswith(("GIT_", "DEVWHO_", "__DEVWHO"))
                and key not in {"GH_TOKEN", "GITHUB_TOKEN"}
            }
            env.update(
                HOME=str(home),
                GIT_CONFIG_GLOBAL=os.devnull,
                GIT_CONFIG_NOSYSTEM="1",
                PATH=str(fake_bin) + os.pathsep + env["PATH"],
            )
            result = subprocess.run(
                [
                    str(DEVWHO),
                    "--config",
                    str(config),
                    "exec",
                    "work",
                    "--",
                    "git",
                    "ls-remote",
                    "git@example.invalid:org/repo.git",
                ],
                cwd=home,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
            )
            self.assertNotEqual(result.returncode, 0)  # The mock never serves a remote.
            self.assertTrue(log.is_file(), result.stderr)
            argv = log.read_bytes().decode().rstrip("\0").split("\0")
            self.assertEqual(argv[argv.index("-i") + 1], str(identity))
            self.assertIn("IdentitiesOnly=yes", argv)
            self.assertIn("git@example.invalid", argv)
            self.assertFalse(marker.exists())
            self.assertFalse((home / str(marker).replace("/", "_")).exists())


if __name__ == "__main__":
    unittest.main()
