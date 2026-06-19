---
name: cloudos
description: >-
  Develop code locally that will be pulled into a Genomics England CloudOS protected
  environment and run there. Use when writing or finalizing code destined for CloudOS.
  Covers the push -> git pull -> pixi run loop, defensive validation (real data exists
  only remotely), one-line fatal errors (failures are transcribed by hand), and the
  linux-64 / CloudOS-path gotchas.
---

# Developing for CloudOS

## The environment, in one picture
- **Local** (here): macOS `osx-arm64`, full internet, **no real data**, Claude can see everything.
- **Remote** (CloudOS): interactive session, `linux-64`, has the real `s3://` data,
  `/public_data_resources` genome refs and IGV ports. conda + PyPI + GitHub are reachable.
  Claude **cannot** see it.
- **The boundary is GitHub only.** Push locally; in CloudOS `git pull` a pixi checkout and
  `pixi run`. There is **no outbound clipboard** — every error is **transcribed by hand**.

## Two facts that govern everything
1. **You cannot test against real data locally.** So you cannot discover data/path bugs by
   running — you must *prevent* them with defensive checks that fire clearly in CloudOS.
2. **Remote iteration is expensive and blind, and errors are hand-copied.** So code must run
   right the first time, and any failure must be **one short, actionable line** — never a
   traceback someone has to transcribe.

## Golden rules
1. **Validate every external input before using it.** Check each S3 object / file / required
   column exists up front; on the first problem, exit with a single line naming *what* and
   *where*. No silent assumptions about schema, dtypes, or path existence.
2. **Fail fast, fail short.** `raise SystemExit(f"CloudOS: <file> missing column 'x'")` style —
   one line, no stack dump. Resolve config and check all inputs *before* doing any work.
3. **Environment-specific values live in config, never in logic.** Every `s3://...`,
   `/public_data_resources/...` genome ref, and port belongs in `config.toml` (bundled as
   package data), so code is identical local vs remote and a wrong path is a config edit.
4. **Cross-platform by construction.** Dev `osx-arm64`, run `linux-64`. Keep *both* platforms in
   `pixi.lock`; regenerate the lock when deps change. No OS-specific paths, shells, or binaries.
5. **Echo resolved config at startup** so a wrong-but-present path is obvious without a crash.

## Pre-push checklist (run before every push)
- [ ] `pixi run fmt` (lint + format) clean
- [ ] Every external input guarded by an explicit existence/schema check with a one-line error
- [ ] No CloudOS-only path hardcoded in logic — all in `config.toml`
- [ ] Logic exercised on synthetic / edge inputs locally (no real data needed)
- [ ] `pixi.lock` covers `linux-64` **and** `osx-arm64`; regenerated if deps changed
- [ ] Commit + push

## In CloudOS (the canonical loop)
```bash
git pull                 # in the pixi project checkout
pixi install             # only if deps / pixi.lock changed
pixi run <entrypoint> -h # smoke test
pixi run <entrypoint> ...
```
On failure you should see one line saying what is wrong and where — fix locally, push, repeat.

## Validation pattern (copy/adapt)
```python
import sys
from pathlib import Path

def require(condition: bool, msg: str) -> None:
    """One-line fatal error — no traceback to transcribe."""
    if not condition:
        sys.exit(f"CloudOS: {msg}")

require(Path(path).exists(), f"missing input: {path}")
require(set(REQUIRED_COLS) <= set(df.columns),
        f"{path} missing columns: {sorted(set(REQUIRED_COLS) - set(df.columns))}")
```

## Gotchas
- **uv on CloudOS** must be installed via `conda install uv` first; a shell restart / PATH
  update may be needed. (pixi-from-source is preferred for dev iteration.)
- `pixi`'s `exclude-newer` / lockfile can drift local vs remote — regenerate the lock when deps
  change so both platforms resolve to the same versions.
