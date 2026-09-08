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

The launcher stays deliberately thin: about 700 lines that pick a folder, detect
your subscription tier, and send a "let's study" trigger. It contains no study
procedure at all. Improve the loop by editing a workspace's `CLAUDE.md`, not this
code.

### Vocabulary

The German terms are load-bearing, so they're worth knowing:

| Term | Means |
|---|---|
| **Lern-Loop** | The study procedure defined in a workspace's `CLAUDE.md` |
| **Lern-Set** | The files opened at the start of a session — reference sheets, newest problem set |
| **Häppchen** | Literally "small bite" — one exercise-sized chunk of work |
| **Fehlermuster** | Error patterns: a running log of mistakes, used to target the next Häppchen |
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

This uses [`cli-tool-kit`](https://github.com/Probst1nator/cli-tool-kit) if it is
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
lernen --set-model <m>       # set the model: auto | opus | sonnet | fable
lernen --set-effort <e>      # set the effort: auto | low | medium | high
lernen --tutor               # Tutors Choice: one session that picks the most urgent course and tutors it
lernen --quickie             # Quickie: one short, winnable Häppchen (5 min); counts a daily streak
lernen --add                 # guided onboarding: Claude helps you pick a folder
lernen --register <ws>       # scaffold + register, no launch (used by onboarding)
lernen --unregister <ws>     # drop from the menu (touches no files)
lernen --print-prompt <ws>   # show the assembled system prompt
lernen --dry-run <ws>        # show the launch command
lernen --install [ws]        # desktop icon + alias (per-workspace when ws given)
lernen --remove [ws]         # remove that icon + alias
```

### The menu

A bare `lernen` opens a small curses picker of your registered courses.
`↑`/`↓` move · `Enter` starts · `m` switches the medium · `d` sets the default ·
`x` removes a course · `q` quits. Left untouched for ten seconds
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

### The medium switch

Sessions work in one of two media: **Xournal++ + Firefox** (exercise PDF in the
browser, calculations on a separate `.xopp` sheet) or a **Tutor Board** (a web
whiteboard with one tab per exercise). The active medium is a single
launcher-level switch — toggle it with `m` in the menu, `lernen --set-medium
xournalpp|board`, or `LERNCLAUDE_MEDIUM` — not a per-course fact.

The mechanics of each medium live in `templates/medium_<name>.md` and ride into
every session via the system prompt; course workspaces carry no medium
instructions at all, so improving how a medium works is one edit for all
subjects. Mid-session you can still switch verbally ("lass uns aufs Board") —
the session carries on and reminds you to flip the menu switch for next time. A
course whose own `CLAUDE.md` pins a fixed medium overrides the switch.

### The exam banner

If you point lernclaude at a markdown file holding your exam dates, the menu
prints the upcoming ones above the course list — soonest first, with the days
left, coloured red inside three days and yellow inside ten:

```
╭─ lernclaude — Kurs wählen ─╮

  ⏳ Nächste Klausuren
      in 34 T  ·  Mi 16.09. 09:00   ·  Experimentalphysik II
      in 39 T  ·  Mo 21.09. 09:00   ·  Datenerfassung u. Modellierung
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
| 66821   | Experimentalphysik II |  2,5 | **Mi 16.09. 09:00** |
| 57181   | Introduction to ML    |    5 | **Fr 25.09.**       |
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
| `fehlermuster.md` | Error-pattern log; the loop reads this to target the next exercise |
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
| `LERNCLAUDE_MODEL` | Pin the model, skipping tier detection |
| `LERNCLAUDE_EFFORT` | Pin the effort level (default: the menu pick, else `medium`) |
| `LERNCLAUDE_MEDIUM` | Override the working medium for one launch (`xournalpp` \| `board`) |
| `CLAUDE_TIER_OVERRIDE` | Force `max` / `pro` instead of detecting |

### Model selection

`tier.py` reads `~/.claude.json` to find your subscription tier and picks
accordingly: **Max → opus**, **Pro → sonnet**, both at `medium` effort. Medium is
deliberate — the loop is interactive tutoring, where latency is felt more than
extra reasoning depth helps. Both the mapping and the effort band are two dicts at
the top of `tier.py`; edit them if you disagree.

That is the `auto` setting. The menu has two more switches next to the Userspace
row — `o` cycles the model (auto | Opus | Sonnet | Fable), `e` the effort
(auto | low | medium | high) — and an explicit pick is used as-is, without the
tier clamp. Both persist in the registry; `--set-model` / `--set-effort` set them
from a script, `LERNCLAUDE_MODEL` / `LERNCLAUDE_EFFORT` override one launch.

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
python3 -m pytest -q          # 42 offline tests, no network, no launch
python3 tier.py               # tier doctests + report this host's detected tier
```

## License

MIT — see [LICENSE](LICENSE).
