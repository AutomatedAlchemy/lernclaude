#!/usr/bin/env python3
"""lernclaude — spawn a Claude Code session that runs a personalized exam-prep Lern-Loop.

A classclaude/surfclaude/bootclaude sibling. Launches a `claude` session straight
inside an exam-prep **workspace folder** and kicks off that folder's "Lern-Loop".

One engine, many subjects: the launcher takes a workspace path (positional, or
via a per-workspace desktop icon) and launches there. A bare `lernen` opens a
menu of the workspaces you have registered; there is no built-in default folder.

Deliberately thin: the whole procedure (which sheets to open, the Häppchen loop,
the topic rotation) is the **single source of truth in each folder's `CLAUDE.md`**
— `claude` loads it automatically because we launch with `--workdir` pointed at
the folder. This tool does NOT re-encode the file list; it only opens the session
in the right place and sends the "lass uns lernen" trigger.

Design answer to "one global loop vs. specific loops per subject": ONE engine
(this file, DRY), MANY thin per-workspace desktop icons (generated on demand).
Improvements to the loop propagate to every subject; each subject still gets a
one-click resume icon that doubles as a passive deadline nudge.

Launch modes:
    lernen                       -> course menu (5s autostart of the registered default)
    lernen <workspace>           -> konsole running `claude` in that workspace folder
    lernen --init <folder>       -> scaffold <folder> into a loop workspace, then launch a bootstrap session
    lernen --print-prompt [ws]   -> print the assembled system prompt (no launch)
    lernen --dry-run [ws]        -> print the launch argv (no launch)
    lernen --install [ws]        -> desktop icon + alias (per-workspace when ws given, via --name/--alias)
    lernen --remove  [ws]        -> remove that icon + alias
"""
import json
import sys

# --advertise must answer before any heavy import (installer 5s timeout).
PARENT_METADATA = {
    "name": "Lern-Loop",
    "capability": "agent",
    "domain": "study-prep",
    "category": "personal",
    "desktop_file": "lernclaude.desktop",
    "icon": "accessories-text-editor",
    "desc": "Spawn a Claude session that runs a personalized exam-prep Lern-Loop in a workspace",
    "terminal": False,
    "args": [],
    "tags": ["CLI", "Icon"],
    "alias": "lernen",
    # Deliberately NO skill_name: lernen is an agent you talk to, not a skill.
}

if "--advertise" in sys.argv:
    print(json.dumps([PARENT_METADATA]))
    sys.exit(0)

import argparse
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = SCRIPT_DIR / "templates"

# `tier` is a sibling module. Running main.py directly puts SCRIPT_DIR on the
# path automatically, but importing it by file location (as the tests do) does
# not — so make the sibling import work either way.
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _material_root() -> str:
    """Where the onboarding session starts browsing for course material.

    Set ``LERNCLAUDE_ROOT`` to the folder your study material lives under (the
    parent of your per-subject workspaces). Defaults to ``$HOME``, which just
    means onboarding starts its search a little wider.
    """
    return os.path.expanduser(os.environ.get("LERNCLAUDE_ROOT", "~"))


def _default_workspace() -> "str | None":
    """The workspace a bare launch targets, or ``None`` on a fresh install.

    This is the registry's ``default`` field (set in the menu with ``d``, or via
    ``--set-default``). ``LERNCLAUDE_DEFAULT_WORKSPACE`` overrides it for
    scripts and one-off launches. There is deliberately no built-in default:
    a fresh clone has no idea what you study, so it opens the menu instead.
    """
    env = os.environ.get("LERNCLAUDE_DEFAULT_WORKSPACE")
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    return _load_registry().get("default")


def _abs_path(arg: str) -> str:
    """Absolute, ``~``-expanded path of an explicitly given workspace."""
    return str(Path(os.path.expanduser(arg)).resolve())


def _resolve_workspace(arg: "str | None") -> "str | None":
    """Absolute path of the workspace to launch, falling back to the default.

    Returns ``None`` when no workspace was given and none is registered yet —
    the caller routes that to the menu.
    """
    return _abs_path(arg) if arg else _default_workspace()


