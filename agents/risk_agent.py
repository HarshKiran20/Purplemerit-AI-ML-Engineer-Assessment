"""
risk_agent.py — Risk/Critic Agent
Worst-case scenarios, risk matrix, escalation triggers
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

from tools.metric_tools   import load_metrics, aggregate_metrics, detect_anomalies, analyze_trends, get_breach_summary, format_metrics_for_prompt
from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues, format_feedback_for_prompt

load_dotenv()


def run_risk_agent(metrics_data=None, feedback_data=None, release_notes=None) -> dict:
    """Main Risk agent entry point."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Tool calls ────────────────────────────────────────────────────────────
    raw_metrics  = load_metrics()
    aggregated   = aggregate_metrics(raw_metrics)
    anomalies    = detect_anomalies(raw_metrics)
    trends       = analyze_trends(raw_metrics)
    breach_sum   = get_breach_summary(aggregated)
    metrics_text = format_metrics_for_prompt(aggregated, anomalies, trends)

    raw_feedback  = load_feedback()
    sentiment     = analyze_sentiment(raw_feedback)
    issues        = categorize_issues(raw_feedback)
    feedback_text = format_feedback_for_prompt(sentiment, issues, {})

    # ── Prompt ────────────────────────────────────────────────────────────────
    system_prompt = """You are a Chief Risk Officer running a product war room.
Your job is to be the devil's advocate — identify worst-case scenarios and hard escalation triggers.
Respond ONLY with valid JSON, no markdown, no preamble.

Return this exact structure:
{
  "overall_risk_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "risk_matrix": [
    {"risk": "<name>", "likelihood": "HIGH|MEDIUM|LOW", "impact": "HIGH|MEDIUM|LOW", "mitigation": "<action>"}
  ],
  "escalation_triggers": ["<trigger that means immediate rollback>", ...],
  "worst_case_scenario": "<if nothing is done in 24h>",
  "immediate_actions": ["<action1>", "<action2>", ...],
  "recommendation": "ROLLBACK" | "HOTFIX_REQUIRED" | "MONITOR_CLOSELY" | "PROCEED"
}"""

    user_message = f"""RISK ASSESSMENT REQUEST

{metrics_text}

{feedback_text}

Critical breaches: {breach_sum['critical_count']} metrics in CRITICAL state.

Identify all risks and escalation triggers. Respond as JSON."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.3,
        max_tokens=1000,
    )

    raw_text = response.choices[0].message.content.strip()

    try:
        result = json.loads(raw_text)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw_text, re.DOTALL)
        result = json.loads(match.group()) if match else {"error": "parse_failed", "raw": raw_text}

    result["_tool_outputs"] = {
        "breach_summary":   breach_sum,
        "critical_metrics": breach_sum.get("CRITICAL", []),
        "anomaly_count":    sum(len(v) for v in anomalies.values()),
    }

    return result


# ── Alias ─────────────────────────────────────────────────────────────────────
run = run_risk_agent