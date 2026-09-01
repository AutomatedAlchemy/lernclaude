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
    lernen                       -> course menu (10s autostart of the registered default)
    lernen <workspace>           -> konsole running `claude` in that workspace folder
    lernen --tutor               -> Tutors Choice: one session that picks the course AND tutors it
    lernen --quickie             -> Quickie: one short, winnable Häppchen (5 min), streak-counted
    lernen [ws] --vorbereitung   -> Vorbereitung: read a self-study overview first, then get quizzed on it
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

    The default may also be the Tutors Choice or Quickie sentinel — those are
    menu/autostart concepts, so scripts and the inspection flags fall back to
    the first course.
    """
    env = os.environ.get("LERNCLAUDE_DEFAULT_WORKSPACE")
    if env:
        return str(Path(os.path.expanduser(env)).resolve())
    data = _load_registry()
    default = data.get("default")
    if default and default not in _SENTINELS:
        return default
    workspaces = data.get("workspaces") or []
    return workspaces[0] if workspaces else None


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
# working medium: one launcher-level switch (menu key `m`), not a per-course fact
# ----------------------------------------------------------------------------
# The *choice* of medium lives here (registry key `medium`, toggled in the TUI);
# the *mechanics* of each medium live in templates/medium_<name>.md and ride into
# the session via the system prompt. Course CLAUDE.mds carry neither any more —
# they keep only course content (Themenkarte, Eckdaten, rotation).
_MEDIA = ("xournalpp", "board")
_MEDIUM_LABELS = {"xournalpp": "Xournal++ + Firefox", "board": "Tutor Board"}


def _current_medium() -> str:
    """The active medium: env override, else registry, else xournalpp."""
    raw = (os.environ.get("LERNCLAUDE_MEDIUM")
           or _load_registry().get("medium") or "xournalpp")
    med = raw.strip().lower()
    return med if med in _MEDIA else "xournalpp"


def _set_medium(medium: str) -> str:
    data = _load_registry()
    data["medium"] = medium
    _save_registry(data)
    return medium


def _medium_prompt(medium: str) -> str:
    """The medium's mechanics from its template file — empty when missing."""
    try:
        return (TEMPLATE_DIR / f"medium_{medium}.md").read_text(encoding="utf-8")
    except OSError:
        return ""


# ----------------------------------------------------------------------------
# prompt assembly
# ----------------------------------------------------------------------------
def _prompt_common() -> str:
    """The launcher-owned orientation every session gets: the active medium and
    its mechanics, the no-LaTeX terminal rule, and today's date."""
    today = datetime.now().strftime("%A %Y-%m-%d")
    medium = _current_medium()
    text = (
        f"Arbeitsmedium dieser Session: {_MEDIUM_LABELS[medium]} — gesetzt über "
        "den Umschalter im lernen-Menü, nicht erfragen. Die Mechanik des Mediums "
        "steht unten. Der User darf mitten im Lernen wechseln („lass uns aufs "
        "Board“, „zurück zu Xournal“) — dann ab dem nächsten Häppchen im neuen "
        "Medium weiterarbeiten und ihn erinnern, fürs nächste Mal den Schalter "
        "im Menü umzulegen. Schreibt die Kurs-CLAUDE.md ausdrücklich ein festes "
        "Medium vor, gilt die Kurs-Datei.\n\n"
        "WICHTIG — Terminal-Ausgabe: Erklär mir OHNE LaTeX. Kein $...$, kein "
        "\\frac, keine LaTeX-Makros — das rendert im Terminal nicht und ist schwer "
        "zu entziffern. Schreib stattdessen in normaler/Unicode-Notation "
        "(z.B. √, x², ∫, ≤, λ, x_1, Brüche als (a+b)/c). LaTeX gehört nur in die "
        ".tex-Dateien der Häppchen, nicht in deine Chat-Erklärungen.\n\n"
        f"---\n# Heute: {today}\n"
    )
    mechanics = _medium_prompt(medium)
    if mechanics:
        text += "\n---\n" + mechanics
    return text


def _assemble_prompt(workspace: str) -> str:
    """Thin orientation only — the actual procedure (which sheets to open, the
    Häppchen rotation) is the SSoT in the workspace's CLAUDE.md, which is loaded
    automatically. We deliberately do NOT restate the file list here. The
    working medium is the one launcher-owned piece: its choice comes from the
    menu switch, its mechanics from templates/medium_<name>.md."""
    return (
        f"Du fährst eine Klausur-Lern-Session im Ordner {workspace}. "
        "Die vollständige Prozedur (welches Lern-Set du öffnest und die "
        "Häppchen-Rotation) steht in der CLAUDE.md dieses Ordners "
        "§'Lern-Loop' — folge ihr, dupliziere sie nicht. "
        "Klausurdatum und Stand stehen im Workspace (z.B. todo.md / CLAUDE.md); "
        "leite die verbleibenden Tage selbst daraus ab.\n\n"
        + _prompt_common()
    )


def _assemble_tutor_prompt() -> str:
    """System prompt for a Tutors Choice session: same session, one extra step —
    it first chooses the course, then runs that course's Lern-Loop itself."""
    return (
        "Du fährst eine Klausur-Lern-Session als Tutor über MEHRERE Kurs-Ordner: "
        "du wählst zuerst selbst den dringendsten Kurs (Dossiers in der ersten "
        "Nachricht) und führst dann dessen Lern-Loop aus. Die vollständige "
        "Prozedur steht in der CLAUDE.md des gewählten Kurs-Ordners §'Lern-Loop' "
        "— lies sie, folge ihr, dupliziere sie nicht; Klausurdatum und Stand "
        "stehen im jeweiligen Workspace (todo.md / CLAUDE.md).\n\n"
        + _prompt_common()
    )


