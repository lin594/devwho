"""Language-neutral parsing, environment and state conformance vectors."""

import copy
import json
import os
from pathlib import Path

from conformance.support import ContractCase, EXECUTABLE


FIXTURES = Path(__file__).with_name("fixtures")


class ConfigurationVectors(ContractCase):
    def test_shared_configuration_vectors(self):
        for vector in json.loads((FIXTURES / "configurations.json").read_text()):
            with self.subTest(vector=vector["name"]):
                self.config.write_text(vector["toml"], encoding="utf-8")
                result = self.invoke("list")
                self.assertEqual(result.returncode, 0 if vector["valid"] else 1, result.stderr)
                if vector["valid"]:
                    env, state = self.transition(vector.get("profile", "a"))
                    for key, value in vector.get("env", {}).items():
                        self.assertEqual(env.get(key), value, key)
                    if "runtime" in vector:
                        pairs = [
                            [env[f"GIT_CONFIG_KEY_{i}"], env[f"GIT_CONFIG_VALUE_{i}"]]
                            for i in range(int(env.get("GIT_CONFIG_COUNT", "0")))
                        ]
                        self.assertEqual(pairs, vector["runtime"])
                    self.assertEqual(self.transition(None, env, state), (self.env, None))
                else:
                    failed = self.invoke(
                        "internal", "transition", "--shell", "bash", "--activate", "a"
                    )
                    self.assertNotEqual(failed.returncode, 0)
                    self.assertEqual(failed.stdout, "")


class TransitionVectors(ContractCase):
    def setUp(self):
        super().setUp()
        self.config.write_text((FIXTURES / "transitions.toml").read_text(), encoding="utf-8")

    def test_switch_chain_missing_empty_and_nonempty(self):
        env = dict(self.env, EMPTY="", PRESENT="outer", DROP="keep", HTTPS_PROXY="proxy")
        baseline = dict(env)
        state = None
        for profile in ("a", "a", "b", "c"):
            env, state = self.transition(profile, env, state)
            self.assertEqual(env["DEVWHO_PROFILE"], profile)
            self.assertEqual(env["HTTPS_PROXY"], "proxy")
        self.assertEqual(env["EMPTY"], "")
        self.assertNotIn("A_ONLY", env)
        self.assertEqual(env["DROP"], "keep")
        self.assertEqual(self.transition(None, env, state), (baseline, None))

    def test_ordered_git_appendages_and_orphans_survive_restore(self):
        baseline = dict(
            self.env,
            GIT_CONFIG_COUNT="1",
            GIT_CONFIG_KEY_0="http.proxy",
            GIT_CONFIG_VALUE_0="proxy",
            GIT_CONFIG_KEY_18="orphan",
            GIT_CONFIG_VALUE_18="untouched",
        )
        env, state = self.transition("a", baseline)
        index = int(env["GIT_CONFIG_COUNT"])
        env[f"GIT_CONFIG_KEY_{index}"] = "http.sslVerify"
        env[f"GIT_CONFIG_VALUE_{index}"] = "true"
        env["GIT_CONFIG_COUNT"] = str(index + 1)
        env, state = self.transition("b", env, state)
        restored, state = self.transition(None, env, state)
        expected = dict(
            baseline,
            GIT_CONFIG_COUNT="2",
            GIT_CONFIG_KEY_1="http.sslVerify",
            GIT_CONFIG_VALUE_1="true",
        )
        self.assertEqual((restored, state), (expected, None))

    def test_mutated_runtime_blocks_and_invalid_counts_are_atomic(self):
        original, state = self.transition(
            "a",
            dict(
                self.env,
                GIT_CONFIG_COUNT="1",
                GIT_CONFIG_KEY_0="http.proxy",
                GIT_CONFIG_VALUE_0="proxy",
            ),
        )
        mutations = [
            {"GIT_CONFIG_VALUE_0": "modified"},
            {"GIT_CONFIG_VALUE_1": "modified"},
            *({"GIT_CONFIG_COUNT": count} for count in ("-1", "bad", "4097", "0000000", "")),
        ]
        for mutation in mutations:
            with self.subTest(mutation=mutation):
                result = self.invoke(
                    "internal",
                    "transition",
                    "--shell",
                    "bash",
                    "--restore",
                    env=dict(original, **mutation),
                    state=json.dumps(state),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")

    def test_env_only_does_not_claim_unrelated_malformed_runtime(self):
        baseline = dict(self.env, GIT_CONFIG_COUNT="broken")
        env, state = self.transition("plain", baseline)
        self.assertEqual(env["GIT_CONFIG_COUNT"], "broken")
        self.assertIsNone(state["runtime"])
        self.assertEqual(self.transition(None, env, state), (baseline, None))

    def test_malformed_state_is_rejected_without_output(self):
        env, valid = self.transition("a")
        states = [
            [],
            {},
            {**valid, "version": True},
            {**valid, "version": 2},
            {**valid, "managed": []},
            {**valid, "extra": "unexpected"},
        ]
        for key, value in (("baseline", {"IFS": "bad"}), ("managed", ["DEVWHO_PROFILE"] * 2)):
            states.append({**valid, key: value})
        broken = copy.deepcopy(valid)
        broken["runtime"]["owned"] = [["key-only"]]
        states.append(broken)
        for state in states:
            with self.subTest(state=state):
                result = self.invoke(
                    "internal",
                    "transition",
                    "--shell",
                    "bash",
                    "--restore",
                    env=env,
                    state=json.dumps(state),
                )
                self.assertEqual(result.returncode, 1)
                self.assertEqual(result.stdout, "")

    def test_cross_implementation_state(self):
        peers = [Path(item) for item in json.loads(os.environ.get("DEVWHO_TEST_PEERS", "[]"))]
        # Same-implementation serialization is still tested with no peers.
        for peer in peers or [EXECUTABLE]:
            with self.subTest(peer=str(peer)):
                baseline = dict(self.env, EMPTY="", PRESENT="outer")
                a_env, a_state = self.transition("a", baseline)
                peer_env, peer_state = self.transition("b", a_env, a_state, executable=peer)
                own_env, own_state = self.transition("b", a_env, a_state)
                self.assertEqual((peer_env, peer_state), (own_env, own_state))
                self.assertEqual(self.transition(None, peer_env, peer_state), (baseline, None))