# ----------------------------------------------------------------------------
# launch environment (copied pattern from classclaude/bootclaude): a .desktop
# launch inherits the graphical-session PATH, which lacks the nvm bin dir where
# `claude` and `node` live. Without this, `konsole -e claude` from the icon
# opens, fails to find claude, and closes.
# ----------------------------------------------------------------------------
def _detect_nvm_node_bin() -> "str | None":
    nvm_root = os.path.expanduser("~/.nvm/versions/node")
    if not os.path.isdir(nvm_root):
        return None
    versions = sorted(
        name for name in os.listdir(nvm_root)
        if os.path.isdir(os.path.join(nvm_root, name, "bin"))
    )
    return os.path.join(nvm_root, versions[-1], "bin") if versions else None


def _launch_env() -> dict:
    env = os.environ.copy()
    nvm_bin = _detect_nvm_node_bin()
    if nvm_bin and nvm_bin not in env.get("PATH", "").split(os.pathsep):
        env["PATH"] = nvm_bin + os.pathsep + env.get("PATH", "")
    return env


# ----------------------------------------------------------------------------
# prompt assembly
# ----------------------------------------------------------------------------
def _assemble_prompt(workspace: str) -> str:
    """Thin orientation only — the actual procedure (which sheets to open, the
    Häppchen rotation) is the SSoT in the workspace's CLAUDE.md, which is loaded
    automatically. We deliberately do NOT restate the file list here."""
    today = datetime.now().strftime("%A %Y-%m-%d")
    return (
        f"Du fährst eine Klausur-Lern-Session im Ordner {workspace}. "
        "Die vollständige Prozedur (welches Lern-Set du öffnest und die "
        "Häppchen-Rotation) steht in der CLAUDE.md dieses Ordners "
        "§'Lern-Loop' — folge ihr, dupliziere sie nicht. "
        "Klausurdatum und Stand stehen im Workspace (z.B. todo.md / CLAUDE.md); "
        "leite die verbleibenden Tage selbst daraus ab.\n\n"
        "WICHTIG — Terminal-Ausgabe: Erklär mir OHNE LaTeX. Kein $...$, kein "
        "\\frac, keine LaTeX-Makros — das rendert im Terminal nicht und ist schwer "
        "zu entziffern. Schreib stattdessen in normaler/Unicode-Notation "
        "(z.B. √, x², ∫, ≤, λ, x_1, Brüche als (a+b)/c). LaTeX gehört nur in die "
        ".tex-Dateien der Häppchen, nicht in deine Chat-Erklärungen.\n\n"
        f"---\n# Heute: {today}\n"
    )


def opening_message(workspace: str) -> str:
    return (
        "Lass uns lernen. Führe die Lern-Loop aus der CLAUDE.md dieses Ordners aus: "
        "öffne das Lern-Set (wie dort beschrieben) und gib mir dann direkt das "
        "nächste Häppchen. Schau dir zuerst meine Lerntrajektorie an und untersuche "
        "meine Fehlermuster, um die nächsten Übungen bewusst und dynamisch zu "
        "personalisieren. Beachte hierbei auch (leicht) die näher rückende Klausur "
        "gemäß Datum sowie die tatsächlich benötigte Zeit pro Häppchen. Nachdem das "
        "vorherige Häppchen erledigt und von dir gesichtet wurde, designe und öffne "
        "bitte das nächste."
    )


def opening_message_bootstrap(workspace: str) -> str:
    """First-run message for `--init`: turn a raw material folder into a loop workspace."""
    return (
        f"Dies ist ein NEUER Lern-Loop-Workspace ({workspace}). Bereite ihn auf: "
        "(1) Sichte das vorhandene Material (PDFs, Folien, Altklausuren, Übungsblätter). "
        "(2) Fülle die Eckdaten in der CLAUDE.md dieses Ordners aus (Fach, Klausurdatum/-modus, "
        "Hilfsmittel). (3) Baue aus dem Material eine `themenkarte.md` (die Klausur-Themen + "
        "je Thema die typische Falle). (4) Lege die leeren lebenden Dokumente an, falls sie "
        "fehlen (`todo.md`, `trajektorie.md`, `notebooklm_lernpausen.md`). "
        "(5) Frag mich nach allem, was du aus dem Material nicht ableiten kannst. "
        "Danach starten wir den normalen Häppchen-Loop."
    )


