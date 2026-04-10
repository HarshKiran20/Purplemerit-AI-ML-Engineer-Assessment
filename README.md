# 🚨 War Room — Multi-Agent Post-Launch Incident Response System

> AI-powered cross-functional war room that simulates coordinated decision-making among 5 specialist agents to produce a structured launch decision: **Proceed / Monitor / Hotfix / Rollback**.

---

## Overview

War Room is a multi-agent system built for **PurpleMerit Technologies** Assessment 1. It ingests real post-launch metrics and user feedback, runs 5 concurrent AI agents (each with a distinct role), and synthesises their outputs into a structured `decision.json` containing a final verdict, risk register, action plan, communication plan, and confidence score.

### Agent Roles

| Agent             | Role                                                                            |
| ----------------- | ------------------------------------------------------------------------------- |
| **PM Agent**      | Defines success criteria, overall health score, go/no-go framing                |
| **Analyst Agent** | Quantitative metrics analysis — anomaly detection, trend regression, root cause |
| **Comms Agent**   | Sentiment analysis, messaging strategy, draft public responses                  |
| **Risk Agent**    | Devil's advocate — risk matrix, worst-case scenarios, escalation triggers       |
| **Support Agent** | Ticket triage, P0/P1 prioritisation, response templates                         |

---

## Project Structure

```
warroom/
├── app.py                  ← Streamlit UI (main entry point)
├── orchestrator.py         ← War room coordinator — runs agents, resolves verdict
├── agents/
│   ├── pm_agent.py         ← Product Manager Agent
│   ├── analyst_agent.py    ← Data Analyst Agent
│   ├── comms_agent.py      ← Marketing/Comms Agent
│   ├── risk_agent.py       ← Risk/Critic Agent
│   └── support_agent.py    ← Support Triage Agent
├── tools/
│   ├── metric_tools.py     ← aggregate, anomaly detection, trend analysis
│   └── feedback_tools.py   ← sentiment analysis, issue categorisation
├── data/
│   ├── metrics.json        ← 10-day time series (10 metrics, Days 1-3 baseline, 4-10 post-launch)
│   ├── feedback.json       ← 30 user feedback entries (mixed sentiment, real issue patterns)
│   └── release_notes.md    ← Feature description + 5 known risks + success criteria
├── output/
│   └── decision.json       ← Final structured output (auto-generated on each run)
└── requirements.txt
```

---

## Setup Instructions

### Prerequisites

