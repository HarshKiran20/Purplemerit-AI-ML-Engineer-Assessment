"""
comms_agent.py — Marketing/Communications Agent
Channel strategy + draft responses for Twitter, App Store, In-App
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues, channel_breakdown, format_feedback_for_prompt

load_dotenv()


def run_comms_agent(feedback_data=None) -> dict:
    """Main Comms agent entry point."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Tool calls ────────────────────────────────────────────────────────────
    raw_feedback  = load_feedback()
    sentiment     = analyze_sentiment(raw_feedback)
    issues        = categorize_issues(raw_feedback)
    channels      = channel_breakdown(raw_feedback)
    feedback_text = format_feedback_for_prompt(sentiment, issues, channels)

    # ── Prompt ────────────────────────────────────────────────────────────────
    system_prompt = """You are a Head of Communications managing a product crisis.
Your job is to draft channel-appropriate responses and define the comms strategy.
Respond ONLY with valid JSON, no markdown, no preamble.

Return this exact structure:
{
  "crisis_level": "CRITICAL" | "HIGH" | "MEDIUM" | "LOW",
  "channel_strategy": {"twitter": "...", "app_store": "...", "in_app": "...", "support": "..."},
  "draft_responses": {
    "tweet": "<280 chars max>",
    "app_store_reply": "<concise reply>",
    "in_app_banner": "<short message>",
    "support_template": "<support email template>"
  },
  "churn_risk_level": "HIGH" | "MEDIUM" | "LOW",
  "retention_actions": ["<action1>", "<action2>", ...],
  "do_not_say": ["<phrase to avoid1>", ...]
}"""

    user_message = f"""COMMUNICATIONS CRISIS BRIEF

{feedback_text}

Draft channel responses and retention strategy. Respond as JSON."""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user",   "content": user_message},
        ],
        temperature=0.5,
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
        "sentiment_summary": sentiment.get("summary", {}),
        "channel_breakdown": {ch: d.get("avg_sentiment", 0) for ch, d in channels.items()},
        "top_issues": {k: v["count"] for k, v in issues.items() if v["count"] > 0},
    }

    return result


# ── Alias ─────────────────────────────────────────────────────────────────────
run = run_comms_agent