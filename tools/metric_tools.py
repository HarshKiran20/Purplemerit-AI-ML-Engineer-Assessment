"""
metric_tools.py — War Room metric analysis toolkit
Handles load, aggregate, anomaly detection, trend analysis
"""

import json
import os
import numpy as np
from scipy import stats

# ── Path resolution ──────────────────────────────────────────────────────────
BASE_DIR   = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
METRICS_PATH = os.path.join(BASE_DIR, "data", "metrics.json")

# ── Thresholds ────────────────────────────────────────────────────────────────
THRESHOLDS = {
    "crash_rate":          {"warning": 2.0,  "critical": 5.0,  "direction": "higher_is_worse"},
    "error_rate":          {"warning": 3.0,  "critical": 6.0,  "direction": "higher_is_worse"},
    "p99_latency_ms":      {"warning": 800,  "critical": 1200, "direction": "higher_is_worse"},
    "dau":                 {"warning": 8000, "critical": 6000, "direction": "lower_is_worse"},
    "retention_d1":        {"warning": 35.0, "critical": 25.0, "direction": "lower_is_worse"},
    "nps_score":           {"warning": 20,   "critical": 10,   "direction": "lower_is_worse"},
    "support_tickets":     {"warning": 150,  "critical": 250,  "direction": "higher_is_worse"},
    "revenue_usd":         {"warning": 8000, "critical": 6000, "direction": "lower_is_worse"},
    "session_duration_min":{"warning": 3.0,  "critical": 2.0,  "direction": "lower_is_worse"},
    "payment_failures":    {"warning": 3.0,  "critical": 6.0,  "direction": "higher_is_worse"},
}


def load_metrics(path: str = METRICS_PATH) -> list:
    """
    Load metrics JSON. Handles two formats:
      - List format:  [ {day:1, metric_name: val, ...}, ... ]
      - Dict format:  { "metric_name": [val_day1, val_day2, ...], ... }
    Always returns a list of day-dicts.
    """
    with open(path, "r") as f:
        raw = json.load(f)

    # ── Normalise dict → list ─────────────────────────────────────────────────
    if isinstance(raw, dict):
        # Find how many days exist (length of first metric array)
        num_days = 0
        for v in raw.values():
            if isinstance(v, list):
                num_days = len(v)
                break

        if num_days == 0:
            return []

        days = []
        for i in range(num_days):
            entry = {"day": i + 1}
            for metric, values in raw.items():
                if isinstance(values, list) and i < len(values):
                    entry[metric] = values[i]
            days.append(entry)
        return days

    # Already a list
    if isinstance(raw, list):
        return raw

    return []


def aggregate_metrics(metrics_data: list) -> dict:
    """
    Pre vs post-launch averages, delta %, breach detection.
    Launch assumed at day 4 (days 1-3 = pre, days 4+ = post).
    """
    pre  = [d for d in metrics_data if d.get("day", 0) <= 3]
    post = [d for d in metrics_data if d.get("day", 0) >  3]

    metric_names = [k for k in THRESHOLDS.keys()]
    result = {}

    for metric in metric_names:
        pre_vals  = [d[metric] for d in pre  if metric in d]
        post_vals = [d[metric] for d in post if metric in d]

        if not pre_vals or not post_vals:
            continue

        pre_avg  = float(np.mean(pre_vals))
        post_avg = float(np.mean(post_vals))
        delta    = ((post_avg - pre_avg) / pre_avg * 100) if pre_avg != 0 else 0

        thresh = THRESHOLDS.get(metric, {})
        direction = thresh.get("direction", "higher_is_worse")
        warning   = thresh.get("warning")
        critical  = thresh.get("critical")

        # Breach detection
        status = "STABLE"
        if warning and critical:
            if direction == "higher_is_worse":
                if post_avg >= critical:
                    status = "CRITICAL"
                elif post_avg >= warning:
                    status = "WARNING"
            else:  # lower_is_worse
                if post_avg <= critical:
                    status = "CRITICAL"
                elif post_avg <= warning:
                    status = "WARNING"

        result[metric] = {
            "pre_avg":  round(pre_avg,  2),
            "post_avg": round(post_avg, 2),
            "delta_pct": round(delta,   2),
            "status":   status,
            "latest":   round(post_vals[-1], 2) if post_vals else None,
        }

    return result


