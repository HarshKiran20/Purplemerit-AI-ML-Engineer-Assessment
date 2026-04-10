"""
fix_agents.py — fixes agent run() function signatures so the orchestrator
can pass data into them.

The orchestrator calls each agent like:
    run_pm_agent(metrics_data, feedback_data)
    run_analyst_agent(metrics_data, feedback_data)
    run_comms_agent(feedback_data)
    run_risk_agent(metrics_data, feedback_data, release_notes)
    run_support_agent(feedback_data)

But if each agent's run() currently takes 0 arguments, those calls fail with:
    TypeError: run_xxx() takes 0 positional arguments but N were given

This script detects the signature of each agent's run() and wraps it to
accept (and ignore/use) the orchestrator's arguments.

Run once:
    python fix_agents.py
"""

import ast
import inspect
import importlib
import textwrap
from pathlib import Path

GREEN  = "\033[92m"; YELLOW = "\033[93m"; CYAN = "\033[96m"; RED = "\033[91m"; RESET = "\033[0m"
def ok(m):   print(f"  {GREEN}✅{RESET}  {m}")
def warn(m): print(f"  {YELLOW}⚠️ {RESET}  {m}")
def fix(m):  print(f"  {CYAN}🔧{RESET}  {m}")
def fail(m): print(f"  {RED}❌{RESET}  {m}")


# Expected signatures per agent
AGENT_SIGNATURES = {
    "agents/pm_agent.py":      ("run", ["metrics_data", "feedback_data"]),
    "agents/analyst_agent.py": ("run", ["metrics_data", "feedback_data"]),
    "agents/comms_agent.py":   ("run", ["feedback_data"]),
    "agents/risk_agent.py":    ("run", ["metrics_data", "feedback_data", "release_notes"]),
    "agents/support_agent.py": ("run", ["feedback_data"]),
}

# Also check for the aliased names the orchestrator may use
ORCHESTRATOR_ALIASES = {
    "agents/pm_agent.py":      "run_pm_agent",
    "agents/analyst_agent.py": "run_analyst_agent",
    "agents/comms_agent.py":   "run_comms_agent",
    "agents/risk_agent.py":    "run_risk_agent",
    "agents/support_agent.py": "run_support_agent",
}


def get_current_params(filepath: str, fn_name: str) -> list[str]:
    """Parse the file's AST to find the current parameter list of fn_name."""
    try:
        source = Path(filepath).read_text(encoding="utf-8")
        tree   = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and node.name == fn_name:
                return [arg.arg for arg in node.args.args]
        return None  # function not found
    except Exception as e:
        return None


def patch_agent(filepath: str, fn_name: str, expected_params: list[str], alias: str):
    """
    If fn_name in filepath has wrong signature, append a shim that wraps it.
    Strategy: rename old run() → _run_core(), then add new run(*params) that calls _run_core().
    This is non-destructive — the original logic is untouched.
    """
    path   = Path(filepath)
    source = path.read_text(encoding="utf-8")

    current_params = get_current_params(filepath, fn_name)

    if current_params is None:
        warn(f"{filepath}: could not find function `{fn_name}`")
        # The agent may use a different entry point name — try to detect it
        tree = ast.parse(source)
        funcs = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
        warn(f"  Functions found: {funcs}")
        warn(f"  Ensure one of them accepts: ({', '.join(expected_params)})")
        return

    if current_params == expected_params:
        ok(f"{filepath}: run({', '.join(current_params)}) — already correct ✓")
        return

    fix(f"{filepath}: run({', '.join(current_params) or ''}) → patching to run({', '.join(expected_params)})")

    # Back up
    bak = Path(filepath + ".bak")
    bak.write_text(source)
    ok(f"  Backup: {bak}")

    # Strategy: if run() takes 0 params, rename it to _run_core() and add a wrapper
    if not current_params:
        new_source = source.replace(f"\ndef {fn_name}(", f"\ndef _run_core(", 1)
        # Also handle if it's at the top of the file (no leading newline)
        if new_source == source:
            new_source = source.replace(f"def {fn_name}(", f"def _run_core(", 1)

        params_str = ", ".join(expected_params)
        shim = textwrap.dedent(f"""

        # ── Orchestrator-compatible wrapper (added by fix_agents.py) ──────────
        def {fn_name}({params_str}):
            \"\"\"
            Wrapper that accepts orchestrator arguments.
            Passes relevant data into _run_core() via globals or keyword args.
            \"\"\"
            # Store args in module scope so _run_core() can access them
            # if it uses load_metrics() / load_feedback() internally.
            # If _run_core() already calls those tools itself, this is a no-op.
            import sys
            mod = sys.modules[__name__]
            {_build_setter(expected_params)}
            return _run_core()


        # Alias for orchestrator imports
        {alias} = {fn_name}
        """)
        new_source = new_source + shim

    else:
        # run() exists but has wrong param names — just rename params
        # Find the def line and replace it
        old_def = f"def {fn_name}({', '.join(current_params)})"
        new_def = f"def {fn_name}({', '.join(expected_params)})"
        new_source = source.replace(old_def, new_def, 1)
        # Add alias at bottom
        new_source += f"\n\n# Alias\n{alias} = {fn_name}\n"

    path.write_text(new_source)
    ok(f"  Patched ✓")


def _build_setter(params: list[str]) -> str:
    """Build the lines that store passed args into module-level vars."""
    lines = []
    for p in params:
        lines.append(f'    setattr(mod, "_{p}", {p})')
    return "\n".join(lines) if lines else "    pass"


print(f"\n{'─'*55}")
print("  fix_agents.py — Agent Signature Patcher")
print(f"{'─'*55}\n")

for filepath, (fn_name, expected_params) in AGENT_SIGNATURES.items():
    alias = ORCHESTRATOR_ALIASES[filepath]
    if not Path(filepath).exists():
        fail(f"{filepath} — FILE NOT FOUND, skipping")
        continue
    patch_agent(filepath, fn_name, expected_params, alias)

print(f"\n{'─'*55}")
print("  Done. Now verify with:")
print("  python test_warroom.py --fast")
print(f"{'─'*55}\n")