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
python3 main.py --init ~/Study/LinearAlgebra
```

`--init` scaffolds the folder, registers it, and launches a bootstrap session in
which Claude reads your material and fills in the exam date, topic map, and
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
lernen                       # course menu — 5s autostart of your default
lernen <workspace>           # skip the menu, launch straight into a folder
lernen --menu                # force the menu
lernen --list                # print registered courses (* marks the default)
lernen --set-default <ws>    # change which course autostarts
lernen --add                 # guided onboarding: Claude helps you pick a folder
lernen --register <ws>       # scaffold + register, no launch
lernen --init <folder>       # scaffold + register + bootstrap-launch
lernen --unregister <ws>     # drop from the menu (touches no files)
lernen --print-prompt <ws>   # show the assembled system prompt
lernen --dry-run <ws>        # show the launch command
lernen --install [ws]        # desktop icon + alias (per-workspace when ws given)
lernen --remove [ws]         # remove that icon + alias
```

### The menu

A bare `lernen` opens a small curses picker of your registered courses.
`↑`/`↓` move · `Enter` starts · `d` sets the default · `a` adds a course ·
`x` removes one · `q` quits. Left untouched for five seconds it autostarts your
default; any keypress cancels the countdown.

A fresh clone has nothing registered, so the menu shows only "add a course" —
there is no built-in default folder.

### Adding a course

`--add` is interactive by design. Rather than prompting you to type an absolute
path, it starts a Claude session that searches your filesystem with you, agrees on
a location, and then calls `--register` itself.

## Workspace layout

`--init` stamps a minimal skeleton and never overwrites an existing file:

| Path | Role |
|---|---|
| `CLAUDE.md` | The Lern-Loop procedure and exam facts. Stamped from `templates/LERNLOOP_TEMPLATE.md`. |
| `todo.md` | Where you left off — subject, exam date, active files |
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
| `LERNCLAUDE_MODEL` | Pin the model, skipping tier detection |
| `LERNCLAUDE_EFFORT` | Pin the effort level (default `medium`) |
| `CLAUDE_TIER_OVERRIDE` | Force `max` / `pro` instead of detecting |

### Model selection

`tier.py` reads `~/.claude.json` to find your subscription tier and picks
accordingly: **Max → opus**, **Pro → sonnet**, both at `medium` effort. Medium is
deliberate — the loop is interactive tutoring, where latency is felt more than
extra reasoning depth helps. Both the mapping and the effort band are two dicts at
the top of `tier.py`; edit them if you disagree.

### The registry

Registered courses live in `data/registry.json`, inside the tool's own directory
rather than `~/.config`. That's so a synced or shared checkout carries the same
course list on every machine you study from. It's gitignored — your course list is
yours.

## Using it in another language

Nothing structural is German; the strings are. To translate, edit the four prompt
builders in `main.py` — `_assemble_prompt`, `opening_message`,
`opening_message_bootstrap`, `opening_message_onboard` — and
`templates/LERNLOOP_TEMPLATE.md`. That's the whole surface. The launcher, registry,
and menu need no changes.

One instruction is worth keeping whatever the language: the prompt tells Claude to
explain **without LaTeX**, in Unicode notation (`√`, `x²`, `∫`, `≤`, `λ`). A
terminal can't render `\frac`, and unrendered LaTeX is genuinely hard to read
mid-exercise. LaTeX belongs in the `.tex` files the exercises produce, not in the
chat.

## Tests

```bash
python3 -m pytest -q          # 20 offline tests, no network, no launch
python3 tier.py               # tier doctests + report this host's detected tier
```

## License

MIT — see [LICENSE](LICENSE).
