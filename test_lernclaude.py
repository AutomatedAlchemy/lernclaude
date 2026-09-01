"""Offline tests for lernclaude — no konsole/claude launch, no network.

Every test asserts a behaviour that would break something real: the registry
state machine, the CLI routing, the launch argv, the parsers that read foreign
files, and the SSoT boundary. Wording of prompts is deliberately not pinned.

Loads main.py under a unique module name (repo runs pytest in prepend-import
mode with no __init__.py, so a bare `import main` would collide with siblings).
"""
import datetime
import importlib.util
import json
import sys
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"
TEMPLATE = (HERE / "templates" / "LERNLOOP_TEMPLATE.md").read_text(encoding="utf-8")


def _load():
    spec = importlib.util.spec_from_file_location("lernclaude_main", MAIN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()


@pytest.fixture(autouse=True)
def spawns(monkeypatch, tmp_path):
    """No test may open a real konsole or exec a real claude. execvpe is
    recorded (tests inspect the argv); a Popen fails the test unless it opted
    in with ``spawns["allow_popen"] = True``. Also isolates the registry."""
    rec = {"exec": [], "popen": [], "cwd": None}
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "registry.json"))
    monkeypatch.delenv("LERNCLAUDE_DEFAULT_WORKSPACE", raising=False)
    monkeypatch.delenv("LERNCLAUDE_MEDIUM", raising=False)
    monkeypatch.delenv("LERNCLAUDE_EXAMS", raising=False)
    monkeypatch.setenv("CLAUDE_TIER_OVERRIDE", "max")
    monkeypatch.setattr(m.os, "chdir", lambda d: rec.update(cwd=d))
    monkeypatch.setattr(m.os, "execvpe", lambda prog, argv, env: rec["exec"].append(argv))
    monkeypatch.setattr(m.subprocess, "Popen", lambda cmd, **k: rec["popen"].append(cmd))
    yield rec
    assert not rec["popen"] or rec.get("allow_popen"), f"real spawn attempted: {rec['popen']}"


def _courses(tmp_path, *names):
    out = []
    for n in names:
        ws = tmp_path / n; ws.mkdir()
        out.append(str(ws))
    return out


# ---- guards --------------------------------------------------------------

def test_no_personal_paths_and_no_builtin_default():
    """A fresh clone must not know anyone's study folders."""
    src = MAIN.read_text(encoding="utf-8")
    for leaked in ("Klausurvorbereitung", "/home/prob", "Synced/OneDrive"):
        assert leaked not in src, f"personal path leaked into main.py: {leaked}"
    assert m._resolve_workspace(None) is None
    data = m._ensure_default(m._load_registry())
    assert data["workspaces"] == [] and data["default"] is None
    assert m._menu_rows([]) == [m._ADD_SENTINEL]


def test_advertise_answers_before_heavy_imports(monkeypatch, capsys):
    """The installer polls --advertise with a 5s timeout; it is answered at
    import time, before argparse, and must be the installer's JSON shape."""
    monkeypatch.setattr(sys, "argv", ["lernen", "--advertise"])
    with pytest.raises(SystemExit) as e:
        _load()
    assert e.value.code == 0
    meta = json.loads(capsys.readouterr().out)[0]
    assert meta["alias"] == "lernen" and meta["capability"] == "agent"
    assert "skill_name" not in meta   # an agent you talk to, not a skill


# ---- registry ------------------------------------------------------------