# The personalization brief shared by both opening messages: how the session
# should tutor once it is inside a course.
_LOOP_BRIEF = (
    "Schau dir zuerst meine Lerntrajektorie an und untersuche "
    "meine Fehlermuster, um die nächsten Übungen bewusst und dynamisch zu "
    "personalisieren. Beachte hierbei die näher rückende Klausur "
    "gemäß Datum sowie die tatsächlich benötigte Zeit pro Häppchen. "
    "Priorisiere Lernstoff den wir in der Klausur erwarten können, "
    "beachte hierbei Anmerkungen der Profs aus Folien oder Übungen sowie Altklausuren falls vorhanden. "
    "Nachdem das vorherige Häppchen eingereicht wurde, sichte und korrigiere es und gebe dem user feedback, "
    "erstelle anschließend ohne Nachfrage das nächste Häppchen oder gehe auf den User ein um die Abgabe noch gemeinsam zu klären. "
    "Halte nach jedem Review in todo.md die Zeile „Fortschritt: x/y Häppchen“ aktuell — "
    "x = reviewte Häppchen, y = deine aktuelle Schätzung, wie viele Häppchen es insgesamt "
    "bis zur Klausurbereitschaft braucht (y darf sich mit jedem Review ändern). "
    "Das Startmenü liest genau diese Zeile."
)


