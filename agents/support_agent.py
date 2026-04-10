"""
support_agent.py — Support Triage Agent
P0/P1/P2 prioritization + response templates
"""

import json
import os
from groq import Groq
from dotenv import load_dotenv

from tools.feedback_tools import load_feedback, analyze_sentiment, categorize_issues, channel_breakdown, format_feedback_for_prompt

load_dotenv()


def run_support_agent(feedback_data=None) -> dict:
    """Main Support agent entry point."""
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    # ── Tool calls ────────────────────────────────────────────────────────────
    raw_feedback  = load_feedback()
    sentiment     = analyze_sentiment(raw_feedback)
    issues        = categorize_issues(raw_feedback)
    channels      = channel_breakdown(raw_feedback)
    feedback_text = format_feedback_for_prompt(sentiment, issues, channels)

    # ── Prompt ────────────────────────────────────────────────────────────────
    system_prompt = """You are a Head of Customer Support triaging a product incident.
Your job is to prioritize issues and provide response templates for the support team.
Respond ONLY with valid JSON, no markdown, no preamble.

Return this exact structure:
{
  "triage_priority_queue": [
    {"priority": "P0|P1|P2", "issue_type": "<type>", "count": <n>, "action": "<immediate action>"}
  ],
  "response_templates": {
    "crash":       "<template>",
    "payment":     "<template>",
    "data_loss":   "<template>",
    "performance": "<template>"
  },
  "staffing_recommendation": "<how many agents, what hours>",
  "immediate_actions": ["<action1>", "<action2>", ...],
  "escalation_threshold": "<when to escalate to engineering>"
}"""

    user_message = f"""SUPPORT TRIAGE REQUEST

{feedback_text}

Prioritize issues and provide response templates. Respond as JSON."""

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
        "sentiment_summary": sentiment.get("summary", {}),
        "issue_counts":  {k: v["count"] for k, v in issues.items() if v["count"] > 0},
        "channel_counts": {ch: d.get("total", 0) for ch, d in channels.items()},
    }

    return result


# ── Alias ─────────────────────────────────────────────────────────────────────
run = run_support_agent