def test_registry_state_machine(tmp_path, monkeypatch):
    a, b = _courses(tmp_path, "A", "B")
    m._register_workspace(a)
    assert m._load_registry()["default"] is None            # registering never claims it
    assert m._ensure_default(m._load_registry())["default"] == a   # sole course is default
    m._register_workspace(b); m._register_workspace(b)
    assert m._load_registry()["workspaces"].count(b) == 1   # idempotent
    data = m._load_registry(); data["default"] = None
    assert m._ensure_default(data)["default"] == m._TUTOR_SENTINEL   # ≥2 → Tutors Choice
    m._set_default(b)
    assert m._load_registry()["default"] == b
    for literal, sentinel in (("tutor", m._TUTOR_SENTINEL), ("quickie", m._QUICKIE_SENTINEL),
                              ("vorbereitung", m._VORBEREITUNG_SENTINEL)):
        m._set_default(literal)
        data = m._load_registry()
        assert data["default"] == sentinel and sentinel not in data["workspaces"]
        assert m._resolve_workspace(None) == a               # scripts never see a sentinel
    monkeypatch.setenv("LERNCLAUDE_DEFAULT_WORKSPACE", b)
    assert m._resolve_workspace(None) == b                   # env wins
    monkeypatch.delenv("LERNCLAUDE_DEFAULT_WORKSPACE")
    m._set_default(a)
    assert m._unregister_workspace(a) and not m._unregister_workspace(a)
    assert m._ensure_default(m._load_registry())["default"] == b   # default falls back
    assert m._menu_rows([a, b]) == [m._QUICKIE_SENTINEL, m._TUTOR_SENTINEL,
                                    m._VORBEREITUNG_SENTINEL, a, b, m._ADD_SENTINEL]
    # tutor needs a choice; Vorbereitung only needs a course
    assert m._menu_rows([a]) == [m._QUICKIE_SENTINEL, m._VORBEREITUNG_SENTINEL, a, m._ADD_SENTINEL]


def test_medium_choice_precedence(monkeypatch):
    assert m._current_medium() == "xournalpp"
    m._set_medium("board")
    assert m._current_medium() == "board"                    # registry
    monkeypatch.setenv("LERNCLAUDE_MEDIUM", "xournalpp")
    assert m._current_medium() == "xournalpp"                # env wins
    monkeypatch.setenv("LERNCLAUDE_MEDIUM", "garbage")
    assert m._current_medium() == "xournalpp"                # junk falls back
    for medium in m._MEDIA:
        assert (HERE / "templates" / f"medium_{medium}.md").is_file()


def test_quickie_streak_arithmetic():
    data = {"workspaces": []}
    assert m._record_quickie(data, "2026-08-24") == (1, 1)
    assert m._record_quickie(data, "2026-08-24") == (1, 2)   # same day: no streak bump
    assert m._record_quickie(data, "2026-08-25") == (2, 3)
    assert m._quickie_stats(data, "2026-08-26") == (2, 3)    # yesterday still counts
    assert m._quickie_stats(data, "2026-08-28") == (0, 3)    # lapsed
    assert m._record_quickie(data, "2026-08-28") == (1, 4)   # restarts
    assert m._quickie_stats({"quickies": {"last": "garbage"}}) == (0, 0)


# ---- CLI routing and launching ------------------------------------------

def test_cli_routes(tmp_path, monkeypatch, spawns):
    a, b = _courses(tmp_path, "A", "B")
    m._register_workspace(a); m._register_workspace(b)
    called = []
    for name in ("run_menu", "launch", "do_add", "_launch_tutor_choice", "_launch_quickie",
                 "_launch_vorbereitung"):
        monkeypatch.setattr(m, name, lambda *x, _n=name, **k: called.append(_n) or 0)
    cases = {
        (): "run_menu",
        (a,): "launch",
        ("--add",): "do_add",
        ("--tutor",): "_launch_tutor_choice",
        ("--quickie",): "_launch_quickie",
        ("--vorbereitung",): "_launch_vorbereitung",          # course: the default
        (b, "--vorbereitung"): "_launch_vorbereitung",        # course: the positional
        ("--dry-run",): None,           # inspection flags: no menu, no launch
        ("--print-prompt",): None,
        ("--register", str(tmp_path / "Neu")): None,
    }
    for argv, expect in cases.items():
        called.clear()
        monkeypatch.setattr(sys, "argv", ["lernen", *argv])
        assert m.main() == 0, argv
        assert called == ([expect] if expect else []), argv
    assert (tmp_path / "Neu" / "CLAUDE.md").is_file()       # --register scaffolded
    assert str(tmp_path / "Neu") in m._load_registry()["workspaces"]


