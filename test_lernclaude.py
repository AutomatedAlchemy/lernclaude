"""Offline tests for lernclaude — no konsole/claude launch, no network.

Loads main.py under a unique module name (repo runs pytest in prepend-import
mode with no __init__.py, so a bare `import main` would collide with siblings).
"""
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAIN = HERE / "main.py"


def _load():
    spec = importlib.util.spec_from_file_location("lernclaude_main", MAIN)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


m = _load()


def test_advertise_is_valid_json_without_skill_name():
    out = subprocess.check_output([sys.executable, str(MAIN), "--advertise"], text=True)
    data = json.loads(out)
    assert isinstance(data, list) and len(data) == 1
    meta = data[0]
    assert meta["name"] == "Lern-Loop"
    assert meta["capability"] == "agent"
    assert meta["alias"] == "lernen"
    assert "CLI" in meta["tags"]
    assert "Icon" in meta["tags"]
    # Lern-Loop is an agent tool, not a skill — must NOT advertise a skill.
    assert "skill_name" not in meta


def test_assemble_prompt_points_at_ssot_without_duplicating_file_list():
    """The prompt orients the session to the workspace CLAUDE.md but must NOT
    restate the file list — that stays SSoT in the workspace's CLAUDE.md."""
    prompt = m._assemble_prompt("/tmp/Study/Datenanalyse")
    assert "CLAUDE.md" in prompt              # points at the SSoT procedure
    assert "Lern-Loop" in prompt
    assert "Heute:" in prompt                 # dated for "days until exam" resolution
    # SSoT guard: the concrete take-in sheet names must not be hardcoded here.
    for sheet in ("cheatsheet_minimal", "algorithmen_konzepte", "basics.pdf"):
        assert sheet not in prompt


def test_prompt_forbids_latex_in_terminal():
    """The terminal can't render LaTeX, so the session must explain in plain/Unicode."""
    prompt = m._assemble_prompt("/tmp/Study/Datenanalyse").lower()
    assert "latex" in prompt
    assert "terminal" in prompt


def test_opening_message_is_the_trigger():
    msg = m.opening_message("/tmp/Study/Datenanalyse")
    assert "lass uns lernen" in msg.lower()
    assert "Häppchen" in msg


def test_no_workspace_is_hardcoded_anywhere(tmp_path, monkeypatch):
    """A fresh clone must not point at anyone's personal study folder."""
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    monkeypatch.delenv("LERNCLAUDE_DEFAULT_WORKSPACE", raising=False)
    assert m._resolve_workspace(None) is None
    src = MAIN.read_text(encoding="utf-8")
    for leaked in ("Klausurvorbereitung", "/home/prob", "Synced/OneDrive"):
        assert leaked not in src, f"personal path leaked into main.py: {leaked}"


def test_default_workspace_comes_from_the_registry(tmp_path, monkeypatch):
    """Bare `lernen` targets whatever the registry calls default."""
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    monkeypatch.delenv("LERNCLAUDE_DEFAULT_WORKSPACE", raising=False)
    ws = tmp_path / "Datenanalyse"; ws.mkdir()
    m._register_workspace(str(ws))
    assert m._resolve_workspace(None) == str(ws)


def test_env_overrides_the_registry_default(tmp_path, monkeypatch):
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    ws = tmp_path / "Fremdsprache"; ws.mkdir()
    monkeypatch.setenv("LERNCLAUDE_DEFAULT_WORKSPACE", str(ws))
    assert m._resolve_workspace(None) == str(ws)


def test_assemble_prompt_reflects_the_given_workspace():
    """Generalized: the prompt names whatever workspace it is launched in, but
    still must not restate the concrete take-in sheet file list."""
    prompt = m._assemble_prompt("/tmp/Study/Datenanalyse")
    assert "/tmp/Study/Datenanalyse" in prompt
    assert "CLAUDE.md" in prompt and "Lern-Loop" in prompt and "Heute:" in prompt
    for sheet in ("cheatsheet_minimal", "algorithmen_konzepte", "basics.pdf"):
        assert sheet not in prompt


def test_scaffold_is_nondestructive_and_creates_living_docs(tmp_path):
    """`--init` scaffolding stamps a CLAUDE.md + living-doc skeletons and never
    overwrites a file that already exists."""
    ws = tmp_path / "NeuesFach"
    ws.mkdir()
    (ws / "todo.md").write_text("KEEP ME", encoding="utf-8")  # pre-existing
    m._scaffold_workspace(str(ws))
    assert (ws / "CLAUDE.md").is_file()
    assert (ws / "fehlermuster.md").is_file()
    assert (ws / "Personalisierte_Übungen").is_dir()
    # situational docs are NOT scaffolded up front — created on demand only
    assert not (ws / "notebooklm_lernpausen.md").exists()
    assert (ws / "todo.md").read_text(encoding="utf-8") == "KEEP ME"  # not clobbered


def test_per_workspace_slug_is_filesystem_safe():
    assert m._slug("Math. Data Analysis (II)") == "math_data_analysis_ii"
    assert m._slug("") == "workspace"


# ---- workspace registry (menu backing store) ----

