# lernclaude — maintainer notes

User-facing docs are in [`README.md`](README.md). This file holds the design
decisions and invariants an agent working on the code needs.

Extracted from the author's `tools` monorepo (2026-08-10) into a standalone MIT
repo, following the same path `bloggen` took. It has **no** dependency on
`_shared` any more: the tier logic was vendored into `tier.py`, and the installer
import falls back gracefully when `cli_tool_kit` is absent.

## The SSoT boundary (the load-bearing invariant)

The study procedure — *which* sheets to open, the Häppchen rotation, the topic
order — lives canonically in each **workspace's** `CLAUDE.md`. This launcher must
never re-encode it.

`test_lernclaude.py` enforces this: the prompt-assembly tests assert that concrete
take-in-sheet filenames never appear in the assembled prompt. If you find yourself
adding a file list to `_assemble_prompt`, the change belongs in the workspace
template instead.

The mechanism is just Claude Code's own behaviour: we launch with the working
directory set to the workspace, so `<workspace>/CLAUDE.md` and its parents load
automatically. The launcher only orients the session — today's date, the workspace
path, a pointer to the procedure.

## No hardcoded personal paths

There is deliberately no built-in default workspace. `_resolve_workspace(None)`
returns `None` on a fresh install, and the caller routes that to the menu.

`test_no_workspace_is_hardcoded_anywhere` greps `main.py` for personal path
fragments and fails if any reappear. That test earned its keep during extraction —
it caught the onboarding prompt still naming the author's study folders after the
constants had been cleaned up.

## Tool-local state

The registry lives at `data/registry.json`, anchored to `SCRIPT_DIR` — **not**
`~/.config`. Rationale: the author runs this from a Syncthing-replicated checkout
across several machines, and per-host config silently diverges (a course list once
showed three courses on one host and one on another). Keeping it beside the tool
makes the course list travel with the checkout.

Consequences to preserve:
- The path takes a `LERNCLAUDE_REGISTRY` override so tests can redirect it to
  `tmp_path`. Every registry test relies on this.
- It is gitignored. It's mutable runtime state; tracking it would leave
  `git status` permanently dirty and invite merge conflicts.
- Because the file is shared, `default` is shared too. Two machines writing it in
  the same sync window can produce a `*.sync-conflict-*` copy — harmless, delete
  the loser.

## One engine, many icons

The engine is global (this one `main.py`) so loop improvements propagate to every
subject. The entry points are specific: `--install <ws> --name X` generates a thin
per-workspace `.desktop` icon whose `Exec` passes that workspace. Each exam gets a
one-click resume icon that doubles as a passive deadline nudge, with no code
duplication.

## Model and effort

`tier.py` is vendored, stdlib-only, and self-contained. It reads
`~/.claude.json` → `.oauthAccount.organizationType` — **not** the startup banner,
which is unstable across locales and releases.

Max → opus, Pro → sonnet, both clamped to `medium` effort. Medium is a deliberate
ceiling, not an oversight: this is interactive tutoring, where latency is felt more
than extra depth helps. `LERNCLAUDE_MODEL` / `LERNCLAUDE_EFFORT` override, and
`CLAUDE_TIER_OVERRIDE` forces a tier for tests.

## Layout

| File | Role |
|------|------|
| `main.py` | launcher, menu, registry, install/remove |
| `tier.py` | vendored subscription-tier → model/effort mapping |
| `templates/LERNLOOP_TEMPLATE.md` | the Lern-Loop procedure stamped into new workspaces |
| `test_lernclaude.py` | 20 offline tests — no network, no launch |
| `requirements.txt` | empty by design; stdlib only |

## Gotchas

- **`--advertise` must answer before any heavy import.** The installer times out
  after 5 s. The check sits above the `import argparse` block on purpose — don't
  move it.
- **`tier` is a sibling import.** `SCRIPT_DIR` is spliced onto `sys.path` at module
  level so it resolves both when run directly and when the tests load `main.py` by
  file location. Static analysers flag this import as unresolved; it works at
  runtime and the tests cover it.
- **`.desktop` files hold absolute paths.** Moving or renaming this directory means
  `--remove` then `--install` from the new location.
- **The nvm PATH fix in `_launch_env()` is not optional.** A `.desktop` launch
  inherits the graphical session's PATH, which lacks the nvm bin dir where `claude`
  and `node` live — without it the icon opens a konsole that immediately closes.
- **Permission mode is left at Claude Code's default.** The session's work — read
  files, open PDFs — is read-only or user-approved.

## Tests

```bash
python3 -m pytest -q     # 20 tests, offline
python3 tier.py          # doctests + report this host's detected tier
```

Tests load `main.py` under a unique module name via `importlib` rather than
`import main`, a habit from the monorepo where sibling tools would collide in
`sys.modules`. Harmless here; keep it if this ever gets vendored back.