def test_launches_exec_one_interactive_session(tmp_path, monkeypatch, spawns):
    """Course, Tutors Choice and Quickie all exec ONE interactive claude (no -p)
    on the tier model at medium effort, in the right directory — and an
    inline launch never falls through into the konsole spawn (it once opened
    three real windows from this suite)."""
    a, b = _courses(tmp_path, "Physik", "Spanisch")
    m.launch(a, inline=True)
    m._launch_tutor_choice({"workspaces": [a, b]}, inline=True)
    data = {"workspaces": [a]}
    m._launch_quickie(data, inline=True)
    data["workspaces"].append(b)
    m._launch_quickie(data, inline=True)
    assert len(spawns["exec"]) == 4
    for argv in spawns["exec"]:
        assert argv[0] == "claude" and "-p" not in argv
        assert argv[argv.index("--model") + 1] == "opus"
        assert argv[argv.index("--effort") + 1] == "medium"
    assert m._load_registry()["quickies"]["total"] == 2      # launches are counted
    monkeypatch.setenv("CLAUDE_TIER_OVERRIDE", "pro")
    argv = m._build_argv(a)
    assert argv[argv.index("--model") + 1] == "sonnet"
    # cwd: course → itself; tutor / multi-course quickie → common root; sole quickie → course
    spawns["exec"].clear()
    cwds = []
    for call in (lambda: m.launch(a, inline=True),
                 lambda: m._launch_tutor_choice({"workspaces": [a, b]}, inline=True),
                 lambda: m._launch_quickie({"workspaces": [a]}, inline=True)):
        call(); cwds.append(spawns["cwd"])
    assert cwds == [a, str(tmp_path), a]
    # the desktop-icon route (inline=False) spawns konsole with the same argv
    spawns["allow_popen"] = True
    m.launch(a)
    assert spawns["popen"][-1][:2] == ["konsole", "--workdir"] and "claude" in spawns["popen"][-1]


# ---- prompts: orient, never re-encode the procedure ----------------------

def test_prompts_orient_without_reencoding_the_procedure(tmp_path, monkeypatch):
    """The SSoT boundary: every prompt points at the workspace CLAUDE.md and
    carries the launcher-owned bits (date, active medium's mechanics — only
    that one's), but no sheet names and no Häppchen file list."""
    a, b = _courses(tmp_path, "Physik", "Spanisch")
    Path(a, "todo.md").write_text("Fortschritt: 2/30 Häppchen\n", encoding="utf-8")
    monkeypatch.setenv("LERNCLAUDE_MEDIUM", "board")
    texts = {
        "course": m._assemble_prompt(a) + m.opening_message(a),
        "tutor": m._assemble_tutor_prompt() + m.opening_message_tutor([a, b]),
        "quickie": m._assemble_quickie_prompt([a, b]) + m.opening_message_quickie([a, b], 3, 7),
        "quickie-solo": m._assemble_quickie_prompt([a]) + m.opening_message_quickie([a], 0, 1),
        "vorbereitung": m._assemble_vorbereitung_prompt(a) + m.opening_message_vorbereitung(a),
    }
    for name, text in texts.items():
        assert "CLAUDE.md" in text and "Heute:" in text, name
        assert "get_canvas" in text and ".xopp" not in text, name   # active medium only
        for forbidden in ("cheatsheet", "basics.pdf", "haeppchen_"):
            assert forbidden not in text, (name, forbidden)
        assert "Fortschritt: x/y Häppchen" in text, name    # the menu reads that line
    assert a in texts["course"]
    assert a in texts["tutor"] and b in texts["tutor"] and "2/30" in texts["tutor"]   # dossiers
    assert a in texts["quickie"] and b in texts["quickie"]
    assert b not in texts["quickie-solo"]                    # one course: no pick
    assert a in texts["vorbereitung"] and b not in texts["vorbereitung"]   # one course, no pick
    assert "Themenkarte" in texts["vorbereitung"]            # the topics come from there
    monkeypatch.setenv("LERNCLAUDE_MEDIUM", "xournalpp")
    assert ".xopp" in m._assemble_prompt(a) and "get_canvas" not in m._assemble_prompt(a)


