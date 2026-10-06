# Manual RC1 release procedure

[简体中文](zh-CN/releasing.md)

Resolve the RC blockers before publication. #11 (tag publication automation) is a later follow-up. Ordinary CI has only `contents: read`; this manual publication does not grant CI write permissions.

The [release plan](../release-plan.json) is authoritative: eight distributions, from exactly three CI artifacts. Canonical Python is **`test (ubuntu-latest, 3.11)` / `devwho-ubuntu-latest-py3.11`**; the other three Python jobs are validation evidence only. Core inputs are `cores (ubuntu-latest)` / `complete-cores-ubuntu-latest` and `cores (macos-latest)` / `complete-cores-macos-latest`. Linux Rust is staged and tested, but RC1 deliberately produces no downloadable Linux Rust archive. The macOS Go/setup binaries declare minimum 13.0, Rust 11.0; check the actual packaged minimums and test host in RUNTIME.txt.

1. Merge the reviewed changes and identify the exact final commit. Require all seven CI jobs to succeed for that commit, including lint/tests/builds, the minimum compilers, cross-core/state/native tests, checksums and no-Python runtime containers. Confirm the chosen run's `head_sha` matches the final commit and inspect job results rather than accepting only an artifact's existence.
2. Download only the three prescribed artifact sources from that successful final-commit run:

   ```sh
   commit=FULL_FINAL_COMMIT_SHA
   run=SUCCESSFUL_FINAL_COMMIT_RUN_ID
   gh api "repos/lin594/devwho/actions/runs/$run" --jq '{head_sha,conclusion,event}'
   gh run download "$run" --repo lin594/devwho \
     -n complete-cores-ubuntu-latest -n complete-cores-macos-latest \
     -n devwho-ubuntu-latest-py3.11 --dir downloads
   python3 scripts/collect_release_assets.py \
     --source complete-cores-ubuntu-latest=downloads/complete-cores-ubuntu-latest/dist/cores \
     --source complete-cores-macos-latest=downloads/complete-cores-macos-latest/dist/cores \
     --source devwho-ubuntu-latest-py3.11=downloads/devwho-ubuntu-latest-py3.11 \
     --commit "$commit" --ci-run "https://github.com/lin594/devwho/actions/runs/$run" \
     --output release-assets
   (cd release-assets && sha256sum -c SHA256SUMS)
   ```

   The collector validates every original checksum, refuses missing or unexpected distributions/sources and differing duplicates, and creates output only after validating the complete plan. The manifest records the canonical Python source, expected filenames, per-asset source, CI jobs, original checksum-list hashes, omitted targets, plan hash and final commit.
3. On FZ2, install the **downloaded** Linux Go/Bash packages into fresh isolated prefixes, not the existing personal installation. Run version, explicit config initialization, Bash/Zsh init, activation, offline doctor, restoration and exec. Test the bundled Go setup frontend and wheel/zipapp outside the checkout. Repeat the no-Python/no-compiler/network-disabled runtime fixtures with the downloaded packages. Inspect macOS ARM64 package headers and their minimum deployment versions; use the originating macOS CI for actual execution evidence. Retain a sanitized `FZ2-VALIDATION.json` with the same commit, CI run and package hashes.
4. Check that runtime versions are `0.1.0-rc.1`, Python metadata is equivalent `0.1.0rc1`, and all selected target/runtime claims match the plan and actual artifacts. Keep unsupported architectures and live authentication limitations explicit. If evidence is added to the asset set, regenerate its complete SHA256SUMS without changing distribution bytes.
5. Tag the exact final commit `v0.1.0-rc.1`. Create a GitHub **pre-release**, attach the eight distributions, checksums, manifest and FZ2 evidence, and keep `prerelease=true` and `make_latest=false`. Do not publish to registries. Check the published tag's commit, release flags and download/checksum the published assets before closing #9/#12–#15. The release notes link the final CI, audited scope, install matrix and known gaps.

End users download just their matching archive and SHA256SUMS and verify the selected entry as shown in the [installation guide](../implementations/README.md). The complete checksum list serves release audit; it does not require an end user to download unrelated platforms.
