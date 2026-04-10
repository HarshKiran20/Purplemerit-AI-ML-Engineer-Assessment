"""
orchestrator.py — War Room Coordinator

Runs all 5 agents (concurrently), synthesizes their outputs,
resolves conflicts, and writes the final decision.json.
"""

import os
import json
import time
import traceback
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from agents.pm_agent import run_pm_agent
from agents.analyst_agent import run_analyst_agent
from agents.comms_agent import run_comms_agent
from agents.risk_agent import run_risk_agent
from agents.support_agent import run_support_agent
from tools.metric_tools import load_metrics, aggregate_metrics, get_breach_summary
from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)
DECISION_FILE = OUTPUT_DIR / "decision.json"

RECOMMENDATION_SEVERITY = {
    "ROLLBACK": 4, "HOTFIX_REQUIRED": 3,
    "MONITOR_CLOSELY": 2, "PROCEED_WITH_CAUTION": 1, "PROCEED": 0,
}
RISK_VERDICT_MAP = {
    "ROLLBACK": "ROLLBACK", "HOTFIX_REQUIRED": "HOTFIX_REQUIRED",
    "MONITOR_WITH_TRIPWIRES": "MONITOR_CLOSELY", "PROCEED_WITH_CAUTION": "PROCEED_WITH_CAUTION",
}


def run_war_room(progress_callback=None) -> dict:
    def progress(msg, pct):
        if progress_callback:
            progress_callback(msg, pct)

    progress("Loading metrics & feedback data...", 5)
    metrics_data  = load_metrics(str(DATA_DIR / "metrics.json"))
    feedback_data = load_feedback(str(DATA_DIR / "feedback.json"))
    release_notes = _load_release_notes(DATA_DIR / "release_notes.md")

    if not metrics_data:  raise ValueError("metrics.json is empty or failed to load.")
    if not feedback_data: raise ValueError("feedback.json is empty or failed to load.")

    agg            = aggregate_metrics(metrics_data)
    breach_summary = get_breach_summary(metrics_data)
    sentiment_raw  = analyze_sentiment(feedback_data)
    issues_raw     = categorize_issues(feedback_data)

    progress("Dispatching agents to war room...", 10)
    agent_jobs = {
        "PM":      lambda: run_pm_agent(metrics_data, feedback_data),
        "Analyst": lambda: run_analyst_agent(metrics_data),
        "Comms":   lambda: run_comms_agent(feedback_data),
        "Risk":    lambda: run_risk_agent(metrics_data, feedback_data, release_notes),
        "Support": lambda: run_support_agent(feedback_data),
    }

    agent_results, agent_errors, agent_timings = {}, {}, {}

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(_run_agent_safe, name, fn): name for name, fn in agent_jobs.items()}
        completed = 0
        for future in as_completed(futures):
            name = futures[future]
            completed += 1
            pct = 10 + int((completed / len(agent_jobs)) * 55)
            progress(f"Agent '{name}' finished...", pct)
            result, error, elapsed = future.result()
            agent_timings[name] = elapsed
            if error: agent_errors[name] = error
            else:     agent_results[name] = result

    progress("Synthesizing agent findings...", 70)
    synthesis = _synthesize(agent_results, agent_errors)

    progress("Resolving conflicts and finalizing verdict...", 85)
    verdict            = _resolve_verdict(agent_results, agg, breach_summary, sentiment_raw, issues_raw)
    consensus          = _build_consensus(agent_results)
    communication_plan = _build_communication_plan(agent_results)
    confidence         = _build_confidence(agent_results)

    progress("Writing decision.json...", 93)
    decision = {
        "war_room_session": {
            "timestamp":          datetime.utcnow().isoformat() + "Z",
            "data_window":        "10 days post-launch",
            "agents_run":         list(agent_results.keys()),
            "agents_failed":      list(agent_errors.keys()),
            "agent_timings_sec":  agent_timings,
            "total_duration_sec": round(sum(agent_timings.values()), 2),
        },
        "final_verdict":      verdict,
        "confidence":         confidence,
        "communication_plan": communication_plan,
        "consensus":          consensus,
        "synthesis":          synthesis,
        "agent_reports": {name: _strip_tool_outputs(r) for name, r in agent_results.items()},
        "agent_errors":  agent_errors,
    }

    with open(DECISION_FILE, "w") as f:
        json.dump(decision, f, indent=2)

    progress("War room complete", 100)
    return decision


