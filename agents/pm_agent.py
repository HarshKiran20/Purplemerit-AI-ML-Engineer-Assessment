"""
pm_agent.py — Product Manager Agent
Produces executive health score + ROLLBACK/HOTFIX/PROCEED recommendation
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

from tools.metric_tools   import load_metrics, aggregate_metrics, detect_anomalies, analyze_trends, get_breach_summary, format_metrics_for_prompt
from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues, channel_breakdown, format_feedback_for_prompt

load_dotenv()

def run_pm_agent(metrics_data=None, feedback_data=None) -> dict:
    """Main PM agent entry point."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Tool calls ────────────────────────────────────────────────────────────
    raw_metrics  = load_metrics()
    aggregated   = aggregate_metrics(raw_metrics)
    anomalies    = detect_anomalies(raw_metrics)
    trends       = analyze_trends(raw_metrics)
    breach_sum   = get_breach_summary(aggregated)
    metrics_text = format_metrics_for_prompt(aggregated, anomalies, trends)

    raw_feedback = load_feedback()
    sentiment    = analyze_sentiment(raw_feedback)
    issues       = categorize_issues(raw_feedback)
    channels     = channel_breakdown(raw_feedback)
    feedback_text = format_feedback_for_prompt(sentiment, issues, channels)

    # ── Release notes ─────────────────────────────────────────────────────────
    notes_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "release_notes.md")
    with open(notes_path) as f:
        release_notes = f.read()

    # ── Prompt ────────────────────────────────────────────────────────────────
    system_prompt = """You are a Senior Product Manager running a post-launch war room.
Your job is to assess product health and make a decisive GO/NO-GO recommendation.
You must respond ONLY with valid JSON — no preamble, no markdown fences.

Return this exact structure:
{
  "recommendation": "ROLLBACK" | "HOTFIX_REQUIRED" | "MONITOR_CLOSELY" | "PROCEED",
  "health_score": <0-100 integer>,
  "executive_summary": "<2-3 sentence summary>",
  "immediate_actions": ["<action1>", "<action2>", ...],
  "key_metrics_to_watch": ["<metric1>", "<metric2>", ...],
  "rationale": "<detailed reasoning>"
}"""

    user_message = f"""WAR ROOM ANALYSIS REQUEST

{metrics_text}

{feedback_text}

RELEASE NOTES:
{release_notes}

Critical breaches: {breach_sum['critical_count']} CRITICAL, {breach_sum['warning_count']} WARNING metrics.

Provide your PM recommendation as JSON."""

    # ── LLM call ──────────────────────────────────────────────────────────────
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
        "breach_summary": breach_sum,
        "anomaly_count":  sum(len(v) for v in anomalies.values()),
        "sentiment_summary": sentiment.get("summary", {}),
    }

    return result


# ── Aliases ───────────────────────────────────────────────────────────────────
run = run_pm_agent