"""
test_warroom.py — War Room pipeline validator
Usage:
    python test_warroom.py              # standard (skips LLM)
    python test_warroom.py --fast       # tools + imports only
    python test_warroom.py --full       # full LLM orchestrator run
"""

import sys, json, time, traceback, os, inspect
from pathlib import Path

GREEN  = "\033[92m"; RED    = "\033[91m"; YELLOW = "\033[93m"
CYAN   = "\033[96m"; BOLD   = "\033[1m";  RESET  = "\033[0m"

def ok(msg):   print(f"  {GREEN}✅ PASS{RESET}  {msg}")
def fail(msg): print(f"  {RED}❌ FAIL{RESET}  {msg}")
def warn(msg): print(f"  {YELLOW}⚠️  WARN{RESET}  {msg}")
def head(msg): print(f"\n{BOLD}{CYAN}{'─'*55}\n  {msg}\n{'─'*55}{RESET}")
def info(msg): print(f"       {msg}")

FAST_MODE = "--fast" in sys.argv
FULL_MODE = "--full" in sys.argv
errors    = []

# ══════════════════════════════════════════════════════
# TEST 1 — File structure
# ══════════════════════════════════════════════════════
head("TEST 1 · File Structure")
required_files = {
    "app.py":                  "Streamlit UI",
    "orchestrator.py":         "Orchestrator",
    "agents/pm_agent.py":      "PM Agent",
    "agents/analyst_agent.py": "Analyst Agent",
    "agents/comms_agent.py":   "Comms Agent",
    "agents/risk_agent.py":    "Risk Agent",
    "agents/support_agent.py": "Support Agent",
    "agents/__init__.py":      "Agents package",
    "tools/metric_tools.py":   "Metric Tools",
    "tools/feedback_tools.py": "Feedback Tools",
    "tools/__init__.py":       "Tools package",
    "data/metrics.json":       "Metrics data",
    "data/feedback.json":      "Feedback data",
    "data/release_notes.md":   "Release notes",
    "output/decision.json":    "Decision output",
    "requirements.txt":        "Dependencies",
}
for path, label in required_files.items():
    if Path(path).exists():
        ok(f"{label:30s}  → {path}")
    else:
        fail(f"{label:30s}  → {path}  (MISSING)")
        errors.append(f"Missing file: {path}")

# ══════════════════════════════════════════════════════
# TEST 2 — Data files
# ══════════════════════════════════════════════════════
head("TEST 2 · Data Files")

try:
    with open("data/metrics.json") as f:
        raw_metrics = json.load(f)
    if isinstance(raw_metrics, list):
        ok(f"metrics.json — {len(raw_metrics)} days (plain list)")
        warn("Plain list — run: python fix_data.py")
    elif isinstance(raw_metrics, dict):
        key  = "daily_metrics" if "daily_metrics" in raw_metrics else "metrics"
        days = len(raw_metrics.get(key, []))
        ok(f"metrics.json — {days} days (dict format ✓)")
except Exception as e:
    fail(f"metrics.json: {e}"); errors.append(str(e))

try:
    with open("data/feedback.json") as f:
        raw_fb = json.load(f)
    entries = raw_fb if isinstance(raw_fb, list) else raw_fb.get("feedback", [])
    if entries and isinstance(entries[0], str):
        ok(f"feedback.json — {len(entries)} entries (plain strings)")
        warn("Plain strings — run: python fix_data.py")
    elif entries and isinstance(entries[0], dict):
        ok(f"feedback.json — {len(entries)} entries (dict format ✓)")
    else:
        warn("feedback.json — empty or unknown format")
except Exception as e:
    fail(f"feedback.json: {e}"); errors.append(str(e))

try:
    text = Path("data/release_notes.md").read_text()
    ok(f"release_notes.md — {len(text)} chars")
except Exception as e:
    fail(f"release_notes.md: {e}"); errors.append(str(e))

# ══════════════════════════════════════════════════════
# TEST 3 — Tool functions
# ══════════════════════════════════════════════════════
head("TEST 3 · Tool Functions")

try:
    from tools.metric_tools import (
        load_metrics, aggregate_metrics, detect_anomalies,
        analyze_trends, get_breach_summary, format_metrics_for_prompt)
    ok("metric_tools — all 6 functions imported")
except ImportError as e:
    fail(f"metric_tools import: {e}"); errors.append(str(e))

try:
    from tools.feedback_tools import (
        analyze_sentiment, categorize_issues,
        channel_breakdown, format_feedback_for_prompt, load_feedback)
    ok("feedback_tools — all 5 functions imported")