def opening_message(workspace: str) -> str:
    return (
        "Lass uns lernen. Führe die Lern-Loop aus der CLAUDE.md dieses Ordners aus: "
        "öffne das Lern-Set (wie dort beschrieben) und gib mir dann direkt das "
        "nächste Häppchen. " + _LOOP_BRIEF
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


def _build_argv(workspace: str) -> list:
    return [
        "claude",
        "--model", _select_model(),
        "--effort", _select_effort(),
        "--append-system-prompt", _assemble_prompt(workspace),
        opening_message(workspace),
    ]


def _exec_or_konsole(inner: list, workdir: str, *, inline: bool) -> int:
    """Run the assembled claude argv in `workdir`. inline=True replaces this
    process (the menu's terminal is handed to claude); inline=False spawns a
    fresh konsole window, falling back to inline when konsole is absent."""
    env = _launch_env()
    if inline:
        os.chdir(workdir)
        os.execvpe("claude", inner, env)  # replaces this process; never returns
        # …except when a test stubs execvpe: then we must NOT fall through
        # into the konsole spawn below (it once opened three real windows).
        return 0
    konsole_cmd = [
        "konsole", "--workdir", workdir, "-p", "tabtitle=Lernen", "-e", *inner,
    ]
    try:
        subprocess.Popen(konsole_cmd, start_new_session=True, env=env)
        print(f"Launched Lern-Loop in a new konsole window ({workdir}).")
        return 0
    except FileNotFoundError:
        # No konsole (headless/server) — exec claude inline in this terminal.
        print("konsole not found — launching claude in this terminal.")
        os.chdir(workdir)
        os.execvpe("claude", inner, env)  # replaces this process; never returns


def launch(workspace: str, *, inline: bool = False) -> int:
    """Launch claude in `workspace`."""
    if not os.path.isdir(workspace):
        print(f"Error: workspace folder not found: {workspace}")
        return 1
    if not os.path.isfile(os.path.join(workspace, "CLAUDE.md")):
        print(f"Warning: {workspace}/CLAUDE.md not found — the Lern-Loop procedure "
              "lives there. Run `lernen` and pick \u201eneuen Kurs anlegen\u201c to set the folder up.")
    return _exec_or_konsole(_build_argv(workspace), workspace, inline=inline)


# ----------------------------------------------------------------------------
# scaffolding: stamp the loop skeleton into a material folder
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
        ("todo.md", "# todo — Wiedereinstieg\n\n> Fach / Klausurdatum / Stand / aktive Arbeitsdateien hier.\n\n"
                    "Fortschritt: 0/? Häppchen  *(y beim ersten Review schätzen — erst dann zeigt das Menü etwas)*\n"),
        ("fehlermuster.md", "# Fehlermuster\n\n> Nach JEDEM Review: Zitat → warum falsch → was stattdessen. Dominante Muster oben.\n"),
    ):
        f = ws / name
        if not f.exists():
            f.write_text(header, encoding="utf-8")
            print(f"  + {f}")


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
    versions seeded a hardcoded prototype folder here.) With courses but no
    explicitly chosen default, Tutors Choice is the default as soon as there is
    a real choice (>= 2 courses); a single course is its own default."""
    if not data["default"] and data["workspaces"]:
        data["default"] = (_TUTOR_SENTINEL if len(data["workspaces"]) >= 2
                           else data["workspaces"][0])
    return data


def _register_workspace(path: str, make_default: bool = False) -> str:
    """Add a course; it does NOT claim the default (unless asked) — an unset
    default means Tutors Choice once a second course exists (`_ensure_default`)."""
    data = _load_registry()
    ap = _abs_path(path)
    if ap not in data["workspaces"]:
        data["workspaces"].append(ap)
    if make_default:
        data["default"] = ap
    _save_registry(data)
    return ap


def _set_default(path: str) -> str:
    literal = path.strip().lower()
    if literal in ("tutor", "tutors-choice", "tutorschoice"):
        data = _load_registry()
        data["default"] = _TUTOR_SENTINEL
        _save_registry(data)
        return "Tutors Choice"
    if literal == "quickie":
        data = _load_registry()
        data["default"] = _QUICKIE_SENTINEL
        _save_registry(data)
        return "Quickie"
    if literal in ("vorbereitung", "vorb", "prep"):
        data = _load_registry()
        data["default"] = _VORBEREITUNG_SENTINEL
        _save_registry(data)
        return "Vorbereitung"
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
        data["default"] = None      # _ensure_default recomputes (tutor / sole course)
    _save_registry(data)
    return True


# ----------------------------------------------------------------------------
# exam calendar (optional): a markdown table of upcoming exams, shown in the menu
# ----------------------------------------------------------------------------
# The file is *not* built in: set ``LERNCLAUDE_EXAMS`` to a markdown file, or put
# its path in the registry as ``exams_file``. Any markdown table in that file is
# read when it has both a date column (Termin/Datum/Date) and a label column
# (Fach/Kurs/Modul/Prüfung/Subject/Course) — everything else in the file is
# ignored, so a personal notes file can host the table without extra structure.
_DATE_HEADERS = ("termin", "datum", "date", "when")
_LABEL_HEADERS = ("fach", "kurs", "modul", "prüfung", "pruefung", "klausur",
                  "subject", "course", "exam")
# A row whose date cell carries one of these is history, not an appointment.
_DONE_MARKERS = ("~~", "abgelegt", "bestanden", "rücktritt", "ruecktritt",
                 "entfällt", "entfaellt", "verschoben", "tbd")
_WEEKDAYS_DE = ("Mo", "Di", "Mi", "Do", "Fr", "Sa", "So")


def _exams_path() -> "str | None":
    """Where the exam table lives, or None if the user has not pointed at one."""
    env = os.environ.get("LERNCLAUDE_EXAMS")
    if env:
        return os.path.expanduser(env)
    entry = _load_registry().get("exams_file")
    return os.path.expanduser(entry) if entry else None


def _clean_cell(cell: str) -> str:
    """Strip the markdown a table cell tends to carry (bold, links, arrows)."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", cell)      # [label](url) -> label
    text = text.replace("**", "").replace("`", "").replace("~~", "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_exam_row(date_cell: str, label_cell: str, today: datetime):
    """One table row -> (datetime, has_time, label), or None if it is not a future date."""
    if any(marker in date_cell.lower() for marker in _DONE_MARKERS):
        return None
    match = re.search(r"(\d{1,2})\.\s*(\d{1,2})\.(?:\s*(\d{4}))?", date_cell)
    if not match:
        return None
    day, month, year = int(match.group(1)), int(match.group(2)), match.group(3)
    time_match = re.search(r"(\d{1,2}):(\d{2})", date_cell)
    hour, minute = (int(time_match.group(1)), int(time_match.group(2))) if time_match else (0, 0)
    try:
        when = datetime(int(year) if year else today.year, month, day, hour, minute)
    except ValueError:
        return None
    if not year and (today - when).days > 180:
        try:
            when = when.replace(year=when.year + 1)   # a bare "02.01." next January
        except ValueError:
            return None
    if when.date() < today.date():
        return None
    label = _clean_cell(label_cell)
    return (when, time_match is not None, label) if label else None


def _parse_exam_tables(text: str, today: datetime) -> list:
    """Every markdown table with a date *and* a label column, oldest date first."""
    found = []
    cols = None          # (date_col, label_col) of the table we are inside
    seen_header = False
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            cols, seen_header = None, False      # a table can only end here
            continue
        cells = [c.strip() for c in stripped.strip("|").split("|")]
        if set("".join(cells)) <= set("-: "):    # the |---|---| separator row
            continue
        if not seen_header:
            seen_header = True
            headers = [_clean_cell(c).lower() for c in cells]
            date_col = next((i for i, h in enumerate(headers)
                             if any(k in h for k in _DATE_HEADERS)), None)
            label_col = next((i for i, h in enumerate(headers)
                              if any(k in h for k in _LABEL_HEADERS)), None)
            # Both columns or nothing — a table without them is not an exam table.
            cols = None if date_col is None or label_col is None else (date_col, label_col)
            continue
        if cols and max(cols) < len(cells):
            row = _parse_exam_row(cells[cols[0]], cells[cols[1]], today)
            if row:
                found.append(row)
    return sorted(found, key=lambda r: r[0])


def upcoming_exams(limit: int = 5, now: "datetime | None" = None) -> list:
    """Upcoming exams as (days_left, "Mi 16.09. 09:00", label) — [] when unconfigured."""
    path = _exams_path()
    if not path or not os.path.isfile(path):
        return []
    try:
        text = Path(path).read_text(encoding="utf-8")
    except OSError:
        return []
    today = now or datetime.now()
    out = []
    for when, has_time, label in _parse_exam_tables(text, today)[:limit]:
        stamp = f"{_WEEKDAYS_DE[when.weekday()]} {when:%d.%m.}"
        if has_time:
            stamp += f" {when:%H:%M}"
        out.append(((when.date() - today.date()).days, stamp, label))
    return out


def _exam_banner_lines(limit: int = 5) -> list:
    """Menu header rows as (text, severity) with severity in {hot, soon, calm}."""
    lines = []
    for days, stamp, label in upcoming_exams(limit):
        left = "heute" if days == 0 else "morgen" if days == 1 else f"in {days} T"
        severity = "hot" if days <= 3 else "soon" if days <= 10 else "calm"
        lines.append((f"   {left:>9}  ·  {stamp:<16}  ·  {label}", severity))
    return lines


# ----------------------------------------------------------------------------
# course progress: the workspace session's own "x/y Häppchen bis klausurbereit"
# ----------------------------------------------------------------------------
# The judgment of how many Häppchen remain until "klausurbereit" belongs to the
# tutor session inside the workspace (SSoT boundary) — it maintains a line
#     Fortschritt: 7/24 Häppchen
# in the workspace's todo.md. The launcher only parses and displays that line,
# and, exam-banner style, fails into silence: no line, no file, garbage -> None.
_PROGRESS_RE = re.compile(r"fortschritt[^\d\n]*(\d+)\s*/\s*(\d+)", re.IGNORECASE)


def course_progress(workspace: str) -> "tuple[int, int] | None":
    """(done, target) from the workspace todo.md's Fortschritt line, or None."""
    try:
        text = (Path(workspace) / "todo.md").read_text(encoding="utf-8")
    except OSError:
        return None
    match = _PROGRESS_RE.search(text)
    if not match:
        return None
    done, target = int(match.group(1)), int(match.group(2))
    return (done, target) if target > 0 else None


def _progress_suffix(workspace: str) -> str:
    """Menu decoration for a course row — empty when the workspace has no line."""
    prog = course_progress(workspace)
    if not prog:
        return ""
    done, target = prog
    mark = "  ✓ bereit" if done >= target else ""
    return f"   · {done}/{target} Häppchen{mark}"


def _days_since_activity(workspace: str) -> "int | None":
    """Days since anything in the course's living files changed, or None."""
    ws = Path(workspace)
    candidates = [ws / "todo.md", ws / "fehlermuster.md"]
    exercises = ws / "Personalisierte_Übungen"
    if exercises.is_dir():
        try:
            candidates.extend(exercises.iterdir())
        except OSError:
            pass
    newest = None
    for f in candidates:
        try:
            mtime = f.stat().st_mtime
        except OSError:
            continue
        newest = mtime if newest is None else max(newest, mtime)
    if newest is None:
        return None
    return max(0, int((time.time() - newest) // 86400))


# ----------------------------------------------------------------------------
# Tutors Choice: ONE interactive session, launched exactly like a course launch,
# that first picks the most urgent course from the dossiers in its opening
# message and then runs that course's Lern-Loop itself — the chooser and the
# Häppchen author are the same tutor. No pre-pass, no second session.
# ----------------------------------------------------------------------------
def _shorten(text: str, limit: int = 140) -> str:
    text = re.sub(r"\s+", " ", text.replace("**", "").replace("`", "")).strip()
    return text if len(text) <= limit else text[:limit - 1] + "…"


def _themenkarte_size(workspace: str) -> "int | None":
    """Number of rows in the CLAUDE.md Themenkarte table — the course's scope."""
    try:
        text = (Path(workspace) / "CLAUDE.md").read_text(encoding="utf-8")
    except OSError:
        return None
    in_section, rows, headers = False, 0, 0
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("## "):
            in_section = "themenkarte" in stripped.lower()
            continue
        if not in_section or not stripped.startswith("|"):
            continue
        cells = "".join(stripped.strip("|").split("|"))
        if set(cells) <= set("-: "):
            headers += 1          # a |---| separator marks one header row above it
            continue
        rows += 1
    count = rows - headers
    return count if count > 0 else None


def _haeppchen_counts(workspace: str) -> "tuple[int, int] | None":
    """(created, reviewed) Häppchen counted from the exercise folder's files.
    Objective activity — independent of the self-reported Fortschritt line.
    Board-medium Häppchen leave no files; the Fortschritt line covers those."""
    folder = Path(workspace) / "Personalisierte_Übungen"
    try:
        names = [f.name for f in folder.iterdir()]
    except OSError:
        return None
    stems = {n.split(".")[0].replace("_reviewt", "")
             for n in names if n.startswith("haeppchen")}
    reviewed = sum(1 for n in names if n.endswith("_reviewt.png"))
    return (len(stems), reviewed) if stems else None


def _top_fehlermuster(workspace: str) -> "str | None":
    """The first entry of fehlermuster.md — by convention the dominant one."""
    try:
        text = (Path(workspace) / "fehlermuster.md").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("- ", "* ")) and len(stripped) > 4:
            return _shorten(stripped[2:])
        if stripped.startswith("### "):
            return _shorten(stripped[4:])
    return None


def _todo_stand(workspace: str) -> "str | None":
    """The newest dated line of todo.md — entries are chronological."""
    try:
        text = (Path(workspace) / "todo.md").read_text(encoding="utf-8")
    except OSError:
        return None
    for line in reversed(text.splitlines()):
        # 4-digit year required: a bare "27.07.10" is usually an old exam's
        # filename, not a log entry.
        if re.search(r"\d{4}-\d{2}-\d{2}|\d{1,2}\.\d{1,2}\.\d{4}", line):
            return _shorten(line.strip().lstrip("-*#> ").strip())
    return None


def _course_dossier(workspace: str) -> str:
    """Everything mechanically extractable from the files every course is
    guaranteed to have (CLAUDE.md, todo.md, fehlermuster.md, the exercise
    folder) — facts, not excerpts; a missing piece drops its line silently.
    Depth stays with the session: it reads the candidates' files itself."""
    prog = course_progress(workspace)
    days = _days_since_activity(workspace)
    facts = [
        f"Fortschritt: {prog[0]}/{prog[1]} Häppchen" if prog else "Fortschritt: unbekannt",
        f"letzte Aktivität: vor {days} Tagen" if days is not None else "letzte Aktivität: unbekannt",
    ]
    topics = _themenkarte_size(workspace)
    if topics:
        facts.append(f"Themenkarte: {topics} Themen")
    counts = _haeppchen_counts(workspace)
    if counts:
        facts.append(f"Übungsdateien: {counts[0]} Häppchen, {counts[1]} reviewt")
    lines = [f"### {Path(workspace).name} — {workspace}", " · ".join(facts)]
    top = _top_fehlermuster(workspace)
    if top:
        lines.append(f"Top-Fehlermuster: {top}")
    stand = _todo_stand(workspace)
    if stand:
        lines.append(f"Zuletzt (todo.md): {stand}")
    return "\n".join(lines)


def _exam_prompt_lines() -> str:
    """The upcoming exams as prompt lines — shared by Tutors Choice and the
    Quickie, both of which pick a course and want the deadlines in view."""
    exams = upcoming_exams()
    return ("\n".join(f"- in {d} Tagen · {stamp} · {label}" for d, stamp, label in exams)
            or "- unbekannt (keine Klausurtabelle konfiguriert)")


def opening_message_tutor(workspaces: list) -> str:
    exam_lines = _exam_prompt_lines()
    dossiers = "\n\n".join(_course_dossier(ws) for ws in workspaces)
    return (
        "Tutors Choice — lass uns lernen. Wähle zuerst selbst den Kurs, den ich "
        "JETZT lernen sollte. Wäge dynamisch ab: nahe Klausur + wenig Fortschritt "
        "= dringend; lange inaktive Kurse nicht verhungern lassen; ein Kurs, der "
        "schon „bereit“ ist, braucht höchstens Frischhalten. Ordne die Klausuren "
        "den Kursen über die Namen zu; lies vor der Entscheidung die todo.md "
        "(und bei Bedarf fehlermuster.md) der aussichtsreichsten Kandidaten.\n\n"
        f"Anstehende Klausuren:\n{exam_lines}\n\nKurse:\n{dossiers}\n\n"
        "Sag mir in EINEM Satz, welchen Kurs du wählst und warum — und dann ohne "
        "Rückfrage direkt los: lies die CLAUDE.md des gewählten Kurs-Ordners, "
        "führe dessen Lern-Loop aus (Lern-Set öffnen, wie dort beschrieben) und "
        "gib mir das nächste Häppchen. Alle Dateiarbeit mit absoluten Pfaden im "
        "gewählten Kurs-Ordner. " + _LOOP_BRIEF
    )


def _tutor_workdir(workspaces: list) -> str:
    """The deepest folder containing every course — the session works across
    them, so it starts at their common root (falling back to $HOME)."""
    try:
        common = os.path.commonpath(workspaces)
    except ValueError:
        common = ""
    if common and common != os.sep and os.path.isdir(common):
        return common
    return str(Path.home())


def _launch_tutor_choice(data: dict, *, inline: bool) -> int:
    """Launch the Tutors Choice session — one interactive claude, started just
    like a course launch, that picks the course and then tutors it."""
    workspaces = data["workspaces"]
    inner = [
        "claude",
        "--model", _select_model(),
        "--effort", _select_effort(),
        "--append-system-prompt", _assemble_tutor_prompt(),
        opening_message_tutor(workspaces),
    ]
    return _exec_or_konsole(inner, _tutor_workdir(workspaces), inline=inline)


# ----------------------------------------------------------------------------
# Quickie: ONE short, winnable Häppchen — the low-threshold entry. Same session
# mechanics as Tutors Choice (one interactive claude, picks the course itself
# when there are several), but the brief is scaled down to five minutes and
# tuned for a quick win plus a "noch eins?" — the point is the habit, not the
# coverage. The launcher keeps a streak (days in a row with a Quickie) in the
# registry and shows it on the menu row; the session gets it to celebrate.
# ----------------------------------------------------------------------------
def _quickie_stats(data: dict, today: "str | None" = None) -> "tuple[int, int]":
    """(active streak in days, total Quickies). The streak counts only when
    the last Quickie was today or yesterday — a lapsed streak shows as 0."""
    q = data.get("quickies") or {}
    today = today or datetime.now().strftime("%Y-%m-%d")
    try:
        last = datetime.strptime(str(q.get("last")), "%Y-%m-%d")
        gap = (datetime.strptime(today, "%Y-%m-%d") - last).days
    except ValueError:
        return 0, int(q.get("total") or 0)
    streak = int(q.get("streak") or 0) if 0 <= gap <= 1 else 0
    return streak, int(q.get("total") or 0)


def _record_quickie(data: dict, today: "str | None" = None) -> "tuple[int, int]":
    """Count this launch: extend the streak (yesterday → +1, today → same,
    older → restart at 1) and bump the total. Returns the new (streak, total).
    The caller persists the registry."""
    today = today or datetime.now().strftime("%Y-%m-%d")
    q = data.setdefault("quickies", {})
    streak, total = _quickie_stats(data, today)
    if q.get("last") != today:
        streak += 1
    q.update(last=today, streak=streak, total=total + 1)
    return streak, total + 1


def _quickie_suffix(data: dict) -> str:
    """Menu-row suffix: the active streak, or the total once there is one."""
    streak, total = _quickie_stats(data)
    if streak >= 2:
        return f"   · Serie: {streak} Tage"
    if total:
        return f"   · bisher {total}"
    return ""


def _assemble_quickie_prompt(workspaces: list) -> str:
    """System prompt for a Quickie: one short Häppchen, the course's own
    Lern-Loop mechanics scaled down to five minutes."""
    if len(workspaces) == 1:
        where = (f"Du fährst ein Quickie im Kurs-Ordner {workspaces[0]} — dessen "
                 "CLAUDE.md ist automatisch geladen. ")
    else:
        where = ("Du fährst ein Quickie als Tutor über MEHRERE Kurs-Ordner: du "
                 "wählst den Kurs selbst (Dossiers in der ersten Nachricht) und "
                 "liest dann dessen CLAUDE.md. ")
    return (
        where +
        "Ein Quickie ist EIN kurzes Häppchen (ca. 5 Minuten), sonst nichts: keine "
        "lange Analyse, kein Programm für die Session. Die Mechanik des Häppchens "
        "(Lern-Set, Medium, Dateien, Review) steht in der CLAUDE.md des Kurses "
        "§'Lern-Loop' — folge ihr, dupliziere sie nicht, aber skaliere sie auf "
        "ein Häppchen herunter.\n\n"
        + _prompt_common()
    )


def opening_message_quickie(workspaces: list, streak: int = 0, total: int = 0) -> str:
    if total <= 1:
        count = "Das ist mein erstes Quickie."
    elif streak >= 2:
        count = f"Das ist Quickie Nr. {total}, Tag {streak} in Folge."
    else:
        count = f"Das ist Quickie Nr. {total}."
    exams = f"Anstehende Klausuren:\n{_exam_prompt_lines()}\n\n"
    if len(workspaces) == 1:
        pick = "Kurs: dieser Ordner, keine Wahl nötig. " + exams
    else:
        dossiers = "\n\n".join(_course_dossier(ws) for ws in workspaces)
        pick = (
            "Wähle den Kurs in EINEM Halbsatz aus den Dossiers unten — ohne vorher "
            "Dateien zu lesen. Nimm den Kurs, in dem ein kleiner Erfolg gerade am "
            "meisten bringt (Klausur nah, oder lange nicht angefasst, oder ein "
            "Fehlermuster, das sich in 5 Minuten knacken lässt); wechsle über die "
            "Tage durch, nicht immer derselbe. Ordne die Klausuren den Kursen über "
            "die Namen zu.\n\n"
            + exams +
            f"Kurse:\n{dossiers}\n\n"
        )
    return (
        f"Quickie! Nur ein kurzes Häppchen, ich hab 5 Minuten. {count} "
        "Begrüß mich in einem Satz, gern mit dem Zähler, dann direkt los.\n\n"
        + pick +
        "Die Aufgabe: EINE kleine, in sich geschlossene Aufgabe, in ca. 5 Minuten "
        "lösbar und klar gewinnbar — leicht unter meiner Kante, nicht darüber; "
        "ein Fehlermuster aus fehlermuster.md als schneller Sieg ist ideal. Wirf "
        "einen Blick in todo.md und fehlermuster.md (nicht mehr), such dir ein "
        "Thema aus der Themenkarte und öffne das Häppchen sofort im aktiven Medium, "
        "so wie es die CLAUDE.md des Kurses beschreibt. Kein Vorgeplänkel, keine "
        "Theorie-Einleitung; wenn ich einen Halbsatz Kontext brauche, dann genau "
        "einen.\n\n"
        "Nach der Abgabe: kurz und warm korrigieren, in einem Satz sagen, was ich "
        "jetzt in der Hand habe (auch wenn das ein Fehler ist), einen Fehler "
        "höchstens in zwei Sätzen erklären. Dann in EINER Zeile fragen: „Noch "
        "eins?“ — mit dem "
        "nächsten Quickie schon im Kopf (nächstes Thema oder eine Stufe schwerer), "
        "damit es bei Ja sofort weitergeht. Sag ich nein oder nichts mehr, "
        "verabschiede dich in einem Satz — kein Nachschieben, keine Predigt, kein "
        "„du solltest noch“. Halte in todo.md die Zeile „Fortschritt: x/y Häppchen“ "
        "aktuell (ein Quickie zählt als Häppchen) und notiere die Quickies mit "
        "Datum und Thema in todo.md, damit die nächste Session sie sieht. Alle "
        "Dateiarbeit mit absoluten Pfaden im Kurs-Ordner."
    )


def _launch_quickie(data: dict, *, inline: bool) -> int:
    """Launch a Quickie session: count it for the streak, then start one
    interactive claude — in the course itself when there is only one, at the
    courses' common root otherwise."""
    workspaces = data["workspaces"]
    streak, total = _record_quickie(data)
    _save_registry(data)
    inner = [
        "claude",
        "--model", _select_model(),
        "--effort", _select_effort(),
        "--append-system-prompt", _assemble_quickie_prompt(workspaces),
        opening_message_quickie(workspaces, streak, total),
    ]
    workdir = workspaces[0] if len(workspaces) == 1 else _tutor_workdir(workspaces)
    return _exec_or_konsole(inner, workdir, inline=inline)


# ----------------------------------------------------------------------------
# Vorbereitung: read first, then be quizzed on exactly that
# ----------------------------------------------------------------------------
# One course per launch (no pick — the course comes in like a normal launch),
# one session, two moves: an overview of the topics planned for this session
# that the user can study on his own, then — once he says he has read it — the
# course's normal Häppchen loop over those same topics. The launcher owns only
# the SHAPE of that (overview → wait → quiz). WHICH topics is a tutoring
# judgment (Themenkarte, in the course CLAUDE.md); HOW the overview is presented
# is medium mechanics (templates/medium_<name>.md). Neither belongs here.
def _assemble_vorbereitung_prompt(workspace: str) -> str:
    """System prompt for a Vorbereitungs-Session — the two moves, nothing else."""
    return (
        f"Du fährst eine Vorbereitungs-Session im Kurs-Ordner {workspace}. Sie "
        "läuft in zwei Zügen: ERST eine selbstlernbare Übersicht über die Themen, "
        "die für diese Session geplant sind — der User liest sie in Ruhe, du "
        "fragst währenddessen nichts ab. ERST wenn er sagt, dass er durch ist, "
        "läuft der normale Häppchen-Betrieb, und zwar über genau diese Themen. "
        "Woher die Themen kommen (Themenkarte) und wie die Häppchen laufen, steht "
        "in der CLAUDE.md dieses Ordners §'Lern-Loop' — folge ihr, dupliziere sie "
        "nicht. Wie die Übersicht im aktiven Medium aussieht, steht unten in der "
        "Medium-Mechanik.\n\n"
        + _prompt_common()
    )


def opening_message_vorbereitung(workspace: str) -> str:
    return (
        "Vorbereitung, dann Abfrage. Erster Zug: such dir aus der Themenkarte die "
        "Themen aus, die für diese Session dran sind — wenige, so viele wie in "
        "eine Session passen; richte dich nach Fortschritt, fehlermuster.md, "
        "todo.md und der Klausurnähe. Sag mir in EINEM Satz, welche das sind und "
        "warum, und schreib mir dann dazu eine Übersicht, die ich allein lesen "
        "und verstehen kann: je Thema die Idee in eigenen Worten, die Notation "
        "ausgeschrieben, das Vorgehen in Schritten, EIN durchgerechnetes Beispiel "
        "und die typische Falle. Setz kein Vorwissen voraus, kürze nichts ab, "
        "frag zwischendurch nichts — ich will lesen, nicht rechnen. Leg sie im "
        "aktiven Medium an (siehe Systemprompt) und warte dann.\n\n"
        "Zweiter Zug: erst wenn ich sage, dass ich sie gelesen habe, geht es los "
        "— dann fragst du mich über genau diese Themen ab, mit den Häppchen aus "
        "der CLAUDE.md dieses Ordners. Steig direkt ein, ohne die Übersicht noch "
        "einmal zu erzählen: die war die Erklärung. Merkst du beim Review, dass "
        "ein Punkt der Übersicht nicht angekommen ist, zeig ihn dort noch einmal "
        "und geh weiter. " + _LOOP_BRIEF
    )


def _vorbereitung_target(data: dict) -> "str | None":
    """The course the menu row prepares: the same one a bare launch would open —
    the registered default, or the first course when the default is a sentinel."""
    default = data.get("default")
    if default and default not in _SENTINELS:
        return default
    workspaces = data.get("workspaces") or []
    return workspaces[0] if workspaces else None


def _launch_vorbereitung(workspace: str, *, inline: bool = False) -> int:
    """Launch a Vorbereitungs-Session in `workspace` — one course, one session."""
    if not os.path.isdir(workspace):
        print(f"Error: workspace folder not found: {workspace}")
        return 1
    inner = [
        "claude",
        "--model", _select_model(),
        "--effort", _select_effort(),
        "--append-system-prompt", _assemble_vorbereitung_prompt(workspace),
        opening_message_vorbereitung(workspace),
    ]
    return _exec_or_konsole(inner, workspace, inline=inline)


# ----------------------------------------------------------------------------
# startup menu (curses): pick a course, add one, set the default; 10s autostart
# ----------------------------------------------------------------------------
_ADD_SENTINEL = "__ADD__"
_TUTOR_SENTINEL = "__TUTOR__"
_QUICKIE_SENTINEL = "__QUICKIE__"
_VORBEREITUNG_SENTINEL = "__VORBEREITUNG__"
_SENTINELS = (_ADD_SENTINEL, _TUTOR_SENTINEL, _QUICKIE_SENTINEL,
              _VORBEREITUNG_SENTINEL)


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
                "add": 0, "foot": 0, "count": curses.A_REVERSE | curses.A_BOLD, "path": 0,
                "hot": curses.A_BOLD, "soon": curses.A_BOLD, "calm": 0,
                "tutor": curses.A_BOLD, "quickie": curses.A_BOLD,
                "vorb": curses.A_BOLD}
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
    curses.init_pair(8, curses.COLOR_RED, bg)                    # exam ≤ 3 days out
    curses.init_pair(9, curses.COLOR_YELLOW, bg)                 # exam ≤ 10 days out
    curses.init_pair(10, curses.COLOR_MAGENTA, bg)               # Tutors Choice
    return {
        "title": curses.color_pair(1) | curses.A_BOLD,
        "cursor": curses.color_pair(2) | curses.A_BOLD,
        "star": curses.color_pair(3),   # not bold — only the selected row goes bold
        "add": curses.color_pair(4),    # not bold — only the selected row goes bold
        "foot": curses.color_pair(5),
        "count": curses.color_pair(6) | curses.A_BOLD,
        "path": curses.color_pair(7),
        "hot": curses.color_pair(8) | curses.A_BOLD,
        "soon": curses.color_pair(9),
        "calm": curses.color_pair(7),
        # Always-bold magenta reads as bright purple in the common palettes —
        # the row should pop, unlike the muted magenta of the add row.
        "tutor": curses.color_pair(10) | curses.A_BOLD,
        # Bold yellow: warm and quick, visibly not the tutor's purple.
        "quickie": curses.color_pair(9) | curses.A_BOLD,
        # Bold cyan: the calm, read-first row — neither the tutor nor the quickie.
        "vorb": curses.color_pair(1) | curses.A_BOLD,
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


def _menu_rows(workspaces: list) -> list:
    """Quickie on top (as soon as there is a course), then Tutors Choice (only
    once there is something to choose between), then Vorbereitung (course-scoped,
    so it needs a course but no choice), the courses, the add row."""
    quickie = [_QUICKIE_SENTINEL] if workspaces else []
    tutor = [_TUTOR_SENTINEL] if len(workspaces) >= 2 else []
    vorb = [_VORBEREITUNG_SENTINEL] if workspaces else []
    return quickie + tutor + vorb + workspaces + [_ADD_SENTINEL]


def _menu_loop(stdscr, data: dict):
    import curses
    curses.curs_set(0)
    stdscr.timeout(200)  # ms poll, so the 10s countdown can tick without a keypress
    C = _init_colors()
    workspaces = list(data["workspaces"])
    rows = _menu_rows(workspaces)
    default = data["default"]
    idx = rows.index(default) if default in rows else 0
    autostart = bool(default) and bool(workspaces)
    interacted = False
    start = time.monotonic()
    exams = _exam_banner_lines()   # read once: the menu lives for seconds, not hours
    progress = {ws: _progress_suffix(ws) for ws in workspaces}  # same lifetime
    medium = str(data.get("medium") or "xournalpp")
    if medium not in _MEDIA:
        medium = "xournalpp"
    while True:
        remaining = 10.0 - (time.monotonic() - start)
        stdscr.erase()
        _safe_addstr(stdscr, 0, 0, "╭─ Lern-Loop ", C["title"])
        _safe_addstr(stdscr, 0, 13, "— Kurs wählen ─╮", C["title"])
        top = 2
        if exams:
            _safe_addstr(stdscr, top, 0, "  ⏳ Nächste Klausuren", C["title"])
            for j, (text, severity) in enumerate(exams):
                _safe_addstr(stdscr, top + 1 + j, 0, text, C[severity])
            top += len(exams) + 2   # banner + its heading + one blank line
        _safe_addstr(stdscr, top, 0, "  ✎ Medium: ", C["title"])
        _safe_addstr(stdscr, top, 12, _MEDIUM_LABELS[medium], C["tutor"])
        _safe_addstr(stdscr, top, 12 + len(_MEDIUM_LABELS[medium]),
                     "   (m = wechseln)", C["foot"])
        top += 2
        for i, row in enumerate(rows):
            selected = (i == idx)
            is_add = (row == _ADD_SENTINEL)
            is_tutor = (row == _TUTOR_SENTINEL)
            is_def = (not is_add and row == default)
            marker = " ▶ " if selected else "   "
            if is_add:
                label = "Neuen Kurs / Pfad hinzufügen …"
                base = C["add"]
            elif row == _QUICKIE_SENTINEL:
                label = "⚡ Quickie — ein kurzes Häppchen" + _quickie_suffix(data)
                base = C["quickie"]
            elif is_tutor:
                label = "Tutors Choice — der Tutor wählt den dringendsten Kurs"
                base = C["tutor"]
            elif row == _VORBEREITUNG_SENTINEL:
                # Name the course: this row does not pick one, it prepares the
                # course a bare launch would open.
                target = _vorbereitung_target(data)
                label = ("Vorbereitung — erst Übersicht lesen, dann abgefragt werden"
                         + (f"   ({Path(target).name})" if target else ""))
                base = C["vorb"]
            else:
                label = row + progress.get(row, "")
                base = C["star"] if is_def else C["path"]
            # Selection is shown by the ▶ arrow only — no background bar; just a bold nudge.
            attr = (base | curses.A_BOLD) if selected else base
            line = marker + label + ("   ★ Standard" if is_def else "")
            _safe_addstr(stdscr, top + i, 0, line, attr)
        foot = top + len(rows) + 1
        _safe_addstr(stdscr, foot, 0,
                     "↑/↓ bewegen · Enter starten · m = Medium · d = Standard · a = hinzufügen · x = löschen · q = beenden",
                     C["foot"])
        if autostart and not interacted:
            _safe_addstr(stdscr, foot + 1, 0,
                         f"  ⏱  Autostart Standard in {max(0, int(remaining) + 1)}s  —  beliebige Taste bricht ab  ",
                         C["count"])
        stdscr.refresh()

        if autostart and not interacted and remaining <= 0:
            if default == _TUTOR_SENTINEL:
                # Sentinel default with the row hidden (course count fell below
                # 2) degrades to the sole course — a tutor pick of one is a launch.
                return ("tutor", None) if default in rows else ("launch", workspaces[0])
            if default == _QUICKIE_SENTINEL:
                return ("quickie", None)
            if default == _VORBEREITUNG_SENTINEL:
                return ("vorbereitung", _vorbereitung_target(data))
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
        elif ch == ord("m"):
            medium = _MEDIA[(_MEDIA.index(medium) + 1) % len(_MEDIA)]
            data["medium"] = medium  # persisted by the caller
        elif ch == ord("d"):
            if rows[idx] != _ADD_SENTINEL:   # the mode rows are valid defaults too
                default = rows[idx]
                data["default"] = default  # persisted by the caller
        elif ch in (ord("x"), curses.KEY_DC):  # delete the highlighted course
            if rows[idx] not in _SENTINELS and _confirm_delete(stdscr, C, rows[idx]):
                data["workspaces"].remove(rows[idx])
                if data["default"] == rows[idx]:
                    data["default"] = None
                _ensure_default(data)   # recompute: tutor / sole course / None
                workspaces = list(data["workspaces"])
                rows = _menu_rows(workspaces)
                default = data["default"]
                idx = min(idx, len(rows) - 1)  # keep the cursor in range
        elif ch in (curses.KEY_ENTER, 10, 13):
            if rows[idx] == _ADD_SENTINEL:
                return ("add", None)
            if rows[idx] == _TUTOR_SENTINEL:
                return ("tutor", None)
            if rows[idx] == _QUICKIE_SENTINEL:
                return ("quickie", None)
            if rows[idx] == _VORBEREITUNG_SENTINEL:
                return ("vorbereitung", _vorbereitung_target(data))
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
    if action == "tutor":
        return _launch_tutor_choice(data, inline=True)
    if action == "quickie":
        return _launch_quickie(data, inline=True)
    if action == "vorbereitung" and ws:
        return _launch_vorbereitung(ws, inline=True)
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
                        help="workspace folder (default: the registered default course)")
    parser.add_argument("--advertise", action="store_true", help="emit installer metadata JSON")
    parser.add_argument("--install", action="store_true", help="install desktop icon + alias (per-workspace when a folder is given)")
    parser.add_argument("--remove", action="store_true", help="remove desktop icon + alias")
    parser.add_argument("--name", default=None, help="label for a per-workspace icon (with --install <ws>)")
    parser.add_argument("--alias", default=None, help="shell alias for a per-workspace icon (with --install <ws>)")
    parser.add_argument("--menu", action="store_true", help="show the course picker menu (default when no workspace is given)")
    parser.add_argument("--list", action="store_true", help="print the registered workspaces + default, then exit")
    parser.add_argument("--add", action="store_true", help="start an interactive onboarding session to add a new course")
    parser.add_argument("--tutor", action="store_true",
                        help="Tutors Choice: launch one session that picks the most "
                             "urgent course and then tutors it")
    parser.add_argument("--quickie", action="store_true",
                        help="Quickie: one short, winnable Häppchen (5 min); "
                             "counts towards the streak shown in the menu")
    parser.add_argument("--vorbereitung", action="store_true",
                        help="Vorbereitung: one session that first writes a "
                             "self-study overview of this session's topics, then "
                             "quizzes you on them (course: positional or default)")
    parser.add_argument("--register", metavar="PATH", default=None,
                        help="scaffold + register PATH as a course (no launch; used by the onboarding session)")
    parser.add_argument("--unregister", metavar="PATH", default=None,
                        help="remove PATH from the menu registry (registry-only, no files touched)")
    parser.add_argument("--set-medium", metavar="MEDIUM", dest="set_medium", default=None,
                        choices=list(_MEDIA),
                        help="set the working medium the sessions use (xournalpp | board); "
                             "also toggled in the menu with `m`")
    parser.add_argument("--set-default", metavar="PATH", dest="set_default", default=None,
                        help="set PATH as the menu's default (auto-selected after 10s); "
                             "the literals `tutor` / `quickie` / `vorbereitung` make "
                             "Tutors Choice / the Quickie / the Vorbereitung the default")
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
        if data["default"] == _TUTOR_SENTINEL:
            print("* Tutors Choice")
        if data["default"] == _QUICKIE_SENTINEL:
            print("* Quickie")
        if data["default"] == _VORBEREITUNG_SENTINEL:
            print("* Vorbereitung")
        for w in data["workspaces"]:
            print(("* " if w == data["default"] else "  ") + w + _progress_suffix(w))
        print(f"Medium: {_MEDIUM_LABELS[_current_medium()]}")
        return 0
    if args.tutor:
        data = _ensure_default(_load_registry())
        if not data["workspaces"]:
            print("Noch kein Kurs registriert — run `lernen` for the menu.")
            return 1
        return _launch_tutor_choice(data, inline=False)
    if args.quickie:
        data = _ensure_default(_load_registry())
        if not data["workspaces"]:
            print("Noch kein Kurs registriert — run `lernen` for the menu.")
            return 1
        return _launch_quickie(data, inline=False)
    if args.vorbereitung:
        ws = _resolve_workspace(args.workspace)
        if ws is None:
            print("Noch kein Kurs registriert — run `lernen` for the menu.")
            return 1
        return _launch_vorbereitung(ws, inline=False)
    if args.set_medium:
        print("Medium:", _MEDIUM_LABELS[_set_medium(args.set_medium)])
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

    # The menu is the interactive route only. The inspection flags stay
    # non-interactive and fall back to the registry default, so they remain
    # usable from scripts and from a pipe.
    if (args.menu or not args.workspace) and not (args.print_prompt or args.dry_run):
        return run_menu()

    ws = _resolve_workspace(args.workspace)
    if ws is None:
        print("No workspace given and none registered yet — run `lernen` for the menu "
              "and pick \u201eneuen Kurs anlegen\u201c.")
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