# ----------------------------------------------------------------------------
# launch
# ----------------------------------------------------------------------------
def _select_model() -> str:
    """The Lern-Loop runs on this host's tier model — opus on Max, sonnet on
    Pro/unknown (see `tier.py`). ``LERNCLAUDE_MODEL`` pins it explicitly."""
    pinned = os.environ.get("LERNCLAUDE_MODEL")
    if pinned:
        return pinned
    from tier import model_effort
    return model_effort()[0]


def _select_effort() -> str:
    """Medium — the Lern-Loop is interactive tutoring, not a heavy one-shot job.
    Routed through the tier band so a Max host never lands below (or above)
    medium. ``LERNCLAUDE_EFFORT`` pins it explicitly."""
    from tier import tier_effort
    return tier_effort(os.environ.get("LERNCLAUDE_EFFORT", "medium"))


def _build_argv(workspace: str, *, bootstrap: bool = False) -> list:
    msg = opening_message_bootstrap(workspace) if bootstrap else opening_message(workspace)
    return [
        "claude",
        "--model", _select_model(),
        "--effort", _select_effort(),
        "--append-system-prompt", _assemble_prompt(workspace),
        msg,
    ]


def launch(workspace: str, *, bootstrap: bool = False,
           inline: bool = False) -> int:
    """Launch claude in `workspace`. inline=True replaces this process (claude
    takes over the current terminal — used from the menu, which already occupies
    a konsole); inline=False spawns a fresh konsole window (direct CLI use)."""
    if not os.path.isdir(workspace):
        print(f"Error: workspace folder not found: {workspace}")
        return 1
    if not bootstrap and not os.path.isfile(os.path.join(workspace, "CLAUDE.md")):
        print(f"Warning: {workspace}/CLAUDE.md not found — the Lern-Loop procedure "
              "lives there. Run `lernen --init <folder>` first to scaffold it.")
    inner = _build_argv(workspace, bootstrap=bootstrap)
    env = _launch_env()
    if inline:
        # We're already inside a terminal (the menu's konsole) — hand it to claude.
        os.chdir(workspace)
        os.execvpe("claude", inner, env)  # replaces this process; never returns
    title = "Lernen (init)" if bootstrap else "Lernen"
    konsole_cmd = [
        "konsole", "--workdir", workspace, "-p", f"tabtitle={title}", "-e", *inner,
    ]
    try:
        subprocess.Popen(konsole_cmd, start_new_session=True, env=env)
        print(f"Launched Lern-Loop in a new konsole window ({workspace}).")
        return 0
    except FileNotFoundError:
        # No konsole (headless/server) — exec claude inline in this terminal.
        print("konsole not found — launching claude in this terminal.")
        os.chdir(workspace)
        os.execvpe("claude", inner, env)  # replaces this process; never returns


# ----------------------------------------------------------------------------
# init: scaffold a new workspace from the template, then bootstrap-launch
# ----------------------------------------------------------------------------
def _scaffold_workspace(workspace: str) -> None:
    """Stamp a CLAUDE.md (loop procedure) + empty living-doc skeletons into a
    material folder — non-destructive: never overwrites existing files."""
    ws = Path(workspace)
    ws.mkdir(parents=True, exist_ok=True)
    template = TEMPLATE_DIR / "LERNLOOP_TEMPLATE.md"
    claude_md = ws / "CLAUDE.md"
    if not claude_md.exists() and template.is_file():
        shutil.copyfile(template, claude_md)
        print(f"  + {claude_md}  (from template)")
    (ws / "Personalisierte_Übungen").mkdir(exist_ok=True)
    # Minimal core only. Situational docs (notebooklm_lernpausen.md for break videos)
    # are created on demand, not up front.
    for name, header in (
        ("todo.md", "# todo — Wiedereinstieg\n\n> Fach / Klausurdatum / Stand / aktive Arbeitsdateien hier.\n"),
        ("fehlermuster.md", "# Fehlermuster\n\n> Nach JEDEM Review: Zitat → warum falsch → was stattdessen. Dominante Muster oben.\n"),
    ):
        f = ws / name
        if not f.exists():
            f.write_text(header, encoding="utf-8")
            print(f"  + {f}")