except ImportError as e:
    fail(f"feedback_tools import: {e}"); errors.append(str(e))

try:
    raw   = load_metrics()
    daily = raw if isinstance(raw, list) else raw.get("daily_metrics", raw.get("metrics", []))
    ok(f"load_metrics()           → {len(daily)} records (type={type(raw).__name__})")
    agg       = aggregate_metrics(raw)
    anomalies = detect_anomalies(raw)
    trends    = analyze_trends(raw)
    breaches  = get_breach_summary(agg)
    prompt    = format_metrics_for_prompt(agg, anomalies, trends)
    ok(f"aggregate_metrics()      → {len(agg) if isinstance(agg,(dict,list)) else type(agg).__name__}")
    ok(f"detect_anomalies()       → {len(anomalies) if isinstance(anomalies,(dict,list)) else anomalies}")
    ok(f"analyze_trends()         → {len(trends) if isinstance(trends,(dict,list)) else trends}")
    ok(f"get_breach_summary()     → {breaches}")
    ok(f"format_metrics_prompt()  → {len(prompt)} chars")
except Exception as e:
    fail(f"metric tool execution: {e}"); info(traceback.format_exc()); errors.append(str(e))

try:
    fb_raw = load_feedback()
    if isinstance(fb_raw, list) and fb_raw and isinstance(fb_raw[0], str):
        fb_norm = [{"text": t, "channel": "unknown", "sentiment": "unknown"} for t in fb_raw]
        warn("Feedback entries are plain strings — normalised for test")
    elif isinstance(fb_raw, list):
        fb_norm = fb_raw
    else:
        fb_norm = fb_raw.get("feedback", [fb_raw])
    ok(f"load_feedback()          → {len(fb_norm)} entries (normalised)")
    sentiment = analyze_sentiment(fb_norm)
    issues    = categorize_issues(fb_norm)
    channels  = channel_breakdown(fb_norm)
    fb_prompt = format_feedback_for_prompt(sentiment, issues, channels)
    ok(f"analyze_sentiment()      → {sentiment.get('overall', '(no overall key)')}")
    ok(f"categorize_issues()      → {len(issues) if isinstance(issues,(dict,list)) else issues}")
    ok(f"channel_breakdown()      → {len(channels) if isinstance(channels,(dict,list)) else channels}")
    ok(f"format_feedback_prompt() → {len(fb_prompt)} chars")
except Exception as e:
    fail(f"feedback tool execution: {e}"); info(traceback.format_exc()); errors.append(str(e))

# ══════════════════════════════════════════════════════
# TEST 4 — Agent signatures
# ══════════════════════════════════════════════════════
head("TEST 4 · Agent Imports & Signatures")

agent_mods = [
    ("agents.pm_agent",      "run"),
    ("agents.analyst_agent", "run"),
    ("agents.comms_agent",   "run"),
    ("agents.risk_agent",    "run"),
    ("agents.support_agent", "run"),
]
for module, fn in agent_mods:
    try:
        import importlib
        mod  = importlib.import_module(module)
        func = getattr(mod, fn, None)
        if not (func and callable(func)):
            fail(f"{module} — no callable `{fn}`"); errors.append(f"{module} missing run()"); continue
        params  = list(inspect.signature(func).parameters.keys())
        nparams = len(params)
        if nparams == 0:
            fail(f"{module}.run() — takes 0 args (needs ≥1)")
            errors.append(f"{module}.run() signature broken")
        else:
            ok(f"{module}.run({', '.join(params)}) — {nparams} param(s) ✓")
    except Exception as e:
        fail(f"{module}: {e}"); errors.append(str(e))

# ══════════════════════════════════════════════════════
# TEST 5 — Orchestrator
# ══════════════════════════════════════════════════════
head("TEST 5 · Orchestrator")
try:
    from orchestrator import run_war_room
    ok("orchestrator.run_war_room() imported ✓")
except Exception as e:
    fail(f"orchestrator import: {e}"); errors.append(str(e))

# ══════════════════════════════════════════════════════
# TEST 6 — Environment
# ══════════════════════════════════════════════════════
head("TEST 6 · Environment")
try:
    from dotenv import load_dotenv; load_dotenv()
    ok("python-dotenv loaded — .env parsed")
except ImportError:
    warn("python-dotenv not installed — pip install python-dotenv")

groq_key = os.getenv("GROQ_API_KEY", "")
if groq_key and groq_key not in ("your_groq_api_key_here", ""):
    ok(f"GROQ_API_KEY set — starts with: {groq_key[:8]}…")
