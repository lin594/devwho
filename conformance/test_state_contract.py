"""Shared JSON state contracts and real-shell transition preflight."""

import json
from pathlib import Path
import shutil
import subprocess

from conformance.support import ContractCase, EXECUTABLE


VECTORS = json.loads(
    (Path(__file__).with_name("fixtures") / "state-contract.json").read_text(encoding="utf-8")
)


class StateContract(ContractCase):
    def setUp(self):
        super().setUp()
        self.config.write_text(VECTORS["config_toml"], encoding="utf-8")

    def test_invalid_json_state_vectors_emit_no_patch(self):
        for vector in VECTORS["invalid_states"]:
            with self.subTest(vector=vector["id"]):
                result = self.invoke(
                    "internal",
                    "transition",
                    "--shell",
                    "bash",
                    "--restore",
                    env=dict(self.env, DEVWHO_PROFILE="atlas"),
                    state=json.dumps(vector["state"]),
                )
                self.assertEqual(result.returncode, vector["status"], result.stderr)
                self.assertEqual(result.stdout, "")

    def test_json_operations_match_expected_environment_and_state(self):
        for vector in VECTORS["operation_sequences"]:
            with self.subTest(vector=vector["id"]):
                env, state = dict(self.env, **vector["initial_env"]), None
                for index, operation in enumerate(vector["operations"]):
                    with self.subTest(operation=index):
                        env, state = self.transition(operation["activate"], env, state)
                        self.assertEqual(env, dict(self.env, **operation["expected_env"]))
                        self.assertEqual(state, operation["expected_state"])

    def test_state_over_one_mib_is_rejected_before_output(self):
        # Structurally valid state; only the transport size should cause failure.
        state = {
            "version": 1,
            "profile": "atlas",
            "runtime": None,
            "managed": ["DEVWHO_PROFILE"],
            "baseline": {"DEVWHO_PROFILE": None, "CASE_PAYLOAD": "x" * (1024 * 1024)},
        }
        result = self.invoke(
            "internal",
            "transition",
            "--shell",
            "bash",
            "--restore",
            state=json.dumps(state),
        )
        self.assertEqual(result.returncode, 1, result.stderr)
        self.assertEqual(result.stdout, "")

    def test_normal_sized_literal_state_roundtrip(self):
        self.config.write_text('version=1\n[profiles.payload.env]\nCASE_PAYLOAD="active"\n')
        value = "literal $HOME 'quote' \\ newline\n雪\t" * 512
        baseline = dict(self.env, CASE_PAYLOAD=value)
        env, state = self.transition("payload", baseline)
        encoded = json.dumps(state).encode("utf-8")
        self.assertGreater(len(encoded), 16 * 1024)
        self.assertLess(len(encoded), 1024 * 1024)
        self.assertEqual(state["baseline"]["CASE_PAYLOAD"], value)
        self.assertEqual(self.transition(None, env, state), (baseline, None))

    def check_array_preflight(self, shell):
        executable = shutil.which(shell)
        if executable is None:
            self.skipTest(f"{shell} is unavailable")
        self.config.write_text(
            'version=1\n[profiles.seed.env]\nCASE_BEFORE="seed"\n'
            '[profiles.blocked.env]\nCASE_BEFORE="changed"\nCASE_Z_ARRAY="scalar"\n'
        )
        # CASE_BEFORE sorts before the array: an implementation that mutates
        # while checking would corrupt it before discovering the array.
        script = """set -e
eval "$("$CASE_CORE" --config "$CASE_CONFIG" init SHELL_NAME)"
setdev seed
CASE_Z_ARRAY=('original first' 'original second')
CASE_SAVED_STATE=$__DEVWHO_STATE
if setdev blocked; then
  printf 'unexpected successful activation\n'
  exit 91
fi
[ "$CASE_BEFORE" = seed ]
[ "$DEVWHO_PROFILE" = seed ]
[ "$__DEVWHO_STATE" = "$CASE_SAVED_STATE" ]
[ "${#CASE_Z_ARRAY[@]}" -eq 2 ]
printf '%s\\0' "${CASE_Z_ARRAY[@]}"
unsetdev
[ "${CASE_BEFORE-present}" = present ]
[ "${DEVWHO_PROFILE-present}" = present ]
""".replace("SHELL_NAME", shell)
        result = subprocess.run(
            [executable, *(["--noprofile", "--norc"] if shell == "bash" else ["-f"]), "-c", script],
            env=dict(self.env, CASE_CORE=str(EXECUTABLE), CASE_CONFIG=str(self.config)),
            cwd=self.root,
            capture_output=True,
            text=True,
            timeout=30,
        )
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout, "original first\0original second\0")
        self.assertIn("array", result.stderr.lower())

    def test_bash_array_preflight_is_atomic(self):
        self.check_array_preflight("bash")

    def test_zsh_array_preflight_is_atomic(self):
        self.check_array_preflight("zsh")