def do_init(workspace: str, *, inline: bool = False) -> int:
    ws = _abs_path(workspace)
    print(f"Scaffolding Lern-Loop workspace: {ws}")
    _scaffold_workspace(ws)
    _register_workspace(ws)  # appears in the menu from now on
    print("Launching bootstrap session (agent fills in themenkarte + Eckdaten from the material)…")
    return launch(ws, bootstrap=True, inline=inline)


# ----------------------------------------------------------------------------
# add a course interactively: a claude session helps decide WHERE the workspace
# goes (search the material, agree on a folder), then registers it itself.
# ----------------------------------------------------------------------------
def _tool_cmd() -> str:
    """How the onboarding session should invoke this tool to register a course."""
    return f"{sys.executable} {Path(__file__).resolve()}"


def opening_message_onboard() -> str:
    return (
        "Ich will einen NEUEN Lern-Loop-Kurs anlegen, weiß aber noch nicht genau, wo die "
        "Materialien liegen bzw. wohin der Kurs-Ordner soll. Hilf mir interaktiv:\n"
        "1. Sieh dich mit mir um: durchsuche sinnvolle Orte (dieses Verzeichnis, "
        "sowie ~/Downloads und ~/Documents) nach vorhandenem "
        "Klausur-/Kursmaterial (PDFs, Altklausuren, Übungsblätter, Folien) und zeig mir, was du findest.\n"
        "2. Schlag mir einen Ziel-Ordner für den Kurs vor (neu anlegen oder einen vorhandenen "
        "nehmen) und stimme ihn mit mir ab — frag nach, entscheide nicht allein.\n"
        "3. Sobald wir uns einig sind, registriere + scaffolde den Ordner mit genau diesem Befehl:\n"
        f"     {_tool_cmd()} --register <ABSOLUTER_PFAD>\n"
        "   Das legt die minimalen lernclaude-Dateien an (CLAUDE.md aus dem Template + todo.md + "
        "fehlermuster.md + Ordner Personalisierte_Übungen/) und trägt den Kurs ins Startmenü ein.\n"
        "4. Danach: sichte das Material und fülle in der CLAUDE.md die Eckdaten (Fach, Klausurdatum/"
        "-modus, Hilfsmittel) UND den Themenkarte-Abschnitt aus (Klausur-Themen + je Thema die typische "
        "Falle). Situative Extra-Dateien (notebooklm_lernpausen.md für Lernpausen-Videos) "
        "legst du nur an, wenn wir sie brauchen. "
        "Dann starten wir den ersten Häppchen-Durchlauf."
    )


def do_add() -> int:
    """Launch an interactive onboarding claude session (inline: takes over the menu terminal)."""
    root = _material_root()
    workdir = root if os.path.isdir(root) else str(Path.home())
    today = datetime.now().strftime("%A %Y-%m-%d")
    sys_prompt = (
        "Du hilfst dem User, einen neuen Lern-Loop-Kurs für das Tool 'lernclaude' anzulegen: "
        "gemeinsam einen Ordner für Material + personalisierte Lern-Dateien finden/festlegen, "
        "dann per angegebenem Befehl registrieren. Erklärungen im Chat OHNE LaTeX — Unicode-"
        "Notation (√, x², ∫, ≤, λ).\n\n"
        f"---\n# Heute: {today}\n"
    )
    inner = [
        "claude", "--model", _select_model(), "--effort", _select_effort(),
        "--append-system-prompt", sys_prompt,
        opening_message_onboard(),
    ]
    env = _launch_env()
    os.chdir(workdir)
    try:
        os.execvpe("claude", inner, env)  # replaces this process; never returns
    except FileNotFoundError:
        print("Error: `claude` not found on PATH — cannot start the onboarding session.")
        return 1


