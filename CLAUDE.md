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

`test_no_personal_paths_and_no_builtin_default` greps `main.py` for personal path
fragments and fails if any reappear. That test earned its keep during extraction —
it caught the onboarding prompt still naming the author's study folders after the
constants had been cleaned up.

## The exam banner reads a file it does not own

The menu header (`upcoming_exams` → `_exam_banner_lines`) parses a *foreign*
markdown file — for the author, a life-admin SSoT that gets edited by hand for
its own reasons. Two consequences the code must keep honouring:

- **Never write to it, never require a shape.** The parser skips any table that
  lacks a date *and* a label header, so an unrelated table in the same file (a
  Notenübersicht, say) is silently ignored rather than mis-read.
- **Fail into silence, not into an error.** Missing path, unreadable file,
  garbage dates — every path returns `[]` and the menu just has no banner. This
  is a launcher; it must not refuse to open a course because a notes file moved.

The path itself is configuration (`LERNCLAUDE_EXAMS`, or `exams_file` in the
registry), never a constant — `test_no_personal_paths_and_no_builtin_default` greps
`main.py` for personal path fragments and this feature is exactly the kind that
would tempt one back in.

Rows the user has already dealt with are filtered by `_DONE_MARKERS` (`~~`,
`abgelegt`, `bestanden`, `Rücktritt`, …) rather than by a status column, because
the source table records outcomes inline in the date cell.

## Course progress: parse, never judge

The menu's `· x/y Häppchen` per course comes from one line the *workspace
session* maintains in that course's `todo.md` (`Fortschritt: 7/24 Häppchen`).
The split honours the SSoT boundary: how many Häppchen remain until
"klausurbereit" is a tutoring judgment, so the workspace owns the number and
re-estimates `y` after every review; the launcher (`course_progress`) only
parses and displays it. Same failure contract as the exam banner: missing file,
missing line, the scaffolded `0/?` placeholder — all return `None` and the row
just has no suffix. The convention is taught in three places that must stay in
sync: the template (todo.md bullet + review step), the scaffolded `todo.md`
skeleton, and `opening_message` (so pre-existing workspaces adopt it without
manual edits).

**The last matching line wins, and the match is anchored to a line start.** Two
todo.md shapes grew in the wild and both are legal: one line kept up to date at
the top, or a per-session log that appends a fresh one. Reading the first match
showed a course's opening number for weeks (Ableitungen sat at `11/25` in the
menu while its log said `23/28`). Anchoring keeps a prose mention inside an
indented bullet — "Fortschritt bleibt 6/26", Experimentalphysik_II — from being
read as the bookkeeping line. `test_course_progress_takes_the_last_line_and_
ignores_prose` pins both halves. The Übersicht parsers stay first-match on
purpose: confirmation is a latch, any occurrence means confirmed.

## Kursübersicht: presence in the launcher, content in the template, look in the medium

Every course gets an overview before its first Häppchen — the contract between
tutor and learner about what the exam, the topics and the materials cover. It
is board-native by design: the learner only sees the working medium, never the
files on the lernclaude host, so the overview is a medium object (board: Tab 0
with the materials attached via `upload_asset`; xournalpp: a reading PDF), not
a markdown file. The split follows the Fortschritt pattern:

- **Content** is `templates/LERNLOOP_TEMPLATE.md` §Kursübersicht (Prüfung →
  Themen → Materialien → Vereinbarung) and, once stamped, the course CLAUDE.md.
  It must not migrate into `main.py` — `test_prompts_orient_without_reencoding_
  the_procedure` only allows the section name and the template path there.