- Python 3.10 or higher
- A [Groq API key](https://console.groq.com) (free tier is sufficient)

### 1. Clone the repository

```bash
git clone https://github.com/<your-username>/warroom.git
cd warroom
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

### 3. Set your environment variable

Create a `.env` file in the project root:

```bash
# .env
GROQ_API_KEY=your_groq_api_key_here
```

Or export it directly:

```bash
export GROQ_API_KEY=your_groq_api_key_here
```

---

## How to Run

### Option A — Streamlit UI (recommended)

```bash
streamlit run app.py
```

Then open [http://localhost:8501](http://localhost:8501) in your browser.

1. Paste your Groq API key in the sidebar (or set it via `.env`)
2. Confirm all 3 data files show ✅ in the sidebar
3. Click **⚡ LAUNCH WAR ROOM**
4. Watch 5 agents run concurrently (~25–30 seconds total)
5. Review the dashboard — Consensus, PM Report, Analyst, Comms, Risk, Support tabs
6. Download `decision.json` from the RAW JSON tab

### Option B — Run orchestrator directly (CLI / headless)

```bash
python -c "
from dotenv import load_dotenv
load_dotenv()
from orchestrator import run_war_room
result = run_war_room()
print('Verdict:', result['final_verdict']['recommendation'])
print('Saved to: output/decision.json')
"
```

---

## Output: decision.json

The final structured output contains all fields required by the assessment:

```json
{
  "war_room_session": { ... },

  "final_verdict": {
    "recommendation": "MONITOR_CLOSELY | HOTFIX_REQUIRED | ROLLBACK | PROCEED",
    "recommendation_rationale": "All agents aligned... 2 metrics in WARNING: crash_rate, p99_latency_ms. User sentiment: 43% negative across 30 entries...",
    "metric_evidence": {
      "critical_breaches": [...],
      "warning_breaches": [...],
      "negative_sentiment_pct": 43.3,
      "churn_signals": 5,
      "top_deltas": { "crash_rate": "+180%", ... }
    },
    "health_score": 80,
    "risk_level": "MEDIUM",
    "time_sensitivity": "48_HOURS"
  },

  "confidence": {
    "score": "MEDIUM",
    "rationale": "...",
    "data_quality": "GOOD",
    "what_would_increase_confidence": [
      "Stable readings on crash_rate, payment_success over next 48h.",
      "Longer post-launch observation window."
    ]
  },

  "communication_plan": {
    "external_messaging": {
      "public_tweet": "...",
      "app_store_response": "...",
      "in_app_notification": "..."
    },
    "internal_messaging": { "support_template": "..." },
    "channel_strategy": [...],
    "retention_actions": [...]
  },

  "consensus": {
    "root_cause_hypothesis": "...",
    "immediate_actions": [
      { "action": "...", "owner": "Engineering", "timeline": "now", "source": "Risk" }
    ],
    "metrics_to_watch": [...],
    "top_concerns": [...]
  },

  "agent_reports": {
    "PM":      { ... },
    "Analyst": { ... },
    "Comms":   { ... },
    "Risk":    { ... },
    "Support": { ... }
  }
}
```

---

## How Agents Interact

```
                       ┌─────────────────┐
                       │  orchestrator   │
                       │  run_war_room() │
                       └────────┬────────┘
                                │ loads data
                    ┌───────────▼──────────────┐
                    │  metrics.json            │
                    │  feedback.json           │
                    │  release_notes.md        │
                    └───────────┬──────────────┘
                                │ dispatches concurrently
          ┌──────────┬──────────┼──────────┬──────────┐
          ▼          ▼          ▼          ▼          ▼
       PM Agent  Analyst    Comms       Risk      Support
          │          │          │          │          │
          │  calls tools first  │          │          │
          └──────────┴──────────┴──────────┴──────────┘
                                │ all return structured JSON
                       ┌────────▼────────┐
                       │  orchestrator   │
                       │  _resolve_verdict()         ← conservative: most severe wins
                       │  _build_consensus()         ← cross-agent action synthesis
                       │  _build_confidence()        ← analyst confidence + what helps
                       │  _build_communication_plan()← comms drafts → decision.json
                       └────────┬────────┘
                                │
                       output/decision.json
```

Each agent independently calls tool functions (`aggregate_metrics`, `detect_anomalies`, `analyze_sentiment`, etc.) before constructing its LLM prompt. This ensures the LLM receives pre-processed, structured data rather than raw JSON, and guarantees tools are called programmatically on every run.

---

## Environment Variables

| Variable       | Required | Description                                                                      |
| -------------- | -------- | -------------------------------------------------------------------------------- |
| `GROQ_API_KEY` | ✅ Yes   | Your Groq API key — get one free at [console.groq.com](https://console.groq.com) |

---

## Model

All agents use **LLaMA3-70B** via the Groq API (`llama3-70b-8192`). Groq's free tier provides sufficient rate limits for a full war room run (5 concurrent calls, ~1200 tokens each).

---

## Example Run

```bash
$ export GROQ_API_KEY=gsk_...
$ streamlit run app.py

  You can now view your Streamlit app in your browser.
  Local URL: http://localhost:8501
```
```
# Click LAUNCH WAR ROOM

# [12:35:44] Dispatching agents to war room...

# [12:35:51] Agent 'Analyst' finished... (4.79s)

# [12:35:51] Agent 'PM' finished... (5.28s)

# [12:35:51] Agent 'Risk' finished... (5.27s)

# [12:35:51] Agent 'Support' finished... (5.27s)

# [12:35:51] Agent 'Comms' finished... (5.38s)

# [12:35:51] Synthesizing agent findings...

# [12:35:51] Resolving conflicts and finalizing verdict...

# War room complete ✓

# Final verdict: MONITOR_CLOSELY

# decision.json saved to output/decision.json

```

---

## Requirements

See `requirements.txt`. Key dependencies:

```

streamlit
requests
python-dotenv
vaderSentiment
scipy
numpy

```

---

## Submission

- **GitHub Repository:** `[(https://github.com/HarshKiran20/Purplemerit-AI-ML-Engineer-Assessment)]`
- **Demo Video:** Screen recording showing the full run and final `decision.json` output


```
