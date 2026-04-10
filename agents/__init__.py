# agents/__init__.py
# Safe lazy re-exports — imports only succeed after fix_agents.py has been run
# so each agent's run() has the correct signature.

def _lazy_import(module: str, fn: str):
    """Import a function lazily — returns None if module is broken."""
    try:
        import importlib
        mod = importlib.import_module(module)
        return getattr(mod, fn, None)
    except Exception:
        return None

# These are the names the orchestrator expects
run_pm_agent      = _lazy_import("agents.pm_agent",      "run_pm_agent")
run_analyst_agent = _lazy_import("agents.analyst_agent", "run_analyst_agent")
run_comms_agent   = _lazy_import("agents.comms_agent",   "run_comms_agent")
run_risk_agent    = _lazy_import("agents.risk_agent",    "run_risk_agent")
run_support_agent = _lazy_import("agents.support_agent", "run_support_agent")

# Fallback: also try the generic "run" names
if run_pm_agent is None:
    run_pm_agent      = _lazy_import("agents.pm_agent",      "run")
if run_analyst_agent is None:
    run_analyst_agent = _lazy_import("agents.analyst_agent", "run")
if run_comms_agent is None:
    run_comms_agent   = _lazy_import("agents.comms_agent",   "run")
if run_risk_agent is None:
    run_risk_agent    = _lazy_import("agents.risk_agent",    "run")
if run_support_agent is None:
    run_support_agent = _lazy_import("agents.support_agent", "run")

__all__ = [
    "run_pm_agent",
    "run_analyst_agent",
    "run_comms_agent",
    "run_risk_agent",
    "run_support_agent",
]