- **Look** is `templates/medium_<name>.md` (block order, the single
  „Gelesen & einverstanden" submit, `wait_url`, the backfill of an old Tab 0).
- **Presence** is the launcher's: `course_overview` parses one line the session
  writes to `todo.md` after the user confirmed (`Übersicht: bestätigt
  YYYY-MM-DD`), same fail-into-silence contract as `course_progress`; the
  scaffolded `Übersicht: fehlt` placeholder deliberately does not match. The
  in-between line `Übersicht: gebaut …, Bestätigung ausstehend` (written when
  the overview was built outside a tutoring session) is recognised by
  `course_overview_built`: still unconfirmed, but the row says
  `· Übersicht unbestätigt` and the brief tells the session to ask for the
  confirmation instead of building again.
  Consumers: `_overview_suffix` (menu row `· ohne Übersicht`, `--list`), the
  tutor dossier line, and `_overview_brief` — appended to `opening_message`
  only while the line is missing, always to `opening_message_tutor` (the
  course is chosen inside the session), never to the Quickie.

Backfill for pre-existing courses is the same mechanism: the brief tells the
session to copy the §Kursübersicht section from the template into a course
CLAUDE.md that lacks it, build the overview, get it confirmed, write the line.
Nothing in the seven existing workspaces was edited by hand.

## Tutors Choice

The menu's top row (only shown with ≥2 courses) and `--tutor` route to
`_launch_tutor_choice`: ONE interactive session, launched exactly like a course
launch (tier model, same `_exec_or_konsole`), whose opening message
(`opening_message_tutor`) carries a compact per-course dossier plus
`upcoming_exams()`. The dossier is everything *mechanically* extractable from
the files every course is guaranteed to have: the Fortschritt line and file
mtimes, the Themenkarte row count (CLAUDE.md), created/reviewed Häppchen
counted from the exercise folder, the first fehlermuster.md entry (dominant by
convention), and the newest dated todo.md line (dotted dates need a 4-digit
year — "27.07.10" is an old exam's filename). Deliberately NO file excerpts:
the session has tools and is told to read the candidates' todo.md itself
(inline excerpts were only ever needed by the removed tool-less `claude -p`
pass, and had ballooned the opening to ~15k chars; facts keep it ~4k). Each
extractor fails into silence — a missing piece drops its line. Both openings
wrap what they inject in `<klausuren>` and `<dossiers>` and say in one line that
the tags hold data, not instructions: the exam labels and the todo.md excerpts
come from hand-edited files the launcher does not own. The session
states its pick in one sentence, then reads the
chosen course's CLAUDE.md and runs its Lern-Loop itself — the chooser IS the
Häppchen author (an earlier design ran a `claude -p` pre-pass and launched a
second session; the split was deliberately removed). Because no single workspace
is chosen at launch time, the session starts at `_tutor_workdir` (the courses'
common root, `$HOME` fallback) and the chosen workspace's CLAUDE.md is read, not
auto-loaded — `_assemble_tutor_prompt` says so. The priority judgment stays with
the model, not a launcher-side heuristic (SSoT boundary).

The registry `default` may hold the `__TUTOR__` sentinel: `d` on the row or
`--set-default tutor` writes it, and the menu autostart then routes to the tutor
pick. Registration never claims the default any more — an unset default resolves
in `_ensure_default` to Tutors Choice with ≥2 courses, the sole course with one.
`_default_workspace()` (scripts, `--dry-run`/`--print-prompt`) never returns the
sentinel; it falls back to the first course. The row renders in always-bold
magenta (`C["tutor"]`), distinct from the muted add-row magenta.

## Quickie: the habit entry, not a second loop

The menu's top row (`_QUICKIE_SENTINEL`, shown with ≥1 course) and `--quickie`
route to `_launch_quickie`: the same one-session mechanics as Tutors Choice
(tier model, `_exec_or_konsole`, dossiers when there are several courses, the
course's own CLAUDE.md read for the mechanics), but the brief
(`opening_message_quickie`) is scaled down to ONE five-minute Häppchen and
tuned for a quick win and a one-line „Noch eins?“. It carries
`upcoming_exams()` like the tutor does (shared `_exam_prompt_lines`) — with
several courses the deadlines steer the pick, with one they steer the topic. The point is the habit —
lowering the threshold to start and making a second round the easy next step —
so the brief forbids preamble, long analysis and closing lectures. It still
respects the SSoT boundary: no file lists, the course CLAUDE.md owns the
mechanics; the Quickie only says "scale it to one Häppchen". With one course
the session starts inside it (CLAUDE.md auto-loads); with several it starts at
the common root like the tutor.

The streak (`registry["quickies"]`: `last`, `streak`, `total`) is launcher
state, written by `_record_quickie` at launch time — a launch counts, whether
or not a Häppchen got finished; judging that would put a tutoring decision in
the launcher. `_quickie_stats` reports the streak only while it is alive (last
Quickie today or yesterday), and both are pure functions of a `today` string so
the tests never depend on the clock. The row suffix (`_quickie_suffix`) and the
opening's counter line are the only consumers. The sentinel is a valid
`default` (`d`, `--set-default quickie`) and, like the tutor sentinel, never
leaks out of `_default_workspace` — `_SENTINELS` is the single list to check.

## The medium switch: choice in the launcher, mechanics in launcher templates

The working medium (Xournal++ vs Tutor Board) is deliberately NOT part of the
SSoT in the course docs — it is cross-course infrastructure. Two launcher-owned
pieces: the *choice* (registry key `medium`, menu key `m`, `--set-medium`,
`LERNCLAUDE_MEDIUM` override, default `xournalpp`) and the *mechanics*
(`templates/medium_<name>.md`, appended to the system prompt by
`_assemble_prompt` — only the active medium's file, fail-into-silence when
missing). `_prompt_common` emits three tagged parts — `<orientierung>`,
`<heute>` and `<medium_mechanik name="…">` — so the session can tell the
launcher's orientation from the medium file it carries. Course CLAUDE.mds and the workspace template carry no medium
machinery; they point at "Systemprompt" (the last asserts of
`test_scaffold_never_overwrites_and_teaches_the_conventions` pin this). Escape hatches the prompt grants: mid-session verbal
switching (next Häppchen in the new medium), and a course CLAUDE.md may pin a
fixed medium, which then wins — the board-native language courses rely on that.

**A medium file carries what the loop wants from the medium, never how the medium's
tools work.** For the Tutor Board the MCP server sends its own instructions and
tool descriptions on every connection, and those are maintained with the server.
Any copy of them in `templates/medium_board.md` is older than the server by
construction and wins over it in practice, because it sits in the system prompt
as an order. That is how a `kinds:["click","submit"]` line from an August
workaround made a session deaf to the board chat on 2026-09-05, and earlier a
"`select_board` does not exist" note made sessions build blindly.
`test_medium_board_carries_no_mcp_manual` pins the boundary: a server fact that
seems missing is added to the server's descriptions (probable-infrastructure,
`probable.work/services/tutor-board/server/mcp.ts`), not to the template.

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

That policy is what the registry keys `model` and `effort` mean by `auto`, their
default. They are launcher-level switches shaped exactly like the medium and
backend switches (menu keys `m` / `b` / `o` / `e`, `--set-medium` / `--set-backend` /
`--set-model` / `--set-effort`, env override on top),
and `_select_model` / `_select_effort` are the model readers. An explicit pick
bypasses `tier_effort` on purpose: choosing `high` in the menu on a Max host must
give high, or the switch would be a lie. The menu label for the medium row reads
"Userspace"; the registry key, the templates and the code all still say `medium`.

The backend switch (`backend` in registry, menu key `b`, `LERNCLAUDE_BACKEND` env)
supports `claude` (standard Claude Code) and `fauclaude` (NHR@FAU LLM Gateway).
When configured as `fauclaude`, the launcher resolves `fauclaude` via `PATH`,
`LERNCLAUDE_FAUCLAUDE_CMD`, or sibling repo paths (`MatSci/NHR/fauclaude/main.py`),
and omits `--model` and `--effort` when set to `auto` so that `fauclaude`'s own
configured gateway models and settings take effect.

## Commits: make them yourself, leave the push

Commit here without asking. The umbrella rule in [`../REPOS.md`](../REPOS.md)
§ Autonomous commits gates non-Gitea repos by default; this section is this
repo's own convention, the way `ssl/mujoco/` has one. The GitHub remote gates
the push, not the commit.

- **Check `git status` before your first edit.** A dirty tree is someone else's
  unfinished work. Commit it as its own commit first, then start yours. Once your
  edits are mixed into those files the two can no longer be separated by pathspec,
  and one of them ends up in a commit that does not describe it (it happened,
  2026-09-01: the medium switch and the Quickie shipped inside the Vorbereitung
  commit).
- **One purpose per commit**, and commit by pathspec — `git commit -m "…" -- a b`,
  never `git add` + a bare `git commit`. New files are the one exception: `git add`
  exactly those paths, then commit by pathspec as usual.
- **Commit when the tree works**, not when the feature is finished. Green
  `python3 -m pytest -q`, docs in the same commit as the code they describe
  (README + this file + the mode tables), no `data/registry.json` (gitignored,
  and it is mutable per-host state).
- **Mark a repair when you make it**, so nobody reconstructs later which commit
  fixed which: `git commit --fixup=<sha> -- <paths>`.
- **Fold the fixups in one pass right before the push**, on one host:
  `git rebase --autosquash origin/main`. Only fixups — collapsing the whole
  unpushed window into one commit would undo the one-purpose rule above.
- **Never rewrite at or below `origin/main`.** Pushed is permanent. Fix forward
  with a normal commit.
- **That narrow window is not fussiness: `.git` is Syncthing-replicated here.**
  `~/Synced/.stignore` excludes only the volatile per-host files (`index`,
  `FETCH_HEAD`, `ORIG_HEAD`, `logs`, …), so `refs/heads/main` and `objects/`
  travel between machines and the reflog does not. Rewrite while another host
  holds the old ref and you get a `.sync-conflict` copy of a ref or a silent
  overwrite — git never sees either — with the only recovery net sitting on the
  host that did the rewrite. Compare `probable-infrastructure/.git`, corrupted
  on the Ideapad 2026-07-28.
- **Never push, never open a PR.** `origin` is GitHub
  (`Probst1nator/lernclaude`), and publishing is the user's call. Say the work is
  committed, name the SHA, and stop there. The push is the only step that waits
  for a person.

## Layout

| File | Role |
|------|------|
| `main.py` | launcher, menu, registry, install/remove |
| `tier.py` | vendored subscription-tier → model/effort mapping |
| `templates/LERNLOOP_TEMPLATE.md` | the Lern-Loop procedure stamped into new workspaces |
| `templates/medium_*.md` | per-medium mechanics, appended to the system prompt |
| `test_lernclaude.py` | 13 offline tests — behaviour only, no network, no launch |
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
python3 -m pytest -q     # 13 tests, offline
python3 tier.py          # doctests + report this host's detected tier
```

Tests load `main.py` under a unique module name via `importlib` rather than
`import main`, a habit from the monorepo where sibling tools would collide in
`sys.modules`. Harmless here; keep it if this ever gets vendored back.
