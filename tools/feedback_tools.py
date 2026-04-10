"""
feedback_tools.py — War Room feedback analysis toolkit
Sentiment, categorization, channel breakdown, prompt formatting
"""

import json
import os
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# ── Path resolution ───────────────────────────────────────────────────────────
BASE_DIR      = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDBACK_PATH = os.path.join(BASE_DIR, "data", "feedback.json")

_analyzer = SentimentIntensityAnalyzer()

# ── Issue keyword buckets ─────────────────────────────────────────────────────
ISSUE_KEYWORDS = {
    "crash":       ["crash", "crashes", "crashed", "crashing", "force close", "closes itself"],
    "payment":     ["payment", "pay", "charge", "billing", "subscription", "refund", "money"],
    "performance": ["slow", "lag", "freeze", "loading", "stuck", "hang", "unresponsive", "timeout"],
    "data_loss":   ["lost", "deleted", "gone", "missing", "disappeared", "wiped", "reset"],
    "churn_signal":["cancel", "cancelling", "uninstall", "delete account", "switching", "competitor",
                    "leaving", "refund", "never using again"],
    "login":       ["login", "sign in", "password", "account", "locked out", "auth", "2fa"],
    "ui_ux":       ["confusing", "hard to find", "ui", "interface", "button", "navigation", "layout"],
    "feature":     ["feature", "missing", "wish", "would be nice", "request", "add", "bring back"],
}


def load_feedback(path: str = FEEDBACK_PATH) -> list:
    """Load feedback JSON from disk."""
    with open(path, "r") as f:
        return json.load(f)


def analyze_sentiment(feedback_data: list) -> dict:
    """
    VADER scoring → POSITIVE / NEUTRAL / NEGATIVE per entry + overall breakdown.
    Returns dict with per-entry scores and aggregate summary.
    """
    results   = []
    pos = neg = neu = 0

    for entry in feedback_data:
        text   = entry.get("text", entry.get("message", entry.get("content", str(entry))))
        scores = _analyzer.polarity_scores(text)
        comp   = scores["compound"]

        if comp >= 0.05:
            label = "POSITIVE";  pos += 1
        elif comp <= -0.05:
            label = "NEGATIVE";  neg += 1
        else:
            label = "NEUTRAL";   neu += 1

        results.append({
            **entry,
            "sentiment":       label,
            "compound_score":  round(comp, 4),
            "vader_scores":    {k: round(v, 4) for k, v in scores.items()},
        })

    total = len(feedback_data) or 1
    return {
        "entries": results,
        "summary": {
            "total":    total,
            "positive": pos,
            "neutral":  neu,
            "negative": neg,
            "negative_pct": round(neg / total * 100, 1),
            "positive_pct": round(pos / total * 100, 1),
        },
    }


def categorize_issues(feedback_data: list) -> dict:
    """
    Keyword bucketing → crash, payment, performance, data_loss, churn_signal, etc.
    An entry can match multiple categories.
    """
    buckets = {k: [] for k in ISSUE_KEYWORDS}
    buckets["uncategorized"] = []

    for entry in feedback_data:
        text    = entry.get("text", entry.get("message", entry.get("content", str(entry)))).lower()
        matched = False
        for category, keywords in ISSUE_KEYWORDS.items():
            if any(kw in text for kw in keywords):
                buckets[category].append(entry)
                matched = True
        if not matched:
            buckets["uncategorized"].append(entry)

    return {
        cat: {"count": len(entries), "entries": entries}
        for cat, entries in buckets.items()
    }


def channel_breakdown(feedback_data: list) -> dict:
    """
    Sentiment per channel (Twitter, App Store, In-App, Support tickets, etc.).
    """
    channels: dict = {}

    for entry in feedback_data:
        channel = entry.get("channel", entry.get("source", "unknown"))
        text    = entry.get("text", entry.get("message", entry.get("content", str(entry))))
        scores  = _analyzer.polarity_scores(text)
        comp    = scores["compound"]
        label   = "POSITIVE" if comp >= 0.05 else ("NEGATIVE" if comp <= -0.05 else "NEUTRAL")

        if channel not in channels:
            channels[channel] = {"POSITIVE": 0, "NEUTRAL": 0, "NEGATIVE": 0, "total": 0, "scores": []}

        channels[channel][label]     += 1
        channels[channel]["total"]   += 1
        channels[channel]["scores"].append(comp)

    # Compute avg sentiment per channel
    for ch, data in channels.items():
        data["avg_sentiment"] = round(sum(data["scores"]) / len(data["scores"]), 4) if data["scores"] else 0
        del data["scores"]  # clean up raw list

    return channels


def format_feedback_for_prompt(
    sentiment_result=None,
    issues_result=None,
    channels_result=None,
) -> str:
    """
    Formats feedback analysis into clean text for LLM prompts.

    Can be called two ways:
      1. format_feedback_for_prompt(sentiment, issues, channels)   ← 3 args (test style)
      2. format_feedback_for_prompt({"sentiment":…,"issues":…,…}) ← 1 dict arg (agent style)
    """
    # ── Handle single-dict call style ─────────────────────────────────────────
    if isinstance(sentiment_result, dict) and issues_result is None:
        combined = sentiment_result
        sentiment_result = combined.get("sentiment", {})
        issues_result    = combined.get("issues",    {})
        channels_result  = combined.get("channels",  {})

    lines = ["=== FEEDBACK ANALYSIS ===\n"]

    # Sentiment summary
    if sentiment_result:
        summary = sentiment_result.get("summary", sentiment_result)
        lines.append("[ Sentiment Overview ]")
        lines.append(f"  Total entries : {summary.get('total', 'N/A')}")
        lines.append(f"  Negative      : {summary.get('negative', 'N/A')} ({summary.get('negative_pct', 'N/A')}%)")
        lines.append(f"  Positive      : {summary.get('positive', 'N/A')} ({summary.get('positive_pct', 'N/A')}%)")
        lines.append(f"  Neutral       : {summary.get('neutral', 'N/A')}")

    # Issue categories
    if issues_result:
        lines.append("\n[ Issue Categories ]")
        for cat, data in issues_result.items():
            count = data.get("count", 0) if isinstance(data, dict) else 0
            if count > 0:
                lines.append(f"  {cat:20s} : {count} reports")

    # Channel breakdown
    if channels_result:
        lines.append("\n[ Channel Breakdown ]")
        for ch, data in channels_result.items():
            if isinstance(data, dict):
                lines.append(
                    f"  {ch:20s} : total={data.get('total',0)} | "
                    f"neg={data.get('NEGATIVE',0)} | avg_sentiment={data.get('avg_sentiment',0)}"
                )

    return "\n".join(lines)