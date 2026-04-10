"""
analyst_agent.py — Data Analyst Agent
Root cause hypothesis via z-score anomalies + regression trends
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

from tools.metric_tools   import load_metrics, aggregate_metrics, detect_anomalies, analyze_trends, format_metrics_for_prompt
from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues, format_feedback_for_prompt

load_dotenv()


def run_analyst_agent(metrics_data=None, feedback_data=None) -> dict:
    """Main Analyst agent entry point."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Tool calls ────────────────────────────────────────────────────────────
    raw_metrics  = load_metrics()
    aggregated   = aggregate_metrics(raw_metrics)
    anomalies    = detect_anomalies(raw_metrics)
    trends       = analyze_trends(raw_metrics)
    metrics_text = format_metrics_for_prompt(aggregated, anomalies, trends)

    raw_feedback  = load_feedback()
    sentiment     = analyze_sentiment(raw_feedback)
    issues        = categorize_issues(raw_feedback)
    feedback_text = format_feedback_for_prompt(sentiment, issues, {})

    # ── Prompt ────────────────────────────────────────────────────────────────
    system_prompt = """You are a Senior Data Analyst in a product war room.
Your job is to identify root causes using statistical evidence — anomalies, trends, correlations.
Respond ONLY with valid JSON, no markdown, no preamble.

Return this exact structure:
{
  "root_cause_hypothesis": "<primary hypothesis>",
  "supporting_evidence": ["<evidence1>", "<evidence2>", ...],
  "correlated_metrics": ["<metricA> → <metricB>", ...],
  "confidence_level": "HIGH" | "MEDIUM" | "LOW",
  "recommended_investigation": ["<step1>", "<step2>", ...],
  "key_metrics_to_watch": ["<metric1>", "<metric2>", ...],
  "data_gaps": ["<gap1>", ...]
}"""

    user_message = f"""DATA ANALYSIS REQUEST

{metrics_text}

{feedback_text}

Identify the root cause and correlations. Respond as JSON."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.2,
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
        "anomalies":  anomalies,
        "trends":     trends,
        "aggregated": {k: v["status"] for k, v in aggregated.items()},
    }

    return result


# ── Alias ─────────────────────────────────────────────────────────────────────
run = run_analyst_agent