def do_register(path: str) -> int:
    """Scaffold + register a workspace WITHOUT launching — called by the onboarding session."""
    ws = _abs_path(path)
    _scaffold_workspace(ws)
    _register_workspace(ws)
    print(f"Registered + scaffolded course: {ws}")
    print("Es erscheint ab jetzt im `lernen`-Startmenü.")
    return 0


# ----------------------------------------------------------------------------
# workspace registry (./data/registry.json): known courses + default
# ----------------------------------------------------------------------------
# Tool-local, not ~/.config: the registry lives inside the tool's own directory
# (anchored to SCRIPT_DIR) so it rides the Syncthing-replicated repo tree and the
# course list is the same on every host. See tools/CLAUDE.md § "Tool-local state".
# gitignored (tools/.gitignore) so the mutable file never dirties git.
def _registry_path() -> Path:
    """Read from env each call so tests can redirect it after import."""
    return Path(os.path.expanduser(
        os.environ.get("LERNCLAUDE_REGISTRY", str(SCRIPT_DIR / "data" / "registry.json"))))


def _load_registry() -> dict:
    try:
        data = json.loads(_registry_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        data = {}
    data.setdefault("workspaces", [])
    data.setdefault("default", None)
    return data


def _save_registry(data: dict) -> None:
    p = _registry_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _ensure_default(data: dict) -> dict:
    """Make sure a non-empty registry always has a default selected.

    A fresh install has no workspaces at all — the menu then shows only the
    "add a course" row, which is the correct first-run experience. (Earlier
    versions seeded a hardcoded prototype folder here.)"""
    if not data["default"] and data["workspaces"]:
        data["default"] = data["workspaces"][0]
    return data


def _register_workspace(path: str, make_default: bool = False) -> str:
    data = _load_registry()
    ap = _abs_path(path)
    if ap not in data["workspaces"]:
        data["workspaces"].append(ap)
    if make_default or not data["default"]:
        data["default"] = ap
    _save_registry(data)
    return ap


def _set_default(path: str) -> str:
    data = _load_registry()
    ap = _abs_path(path)
    if ap not in data["workspaces"]:
        data["workspaces"].append(ap)
    data["default"] = ap
    _save_registry(data)
    return ap


def _unregister_workspace(path: str) -> bool:
    """Drop a workspace from the registry (registry-only — never touches files).
    Returns True if it was present. If it was the default, the default falls back
    to the first remaining workspace (or None)."""
    data = _load_registry()
    ap = _abs_path(path)
    if ap not in data["workspaces"]:
        return False
    data["workspaces"].remove(ap)
    if data["default"] == ap:
        data["default"] = data["workspaces"][0] if data["workspaces"] else None
    _save_registry(data)
    return True


# ----------------------------------------------------------------------------
# startup menu (curses): pick a course, add one, set the default; 5s autostart
# ----------------------------------------------------------------------------
_ADD_SENTINEL = "__ADD__"


def _needs_konsole_reexec() -> bool:
    """The desktop icon launches us with no controlling terminal; curses needs one."""
    try:
        return not (sys.stdin.isatty() and sys.stdout.isatty())
    except ValueError:
        return True


def _safe_addstr(stdscr, y: int, x: int, text: str, attr=0) -> None:
    try:
        stdscr.addstr(y, x, text, attr)
    except Exception:
        pass  # terminal too small / out of bounds — skip that line


def _init_colors():
    """Set up color pairs; returns a dict of ready-to-use attrs (0 = plain fallback)."""
    import curses
    if not curses.has_colors():
        # No color: only the selected row goes bold (added in the loop); countdown reverse.
        return {"title": curses.A_BOLD, "cursor": 0, "star": 0,
                "add": 0, "foot": 0, "count": curses.A_REVERSE | curses.A_BOLD, "path": 0}
    curses.start_color()
    try:
        curses.use_default_colors()
        bg = -1  # terminal's own background
    except curses.error:
        bg = curses.COLOR_BLACK
    curses.init_pair(1, curses.COLOR_CYAN, bg)                   # title
    curses.init_pair(2, curses.COLOR_WHITE, curses.COLOR_BLUE)   # cursor: white on blue bar
    curses.init_pair(3, curses.COLOR_GREEN, bg)                  # ★ default
    curses.init_pair(4, curses.COLOR_MAGENTA, bg)               # add entry
    curses.init_pair(5, curses.COLOR_BLUE, bg)                   # footer
    curses.init_pair(6, curses.COLOR_WHITE, curses.COLOR_BLUE)   # countdown: white on blue bar
    curses.init_pair(7, curses.COLOR_WHITE, bg)                 # path text
    return {
        "title": curses.color_pair(1) | curses.A_BOLD,
        "cursor": curses.color_pair(2) | curses.A_BOLD,
        "star": curses.color_pair(3),   # not bold — only the selected row goes bold
        "add": curses.color_pair(4),    # not bold — only the selected row goes bold
        "foot": curses.color_pair(5),
        "count": curses.color_pair(6) | curses.A_BOLD,
        "path": curses.color_pair(7),
    }


def _confirm_delete(stdscr, C, path: str) -> bool:
    """Blocking y/n confirmation before removing a course from the menu."""
    import curses
    while True:
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, "╭─ Kurs entfernen? ─╮", C["title"])
        _safe_addstr(stdscr, 2, 0, "Diesen Kurs aus dem Startmenü entfernen?", C["path"])
        _safe_addstr(stdscr, 3, 2, path, C["star"])
        _safe_addstr(stdscr, 5, 0,
                     "(nur der Registry-Eintrag wird gelöscht — keine Dateien werden angefasst)",
                     C["foot"])
        _safe_addstr(stdscr, 7, 0,
                     "  j / y = ja, entfernen   ·   n / Esc = abbrechen  ", C["count"])
        stdscr.refresh()
        ch = stdscr.getch()
        if ch == -1:
            continue  # timeout tick — keep waiting for a real key
        if ch in (ord("y"), ord("j")):
            return True
        if ch in (ord("n"), ord("q"), 27):  # 27 = Esc
            return False