def _run_agent_safe(name, fn):
    start = time.time()
    try:
        return fn(), None, round(time.time() - start, 2)
    except Exception as e:
        return None, f"{type(e).__name__}: {e}\n{traceback.format_exc()}", round(time.time() - start, 2)


def _resolve_verdict(agent_results, agg, breach_summary, sentiment_raw, issues_raw):
    recommendations = {}
    pm   = agent_results.get("PM",   {})
    risk = agent_results.get("Risk", {})

    if "recommendation" in pm:
        recommendations["PM"] = pm["recommendation"]
    if "risk_agent_verdict" in risk:
        raw = risk["risk_agent_verdict"]
        recommendations["Risk"] = RISK_VERDICT_MAP.get(raw, raw)

    if not recommendations:
        final_rec, conflict = "MONITOR_CLOSELY", False
    else:
        final_rec = max(recommendations.values(), key=lambda r: RECOMMENDATION_SEVERITY.get(r, 0))
        conflict  = len(set(recommendations.values())) > 1

    parts = []
    if conflict:
        parts.append(f"Agents disagreed ({recommendations}); conservative escalation to '{final_rec}'.")
    else:
        parts.append(f"All agents aligned on '{final_rec}'.")

    crit         = breach_summary.get("critical_count", 0)
    warn         = breach_summary.get("warning_count",  0)
    crit_metrics = breach_summary.get("critical_metrics", [])
    warn_metrics = breach_summary.get("warning_metrics",  [])
    if crit > 0: parts.append(f"{crit} metric(s) in CRITICAL breach: {', '.join(crit_metrics)}.")
    if warn > 0: parts.append(f"{warn} metric(s) in WARNING: {', '.join(warn_metrics)}.")
    if crit == 0 and warn == 0: parts.append("All metrics within acceptable thresholds.")

    ov      = sentiment_raw.get("overall", {})
    neg_pct = ov.get("negative_pct", 0)
    total   = ov.get("total", 0)
    if neg_pct: parts.append(f"User sentiment: {neg_pct}% negative across {total} feedback entries.")

    churn_count = len(issues_raw.get("churn_signals", []))
    if churn_count: parts.append(f"{churn_count} explicit churn signal(s) detected.")

    top_deltas = _top_metric_deltas(agg, n=3)
    if top_deltas:
        parts.append("Largest post-launch deltas — " + "; ".join(f"{m}: {d:+.1f}%" for m, d in top_deltas) + ".")

    return {
        "recommendation":             final_rec,
        "recommendation_rationale":   " ".join(parts),
        "agent_recommendations":      recommendations,
        "conflict_detected":          conflict,
        "overall_health":             pm.get("overall_health", "UNKNOWN"),
        "health_score":               pm.get("health_score"),
        "risk_level":                 risk.get("overall_risk_level", "UNKNOWN"),
        "time_sensitivity":           risk.get("time_sensitivity", "UNKNOWN"),
        "metric_evidence": {
            "critical_breaches":       crit_metrics,
            "warning_breaches":        warn_metrics,
            "negative_sentiment_pct":  neg_pct,
            "churn_signals":           churn_count,
            "top_deltas":              {m: f"{d:+.1f}%" for m, d in top_deltas},
        },
    }


