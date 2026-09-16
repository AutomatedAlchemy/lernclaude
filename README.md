# lernclaude

Launch a [Claude Code](https://claude.com/claude-code) session *inside an exam-prep
folder* and have it run that folder's study loop — open your reference sheets and
the newest problem set, then feed you one bite-sized exercise at a time,
personalised from the mistakes you actually made.

> **The tool speaks German.** The prompts it sends to Claude, the workspace
> template it stamps out, and the menu are all German — it was built for a German
> university workload and hasn't been translated. This README is in English so you
> can decide whether that's a problem before you clone it. The core loop is
> language-agnostic; see [Using it in another language](#using-it-in-another-language).

## The idea

Most "AI study helper" setups put the intelligence in the tool. This one puts it
in the *folder*.

Each subject gets a **workspace** — a normal directory holding your lecture PDFs,
past papers, and problem sets, plus a `CLAUDE.md` describing how you want to study
*that* subject. `lernen <workspace>` starts Claude with its working directory set
there, so Claude Code loads that `CLAUDE.md` automatically and follows it.

The launcher stays deliberately thin: about 2000 lines that pick a folder, pick a
model, and send a "let's study" trigger. It contains no study procedure at all.
Improve the loop by editing a workspace's `CLAUDE.md`, not this code.

### Vocabulary

The German terms are load-bearing, so they're worth knowing:

| Term | Means |
|---|---|
| **Lern-Loop** | The study procedure defined in a workspace's `CLAUDE.md` |
| **Lern-Set** | The files opened at the start of a session — reference sheets, newest problem set |
| **Häppchen** | Literally "small bite" — one exercise-sized chunk of work |
| **Fehlermuster** | Error patterns: a ranked table of the mistakes still open, plus the log of evidence behind each; used to target the next Häppchen |
| **Themenkarte** | Topic map: the exam's topics and the typical trap in each |

## Requirements

- [Claude Code](https://claude.com/claude-code) on your `PATH`
- Python 3.9+ — **standard library only**, `requirements.txt` is empty
- `konsole` (KDE) for the windowed launch. Without it, the tool falls back to
  running in your current terminal, so it works fine anywhere.

## Install

```bash
git clone https://github.com/Probst1nator/lernclaude.git
cd lernclaude
python3 main.py
```

The menu opens with a single entry, *neuen Kurs anlegen*. Pick it and Claude
searches your filesystem with you, agrees on a course folder, scaffolds and
registers it, then reads your material and fills in the exam date, topic map, and
starting points itself.

To get a desktop icon and a `lernen` shell alias:

```bash
python3 main.py --install
```

This uses [`cli-tools-kit`](https://github.com/Probst1nator/cli-tools-kit) if it is
installed; without it, `--install` reports what's missing and everything else
keeps working. Run the tool by path if you skip the alias.

## Usage

```
lernen                       # course menu — 10s autostart of your default
lernen <workspace>           # skip the menu, launch straight into a folder
lernen --menu                # force the menu
lernen --list                # print registered courses (* marks the default)
lernen --set-default <ws>    # change which course autostarts
lernen --set-medium <m>      # set the working medium (Userspace): xournalpp | board
lernen --set-model <m>       # set the model: opus | sonnet | fable
lernen --set-effort <e>      # set the effort: low | medium | high | xhigh | max
lernen --tutor               # Tutors Choice: one session that picks the most urgent course and tutors it
lernen --quickie             # Quickie: one short, winnable Häppchen (5 min); counts a daily streak
lernen --meta [ZIEL QUELLE…] # Meta-Häppchen: one short Häppchen in ZIEL shaped by the QUELLE courses; bare = last combination
lernen --add                 # guided onboarding: Claude helps you pick a folder
lernen --register <ws>       # scaffold + register, no launch (used by onboarding)
lernen --unregister <ws>     # drop from the menu (touches no files)
lernen --print-prompt <ws>   # show the assembled system prompt
lernen --dry-run <ws>        # show the launch command
lernen --install [ws]        # desktop icon + alias (per-workspace when ws given)
lernen --remove [ws]         # remove that icon + alias
```

### Starting on login

The desktop icon installed by `--install` can also start on login: tick
**Auto-Start** for lernclaude in the [`cli-tools-kit`](https://github.com/Probst1nator/cli-tools-kit)
installer, which symlinks the icon into `~/.config/autostart`. lernclaude
advertises `default_autostart`, so that box comes pre-ticked. There is no
`lernen` flag for it — the installer owns autostart for every tool in this
family, and it also clears the entry when you remove the tool.

What starts is the **menu**, because the icon's command takes no arguments: it
counts down ten seconds to your default (a course, the Quickie, Tutors Choice or
a Meta-Häppchen) and any keypress cancels that. You never land in a session you
cannot get out of.

### The menu

A bare `lernen` opens a small curses picker of your registered courses.
`↑`/`↓` move · `Enter` starts · `Space` opens the Meta multiselect · `m` switches
the medium · `d` sets the default · `x` removes a course · `q` quits. Left untouched for ten seconds
it autostarts your default; any keypress cancels the countdown.

A fresh clone has nothing registered, so the menu shows only "add a course" —
there is no built-in default folder.

Each course row also shows its progress, e.g. `· 7/24 Häppchen` (and `✓ bereit`
once the target is reached), and `· ohne Übersicht` while the course has no
confirmed overview yet (see *The course overview* below). The numbers come from a single line the study
session itself maintains in the workspace's `todo.md`:

```
Fortschritt: 7/24 Häppchen
```

`x` counts reviewed Häppchen; `y` is the session's *living estimate* of how many
it will take until you are exam-ready, re-judged after every review. The launcher
only reads the line — the judgment stays in the workspace. No line, no display.

### Tutors Choice

With two or more courses registered, the menu's top row is **Tutors Choice**.
Picking it (or running `lernen --tutor`) launches one interactive session,
exactly like starting a course — except its opening message carries a compact,
mechanically extracted dossier per course (progress line, days since last
activity, Themenkarte size, created/reviewed Häppchen counts, the dominant
Fehlermuster, the newest todo.md entry) plus your upcoming exams, and tells it
to read the strongest candidates' `todo.md` before
deciding. The session weighs exam proximity against neglect and progress,
tells you in one sentence which course
it picks and why, then reads that course's `CLAUDE.md` and runs its Lern-Loop
itself. The chooser and the tutor writing your Häppchen are the same session —
no hidden pre-pass, no wait at the menu. It starts at the courses' common
parent folder so it can work across all of them.

Tutors Choice can itself be the default: press `d` on its row, or run
`lernen --set-default tutor` — the 10s autostart then runs the tutor pick. It
is also the automatic default whenever you have two or more courses and never
explicitly chose one, so a fresh install autostarts into Tutors Choice as soon
as there is a real choice. (Scripted flags like `--dry-run` need a concrete
folder and fall back to the first course.)

### Quickie

The menu's very top row (shown as soon as one course exists) is **⚡ Quickie**
— one short Häppchen, about five minutes, nothing else. It is the low-threshold
entry for days when a full session feels like too much: pick it (or run
`lernen --quickie`) and the session greets you in one sentence, picks a course
in half a sentence when there are several (no file reading first — the dossiers
suffice), and opens one small, self-contained, deliberately *winnable* task in
the active medium, following that course's `CLAUDE.md` mechanics scaled down to
a single Häppchen. After your answer it corrects briefly, names what you got
right, and asks „Noch eins?“ the way the active medium does it (a button on the
board, a line in the chat) — with the next Quickie already in mind. If you stop, it says goodbye in a sentence; no lecture. A Quickie still
counts in the `Fortschritt:` line and is noted with date and topic in `todo.md`.

The launcher keeps a streak in the registry (`quickies`: last date, days in a
row, total) and shows it on the row — `· Serie: 3 Tage` while the streak is
alive (a Quickie today or yesterday), `· bisher 12` otherwise. The session gets
the numbers to mention in its greeting. A launch counts as a Quickie; the
launcher never judges whether you finished. `lernen --set-default quickie`
(or `d` on the row) makes it the 10s autostart target.

### Meta-Häppchen

A Meta-Häppchen is one short Häppchen in a **target** course, written with the
other selected **source** courses in view: the session reads each source's
`fehlermuster.md` in full and the last ten or so dated lines of its `todo.md`,
then builds a single winnable task in the target's own material that provokes
the sources' error patterns or reuses what they just practised. Which of the
two dominates is the session's call. It names in half a sentence which source
shaped the task, reviews briefly, and asks „Noch eins?“ with the same
selection. Only the target's files change (its `Fortschritt:` line and a dated
`todo.md` note naming the sources); the sources are read-only. A launch counts
as a Quickie day too, so the streak survives a Meta-only day.

In the menu, `Space` on any row opens the multiselect. The first course you
check is the target (`◉`), further checks are sources (`☑`), `z` moves the
target to the cursor row, `Enter` launches with a target and at least one
source, `Esc` goes back. The selection is remembered in the registry (`meta`:
target, sources, total), and the multiselect opens pre-checked with it next
time. Once something is remembered, a row `⇄ Meta-Häppchen — Mathe + Spanisch
→ Physik` appears under Tutors Choice: `Enter` repeats the combination, `d`
makes it the 10s autostart target (`lernen --set-default meta` does the same),
and it disappears while one of its courses is unregistered.

From a script: `lernen --meta ZIEL QUELLE [QUELLE…]` launches and remembers an
explicit combination (unregistered paths get registered, like `--set-default`);
bare `lernen --meta` reuses the remembered one; `lernen --print-prompt --meta …`
shows the system prompt without launching or remembering.

### The medium switch

Sessions work in one of two media: **Xournal++ + Firefox** (exercise PDF in the
browser, calculations on a separate `.xopp` sheet) or a **Tutor Board** (a web
whiteboard with one tab per exercise; see § Tutor Board, it needs an account on
the author's service). The active medium is a single
launcher-level switch — toggle it with `m` in the menu, `lernen --set-medium
xournalpp|board`, or `LERNCLAUDE_MEDIUM` — not a per-course fact.

The mechanics of each medium live in `templates/medium_<name>.md` and ride into
every session via the system prompt; course workspaces carry no medium
instructions at all, so improving how a medium works is one edit for all
subjects. Mid-session you can still switch verbally ("lass uns aufs Board") —
the session carries on and reminds you to flip the menu switch for next time. A
course whose own `CLAUDE.md` pins a fixed medium overrides the switch.

### Tutor Board

The `board` medium targets Tutor Board, the author's agent-driven live
whiteboard at <https://beta.probable.work>. An LLM agent connected to it as an
MCP (Model Context Protocol) connector — `https://beta.probable.work/mcp`,
OAuth 2.1 + PKCE (Proof Key for Code Exchange) — builds the board out of typed
blocks: Markdown with LaTeX, input widgets, sandboxed interactive HTML,
drawable canvases, images. It reads the learner's answers and drawings back the
same way.

Boards need a probable.work account, and accounts are invite-only. Without one
the `board` medium has nothing to talk to — use `xournalpp` then. Setup and the
agent-facing docs are served live at <https://beta.probable.work/setup.md> and
<https://beta.probable.work/agent.md>.

lernclaude carries no MCP client and no credentials for the board. The
connection comes from your own Claude Code MCP config, and
`templates/medium_board.md` only tells the loop what to do with a board, not how
the tools work.

Status as of 2026-09-16: the service is multi-user — each board belongs to one
account, and state is persisted per account. Running several agents in parallel
on one account is not safe yet: board selection is shared per account link, and
reads of events and chat are consumed by whichever agent reads first. One agent
per account link is the supported mode.

### The exam banner

If you point lernclaude at a markdown file holding your exam dates, the menu
prints the upcoming ones above the course list — soonest first, with the days
left, coloured red inside three days and yellow inside ten:

```
╭─ lernclaude — Kurs wählen ─╮

  ⏳ Nächste Klausuren
      in 34 T  ·  Mi 16.09. 09:00   ·  Lineare Algebra I
      in 39 T  ·  Mo 21.09. 09:00   ·  Thermodynamik
```

Point at the file with `LERNCLAUDE_EXAMS=/path/to/exams.md`, or store the path
once in the registry as `"exams_file"`. Without it the banner simply does not
appear.

The file needs no particular structure — lernclaude reads every markdown table
in it that has **both** a date column (`Termin`, `Datum`, `Date`, `When`) and a
label column (`Fach`, `Kurs`, `Modul`, `Prüfung`, `Klausur`, `Subject`,
`Course`, `Exam`), and ignores the rest. So an existing notes file works as-is:

```markdown
| Prüf-Nr | Fach                  | ECTS | Termin              |
|---------|-----------------------|-----:|---------------------|
| 12345   | Lineare Algebra I     |  2,5 | **Mi 16.09. 09:00** |
| 23456   | Thermodynamik         |    5 | **Fr 25.09.**       |
```

The time is optional. A bare `12.01.` with no year is read as the *next*
12 January. Rows already dealt with drop out on their own: anything in the past,
struck through (`~~…~~`), or marked `abgelegt` / `bestanden` / `Rücktritt` /
`entfällt` / `verschoben` / `TBD` is not shown.

### Adding a course

`--add` is interactive by design. Rather than prompting you to type an absolute
path, it starts a Claude session that searches your filesystem with you, agrees on
a location, and then calls `--register` itself.

### The course overview (the contract)

Every course gets an overview before its first Häppchen: what the exam asks,
every topic of the Themenkarte explained from scratch, every material in the
course folder named and explained, and an agreement on what is in and what is
out. You read it on your own, then confirm it — that confirmation is the
contract between you and the tutor about what the course covers. It lives in
the working medium (on the board it is Tab 0, with the material attached so you
can open it from there), not in a file: the learner only ever sees the medium.

The launcher owns none of the content. It reads one bookkeeping line the
session writes to the course's `todo.md` once you have confirmed
(`Übersicht: bestätigt 2026-09-02`), shows `· ohne Übersicht` on the menu row
until then (`· Übersicht unbestätigt` once the line says it is built and only
the confirmation is missing), and tells a normal launch or Tutors Choice to
build the overview first, or to ask for the confirmation if it is already built. Courses created before this existed pick it up the same way on their
next launch; the session copies the `Kursübersicht` section from the template
into the course `CLAUDE.md` if it is missing. The Quickie never builds one.
Changing the Themenkarte means the overview is redone and confirmed again.

## Workspace layout

Onboarding stamps a minimal skeleton and never overwrites an existing file:

| Path | Role |
|---|---|
| `CLAUDE.md` | The Lern-Loop procedure and exam facts. Stamped from `templates/LERNLOOP_TEMPLATE.md`. |
| `todo.md` | Where you left off — subject, exam date, active files, plus the two bookkeeping lines the menu reads (`Fortschritt: x/y Häppchen`, `Übersicht: bestätigt YYYY-MM-DD`) |
| `fehlermuster.md` | Error patterns: ranked `## Aktive Muster` table on top (the menu's dossier reads its first row), chronological `## Belege` log below |
| `Personalisierte_Übungen/` | Generated exercises land here |

Everything else is created on demand, when a workflow is first used.

## Configuration

All optional — the tool works with none of them set.

| Variable | Effect |
|---|---|
| `LERNCLAUDE_REGISTRY` | Path to the course registry (default: `./data/registry.json`) |
| `LERNCLAUDE_DEFAULT_WORKSPACE` | Override the registered default for one launch |
| `LERNCLAUDE_ROOT` | Where guided onboarding starts searching (default: `$HOME`) |
| `LERNCLAUDE_EXAMS` | Markdown file with your exam-date table (banner off when unset; registry key `exams_file` does the same) |
| `LERNCLAUDE_MEDIUM` | Override the working medium for one launch (`xournalpp` \| `board`) |

### Model selection

Sessions launch on **Opus at `medium` effort** by default. Medium is deliberate —
the loop is interactive tutoring, where latency is felt more than extra reasoning
depth helps.

You change it in the menu, next to the Userspace row: `o` cycles the model
(Opus | Sonnet | Fable), `e` the effort (low | medium | high | xhigh | max). The
pick is used exactly as chosen — nothing clamps it — and persists in the registry
as the new default, so it is set once per course collection rather than per
launch. `--set-model` / `--set-effort` do the same from a script.

### The registry

Registered courses live in `data/registry.json`, inside the tool's own directory
rather than `~/.config`. That's so a synced or shared checkout carries the same
course list on every machine you study from. It's gitignored — your course list is
yours.

## Using it in another language

Nothing structural is German; the strings are. To translate, edit the four prompt
builders in `main.py` — `_assemble_prompt`, `opening_message`,
`opening_message_onboard` — and
`templates/LERNLOOP_TEMPLATE.md`. That's the whole surface. The launcher, registry,
and menu need no changes.

One instruction is worth keeping whatever the language: the prompt tells Claude to
explain **without LaTeX**, in Unicode notation (`√`, `x²`, `∫`, `≤`, `λ`). A
terminal can't render `\frac`, and unrendered LaTeX is genuinely hard to read
mid-exercise. LaTeX belongs in the `.tex` files the exercises produce, not in the
chat.

## Tests

```bash
python3 -m pytest -q          # 17 offline tests, no network, no launch
```

## License

MIT — see [LICENSE](LICENSE).
