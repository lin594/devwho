#!/usr/bin/env python3
"""Executable native-consumer cases, independent of any compatibility core API."""

import argparse
import json
import os
from pathlib import Path
import subprocess
import tempfile


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--consumer", required=True, type=Path)
    parser.add_argument("--producer", action="append", type=Path, default=[])
    args = parser.parse_args()
    consumer = str(args.consumer.resolve())
    producers = [str(path.resolve()) for path in args.producer]
    cases = json.loads(Path(__file__).with_name("selection.json").read_text())["cases"]
    with tempfile.TemporaryDirectory(prefix="native-consumer-") as temporary:
        root = Path(temporary)
        config = root / "app.json"
        config.write_text(
            json.dumps(
                {
                    "default_account": "personal",
                    "accounts": {"personal": "personal.txt", "work-account": "work.txt"},
                    "profiles": {"work": "work-account"},
                }
            )
        )
        env = {"PATH": os.environ["PATH"], "HOME": str(root)}
        for case in cases:
            selected = dict(env)
            if case["env_present"]:
                selected["DEVWHO_PROFILE"] = case["env"]
            argv = [consumer, "--config", str(config)]
            if case["explicit"]:
                argv.extend(["--account", case["explicit"]])
            result = subprocess.run(
                [*argv, "status"],
                env=selected,
                cwd=root,
                capture_output=True,
                text=True,
                timeout=10,
            )
            if "error" in case:
                assert result.returncode != 0, case["name"]
                result = subprocess.run(
                    [*argv, "add", "must not write"],
                    env=selected,
                    cwd=root,
                    capture_output=True,
                    timeout=10,
                )
                assert result.returncode != 0, case["name"]
                assert not (root / "personal.txt").exists(), case["name"]
                assert not (root / "work.txt").exists(), case["name"]
            else:
                assert result.returncode == 0, result.stderr
                assert result.stdout == "account=" + case["want"] + "\n", case["name"]

        # Plain environment is sufficient: no compatibility core is involved.
        base = [consumer, "--config", str(config)]
        subprocess.run(
            [*base, "add", "plain"],
            env={**env, "DEVWHO_PROFILE": "work"},
            check=True,
            cwd=root,
            timeout=10,
        )
        source = root / "producer.env"
        source.write_text("DEVWHO_PROFILE=work\n")
        for producer in producers:
            subprocess.run(
                [producer, "--env-file", str(source), "exec", "work", "--", *base, "add", "dotenv"],
                env=env,
                cwd=root,
                check=True,
                timeout=30,
            )
        assert (root / "work.txt").read_text() == "plain\n" + "dotenv\n" * len(producers)
        assert not (root / "personal.txt").exists()
        output = subprocess.check_output(
            [*base, "list"], env={**env, "DEVWHO_PROFILE": "work"}, cwd=root, text=True, timeout=10
        )
        assert output == (root / "work.txt").read_text()
    print(
        f"Native consumer passed {len(cases)} selection cases and {len(producers)} producer integrations"
    )


if __name__ == "__main__":
    main()