else:
    fail("GROQ_API_KEY not set or is placeholder")
    errors.append("GROQ_API_KEY missing")

# ══════════════════════════════════════════════════════
# TEST 7 — Groq package version + API connectivity
# ══════════════════════════════════════════════════════
head("TEST 7 · Groq Package + API Connectivity")

# Check groq package version first
try:
    import groq as groq_pkg
    groq_version = getattr(groq_pkg, "__version__", "unknown")
    ok(f"groq package version: {groq_version}")

    # Warn if version is known-bad
    try:
        from packaging.version import Version
        if Version(groq_version) < Version("0.9.0"):
            warn(f"groq {groq_version} is outdated — run: pip install --upgrade groq httpx")
            errors.append(f"groq package too old: {groq_version}")
    except ImportError:
        pass  # packaging not installed, skip version check

except ImportError:
    fail("groq package not installed — pip install groq")
    errors.append("groq not installed")

if FAST_MODE:
    warn("API connectivity skipped — fast mode")
elif not groq_key or groq_key in ("your_groq_api_key_here", ""):
    warn("Skipped — no valid API key")
else:
    try:
        # Test with Groq SDK directly (same as agents use)
        from groq import Groq
        client = Groq(api_key=groq_key)
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",       # ← updated model
            messages=[{"role": "user", "content": "Reply with the word OK only."}],
            max_tokens=5,
        )
        reply = resp.choices[0].message.content.strip()
        ok(f"Groq API reachable — model: llama-3.3-70b-versatile — reply: '{reply}'")
    except TypeError as e:
        if "proxies" in str(e):
            fail(f"groq/httpx version conflict: {e}")
            info("→ Fix: pip install --upgrade groq httpx")
            errors.append("groq proxies conflict — upgrade groq + httpx")
        else:
            fail(f"Groq TypeError: {e}"); errors.append(str(e))
    except Exception as e:
        fail(f"Groq API error: {e}"); errors.append(str(e))

# ══════════════════════════════════════════════════════
# TEST 8 — Full orchestrator run
# ══════════════════════════════════════════════════════
head("TEST 8 · Full Orchestrator Run")
if not FULL_MODE:
    warn("Skipped — use --full to run the complete LLM pipeline")
    info("  python test_warroom.py --full")
elif errors:
    warn(f"Skipped — fix the {len(errors)} issue(s) above first")
else:
    try:
        from orchestrator import run_war_room
        def cb(msg, pct): print(f"  [{int(pct*100):3d}%] {msg}")
        start  = time.time()
        result = run_war_room(progress_callback=cb)
        elapsed = round(time.time() - start, 2)

        for key in ("final_verdict","consensus","agent_reports","war_room_session"):
            assert key in result, f"Missing key: {key}"

        verdict   = result["final_verdict"].get("recommendation","?")
        agents_ok = result["war_room_session"].get("agents_completed",0)
        errs      = result.get("agent_errors",{})

        ok(f"run_war_room() — {elapsed}s")
        ok(f"Verdict: {verdict}")
        ok(f"Agents completed: {agents_ok}/5")
        for agent, err in errs.items(): warn(f"Agent error in {agent}: {str(err)[:100]}")
        if not errs: ok("No agent errors ✓")
        if Path("output/decision.json").exists(): ok("decision.json written ✓")
        else: warn("decision.json was NOT written")
    except Exception as e:
        fail(f"Full run: {e}"); info(traceback.format_exc()); errors.append(str(e))

# ══════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════
print(f"\n{'═'*55}")
if not errors:
    print(f"{GREEN}{BOLD}  ✅  ALL TESTS PASSED — run: streamlit run app.py{RESET}")
else:
    print(f"{RED}{BOLD}  ❌  {len(errors)} ISSUE(S) FOUND:{RESET}")
    for i,e in enumerate(errors,1): print(f"     {i}. {e}")
    print()
    if any("proxies" in str(e) or "groq" in str(e).lower() for e in errors):
        print(f"{YELLOW}  👉  pip install --upgrade groq httpx{RESET}")
    if any("signature" in str(e) for e in errors):
        print(f"{YELLOW}  👉  Replace agent files from the latest output{RESET}")
    if any("data" in str(e).lower() or "list" in str(e) for e in errors):
        print(f"{YELLOW}  👉  python fix_data.py{RESET}")
    print(f"{YELLOW}  👉  python test_warroom.py --fast  ← re-verify{RESET}")
print(f"{'═'*55}\n")