def _build_communication_plan(agent_results):
    comms = agent_results.get("Comms", {})
    if not comms:
        return {"status": "Comms agent did not run."}

    drafts    = comms.get("draft_responses",          {}) or {}
    _sa       = comms.get("sentiment_assessment",     {}) or {}
    mood      = _sa.get("overall_mood", "UNKNOWN") if isinstance(_sa, dict) else "UNKNOWN"
    churn     = _sa.get("churn_risk",   "UNKNOWN") if isinstance(_sa, dict) else "UNKNOWN"

    def _d(k): return str(drafts.get(k, "")) if isinstance(drafts, dict) else ""

    return {
        "overall_sentiment_mood": mood,
        "churn_risk":             churn,
        "internal_messaging": {
            "summary":         "Acknowledge known issues; communicate that monitoring is active and hotfix assessment is underway.",
            "support_template": _d("support_template"),
            "do_not_say":       _safe_list_of_strings(comms.get("messaging_do_not_say", []))[:5],
        },
        "external_messaging": {
            "public_tweet":        _d("public_tweet"),
            "app_store_response":  _d("app_store_response"),
            "in_app_notification": _d("in_app_notification"),
        },
        "channel_strategy":  _safe_list_of_dicts(comms.get("channel_strategy",         []))[:4],
        "proactive_actions": _safe_list_of_dicts(comms.get("proactive_communications", []))[:4],
        "retention_actions": _safe_list_of_dicts(comms.get("retention_actions",        []))[:4],
    }


def _build_confidence(agent_results):
    analyst = agent_results.get("Analyst", {}) or {}
    pm      = agent_results.get("PM",      {}) or {}
    risk    = agent_results.get("Risk",    {}) or {}

    level       = analyst.get("analyst_confidence",  "UNKNOWN")
    rationale   = analyst.get("confidence_rationale", "")
    data_quality = analyst.get("data_quality",        "UNKNOWN")
    most_critical = analyst.get("most_critical_metric", {})

    what_would_help = []
    if data_quality in ("PARTIAL", "POOR"):
        what_would_help.append("More complete metrics data (fewer gaps in time series).")
    if level in ("LOW", "MEDIUM"):
        what_would_help.append("Longer post-launch observation window (currently 10 days).")
    for b in _safe_list_of_strings(risk.get("do_not_proceed_if", []))[:2]:
        what_would_help.append(f"Resolve blocker: {b}")
    watch = pm.get("key_metrics_to_watch", [])
    if watch:
        ms = ", ".join(_safe_list_of_strings(watch)[:3])
        what_would_help.append(f"Stable readings on: {ms} over next 48h.")
    if not what_would_help:
        what_would_help.append("Continue monitoring; current confidence is sufficient to proceed.")

    trend_findings = analyst.get("trend_findings") or []
    return {
        "score":        level,
        "rationale":    rationale,
        "data_quality": data_quality,
        "most_critical_metric": most_critical if isinstance(most_critical, dict) else {},
        "what_would_increase_confidence": what_would_help,
        "analyst_findings_summary": {
            "high_severity_anomalies": len([
                m for m in (analyst.get("anomaly_findings") or [])
                if isinstance(m, dict) and m.get("severity") == "HIGH"
            ]),
            "worsening_metrics": [
                t.get("metric") for t in trend_findings
                if isinstance(t, dict) and t.get("direction") == "WORSENING"
            ],
            "improving_metrics": [
                t.get("metric") for t in trend_findings
                if isinstance(t, dict) and t.get("direction") == "IMPROVING"
            ],
            "root_cause_hypothesis": analyst.get("root_cause_hypothesis", ""),
        },
    }


