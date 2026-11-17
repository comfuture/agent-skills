# Rust build output

Decide explicitly whether to use `cargo clean`. Record the selected workspace, target and build roots, current users, evidence to retain, scope, estimated rebuild cost and reason for cleaning, skipping or deferring.

## Locate both outputs

1. Identify the Cargo executable and toolchain used by the build. Inspect its version and `cargo clean --help` from a trusted directory. A rustup proxy may install a missing toolchain when run in a checkout. Use an already installed executable.
2. Reconstruct the invocation directory, manifest, flags, environment and effective configuration from the build. Cargo looks up configuration from its **working directory**, including ancestor and Cargo home config. Check `--target-dir`, `CARGO_TARGET_DIR`, `CARGO_BUILD_TARGET_DIR`, `build.target-dir`, and the independent `CARGO_BUILD_BUILD_DIR` / `build.build-dir` on versions supporting it. Resolve relative paths, includes, templates, symlinks and mounted volumes. The usual default for both roots is the workspace's `target/`. [Cargo configuration](https://doc.rust-lang.org/cargo/reference/config.html) · [Build cache layout](https://doc.rust-lang.org/cargo/reference/build-cache.html)
3. In a trusted Cargo configuration, `cargo metadata --frozen --no-deps --format-version 1` from the recorded invocation directory reports `workspace_root`, `target_directory` and, in some versions, `build_directory`. Reproduce configuration overrides used in the build. If the build field is missing, check the installed capability and settings. If executable hooks, hidden configuration, or unresolved paths prevent read-only inspection, use existing build records or defer. Avoid invoking build scripts, compiler wrappers, or project cleanup commands to gather evidence. [Cargo metadata](https://doc.rust-lang.org/cargo/commands/cargo-metadata.html)

## Decide the scope

- Compare both resolved roots with sibling checkouts, CI runners and other consumers. Examine active `cargo`, `rustc`, compiler wrappers and descendant processes for their working directories, command arguments and open handles. Apply the process inspection procedure when identity or visibility needs verification. A path outside the workspace frequently requires tracing its owner. A workspace-local path can be shared too.
- Keep the complete `CARGO_HOME` (by default `~/.cargo`) and rustup home/toolchains. This includes registry archives and sources, Git dependency objects and checkouts, installed binaries, credentials and config. Check for overlapping paths in either direction. Download-cache eviction would need its own scope. [Cargo home](https://doc.rust-lang.org/cargo/guide/cargo-home.html)
- To compare the roots collected above, run the bundled `scripts/compare_cargo_roots.py` with explicit absolute paths. Supply other workspaces' target **and** build roots with repeated `--other-output`, and active users' output roots with `--busy-output`. An unknown owner, unresolved mount alias or incomplete process scan still requires deferral. The helper reads path identity only.

  ```sh
  python3 "$skill_dir/scripts/compare_cargo_roots.py" \
    --workspace "$workspace" --target-dir "$target_dir" --build-dir "$build_dir" \
    --cargo-home "$cargo_home" --rustup-home "$rustup_home" \
    --other-output "$sibling_build_dir"
  ```

- `defer` identifies a conflict. Preserve active/shared roots until the users are accounted for and the exact scope is authorized and idle. `--removing-worktree` can identify a `redundant` clean when both private outputs disappear with an already planned worktree removal. Check the gates on worktree removal separately. `review` calls for inspecting the files and choosing a scope.
- Inventory ignored and hand-written data in **both** roots. Look for raw Criterion samples, CSVs, benchmark/toolchain receipts, generated release deliverables, and record the applicable `Cargo.lock` revision. Before removal copy the required items to the project's verification location or the user's chosen destination outside the removal set. Verify content hashes. Retain private settings with their project.
- Assess space against rebuild cost. Identify packages, profiles, targets and dependents that must recompile, with measured timings if available. Consider a supported `--package`, `--profile`, `--target` or `--doc` scope. A whole-tree clean can remove custom files in either root. Space estimates from `du` or Cargo can differ from filesystem space reclaimed.

## Apply the recorded decision

Prefer a verbose preview of the precise approved scope. For an existing, trusted build with a usable lockfile, a typical invocation is `cargo clean --frozen --dry-run --verbose` plus the recorded selectors in the original directory, toolchain and configuration. A preview suppresses deletion, but Cargo or a wrapper may write bookkeeping during resolution. For a strict inspect-only audit use filesystem observations, or preview against an isolated copy with **both** outputs remapped and a disposable Cargo home. If the installed version lacks preview, inspect the selected paths directly and defer ambiguous scope. [Cargo clean](https://doc.rust-lang.org/cargo/commands/cargo-clean.html)

Before an authorized clean, recheck roots, active users, owner, preserved hashes and selectors. Run that exact invocation without `--dry-run`. Compare remaining evidence, build roots and free space on the same volumes. If interrupted, inspect what remains and revalidate a narrower retry.