def detect_anomalies(metrics_data: list, z_threshold: float = 2.0) -> dict:
    """
    Z-score based anomaly detection per metric.
    Returns dict of metric → list of anomalous days.
    """
    metric_names = [k for k in THRESHOLDS.keys()]
    anomalies = {}

    for metric in metric_names:
        values = [(d.get("day", i+1), d[metric]) for i, d in enumerate(metrics_data) if metric in d]
        if len(values) < 3:
            continue

        days, vals = zip(*values)
        arr = np.array(vals, dtype=float)
        z_scores = np.abs(stats.zscore(arr))

        flagged = [
            {"day": int(days[i]), "value": round(float(arr[i]), 2), "z_score": round(float(z_scores[i]), 2)}
            for i in range(len(arr))
            if z_scores[i] >= z_threshold
        ]

        if flagged:
            anomalies[metric] = flagged

    return anomalies


def analyze_trends(metrics_data: list, post_launch_day: int = 4) -> dict:
    """
    Linear regression slope on post-launch days.
    Returns IMPROVING / WORSENING / STABLE per metric.
    """
    post = [d for d in metrics_data if d.get("day", 0) >= post_launch_day]
    if len(post) < 2:
        return {}

    metric_names = [k for k in THRESHOLDS.keys()]
    trends = {}

    for metric in metric_names:
        vals = [d[metric] for d in post if metric in d]
        if len(vals) < 2:
            continue

        x = np.arange(len(vals), dtype=float)
        y = np.array(vals, dtype=float)
        slope, _, r_value, p_value, _ = stats.linregress(x, y)

        direction = THRESHOLDS.get(metric, {}).get("direction", "higher_is_worse")

        if abs(slope) < 0.01 * np.mean(y) or p_value > 0.1:
            trend = "STABLE"
        elif direction == "higher_is_worse":
            trend = "WORSENING" if slope > 0 else "IMPROVING"
        else:
            trend = "WORSENING" if slope < 0 else "IMPROVING"

        trends[metric] = {
            "trend":   trend,
            "slope":   round(float(slope), 4),
            "r_squared": round(float(r_value ** 2), 4),
            "p_value": round(float(p_value), 4),
        }

    return trends


def get_breach_summary(aggregated: dict) -> dict:
    """Quick count of metrics by status."""
    summary = {"CRITICAL": [], "WARNING": [], "STABLE": []}
    for metric, data in aggregated.items():
        status = data.get("status", "STABLE")
        summary.setdefault(status, []).append(metric)
    summary["critical_count"] = len(summary["CRITICAL"])
    summary["warning_count"]  = len(summary["WARNING"])
    return summary


def format_metrics_for_prompt(
    aggregated: dict,
    anomalies:  dict,
    trends:     dict,
) -> str:
    """Formats metric analysis into clean text for LLM prompts."""
    lines = ["=== METRIC ANALYSIS ===\n"]

    lines.append("[ Aggregated Status ]")
    for metric, data in aggregated.items():
        lines.append(
            f"  {metric:30s} | pre={data['pre_avg']:>8} | post={data['post_avg']:>8} "
            f"| delta={data['delta_pct']:>+7.1f}% | {data['status']}"
        )

    lines.append("\n[ Anomalies Detected ]")
    if anomalies:
        for metric, flags in anomalies.items():
            for f in flags:
                lines.append(f"  {metric}: Day {f['day']} = {f['value']} (z={f['z_score']})")
    else:
        lines.append("  None detected")

    lines.append("\n[ Post-Launch Trends ]")
    for metric, t in trends.items():
        lines.append(f"  {metric:30s} | {t['trend']:10s} | slope={t['slope']}")

    return "\n".join(lines)