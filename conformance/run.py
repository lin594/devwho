#!/usr/bin/env python3
"""Run the same black-box contract against a selected DevWho executable."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import sys
import unittest


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def cases(suite):
    for test in suite:
        if isinstance(test, unittest.TestSuite):
            yield from cases(test)
        else:
            yield test


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--executable", required=True, type=Path)
    parser.add_argument("--peer", action="append", type=Path, default=[])
    parser.add_argument("--report", type=Path)
    parser.add_argument("--failfast", action="store_true")
    args = parser.parse_args()
    target = args.executable.resolve()
    if not target.is_file() or not os.access(target, os.X_OK):
        parser.error("--executable must name an existing executable")
    os.environ["DEVWHO_TEST_EXECUTABLE"] = str(target)
    peers = [str(path.resolve()) for path in args.peer]
    os.environ["DEVWHO_TEST_PEERS"] = json.dumps(peers)
    names = [
        "tests.test_shells",
        "tests.test_cli",
        "tests.test_ssh",
        "conformance.test_vectors",
        "conformance.test_processes",
        "conformance.test_dotenv",
    ]
    loaded = unittest.defaultTestLoader.loadTestsFromNames(names)
    # Python archive tests remain in its own suite. Shared tests drive real
    # executables and never import a core implementation.
    selected = unittest.TestSuite(
        test for test in cases(loaded) if "test_relocated_zipapp" not in test.id()
    )
    result = unittest.TextTestRunner(verbosity=2, failfast=args.failfast).run(selected)
    if args.report:
        report = {
            "contract": "compatibility-core-v1",
            "executable": str(target),
            "peers": peers,
            "tests": result.testsRun,
            "successful": result.wasSuccessful(),
            "failures": [test.id() for test, _ in result.failures],
            "errors": [test.id() for test, _ in result.errors],
            "skipped": [{"test": test.id(), "reason": why} for test, why in result.skipped],
        }
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
