"""
fix_data.py — patches data/metrics.json and data/feedback.json
to the format the tool functions expect.

Run once:
    python fix_data.py

Safe to run multiple times (idempotent).
"""

import json
from pathlib import Path

GREEN  = "\033[92m"; YELLOW = "\033[93m"; RED = "\033[91m"; RESET = "\033[0m"
def ok(m):   print(f"  \033[92m✅\033[0m  {m}")
def warn(m): print(f"  \033[93m⚠️ \033[0m  {m}")
def fix(m):  print(f"  \033[96m🔧\033[0m  {m}")

# ── 1. metrics.json ───────────────────────────────────────────────────────────
print("\n── Checking data/metrics.json ──")
metrics_path = Path("data/metrics.json")

with open(metrics_path) as f:
    metrics = json.load(f)

if isinstance(metrics, list):
    fix(f"metrics.json is a plain list ({len(metrics)} items) — wrapping in {{\"daily_metrics\": [...]}}")
    # Back up original
    bak = Path("data/metrics.json.bak")
    bak.write_text(json.dumps(metrics, indent=2))
    ok(f"Backup saved → {bak}")

    wrapped = {"daily_metrics": metrics}
    with open(metrics_path, "w") as f:
        json.dump(wrapped, f, indent=2)
    ok("metrics.json patched → {\"daily_metrics\": [...]}")

elif isinstance(metrics, dict) and "daily_metrics" in metrics:
    ok(f"metrics.json already in correct format ({len(metrics['daily_metrics'])} days) — no change needed")
elif isinstance(metrics, dict) and "metrics" in metrics:
    fix("metrics.json has 'metrics' key — renaming to 'daily_metrics'")
    bak = Path("data/metrics.json.bak")
    bak.write_text(json.dumps(metrics, indent=2))
    metrics["daily_metrics"] = metrics.pop("metrics")
    with open(metrics_path, "w") as f:
        json.dump(metrics, f, indent=2)
    ok("metrics.json patched")
else:
    warn(f"metrics.json: unexpected format (type={type(metrics).__name__}, keys={list(metrics.keys()) if isinstance(metrics, dict) else 'N/A'})")
    warn("Could not auto-fix — inspect the file manually")


# ── 2. feedback.json ──────────────────────────────────────────────────────────
print("\n── Checking data/feedback.json ──")
feedback_path = Path("data/feedback.json")

with open(feedback_path) as f:
    feedback = json.load(f)

# Normalise to a flat list first
if isinstance(feedback, list):
    entries = feedback
elif isinstance(feedback, dict):
    entries = feedback.get("feedback", feedback.get("entries", feedback.get("data", [])))
else:
    entries = []

if not entries:
    warn("feedback.json appears empty — nothing to patch")

elif isinstance(entries[0], str):
    fix(f"feedback entries are plain strings ({len(entries)} entries) — converting to dicts")
    bak = Path("data/feedback.json.bak")
    bak.write_text(json.dumps(feedback, indent=2))
    ok(f"Backup saved → {bak}")

    # Convert each string to a proper feedback dict
    # Try to infer channel from keywords in the text
    def infer_channel(text: str) -> str:
        t = text.lower()
        if any(k in t for k in ["twitter", "tweet", "@"]): return "Twitter"
        if any(k in t for k in ["app store", "google play", "★", "stars", "rating"]): return "App Store"
        if any(k in t for k in ["ticket", "support", "help desk", "emailed"]): return "Support Ticket"
        return "In-App Feedback"

    def infer_sentiment(text: str) -> str:
        t = text.lower()
        negative_words = ["crash", "broken", "terrible", "awful", "hate", "bug", "fail",
                          "horrible", "worst", "useless", "disappointed", "frustrat",
                          "doesn't work", "not working", "error", "problem", "issue",
                          "cancel", "refund", "scam", "waste"]
        positive_words = ["love", "great", "excellent", "amazing", "awesome", "perfect",
                          "fantastic", "wonderful", "best", "brilliant", "happy", "thanks"]
        neg_score = sum(1 for w in negative_words if w in t)
        pos_score = sum(1 for w in positive_words if w in t)
        if neg_score > pos_score:   return "negative"
        if pos_score > neg_score:   return "positive"
        return "neutral"

    converted = []
    for i, text in enumerate(entries):
        converted.append({
            "id":        i + 1,
            "text":      text,
            "channel":   infer_channel(text),
            "sentiment": infer_sentiment(text),
            "date":      f"2024-01-{min(i % 10 + 1, 10):02d}",  # spread across days
            "user_id":   f"user_{1000 + i}",
        })

    with open(feedback_path, "w") as f:
        json.dump(converted, f, indent=2)
    ok(f"feedback.json patched — {len(converted)} entries now have: id, text, channel, sentiment, date, user_id")

    # Show sample
    print(f"\n  Sample entry (first):")
    print(f"  {json.dumps(converted[0], indent=4)}")

elif isinstance(entries[0], dict):
    # Check required keys are present
    required_keys = {"text", "channel", "sentiment"}
    entry_keys    = set(entries[0].keys())
    missing       = required_keys - entry_keys

    if not missing:
        ok(f"feedback.json already in correct format ({len(entries)} dict entries) — no change needed")
    else:
        fix(f"feedback entries are dicts but missing keys: {missing} — patching")
        bak = Path("data/feedback.json.bak")
        bak.write_text(json.dumps(feedback, indent=2))

        for entry in entries:
            if "text" not in entry:
                # Try common alternate keys
                entry["text"] = entry.get("message", entry.get("content",
                                entry.get("body", entry.get("review", str(entry)))))
            if "channel" not in entry:
                entry["channel"] = entry.get("source", entry.get("platform", "unknown"))
            if "sentiment" not in entry:
                entry["sentiment"] = "unknown"

        with open(feedback_path, "w") as f:
            json.dump(entries, f, indent=2)
        ok(f"feedback.json patched — added missing keys to {len(entries)} entries")

print("\n── Done ──────────────────────────────────────────────")
print("  Re-run the test suite:")
print("  python test_warroom.py --fast\n")