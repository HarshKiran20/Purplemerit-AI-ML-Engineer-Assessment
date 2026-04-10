"""
War Room — Streamlit UI (Step 5)
Run: streamlit run app.py
"""

import streamlit as st
import json
import time
import os
from datetime import datetime
from pathlib import Path

# ── Page config (must be first Streamlit call) ──────────────────────────────
st.set_page_config(
    page_title="War Room",
    page_icon="🚨",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Custom CSS ───────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;600&family=IBM+Plex+Sans:wght@300;400;600;700&display=swap');

html, body, [class*="css"] { font-family: 'IBM Plex Sans', sans-serif; }

:root {
    --bg:      #0a0b0e;
    --surface: #111318;
    --border:  #1e2028;
    --accent:  #ff3b30;
    --amber:   #ff9f0a;
    --green:   #30d158;
    --blue:    #0a84ff;
    --text:    #e5e7eb;
    --muted:   #6b7280;
    --mono:    'IBM Plex Mono', monospace;
}

.stApp { background: var(--bg) !important; color: var(--text) !important; }
#MainMenu, footer, header { visibility: hidden; }
.block-container { padding: 1.5rem 2rem !important; max-width: 1400px; }

.war-header {
    background: linear-gradient(135deg, #1a0505 0%, #0a0b0e 60%);
    border: 1px solid var(--accent);
    border-radius: 8px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
}
.war-header h1 {
    font-family: var(--mono);
    font-size: 1.6rem;
    color: var(--accent);
    margin: 0;
    letter-spacing: 0.08em;
    text-transform: uppercase;
}
.war-header .sub {
    color: var(--muted);
    font-size: 0.8rem;
    font-family: var(--mono);
    margin-top: 0.2rem;
}

.verdict-card {
    border-radius: 8px;
    padding: 1.5rem 2rem;
    margin-bottom: 1.5rem;
    border-width: 1px;
    border-style: solid;
}
.verdict-ROLLBACK { background: #1a0505; border-color: var(--accent); }
.verdict-HOTFIX   { background: #1a1000; border-color: var(--amber);  }
.verdict-MONITOR  { background: #001020; border-color: var(--blue);   }
.verdict-PROCEED  { background: #001508; border-color: var(--green);  }

.verdict-label { font-family: var(--mono); font-size: 0.7rem; letter-spacing: 0.12em; text-transform: uppercase; color: var(--muted); }
.verdict-title { font-size: 2rem; font-weight: 700; margin: 0.3rem 0; font-family: var(--mono); }
.verdict-ROLLBACK .verdict-title { color: var(--accent); }
.verdict-HOTFIX   .verdict-title { color: var(--amber);  }
.verdict-MONITOR  .verdict-title { color: var(--blue);   }
.verdict-PROCEED  .verdict-title { color: var(--green);  }

.metric-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 0.75rem; margin-bottom: 1.5rem; }
.metric-tile { background: var(--surface); border: 1px solid var(--border); border-radius: 6px; padding: 1rem 1.2rem; }
.metric-tile .label { font-family: var(--mono); font-size: 0.65rem; letter-spacing: 0.1em; color: var(--muted); text-transform: uppercase; margin-bottom: 0.4rem; }
.metric-tile .value { font-size: 1.6rem; font-weight: 700; font-family: var(--mono); }
.metric-tile .sub-label { font-size: 0.75rem; font-family: var(--mono); margin-top: 0.2rem; color: var(--muted); }

.red   { color: var(--accent); }
.amber { color: var(--amber);  }
.green { color: var(--green);  }
.blue  { color: var(--blue);   }

.action-item {
    background: var(--surface);
    border-left: 3px solid var(--accent);
    padding: 0.6rem 1rem;
    margin: 0.4rem 0;
    border-radius: 0 4px 4px 0;
    font-size: 0.85rem;
    font-family: var(--mono);
}
.action-item .act-meta {
    font-size: 0.7rem;
    color: var(--muted);
    margin-top: 0.25rem;
}

.stProgress > div > div { background: var(--accent) !important; }

.stButton > button {
    background: var(--accent) !important;
    color: white !important;
    border: none !important;
    font-family: var(--mono) !important;
    letter-spacing: 0.08em !important;
    font-weight: 600 !important;
    padding: 0.6rem 2rem !important;
    border-radius: 4px !important;
    text-transform: uppercase !important;
    font-size: 0.85rem !important;
}
.stButton > button:hover { background: #cc2e25 !important; box-shadow: 0 0 20px rgba(255,59,48,0.3) !important; }

.stTabs [data-baseweb="tab-list"] { background: var(--surface) !important; border-bottom: 1px solid var(--border) !important; gap: 0 !important; }
.stTabs [data-baseweb="tab"] { font-family: var(--mono) !important; font-size: 0.75rem !important; letter-spacing: 0.08em !important; color: var(--muted) !important; text-transform: uppercase !important; padding: 0.75rem 1.5rem !important; border-bottom: 2px solid transparent !important; }
.stTabs [aria-selected="true"] { color: var(--text) !important; border-bottom: 2px solid var(--accent) !important; background: transparent !important; }
.stTabs [data-baseweb="tab-panel"] { padding: 1rem 0 0 0 !important; }

.streamlit-expanderHeader { font-family: var(--mono) !important; font-size: 0.8rem !important; background: var(--surface) !important; border: 1px solid var(--border) !important; border-radius: 4px !important; }
.stCodeBlock { background: #0d0f13 !important; }

.badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 3px; font-family: var(--mono); font-size: 0.65rem; font-weight: 600; letter-spacing: 0.08em; text-transform: uppercase; }
.badge-red   { background: rgba(255,59,48,0.15);  color: var(--accent); border: 1px solid rgba(255,59,48,0.3); }
.badge-amber { background: rgba(255,159,10,0.15); color: var(--amber);  border: 1px solid rgba(255,159,10,0.3); }
.badge-green { background: rgba(48,209,88,0.15);  color: var(--green);  border: 1px solid rgba(48,209,88,0.3); }
.badge-blue  { background: rgba(10,132,255,0.15); color: var(--blue);   border: 1px solid rgba(10,132,255,0.3); }

hr { border-color: var(--border) !important; margin: 1rem 0 !important; }
.scroll-box { max-height: 300px; overflow-y: auto; padding-right: 0.5rem; }
.scroll-box::-webkit-scrollbar { width: 4px; }
.scroll-box::-webkit-scrollbar-thumb { background: var(--border); border-radius: 2px; }
</style>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Helper utilities
# ══════════════════════════════════════════════════════════════════════════════

def _verdict_class(verdict: str) -> str:
    v = verdict.upper()
    if "ROLLBACK" in v: return "ROLLBACK"
    if "HOTFIX"   in v: return "HOTFIX"
    if "MONITOR"  in v: return "MONITOR"
    return "PROCEED"


def _badge(text: str, color: str = "blue") -> str:
    return f'<span class="badge badge-{color}">{text}</span>'


def _status_color(status: str) -> str:
    s = status.upper()
    if any(x in s for x in ("CRITICAL","WORSENING","NEGATIVE","ROLLBACK","HIGH")): return "red"
    if any(x in s for x in ("WARNING","STABLE","HOTFIX","MEDIUM")):               return "amber"
    if any(x in s for x in ("IMPROVING","POSITIVE","PROCEED","LOW")):             return "green"
    return "blue"


def _load_existing_decision() -> dict | None:
    path = Path("output/decision.json")
    if path.exists():
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            return None
    return None


def _safe_str(val) -> str:
    """Convert any value to a display-safe string."""
    if val is None: return "—"
    if isinstance(val, dict): return val.get("action", str(val))
    return str(val)


# ══════════════════════════════════════════════════════════════════════════════
# FIX: Normalize orchestrator agent key names (PM → pm_agent, etc.)
# ══════════════════════════════════════════════════════════════════════════════

# Orchestrator stores reports under "PM", "Analyst", etc.
# app.py expects "pm_agent", "analyst_agent", etc.
# This map handles both directions.
AGENT_KEY_MAP = {
    "PM":       "pm_agent",
    "Analyst":  "analyst_agent",
    "Comms":    "comms_agent",
    "Risk":     "risk_agent",
    "Support":  "support_agent",
}

def _normalize_reports(raw_reports: dict) -> dict:
    """Remap short keys → long keys so UI always finds the right report."""
    normalized = {}
    for k, v in raw_reports.items():
        long_key = AGENT_KEY_MAP.get(k, k)  # map PM→pm_agent, or keep as-is
        normalized[long_key] = v
    return normalized


# ══════════════════════════════════════════════════════════════════════════════
# Header
# ══════════════════════════════════════════════════════════════════════════════

st.markdown("""
<div class="war-header">
    <div>
        <h1>🚨 War Room</h1>
        <div class="sub">AI-Powered Post-Launch Incident Response · Multi-Agent Decision Engine</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# Session state
# ══════════════════════════════════════════════════════════════════════════════
if "result"   not in st.session_state: st.session_state.result   = None
if "running"  not in st.session_state: st.session_state.running  = False
if "log"      not in st.session_state: st.session_state.log      = []
if "progress" not in st.session_state: st.session_state.progress = 0


# ══════════════════════════════════════════════════════════════════════════════
# Sidebar
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("### ⚙️ Configuration")
    st.markdown("---")

    api_key_input = st.text_input(
        "Groq API Key",
        value=os.getenv("GROQ_API_KEY", ""),
        type="password",
        help="Set in .env or paste here",
    )
    if api_key_input:
        os.environ["GROQ_API_KEY"] = api_key_input

    st.markdown("---")
    st.markdown("### 📁 Data Files")
    for fp, label in [
        ("data/metrics.json",     "metrics.json"),
        ("data/feedback.json",    "feedback.json"),
        ("data/release_notes.md", "release_notes.md"),
    ]:
        icon = "✅" if Path(fp).exists() else "❌"
        st.markdown(f"{icon} `{label}`")

    st.markdown("---")
    st.markdown("### 📋 Previous Run")
    prev = _load_existing_decision()
    if prev:
        ts = prev.get("war_room_session", {}).get("timestamp", "unknown")
        st.markdown(f"**Last run:** `{ts[:19]}`")
        if st.button("Load Previous", use_container_width=True):
            st.session_state.result = prev
    else:
        st.markdown("_No previous run found_")


# ══════════════════════════════════════════════════════════════════════════════
# Launch area
# ══════════════════════════════════════════════════════════════════════════════
col_btn, col_status = st.columns([2, 5])
with col_btn:
    launch = st.button("⚡ LAUNCH WAR ROOM", use_container_width=True)
with col_status:
    status_placeholder = st.empty()

progress_bar    = st.empty()
log_placeholder = st.empty()


# ══════════════════════════════════════════════════════════════════════════════
# War room execution
# ══════════════════════════════════════════════════════════════════════════════
if launch and not st.session_state.running:
    if not os.getenv("GROQ_API_KEY"):
        st.error("❌ GROQ_API_KEY not set. Add it in the sidebar or your .env file.")
    else:
        st.session_state.running  = True
        st.session_state.log      = []
        st.session_state.progress = 0
        st.session_state.result   = None

        try:
            from orchestrator import run_war_room
        except ImportError as e:
            st.error(f"❌ Could not import orchestrator: {e}")
            st.session_state.running = False
            st.stop()

        def on_progress(msg: str, pct: float):
            ts = datetime.now().strftime("%H:%M:%S")
            st.session_state.log.append(f"[{ts}] {msg}")
            st.session_state.progress = pct
            progress_bar.progress(min(int(pct), 100))

            # Color-highlight agent names in log
            log_lines = []
            for line in st.session_state.log[-8:]:
                for agent in ("Analyst","Support","PM","Comms","Risk"):
                    if f"'{agent}'" in line:
                        line = line.replace(f"'{agent}'", f"'{agent}'")
                log_lines.append(line)
            log_placeholder.code("\n".join(log_lines), language="bash")
            status_placeholder.markdown(f"**⏳ {msg}**")

        with st.spinner("War room assembling agents…"):
            try:
                result = run_war_room(progress_callback=on_progress)
                st.session_state.result  = result
                st.session_state.running = False
                progress_bar.progress(100)
                status_placeholder.markdown("**✅ War room complete**")
                log_placeholder.empty()
            except Exception as e:
                st.session_state.running = False
                st.error(f"❌ War room failed: {e}")
                st.exception(e)
                st.stop()


# ══════════════════════════════════════════════════════════════════════════════
# Results dashboard
# ══════════════════════════════════════════════════════════════════════════════
result = st.session_state.result
if result is None:
    st.markdown("""
    <div style="text-align:center; padding: 4rem 2rem; color: #6b7280;">
        <div style="font-size:3rem; margin-bottom:1rem;">🎯</div>
        <div style="font-family:'IBM Plex Mono',monospace; font-size:0.9rem; letter-spacing:0.08em;">
            AWAITING LAUNCH — CLICK THE BUTTON ABOVE TO BEGIN
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.stop()


# ── Parse top-level result ────────────────────────────────────────────────────
session   = result.get("war_room_session", {})
verdict   = result.get("final_verdict",    {})
consensus = result.get("consensus",        {})
synthesis = result.get("synthesis",        {})
errors    = result.get("agent_errors",     {})

# FIX 1: Normalize agent keys  PM → pm_agent etc.
reports = _normalize_reports(result.get("agent_reports", {}))

vclass = _verdict_class(verdict.get("recommendation", "MONITOR_CLOSELY"))
vtext  = verdict.get("recommendation", "MONITOR_CLOSELY")

# FIX 2: Pull rationale from correct key name
vreason = (
    verdict.get("recommendation_rationale")
    or verdict.get("rationale")
    or verdict.get("reasoning")
    or ""
)

agents_run    = session.get("agents_run", [])
agents_failed = session.get("agents_failed", [])
timings       = session.get("agent_timings_sec", {})
total_sec     = round(sum(timings.values()), 1) if timings else 0


# ══════════════════════════════════════════════════════════════════════════════
# 1. Verdict banner  — FIX 3: use plain text badges, not raw HTML in f-string
# ══════════════════════════════════════════════════════════════════════════════
agents_badge  = _badge(f"Agents: {len(agents_run)}/{len(agents_run)+len(agents_failed)}", "green")
duration_badge = _badge(f"Duration: {total_sec}s", "amber")
conflict_badge = _badge("⚡ Conflict Resolved", "red") if verdict.get("conflict_detected") else ""

st.markdown(f"""
<div class="verdict-card verdict-{vclass}">
    <div class="verdict-label">Final Verdict · {session.get("timestamp","")[:19]}</div>
    <div class="verdict-title">{vtext}</div>
    <div style="color:#9ca3af; font-size:0.9rem; margin-top:0.5rem;">{vreason}</div>
    <div style="margin-top:0.75rem; display:flex; gap:0.75rem; flex-wrap:wrap;">
        {agents_badge}
        {duration_badge}
        {conflict_badge}
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 2. KPI tiles  — FIX 4: use correct keys from orchestrator synthesis output
# ══════════════════════════════════════════════════════════════════════════════

# Health score — in synthesis AND final_verdict
health = synthesis.get("health_score") or verdict.get("health_score") or "—"

# Negative sentiment % — pull from PM agent _tool_outputs or comms report
neg_pct = "—"
pm_report = reports.get("pm_agent", {})
tool_out  = pm_report.get("_tool_outputs", {}) if isinstance(pm_report, dict) else {}
sent_ov   = tool_out.get("sentiment_overview", {})
if isinstance(sent_ov, dict):
    neg_pct = sent_ov.get("negative_pct", sent_ov.get("negative_percentage", "—"))

# Also try comms agent
if neg_pct == "—":
    comms_report = reports.get("comms_agent", {})
    comms_tool   = comms_report.get("_tool_outputs", {}) if isinstance(comms_report, dict) else {}
    comms_sent   = comms_tool.get("sentiment", {})
    if isinstance(comms_sent, dict):
        overall = comms_sent.get("overall", {})
        neg_pct = overall.get("negative_pct", "—")

# Critical anomalies count — from analyst _tool_outputs
critical_anomalies_count = 0
analyst_report = reports.get("analyst_agent", {})
analyst_tool   = analyst_report.get("_tool_outputs", {}) if isinstance(analyst_report, dict) else {}
anomalies_data = analyst_tool.get("anomalies", {})
if isinstance(anomalies_data, dict):
    critical_anomalies_count = sum(
        1 for v in anomalies_data.values()
        if isinstance(v, dict) and v.get("has_anomalies")
    )

# Churn risk — from consensus or comms agent
churn_risk = consensus.get("churn_risk", "—")
if churn_risk == "—" or churn_risk == "UNKNOWN":
    comms_report = reports.get("comms_agent", {})
    if isinstance(comms_report, dict):
        sa = comms_report.get("sentiment_assessment", {})
        churn_risk = sa.get("churn_risk", "—") if isinstance(sa, dict) else "—"

# Top issue from support or comms
top_issue = "—"
support_report = reports.get("support_agent", {})
if isinstance(support_report, dict):
    load_assess = support_report.get("support_load_assessment", {})
    if isinstance(load_assess, dict):
        top_issue = load_assess.get("top_issue_type", "—")

# Color helpers
def _health_color(h):
    try:
        h = int(h)
        return "green" if h >= 70 else "amber" if h >= 50 else "red"
    except: return "blue"

def _neg_color(n):
    try:
        n = float(str(n).replace("%",""))
        return "red" if n > 50 else "amber"
    except: return "amber"

def _churn_color(c):
    c = str(c).upper()
    return "red" if "HIGH" in c else "amber" if "MEDIUM" in c else "green"

st.markdown(f"""
<div class="metric-grid">
    <div class="metric-tile">
        <div class="label">Health Score</div>
        <div class="value {_health_color(health)}">{health}<span style="font-size:1rem">/100</span></div>
        <div class="sub-label">Overall system health</div>
    </div>
    <div class="metric-tile">
        <div class="label">Negative Sentiment</div>
        <div class="value {_neg_color(neg_pct)}">{neg_pct}{'%' if neg_pct != '—' and '%' not in str(neg_pct) else ''}</div>
        <div class="sub-label">of user feedback</div>
    </div>
    <div class="metric-tile">
        <div class="label">Metrics w/ Anomalies</div>
        <div class="value {'red' if critical_anomalies_count > 3 else 'amber' if critical_anomalies_count > 0 else 'green'}">{critical_anomalies_count}</div>
        <div class="sub-label">metrics breached threshold</div>
    </div>
    <div class="metric-tile">
        <div class="label">Churn Risk</div>
        <div class="value {_churn_color(churn_risk)}">{churn_risk}</div>
        <div class="sub-label">top issue: {str(top_issue)[:25]}</div>
    </div>
</div>
""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════════════════════
# 3. Tabs
# ══════════════════════════════════════════════════════════════════════════════
tabs = st.tabs([
    "🎯 CONSENSUS",
    "📊 PM REPORT",
    "🔬 ANALYST",
    "📣 COMMS",
    "⚠️ RISK",
    "🎫 SUPPORT",
    "📄 RAW JSON",
])


# ─── Tab 0: Consensus ──────────────────────────────────────────────────────────
with tabs[0]:
    col_a, col_b = st.columns(2)

    with col_a:
        st.markdown("#### 🔴 Immediate Actions")
        actions = consensus.get("immediate_actions", [])
        if actions:
            for i, act in enumerate(actions[:10], 1):
                # FIX 5: act can be a dict OR a string — handle both
                if isinstance(act, dict):
                    action_text = act.get("action", str(act))
                    owner       = act.get("owner", "")
                    timeline    = act.get("timeline", "")
                    source      = act.get("source", "")
                    meta = " · ".join(filter(None, [
                        f"👤 {owner}"    if owner    else "",
                        f"⏱ {timeline}" if timeline else "",
                        f"[{source}]"   if source   else "",
                    ]))
                    st.markdown(
                        f'<div class="action-item">'
                        f'<span style="color:var(--muted);margin-right:0.5rem;">{"0"+str(i) if i<10 else i}.</span>'
                        f'{action_text}'
                        f'{"<div class=act-meta>" + meta + "</div>" if meta else ""}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
                else:
                    # Plain string action
                    st.markdown(
                        f'<div class="action-item">'
                        f'<span style="color:var(--muted);margin-right:0.5rem;">{"0"+str(i) if i<10 else i}.</span>'
                        f'{str(act)}'
                        f'</div>',
                        unsafe_allow_html=True
                    )
        else:
            st.info("No actions extracted.")

    with col_b:
        st.markdown("#### 📍 Key Metrics to Watch")
        metrics_watch = consensus.get("metrics_to_watch", [])  # FIX: correct key name
        if metrics_watch:
            for m in metrics_watch:
                st.markdown(f'<div class="action-item">{m}</div>', unsafe_allow_html=True)
        else:
            st.info("No metrics flagged.")

    st.markdown("---")
    col_c, col_d = st.columns(2)

    with col_c:
        st.markdown("#### 🤝 Top Concerns")
        concerns = consensus.get("top_concerns", [])
        if concerns:
            for c in concerns:
                if isinstance(c, dict):
                    concern_text = c.get("concern", str(c))
                    severity     = c.get("severity", "")
                    evidence     = c.get("data_evidence", "")
                    source       = c.get("source", "")
                    color        = _status_color(severity)
                    badge_html   = _badge(severity, color) if severity else ""
                    src_html     = f'<span style="color:var(--muted);font-size:0.7rem;"> [{source}]</span>' if source else ""
                    ev_html      = f'<div style="color:var(--muted);font-size:0.75rem;margin-top:0.2rem;">{evidence}</div>' if evidence else ""
                    st.markdown(
                        f'<div style="padding:0.5rem 0; border-bottom:1px solid var(--border);">'
                        f'{badge_html} <span style="font-size:0.85rem;">{concern_text}</span>{src_html}'
                        f'{ev_html}</div>',
                        unsafe_allow_html=True
                    )
                else:
                    st.markdown(f"- {c}")
        else:
            st.info("No concerns extracted.")

    with col_d:
        st.markdown("#### 📊 Agent Verdicts")
        # Pull verdicts from each agent report
        agent_display = {
            "PM":      ("pm_agent",      "recommendation"),
            "Analyst": ("analyst_agent", "analyst_confidence"),
            "Comms":   ("comms_agent",   "sentiment_assessment"),
            "Risk":    ("risk_agent",    "risk_agent_verdict"),
            "Support": ("support_agent", "support_load_assessment"),
        }
        for display_name, (key, field) in agent_display.items():
            rep = reports.get(key, {})
            if not rep:
                val = "NO REPORT"
                color = "red"
            else:
                raw = rep.get(field, "—")
                if isinstance(raw, dict):
                    # e.g. sentiment_assessment dict → pull overall_mood
                    val = raw.get("overall_mood") or raw.get("volume") or "—"
                else:
                    val = str(raw) if raw else "—"
                color = _status_color(val)

            st.markdown(
                f'<div style="display:flex;justify-content:space-between;align-items:center;'
                f'padding:0.5rem 0;border-bottom:1px solid #1e2028;">'
                f'<span style="font-family:monospace;font-size:0.85rem;">{display_name}</span>'
                f'{_badge(val, color)}</div>',
                unsafe_allow_html=True
            )

        # Positive signals
        positives = consensus.get("positive_signals", [])
        if positives:
            st.markdown("---")
            st.markdown("**✅ Positive Signals**")
            for p in positives:
                st.markdown(f"- {p}")

    # Agent errors
    if errors:
        st.markdown("---")
        st.markdown("#### ❌ Agent Errors")
        for agent_name, err in errors.items():
            with st.expander(f"Error in {agent_name}"):
                st.code(str(err)[:2000], language="text")


# ══════════════════════════════════════════════════════════════════════════════
# Agent report renderer  — shared across tabs 1-5
# ══════════════════════════════════════════════════════════════════════════════

def _render_agent_report(tab_obj, agent_key: str):
    with tab_obj:
        report = reports.get(agent_key)
        if not report:
            st.info(f"No report available for **{agent_key}**.")
            return

        # Pull top-level verdict/recommendation badge
        for top_key in ("recommendation","risk_agent_verdict","primary_recommendation","overall_health","overall_risk_level"):
            if top_key in report:
                val   = report[top_key]
                color = _status_color(str(val))
                st.markdown(f'<div style="margin-bottom:1rem;">{_badge(str(val), color)}</div>', unsafe_allow_html=True)
                break

        # Render fields
        skip_keys = {"_tool_outputs", "_raw_response", "agent", "parse_error", "raw_response"}
        for key, val in report.items():
            if key in skip_keys:
                continue
            label = key.replace("_", " ").title()

            if isinstance(val, list):
                if not val:
                    continue
                st.markdown(f"**{label}**")
                for item in val:
                    if isinstance(item, dict):
                        # Render dict items as formatted cards, not raw JSON
                        lines = [f"**{k.replace('_',' ').title()}:** {v}" for k, v in item.items()]
                        with st.container():
                            st.markdown(
                                '<div style="background:var(--surface);border:1px solid var(--border);'
                                'border-radius:4px;padding:0.6rem 1rem;margin:0.3rem 0;font-size:0.85rem;">'
                                + " &nbsp;·&nbsp; ".join(lines) +
                                "</div>",
                                unsafe_allow_html=True
                            )
                    else:
                        st.markdown(f"- {item}")

            elif isinstance(val, dict):
                st.markdown(f"**{label}**")
                st.json(val)

            else:
                st.markdown(f"**{label}:** {val}")

        # Tool outputs expander
        if "_tool_outputs" in report:
            with st.expander("🔧 Raw Tool Outputs"):
                st.json(report["_tool_outputs"])


_render_agent_report(tabs[1], "pm_agent")
_render_agent_report(tabs[2], "analyst_agent")
_render_agent_report(tabs[3], "comms_agent")
_render_agent_report(tabs[4], "risk_agent")
_render_agent_report(tabs[5], "support_agent")


# ─── Tab 6: Raw JSON ───────────────────────────────────────────────────────────
with tabs[6]:
    col_dl, _ = st.columns([2, 5])
    with col_dl:
        json_str = json.dumps(result, indent=2, default=str)
        st.download_button(
            label="⬇ Download decision.json",
            data=json_str,
            file_name="decision.json",
            mime="application/json",
            use_container_width=True,
        )
    st.code(json_str[:8000] + ("\n… (truncated)" if len(json_str) > 8000 else ""), language="json")


# ── Footer ─────────────────────────────────────────────────────────────────────
st.markdown(f"""
<div style="text-align:center; padding:2rem 0 1rem; color:#374151;
    font-family:'IBM Plex Mono',monospace; font-size:0.7rem; letter-spacing:0.08em;">
    WAR ROOM · MULTI-AGENT INCIDENT RESPONSE · SESSION {session.get("timestamp","—")[:10].upper()}
</div>
""", unsafe_allow_html=True)