def _menu_loop(stdscr, data: dict):
    import curses
    curses.curs_set(0)
    stdscr.timeout(200)  # ms poll, so the 5s countdown can tick without a keypress
    C = _init_colors()
    workspaces = list(data["workspaces"])
    rows = workspaces + [_ADD_SENTINEL]
    default = data["default"]
    idx = workspaces.index(default) if default in workspaces else 0
    autostart = bool(default) and bool(workspaces)
    interacted = False
    start = time.monotonic()
    while True:
        remaining = 5.0 - (time.monotonic() - start)
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, "╭─ Lern-Loop ", C["title"])
        _safe_addstr(stdscr, 0, 13, "— Kurs wählen ─╮", C["title"])
        for i, row in enumerate(rows):
            selected = (i == idx)
            is_add = (row == _ADD_SENTINEL)
            is_def = (not is_add and row == default)
            marker = " ▶ " if selected else "   "
            if is_add:
                label = "Neuen Kurs / Pfad hinzufügen …"
                base = C["add"]
            else:
                label = row
                base = C["star"] if is_def else C["path"]
            # Selection is shown by the ▶ arrow only — no background bar; just a bold nudge.
            attr = (base | curses.A_BOLD) if selected else base
            line = marker + label + ("   ★ Standard" if is_def else "")
            _safe_addstr(stdscr, 2 + i, 0, line, attr)
        foot = 2 + len(rows) + 1
        _safe_addstr(stdscr, foot, 0,
                     "↑/↓ bewegen · Enter starten · d = Standard · a = hinzufügen · x = löschen · q = beenden",
                     C["foot"])
        if autostart and not interacted:
            _safe_addstr(stdscr, foot + 1, 0,
                         f"  ⏱  Autostart Standard in {max(0, int(remaining) + 1)}s  —  beliebige Taste bricht ab  ",
                         C["count"])
        stdscr.refresh()

        if autostart and not interacted and remaining <= 0:
            return ("launch", default)

        ch = stdscr.getch()
        if ch == -1:
            continue
        interacted = True  # any key cancels the autostart countdown
        if ch in (curses.KEY_UP, ord("k")):
            idx = (idx - 1) % len(rows)
        elif ch in (curses.KEY_DOWN, ord("j")):
            idx = (idx + 1) % len(rows)
        elif ch == ord("q"):
            return ("quit", None)
        elif ch == ord("a"):
            return ("add", None)
        elif ch == ord("d"):
            if rows[idx] != _ADD_SENTINEL:
                default = rows[idx]
                data["default"] = default  # persisted by the caller
        elif ch in (ord("x"), curses.KEY_DC):  # delete the highlighted course
            if rows[idx] != _ADD_SENTINEL and _confirm_delete(stdscr, C, rows[idx]):
                data["workspaces"].remove(rows[idx])
                if data["default"] == rows[idx]:
                    data["default"] = data["workspaces"][0] if data["workspaces"] else None
                workspaces = list(data["workspaces"])
                rows = workspaces + [_ADD_SENTINEL]
                default = data["default"]
                idx = min(idx, len(rows) - 1)  # keep the cursor in range
        elif ch in (curses.KEY_ENTER, 10, 13):
            if rows[idx] == _ADD_SENTINEL:
                return ("add", None)
            return ("launch", rows[idx])