def test_registry_add_and_set_default(tmp_path, monkeypatch):
    reg = tmp_path / "registry.json"
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(reg))
    a = tmp_path / "Datenanalyse"; a.mkdir()
    b = tmp_path / "MFML"; b.mkdir()
    # first registered workspace becomes default automatically
    m._register_workspace(str(a))
    data = m._load_registry()
    assert str(a) in data["workspaces"] and data["default"] == str(a)
    # adding a second does NOT steal the default
    m._register_workspace(str(b))
    assert m._load_registry()["default"] == str(a)
    # explicit set_default switches it
    m._set_default(str(b))
    assert m._load_registry()["default"] == str(b)
    # idempotent: registering an existing one doesn't duplicate
    m._register_workspace(str(a))
    assert m._load_registry()["workspaces"].count(str(a)) == 1


def test_fresh_registry_stays_empty_and_offers_only_add(tmp_path, monkeypatch):
    """No hardcoded seed: a fresh install has nothing registered, so the menu
    shows only the 'add a course' row."""
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    data = m._ensure_default(m._load_registry())
    assert data["workspaces"] == [] and data["default"] is None


def test_ensure_default_selects_one_when_missing(tmp_path, monkeypatch):
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    a = tmp_path / "A"; a.mkdir()
    m._register_workspace(str(a))
    data = m._load_registry(); data["default"] = None
    assert m._ensure_default(data)["default"] == str(a)


def test_menu_is_the_default_route_when_no_workspace(monkeypatch):
    """Bare `lernen` (no positional workspace) opens the menu, not a direct launch."""
    called = {}
    monkeypatch.setattr(m, "run_menu", lambda: called.setdefault("menu", True) or 0)
    monkeypatch.setattr(m, "launch", lambda *a, **k: called.setdefault("launch", True) or 0)
    monkeypatch.setattr(sys, "argv", ["lernen"])
    m.main()
    assert called.get("menu") and not called.get("launch")


def test_register_scaffolds_and_registers_without_launching(tmp_path, monkeypatch):
    """`--register` (used by the onboarding session) prepares a course but never launches."""
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    launched = {}
    monkeypatch.setattr(m, "launch", lambda *a, **k: launched.setdefault("x", True))
    ws = tmp_path / "Datenanalyse"; ws.mkdir()
    rc = m.do_register(str(ws))
    assert rc == 0
    assert (ws / "CLAUDE.md").is_file() and (ws / "fehlermuster.md").is_file()
    assert str(ws) in m._load_registry()["workspaces"]
    assert not launched  # no session spun up


def test_add_flag_routes_to_onboarding(monkeypatch):
    called = {}
    monkeypatch.setattr(m, "do_add", lambda: called.setdefault("add", True) or 0)
    monkeypatch.setattr(m, "launch", lambda *a, **k: called.setdefault("launch", True) or 0)
    monkeypatch.setattr(sys, "argv", ["lernen", "--add"])
    m.main()
    assert called.get("add") and not called.get("launch")


def test_onboarding_message_tells_claude_how_to_register():
    """The onboarding prompt must hand claude the exact --register command."""
    msg = m.opening_message_onboard()
    assert "--register" in msg
    assert "entscheide nicht allein" in msg  # must confirm the location with the user


def test_explicit_workspace_launches_directly(monkeypatch, tmp_path):
    ws = tmp_path / "Foo"; ws.mkdir()
    called = {}
    monkeypatch.setattr(m, "run_menu", lambda: called.setdefault("menu", True) or 0)
    monkeypatch.setattr(m, "launch", lambda *a, **k: called.setdefault("launch", (a, k)) or 0)
    monkeypatch.setattr(sys, "argv", ["lernen", str(ws)])
    m.main()
    assert called.get("launch") and not called.get("menu")


def test_build_argv_uses_opus_on_max(monkeypatch):
    """On a Max host the Lern-Loop runs opus at medium effort."""
    monkeypatch.setenv("CLAUDE_TIER_OVERRIDE", "max")
    argv = m._build_argv("/tmp/Study/Datenanalyse")
    assert argv[argv.index("--model") + 1] == "opus"
    assert argv[argv.index("--effort") + 1] == "medium"


def test_build_argv_uses_tier_model_on_pro(monkeypatch):
    """A Pro host gets its cheaper tier model, still at medium effort."""
    monkeypatch.setenv("CLAUDE_TIER_OVERRIDE", "pro")
    argv = m._build_argv("/tmp/Study/Datenanalyse")
    assert argv[argv.index("--model") + 1] == "sonnet"
    assert argv[argv.index("--effort") + 1] == "medium"


def test_inspection_flags_do_not_open_the_menu(tmp_path, monkeypatch):
    """--dry-run / --print-prompt must stay non-interactive and fall back to the
    registry default. They used to fall through to the curses menu and hang."""
    monkeypatch.setenv("LERNCLAUDE_REGISTRY", str(tmp_path / "r.json"))
    ws = tmp_path / "Kurs"; ws.mkdir()
    m._register_workspace(str(ws))
    for flag in ("--dry-run", "--print-prompt"):
        called = {}
        monkeypatch.setattr(m, "run_menu", lambda: called.setdefault("menu", True) or 0)
        monkeypatch.setattr(sys, "argv", ["lernen", flag])
        assert m.main() == 0
        assert not called.get("menu"), f"{flag} opened the menu"