def _build_consensus(agent_results):
    pm      = agent_results.get("PM",      {}) or {}
    risk    = agent_results.get("Risk",    {}) or {}
    support = agent_results.get("Support", {}) or {}
    analyst = agent_results.get("Analyst", {}) or {}
    comms   = agent_results.get("Comms",   {}) or {}

    all_actions = []
    for action in pm.get("immediate_actions", []):
        if isinstance(action, dict):   all_actions.append({**action, "source": "PM"})
        elif isinstance(action, str):  all_actions.append({"action": action, "owner": "Team", "timeline": "ASAP", "source": "PM"})

    for trigger in risk.get("escalation_triggers", []):
        if isinstance(trigger, dict):  all_actions.append({"action": trigger.get("action_if_triggered", str(trigger)), "owner": "Engineering", "timeline": "now", "source": "Risk"})
        elif isinstance(trigger, str): all_actions.append({"action": trigger, "owner": "Engineering", "timeline": "now", "source": "Risk"})

    for item in support.get("escalation_to_engineering", []):
        if isinstance(item, dict):   all_actions.append({"action": f"Engineering: fix {item.get('issue', str(item))}", "owner": "Engineering", "timeline": item.get("urgency","24H").lower(), "source": "Support"})
        elif isinstance(item, str):  all_actions.append({"action": item, "owner": "Engineering", "timeline": "24H", "source": "Support"})

    top_concerns = []
    for c in pm.get("top_concerns", []):
        if isinstance(c, dict):  top_concerns.append({**c, "source": "PM"})
        elif isinstance(c, str): top_concerns.append({"concern": c, "severity": "UNKNOWN", "data_evidence": "", "source": "PM"})
    for r in risk.get("risk_matrix", [])[:3]:
        if isinstance(r, dict):  top_concerns.append({"concern": r.get("risk_name", str(r)), "severity": r.get("risk_score", ""), "data_evidence": r.get("evidence", ""), "source": "Risk"})
        elif isinstance(r, str): top_concerns.append({"concern": r, "severity": "UNKNOWN", "data_evidence": "", "source": "Risk"})

    _sa       = comms.get("sentiment_assessment", {})
    churn_risk = _sa.get("churn_risk", "UNKNOWN") if isinstance(_sa, dict) else "UNKNOWN"

    def _sl(val):
        if isinstance(val, list): return [str(v) for v in val]
        if isinstance(val, str):  return [val]
        return []

    return {
        "root_cause_hypothesis": analyst.get("root_cause_hypothesis", "Not determined."),
        "churn_risk":            churn_risk,
        "top_concerns":          top_concerns[:6],
        "immediate_actions":     _dedupe_actions(all_actions),
        "metrics_to_watch":      list(set(_sl(pm.get("key_metrics_to_watch",[])) + _sl(analyst.get("metrics_to_escalate",[])))),
        "positive_signals":      pm.get("positive_signals", []),
    }


def _synthesize(agent_results, agent_errors):
    pm      = agent_results.get("PM",      {}) or {}
    risk    = agent_results.get("Risk",    {}) or {}
    comms   = agent_results.get("Comms",   {}) or {}
    analyst = agent_results.get("Analyst", {}) or {}
    support = agent_results.get("Support", {}) or {}
    _sa     = comms.get("sentiment_assessment", {})
    _sl     = support.get("support_load_assessment", {})
    return {
        "executive_summary":   pm.get("executive_summary", "PM agent did not return a summary."),
        "overall_health":      pm.get("overall_health", "UNKNOWN"),
        "health_score":        pm.get("health_score"),
        "worst_case_scenario": risk.get("worst_case_scenario", ""),
        "sentiment_mood":      _sa.get("overall_mood", "UNKNOWN") if isinstance(_sa, dict) else "UNKNOWN",
        "support_load":        _sl.get("volume", "UNKNOWN") if isinstance(_sl, dict) else "UNKNOWN",
        "analyst_confidence":  analyst.get("analyst_confidence", "UNKNOWN"),
        "failed_agents":       list(agent_errors.keys()),
        "agents_succeeded":    len(agent_results),
        "agents_failed":       len(agent_errors),
    }


def _load_release_notes(path):
    try:    return path.read_text(encoding="utf-8")
    except: return ""

def _strip_tool_outputs(report):
    if not report: return {}
    return {k: v for k, v in report.items() if k != "_tool_outputs"}

def _dedupe_actions(actions):
    seen, unique = set(), []
    for a in actions:
        key = a.get("action", "").lower()[:60]
        if key and key not in seen:
            seen.add(key); unique.append(a)
    return unique[:10]

def _top_metric_deltas(agg, n=3):
    deltas = [(m, d["delta_pct"]) for m, d in agg.items() if isinstance(d, dict) and "delta_pct" in d]
    return sorted(deltas, key=lambda x: abs(x[1]), reverse=True)[:n]

def _safe_list_of_dicts(val):
    return [i for i in val if isinstance(i, dict)] if isinstance(val, list) else []

def _safe_list_of_strings(val):
    if isinstance(val, list): return [str(i) for i in val]
    if isinstance(val, str):  return [val]
    return []