def run_menu() -> int:
    # From the desktop icon there is no TTY — re-open inside konsole running the menu.
    if _needs_konsole_reexec():
        cmd = ["konsole", "-p", "tabtitle=Lernen", "-e",
               sys.executable, str(Path(__file__).resolve()), "--menu"]
        try:
            subprocess.Popen(cmd, start_new_session=True, env=_launch_env())
            return 0
        except FileNotFoundError:
            print("No TTY and no konsole found — run `lernen --menu` from a terminal.")
            return 1

    data = _ensure_default(_load_registry())
    _save_registry(data)
    import curses
    action, ws = curses.wrapper(_menu_loop, data)
    _save_registry(data)  # persist any default change made with 'd'

    if action == "quit":
        return 0
    if action == "launch" and ws:
        return launch(ws, inline=True)
    if action == "add":
        return do_add()  # interactive: claude helps decide the location, then --register's it
    return 0


# ----------------------------------------------------------------------------
# install / remove (shared cli_tool_kit installer)
# ----------------------------------------------------------------------------
def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_") or "workspace"


def _do_install_remove(remove: bool, workspace: "str | None" = None,
                       name: "str | None" = None, alias: "str | None" = None) -> int:
    try:
        from cli_tool_kit import ToolInstaller, ToolMetadata
    except ImportError:
        try:
            from _shared.tool_installer import ToolInstaller, ToolMetadata
        except ImportError:
            print("Error: cli_tool_kit / _shared.tool_installer not found.")
            return 1

    if workspace:
        # Per-workspace icon: one thin launcher that calls `lernclaude <ws>`.
        ws = _abs_path(workspace)
        label = name or Path(ws).name
        slug = _slug(label)
        meta = ToolMetadata(
            name=f"Lern-Loop: {label}",
            desktop_file=f"lernclaude_{slug}.desktop",
            icon=PARENT_METADATA["icon"],
            desc=f"Lern-Loop im Workspace {ws}",
            tags=PARENT_METADATA["tags"],
            alias=alias or f"lernen_{slug}",
            terminal=PARENT_METADATA["terminal"],
            args=[ws],                       # appended to the .desktop Exec / alias
        )
    else:
        meta = ToolMetadata(
            name=PARENT_METADATA["name"], desktop_file=PARENT_METADATA["desktop_file"],
            icon=PARENT_METADATA["icon"], desc=PARENT_METADATA["desc"],
            tags=PARENT_METADATA["tags"], alias=PARENT_METADATA["alias"],
            terminal=PARENT_METADATA["terminal"], args=PARENT_METADATA["args"])

    installer = ToolInstaller(script_path=__file__, metadata=meta)
    installer.remove() if remove else installer.install()
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(prog="lernen", description=PARENT_METADATA["desc"])
    parser.add_argument("workspace", nargs="?", default=None,
                        help="workspace folder (default: the Math DS 2 prototype)")
    parser.add_argument("--advertise", action="store_true", help="emit installer metadata JSON")
    parser.add_argument("--install", action="store_true", help="install desktop icon + alias (per-workspace when a folder is given)")
    parser.add_argument("--remove", action="store_true", help="remove desktop icon + alias")
    parser.add_argument("--name", default=None, help="label for a per-workspace icon (with --install <ws>)")
    parser.add_argument("--alias", default=None, help="shell alias for a per-workspace icon (with --install <ws>)")
    parser.add_argument("--init", action="store_true", help="scaffold <workspace> into a loop workspace, then bootstrap-launch")
    parser.add_argument("--menu", action="store_true", help="show the course picker menu (default when no workspace is given)")
    parser.add_argument("--list", action="store_true", help="print the registered workspaces + default, then exit")
    parser.add_argument("--add", action="store_true", help="start an interactive onboarding session to add a new course")
    parser.add_argument("--register", metavar="PATH", default=None,
                        help="scaffold + register PATH as a course (no launch; used by the onboarding session)")
    parser.add_argument("--unregister", metavar="PATH", default=None,
                        help="remove PATH from the menu registry (registry-only, no files touched)")
    parser.add_argument("--set-default", metavar="PATH", dest="set_default", default=None,
                        help="set PATH as the menu's default (auto-selected after 5s)")
    parser.add_argument("--print-prompt", dest="print_prompt", action="store_true",
                        help="print the assembled system prompt and exit (no launch)")
    parser.add_argument("--dry-run", dest="dry_run", action="store_true",
                        help="print the launch argv and exit (no launch)")
    args = parser.parse_args()

    if args.advertise:                      # (also handled pre-import above)
        print(json.dumps([PARENT_METADATA]))
        return 0
    if args.install or args.remove:
        if args.workspace and not args.remove:
            _register_workspace(args.workspace)   # a per-workspace icon → also in the menu
        return _do_install_remove(remove=args.remove, workspace=args.workspace,
                                  name=args.name, alias=args.alias)
    if args.list:
        data = _ensure_default(_load_registry())
        _save_registry(data)  # persist the first-use seed so the view matches disk
        for w in data["workspaces"]:
            print(("* " if w == data["default"] else "  ") + w)
        return 0
    if args.set_default:
        print("Default:", _set_default(args.set_default))
        return 0
    if args.register:
        return do_register(args.register)
    if args.unregister:
        ap = _abs_path(args.unregister)
        if _unregister_workspace(args.unregister):
            print(f"Removed from menu: {ap}")
            return 0
        print(f"Not in registry: {ap}")
        return 1
    if args.add:
        return do_add()

    if args.init:
        if not args.workspace:
            print("Error: --init needs a workspace folder, e.g. `lernen --init ~/Study/Datenanalyse`")
            return 1
        return do_init(args.workspace)

    # The menu is the interactive route only. The inspection flags stay
    # non-interactive and fall back to the registry default, so they remain
    # usable from scripts and from a pipe.
    if (args.menu or not args.workspace) and not (args.print_prompt or args.dry_run):
        return run_menu()

    ws = _resolve_workspace(args.workspace)
    if ws is None:
        print("No workspace given and none registered yet — run `lernen` for the menu, "
              "or `lernen --init <folder>` to set one up.")
        return 1

    if args.print_prompt:
        print(_assemble_prompt(ws))
        return 0
    if args.dry_run:
        argv = _build_argv(ws)
        shown = [a if len(a) < 120 else f"<{len(a)} chars of system prompt>" for a in argv]
        print("konsole --workdir", ws, "-e \\\n  " + " ".join(shown))
        return 0
    return launch(ws)


if __name__ == "__main__":
    sys.exit(main())