def test_scaffold_never_overwrites_and_teaches_the_conventions(tmp_path):
    ws = tmp_path / "NeuesFach"; ws.mkdir()
    (ws / "todo.md").write_text("KEEP ME", encoding="utf-8")
    m._scaffold_workspace(str(ws))
    assert (ws / "CLAUDE.md").is_file() and (ws / "fehlermuster.md").is_file()
    assert (ws / "Personalisierte_Übungen").is_dir()
    assert (ws / "todo.md").read_text(encoding="utf-8") == "KEEP ME"
    fresh = tmp_path / "Leer"; fresh.mkdir()
    m._scaffold_workspace(str(fresh))
    assert "Fortschritt: 0/?" in (fresh / "todo.md").read_text(encoding="utf-8")
    assert "Fortschritt: x/y Häppchen" in TEMPLATE
    # the medium is the launcher's: the template points at the system prompt
    # and carries no per-medium mechanics
    assert "Systemprompt" in TEMPLATE
    assert "get_canvas" not in TEMPLATE and "xournalpp <datei>" not in TEMPLATE


def test_vorbereitung_is_one_course_session(tmp_path, spawns):
    """Vorbereitung launches ONE interactive session in ONE course — the course
    a bare launch would open, never a pick across courses."""
    a, b = _courses(tmp_path, "Physik", "Spanisch")
    m._register_workspace(a); m._register_workspace(b)
    m._launch_vorbereitung(b, inline=True)
    argv = spawns["exec"][-1]
    assert argv[0] == "claude" and "-p" not in argv
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--effort") + 1] == "medium"
    assert spawns["cwd"] == b            # the course itself, not the common root
    assert m._launch_vorbereitung(str(tmp_path / "weg")) == 1   # missing folder: no launch
    # the menu row targets the default course; a sentinel default falls back
    m._set_default(b)
    assert m._vorbereitung_target(m._load_registry()) == b
    m._set_default("vorbereitung")
    assert m._load_registry()["default"] == m._VORBEREITUNG_SENTINEL
    assert m._vorbereitung_target(m._load_registry()) == a
    assert m._vorbereitung_target({"workspaces": [], "default": None}) is None


# ---- parsers of files the launcher does not own --------------------------

def test_course_progress_parses_or_stays_silent(tmp_path):
    ws = tmp_path / "Kurs"; ws.mkdir()
    todo = ws / "todo.md"
    todo.write_text("# todo\n\n**Fortschritt:** 7/24 Häppchen (Stand 2026-08-20)\n", encoding="utf-8")
    assert m.course_progress(str(ws)) == (7, 24)
    assert "7/24 Häppchen" in m._progress_suffix(str(ws))
    todo.write_text("Fortschritt: 20/20 Häppchen\n", encoding="utf-8")
    assert "bereit" in m._progress_suffix(str(ws))
    todo.write_text("Fortschritt: 0/? Häppchen\n", encoding="utf-8")   # scaffold placeholder
    assert m.course_progress(str(ws)) is None and m._progress_suffix(str(ws)) == ""
    assert m.course_progress(str(tmp_path / "missing")) is None


