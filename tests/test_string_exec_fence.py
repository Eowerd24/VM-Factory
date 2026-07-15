"""G1 security floor: raw string exec (TransportBackend.run_cmd) and the
git-clone-assign path must stay confined to the standalone legacy site and
never gain a second caller (e.g. a future FactoryPort adapter bypassing
typed execution). No trusted-path arbitrary shell (UCC-Standards §15;
roadmap §3 G1, §8 "VMF ssh host-key + string-exec fence").

Uses AST call-site detection, not text/regex matching: an earlier version
matched the bare substring ".assign(" anywhere in a file, which false-
positived on this fence's own explanatory prose the moment another module
(library/factory_port.py, G3) documented the fence in its docstring. Only
actual `X.assign(...)` / `X.run_cmd(...)` call expressions count.
"""
import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

ALLOWED_RUN_CMD_CALLERS = {
    REPO_ROOT / "library" / "engine.py",  # fenced legacy assign implementation only
}

ALLOWED_ASSIGN_CALLERS = {
    REPO_ROOT / "library" / "engine.py",  # definition site
    REPO_ROOT / "nodectl.py",             # standalone CLI
    REPO_ROOT / "panel" / "main.py",      # standalone panel
}


def _python_files():
    for path in REPO_ROOT.rglob("*.py"):
        if any(part in {"__pycache__", ".venv", "node_modules"} for part in path.parts):
            continue
        if path.parts[-3:-1] == ("tests", "__pycache__"):
            continue
        if REPO_ROOT / "tests" in path.parents and path.name.startswith("test_"):
            continue
        yield path


def _called_attrs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.func.attr
        for node in ast.walk(tree)
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
    }


def test_run_cmd_confined_to_legacy_assign_path():
    offenders = []
    for path in _python_files():
        if "run_cmd" in _called_attrs(path) and path not in ALLOWED_RUN_CMD_CALLERS:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"raw string-exec run_cmd() called outside the fenced legacy path: {offenders}. "
        "If this is a new FactoryPort adapter, route through typed execution instead."
    )


def test_engine_assign_confined_to_standalone_entry_points():
    offenders = []
    for path in _python_files():
        if "assign" in _called_attrs(path) and path not in ALLOWED_ASSIGN_CALLERS:
            offenders.append(str(path.relative_to(REPO_ROOT)))
    assert not offenders, (
        f"NodeLifecycleEngine.assign() (git-clone-assign legacy path) called outside "
        f"standalone entry points: {offenders}."
    )