def test_dossier_extracts_facts_and_drops_missing_pieces(tmp_path):
    ws = tmp_path / "Physik"; ws.mkdir()
    (ws / "CLAUDE.md").write_text(
        "## Themenkarte\n\n| # | Thema | Falle |\n|---|---|---|\n"
        "| 1 | Coulomb | Vorzeichen |\n| 2 | Gauß | Symmetrie |\n\n## Sonst\n",
        encoding="utf-8")
    (ws / "todo.md").write_text(
        "# todo\nFortschritt: 2/26 Häppchen\n\n## Stand\n"
        "- 2026-08-13 — Workspace angelegt.\n- 2026-08-20 — **H01** neu ausgeliefert.\n"
        "- Altklausur 27.07.10 durchgesehen\n",   # dotted date without a 4-digit year: not a log line
        encoding="utf-8")
    (ws / "fehlermuster.md").write_text(
        "# Fehlermuster\n\n> Nach JEDEM Review …\n\n- Vorzeichen bei Feldrichtung vergessen\n",
        encoding="utf-8")
    ex = ws / "Personalisierte_Übungen"; ex.mkdir()
    for name in ("haeppchen_01.tex", "haeppchen_01.pdf", "haeppchen_01_reviewt.png",
                 "haeppchen_02.tex", "rechenblatt_01.xopp"):
        (ex / name).touch()
    assert m._themenkarte_size(str(ws)) == 2
    assert m._haeppchen_counts(str(ws)) == (2, 1)
    assert m._top_fehlermuster(str(ws)) == "Vorzeichen bei Feldrichtung vergessen"
    assert "H01 neu ausgeliefert" in m._todo_stand(str(ws))
    dossier = m._course_dossier(str(ws))
    for expected in ("2/26 Häppchen", "2 Themen", "2 Häppchen, 1 reviewt", "Vorzeichen", "H01"):
        assert expected in dossier
    bare = tmp_path / "Leer"; bare.mkdir()
    dossier = m._course_dossier(str(bare))
    assert "unbekannt" in dossier
    for absent in ("Themenkarte", "Übungsdateien", "Top-Fehlermuster", "Zuletzt"):
        assert absent not in dossier


_EXAM_TABLE = """# Prüfungen

| Prüf-Nr | Fach | Form | ECTS | Termin | Prüfer |
|---|---|---|---:|---|---|
| 57561 | ML in Materialwissenschaften | **schriftlich** — Mail 23.07. | 7,5 | **Fr 31.07. 09:00** (90 min) | Pelz |
| 57121 | Math für Data Science 2 | Klausur | 8 | ~~Mo 20.07.~~ **nicht bestanden** | Kronz |
| 50641 | Math. Grundlagen ML | mündlich | 5 | **abgelegt Fr 24.07. — bestanden 1,7** | Pelz |
| 66821 | Experimentalphysik II | Klausur | 2,5 | **Mi 16.09. 09:00** | Krstic |
| 57181 | Introduction to ML | Klausur | 5 | **Fr 25.09.** | Maier |
| 57190 | Analysis | Klausur | 5 | **Mo 12.01. 08:00** | Maier |

| Modul-Nr | Modul | ECTS | Note |
|---|---|---:|---|
| 65711 | Mathematik für Data Science 1 | 10 | 3,0 |
"""


def test_exam_table_parsing(tmp_path, monkeypatch):
    """Future rows only, soonest first, weekday re-derived, bare dates roll
    into next year, settled rows (~~, abgelegt) and tables without a date
    column are ignored — and no configured file means no banner, no error."""
    assert m.upcoming_exams() == []
    f = tmp_path / "Pruefungen.md"
    f.write_text(_EXAM_TABLE, encoding="utf-8")
    monkeypatch.setenv("LERNCLAUDE_EXAMS", str(f))
    rows = m.upcoming_exams(now=datetime.datetime(2026, 8, 13, 10, 0))
    assert [r[2] for r in rows] == ["Experimentalphysik II", "Introduction to ML", "Analysis"]
    assert rows[0][:2] == (34, "Mi 16.09. 09:00")
    assert rows[1][1] == "Fr 25.09."                          # no time in the cell
    assert rows[2][1] == "Di 12.01. 08:00" and rows[2][0] > 100   # January = next year
    f.write_text("| Fach | Termin |\n|---|---|\n| X | garbage |\n", encoding="utf-8")
    assert m.upcoming_exams() == []                           # fail into silence
