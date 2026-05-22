"""HCEE Closed-Loop Dashboard (S3 Full HCEE) - Multi-Temporal View
Real-time experience signals -> TC trigger -> Governance lever adjustment.

Multi-temporal architecture (4 tabs):
  Tab 1: Real-time AI monitoring (hourly cadence)
  Tab 2: Weekly experience surveys (PROMs cadence)
  Tab 3: Daily governance loop (core closed-loop, current focus)
  Tab 4: Adaptive learning (monthly cadence)

Run: pip install streamlit pandas numpy plotly && streamlit run hcee_dashboard.py

Author: Minseong Kim
HCEE Trademark Application Pending (KIPO 40-2026-0084368/0084369/0084370)
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

st.set_page_config(page_title="HCEE Closed-Loop Dashboard",
                   layout="wide", initial_sidebar_state="expanded")

TH_PXI, TH_EXI = 70, 65
TH_GAP = 15
RECOVERY_PXI = 75
RECOVERY_EXI = 70
SUSTAINED_TICKS = 2
RELEASE_AAL = 0.10
RELEASE_IF = 0.10
RELEASE_HOI = 0.50
RELEASE_TR = 0.25
INIT_PXI, INIT_EXI = 69.88, 65.10

NETLOGO_BASELINES = {
    "automation_level": 1.0,
    "interaction_mult": 1.0,
    "penalty_coeff":    1.0,
    "rationale_prob":   0.5,
}
CONCEPT_BASELINES = {"AAL": 1.00, "HOI": 0.25, "IF": 1.00, "TR": 0.50}

C_PXI, C_EXI = "#5A7548", "#7A2E2E"
C_TITLE, C_BG, C_SUB, C_ON = "#3F4A35", "#F4F0E4", "#7E776B", "#7A2E2E"
C_STAB = "#B4953C"

st.markdown(f"""<style>
.main {{ background-color: {C_BG}; }}
.stMetric label {{ color: {C_SUB} !important; }}
div[data-testid="stMetricValue"] {{ color: {C_TITLE} !important; }}
div[data-testid="stMetricDelta"] {{ font-size: 0.85em !important; }}
.tpill {{ display: inline-block; padding: 5px 13px; border-radius: 12px;
  font-size: 0.88em; font-weight: 600; margin-right: 8px; }}
.ton  {{ background: {C_ON}; color: white; }}
.tstab {{ background: {C_STAB}; color: white; }}
.toff {{ background: #E8E4D8; color: {C_SUB}; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 4px;
  background: {C_TITLE}; color: white; font-size: 0.78em;
  font-weight: 600; margin-left: 8px; vertical-align: middle; }}
.placeholder {{
  background: #FFFFFF; border: 0.5px dashed #C9B68A;
  border-radius: 6px; padding: 16px; color: {C_SUB};
  font-size: 0.85em; line-height: 1.6;
}}
.recommendation {{
  background: #FAF6E8; border-left: 3px solid {C_STAB};
  padding: 10px 14px; margin: 6px 0; font-size: 0.88em;
}}
</style>""", unsafe_allow_html=True)


def reset_state():
    st.session_state.tick = 0
    st.session_state.PXI  = INIT_PXI
    st.session_state.EXI  = INIT_EXI
    st.session_state.automation_level = NETLOGO_BASELINES["automation_level"]
    st.session_state.interaction_mult = NETLOGO_BASELINES["interaction_mult"]
    st.session_state.penalty_coeff    = NETLOGO_BASELINES["penalty_coeff"]
    st.session_state.rationale_prob   = NETLOGO_BASELINES["rationale_prob"]
    st.session_state.tc01_phase = "normal"
    st.session_state.tc02_phase = "normal"
    st.session_state.tc01_stable_count = 0
    st.session_state.tc02_stable_count = 0
    st.session_state.tc01_active = False
    st.session_state.tc02_active = False
    st.session_state.tc03_active = False
    st.session_state.tc01_engagements = 0
    st.session_state.tc02_engagements = 0
    st.session_state.history = []

if "tick" not in st.session_state:
    reset_state()


def c_AAL(): return st.session_state.automation_level
def c_IF():  return st.session_state.interaction_mult
def c_HOI():
    s = st.session_state
    return 0.5 * (1.0 - s.penalty_coeff) + 0.5 * s.rationale_prob
def c_TR():  return st.session_state.rationale_prob


def generate_signal():
    s = st.session_state
    s.tick += 1
    pxi_target = 58 + (1 - s.automation_level) * 55 + (s.interaction_mult - 1) * 46.5
    exi_target = 52 + (1 - s.penalty_coeff) * 15 + (s.rationale_prob - 0.5) * 15
    s.PXI = float(np.clip(s.PXI + (pxi_target - s.PXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    s.EXI = float(np.clip(s.EXI + (exi_target - s.EXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    apply_tc_rules()
    s.history.append({
        "tick": s.tick,
        "time": datetime.now().strftime("%H:%M:%S"),
        "PXI": round(s.PXI, 2), "EXI": round(s.EXI, 2),
        "AAL": round(c_AAL(), 2), "HOI": round(c_HOI(), 2),
        "IF":  round(c_IF(), 2),  "TR":  round(c_TR(), 2),
        "TC-01": s.tc01_phase,
        "TC-02": s.tc02_phase,
        "action": last_action(),
    })


def apply_tc_rules():
    s = st.session_state

    if s.tc01_phase == "normal":
        if s.PXI < TH_PXI:
            s.tc01_phase = "engaged"
            s.automation_level = 0.80
            s.interaction_mult = 1.20
            s.tc01_stable_count = 0
            s.tc01_engagements += 1
    elif s.tc01_phase == "engaged":
        if s.PXI > RECOVERY_PXI:
            s.tc01_stable_count += 1
            if s.tc01_stable_count >= SUSTAINED_TICKS:
                s.tc01_phase = "stabilizing"
        else:
            s.tc01_stable_count = 0
    elif s.tc01_phase == "stabilizing":
        if s.PXI < TH_PXI:
            s.tc01_phase = "engaged"
            s.automation_level = 0.80
            s.interaction_mult = 1.20
            s.tc01_stable_count = 0
            s.tc01_engagements += 1
        else:
            s.automation_level = min(1.0, s.automation_level + RELEASE_AAL)
            s.interaction_mult = max(1.0, s.interaction_mult - RELEASE_IF)
            if s.automation_level >= 1.0 and s.interaction_mult <= 1.0:
                s.tc01_phase = "normal"
                s.automation_level = 1.0
                s.interaction_mult = 1.0
                s.tc01_stable_count = 0

    if s.tc02_phase == "normal":
        if s.EXI < TH_EXI:
            s.tc02_phase = "engaged"
            s.penalty_coeff = 0.0
            s.rationale_prob = 1.0
            s.tc02_stable_count = 0
            s.tc02_engagements += 1
    elif s.tc02_phase == "engaged":
        if s.EXI > RECOVERY_EXI:
            s.tc02_stable_count += 1
            if s.tc02_stable_count >= SUSTAINED_TICKS:
                s.tc02_phase = "stabilizing"
        else:
            s.tc02_stable_count = 0
    elif s.tc02_phase == "stabilizing":
        if s.EXI < TH_EXI:
            s.tc02_phase = "engaged"
            s.penalty_coeff = 0.0
            s.rationale_prob = 1.0
            s.tc02_stable_count = 0
            s.tc02_engagements += 1
        else:
            s.penalty_coeff = min(1.0, s.penalty_coeff + RELEASE_HOI)
            s.rationale_prob = max(0.5, s.rationale_prob - RELEASE_TR)
            if s.penalty_coeff >= 1.0 and s.rationale_prob <= 0.5:
                s.tc02_phase = "normal"
                s.penalty_coeff = 1.0
                s.rationale_prob = 0.5
                s.tc02_stable_count = 0

    s.tc01_active = (s.tc01_phase == "engaged")
    s.tc02_active = (s.tc02_phase == "engaged")
    s.tc03_active = abs(s.PXI - s.EXI) > TH_GAP


def last_action():
    s = st.session_state
    parts = []
    if s.tc01_phase == "engaged":    parts.append("TC-01 ENGAGED")
    elif s.tc01_phase == "stabilizing": parts.append("TC-01 releasing")
    if s.tc02_phase == "engaged":    parts.append("TC-02 ENGAGED")
    elif s.tc02_phase == "stabilizing": parts.append("TC-02 releasing")
    if s.tc03_active: parts.append("TC-03 flagged")
    return " | ".join(parts) if parts else "Normal operation"


def interpretation():
    s = st.session_state
    if s.tc01_phase == "normal" and s.tc02_phase == "normal" and not s.tc03_active:
        return ("Normal operation. PXI >= 70 and EXI >= 65. "
                "All levers at baseline; no governance intervention required.")
    parts = []
    if s.tc01_phase == "engaged":
        parts.append(
            f"**TC-01 ENGAGED** — Active intervention. PXI = {s.PXI:.1f} < 70. "
            f"AAL = {c_AAL():.2f}, IF = {c_IF():.2f}. "
            f"Waiting for sustained PXI > {RECOVERY_PXI} "
            f"({s.tc01_stable_count}/{SUSTAINED_TICKS} ticks)."
        )
    elif s.tc01_phase == "stabilizing":
        parts.append(
            f"**TC-01 STABILIZING** — Recovery phase. PXI = {s.PXI:.1f}. "
            f"Releasing: AAL = {c_AAL():.2f} → 1.00, IF = {c_IF():.2f} → 1.00."
        )
    if s.tc02_phase == "engaged":
        parts.append(
            f"**TC-02 ENGAGED** — Active intervention. EXI = {s.EXI:.1f} < 65. "
            f"HOI = {c_HOI():.2f}, TR = {c_TR():.2f}. AAL unchanged. "
            f"Waiting for sustained EXI > {RECOVERY_EXI} "
            f"({s.tc02_stable_count}/{SUSTAINED_TICKS} ticks)."
        )
    elif s.tc02_phase == "stabilizing":
        parts.append(
            f"**TC-02 STABILIZING** — Recovery phase. EXI = {s.EXI:.1f}. "
            f"Releasing: HOI = {c_HOI():.2f} → 0.25, TR = {c_TR():.2f} → 0.50."
        )
    if s.tc03_active:
        gap = abs(s.PXI - s.EXI)
        parts.append(f"**TC-03 flagged** (|PXI − EXI| = {gap:.1f} > 15).")
    return "  \n\n".join(parts)


with st.sidebar:
    st.markdown("### Control Panel")
    if st.button("Generate one signal", use_container_width=True, type="primary"):
        generate_signal()
    auto_run = st.checkbox("Auto-run signals")
    speed = st.slider("Speed (sec/tick)", 0.3, 3.0, 0.8, 0.1) if auto_run else 0.8
    if st.button("Reset", use_container_width=True):
        reset_state()
        st.rerun()
    st.markdown("---")
    with st.expander("Lever Baselines"):
        st.markdown(f"""
        | Lever | Normal | Engaged | Release |
        | --- | --- | --- | --- |
        | **AAL** | 1.00 | 0.80 | +{RELEASE_AAL}/tick |
        | **HOI** | 0.25 | 1.00 | composite |
        | **IF**  | 1.00 | 1.20 | −{RELEASE_IF}/tick |
        | **TR**  | 0.50 | 1.00 | −{RELEASE_TR}/tick |
        """)
        st.caption(
            f"3-phase: NORMAL → ENGAGED → STABILIZING → NORMAL. "
            f"Release after {SUSTAINED_TICKS}-tick sustained recovery. "
            "HOI = 0.5·(1−penalty) + 0.5·rationale (composite of HOI-only + TR-shared)."
        )

st.markdown(
    "## HCEE Closed-Loop Dashboard "
    "<span class='badge'>S3 · Full HCEE · Multi-Temporal</span>",
    unsafe_allow_html=True
)
st.caption("Real-time experience signals → TC trigger → Governance lever adjustment")
ct1, ct2 = st.columns([3, 1])
with ct1:
    st.caption(f"Current Date / Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with ct2:
    st.caption(f"Tick: {st.session_state.tick}")

s = st.session_state

tab1, tab2, tab3, tab4 = st.tabs([
    "Real-time AI",
    "Weekly Surveys",
    "Daily Governance Loop",
    "Adaptive Learning"
])

with tab1:
    st.markdown("### Real-time AI Monitoring")
    st.caption("Hourly cadence · feeds TC-04 safety circuit breaker (Phase 2)")
    ai_errors_24h = int(max(0, (1 - c_AAL()) * 30 + np.random.poisson(2)))
    response_time = round(0.8 + (1 - c_AAL()) * 1.5, 2)
    intervention_rate = round((1 - c_AAL()) * 100, 1)
    safety_events = 1 if c_AAL() < 0.85 and np.random.random() < 0.15 else 0
    a = st.columns(4)
    a[0].metric("AI errors / 24h", ai_errors_24h)
    a[1].metric("Avg response time", f"{response_time}s")
    a[2].metric("Intervention rate", f"{intervention_rate}%")
    a[3].metric("Safety events", safety_events)
    if s.history:
        df_ai = pd.DataFrame(s.history[-30:])
        df_ai["AI_load"] = df_ai["AAL"] * 10
        fig_ai = go.Figure()
        fig_ai.add_trace(go.Bar(x=df_ai["tick"], y=df_ai["AI_load"],
                                marker_color=C_TITLE, name="AI operational load"))
        fig_ai.update_layout(height=240, margin=dict(l=20, r=20, t=20, b=30),
                             xaxis_title="tick", yaxis_title="load index",
                             paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                             showlegend=False,
                             font=dict(color=C_TITLE))
        st.plotly_chart(fig_ai, use_container_width=True)
    else:
        st.caption("(Generate signals to populate)")
    st.markdown(
        "<div class='placeholder'>"
        "<b>Phase 2 deployment:</b> Live EHR integration · AI module health monitoring · "
        "hourly anomaly detection feeding TC-04 safety circuit breaker. "
        "Current view shows simulated AI load derived from AAL state."
        "</div>", unsafe_allow_html=True
    )

with tab2:
    st.markdown("### Weekly Experience Surveys")
    st.caption("Weekly cadence · PROMs + employee pulse survey (Phase 2)")
    b = st.columns(4)
    b[0].metric("PXI (current week)", f"{s.PXI:.1f}")
    b[1].metric("EXI (current week)", f"{s.EXI:.1f}")
    b[2].metric("PROMs response rate", "68%")
    b[3].metric("Pulse coverage", "89%")
    if len(s.history) >= 7:
        df_w = pd.DataFrame(s.history)
        df_w["week"] = (df_w["tick"] - 1) // 7 + 1
        weekly = df_w.groupby("week").agg(PXI=("PXI", "mean"), EXI=("EXI", "mean")).reset_index()
        fig_w = go.Figure()
        fig_w.add_trace(go.Bar(x=weekly["week"], y=weekly["PXI"], name="PXI",
                               marker_color=C_PXI))
        fig_w.add_trace(go.Bar(x=weekly["week"], y=weekly["EXI"], name="EXI",
                               marker_color=C_EXI))
        fig_w.update_layout(height=260, margin=dict(l=20, r=20, t=20, b=30),
                            xaxis_title="week", yaxis_title="index",
                            barmode="group", paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                            font=dict(color=C_TITLE))
        st.plotly_chart(fig_w, use_container_width=True)
    else:
        st.caption(f"(Need at least 7 ticks to show weekly aggregates; currently {len(s.history)})")
    st.markdown(
        "<div class='placeholder'>"
        "<b>Phase 2 deployment:</b> PROMs auto-collection from patient discharge survey · "
        "weekly pulse survey integration · response rate monitoring · trend confirmation "
        "before TC trigger commitment. Current view shows weekly aggregates from simulated data."
        "</div>", unsafe_allow_html=True
    )

with tab3:
    st.markdown("### Daily Governance Loop")
    st.caption("Daily cadence · core closed-loop (TC-01/02/03)")
    m = st.columns(6)
    m[0].metric("PXI", f"{s.PXI:.2f}", f"{s.PXI - INIT_PXI:+.2f}")
    m[1].metric("EXI", f"{s.EXI:.2f}", f"{s.EXI - INIT_EXI:+.2f}")
    m[2].metric("AAL", f"{c_AAL():.2f}",
                f"{c_AAL() - CONCEPT_BASELINES['AAL']:+.2f}" if c_AAL() != CONCEPT_BASELINES['AAL'] else None)
    m[3].metric("HOI", f"{c_HOI():.2f}",
                f"{c_HOI() - CONCEPT_BASELINES['HOI']:+.2f}" if c_HOI() != CONCEPT_BASELINES['HOI'] else None)
    m[4].metric("IF",  f"{c_IF():.2f}",
                f"{c_IF() - CONCEPT_BASELINES['IF']:+.2f}" if c_IF() != CONCEPT_BASELINES['IF'] else None)
    m[5].metric("TR",  f"{c_TR():.2f}",
                f"{c_TR() - CONCEPT_BASELINES['TR']:+.2f}" if c_TR() != CONCEPT_BASELINES['TR'] else None)

    st.markdown("**Trigger Status**")
    html = ""
    for code, phase, desc in [("TC-01", s.tc01_phase, "PXI < 70"),
                              ("TC-02", s.tc02_phase, "EXI < 65")]:
        if phase == "engaged":
            cls, label = "ton", "ENGAGED"
        elif phase == "stabilizing":
            cls, label = "tstab", "STABILIZING"
        else:
            cls, label = "toff", "NORMAL"
        html += f"<span class='tpill {cls}'>{code} · {label} · {desc}</span>"
    cls = "ton" if s.tc03_active else "toff"
    label = "ACTIVE" if s.tc03_active else "OFF"
    html += f"<span class='tpill {cls}'>TC-03 · {label} · |PXI−EXI| &gt; 15</span>"
    st.markdown(html, unsafe_allow_html=True)

    st.markdown("**System Interpretation**")
    st.info(interpretation())

    if s.history:
        df_p = pd.DataFrame(s.history)
        fig_p = go.Figure()
        fig_p.add_trace(go.Scatter(x=df_p["tick"], y=df_p["PXI"], name="PXI",
                                   line=dict(color=C_PXI, width=2.5),
                                   mode="lines+markers", marker=dict(size=5)))
        fig_p.add_trace(go.Scatter(x=df_p["tick"], y=df_p["EXI"], name="EXI",
                                   line=dict(color=C_EXI, width=2.5),
                                   mode="lines+markers", marker=dict(size=5)))
        fig_p.add_hline(y=TH_PXI, line_dash="dot", line_color=C_PXI, opacity=0.5,
                        annotation_text="PXI threshold (70)", annotation_position="right")
        fig_p.add_hline(y=TH_EXI, line_dash="dot", line_color=C_EXI, opacity=0.5,
                        annotation_text="EXI threshold (65)", annotation_position="right")
        fig_p.update_layout(height=340, margin=dict(l=20, r=20, t=30, b=30),
                            xaxis_title="tick", yaxis_title="index",
                            yaxis_range=[35, 100],
                            paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                            font=dict(color=C_TITLE),
                            legend=dict(orientation="h", y=1.1, x=0.0))
        st.plotly_chart(fig_p, use_container_width=True)

    if s.history:
        with st.expander("Trigger Change History"):
            df_h = pd.DataFrame(s.history[-20:])
            st.dataframe(df_h, use_container_width=True, hide_index=True)

with tab4:
    st.markdown("### Adaptive Learning")
    st.caption("Monthly cadence · pattern recognition · TC-05 meta-learning (Phase 3)")
    d = st.columns(4)
    d[0].metric("TC-01 activations", s.tc01_engagements)
    d[1].metric("TC-02 activations", s.tc02_engagements)
    if s.history:
        tot = len(s.history)
        eng_ticks = sum(1 for h in s.history if h["TC-01"] == "engaged" or h["TC-02"] == "engaged")
        eng_ratio = round(eng_ticks / tot * 100, 1) if tot > 0 else 0
        d[2].metric("Engaged ticks ratio", f"{eng_ratio}%")
    else:
        d[2].metric("Engaged ticks ratio", "—")
    d[3].metric("Total ticks", s.tick)

    if s.history and len(s.history) >= 5:
        df_l = pd.DataFrame(s.history)
        df_l["tc01_engaged"] = (df_l["TC-01"] == "engaged").astype(int)
        df_l["tc02_engaged"] = (df_l["TC-02"] == "engaged").astype(int)
        fig_l = go.Figure()
        fig_l.add_trace(go.Scatter(x=df_l["tick"], y=df_l["tc01_engaged"],
                                   name="TC-01 engaged", line=dict(color=C_PXI, shape="hv", width=2),
                                   fill="tozeroy"))
        fig_l.add_trace(go.Scatter(x=df_l["tick"], y=df_l["tc02_engaged"] * 0.7,
                                   name="TC-02 engaged", line=dict(color=C_EXI, shape="hv", width=2),
                                   fill="tozeroy"))
        fig_l.update_layout(height=200, margin=dict(l=20, r=20, t=20, b=30),
                            xaxis_title="tick", yaxis_title="engaged",
                            yaxis_range=[0, 1.2], yaxis_showticklabels=False,
                            paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                            font=dict(color=C_TITLE),
                            legend=dict(orientation="h", y=1.15, x=0.0))
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.caption("(Run more signals to see activation patterns)")

    st.markdown("**Policy Recommendations** (derived from observed patterns)")
    recs = []
    if s.tc01_engagements >= 3:
        recs.append("TC-01 has fired ≥3 times — consider raising AAL baseline review or "
                   "investigating upstream AI configuration.")
    if s.tc02_engagements >= 3:
        recs.append("TC-02 has fired ≥3 times — review staff workload patterns and AI "
                   "decision rationale clarity.")
    if s.tick >= 20 and s.tc01_engagements == 0 and s.tc02_engagements == 0:
        recs.append("No trigger activations observed — system may be over-stable. "
                   "Consider tightening thresholds for finer governance sensitivity.")
    if not recs:
        recs.append("Insufficient data for recommendations. Continue monitoring.")
    for r in recs:
        st.markdown(f"<div class='recommendation'>{r}</div>", unsafe_allow_html=True)

    st.markdown(
        "<div class='placeholder'>"
        "<b>Phase 3 deployment:</b> Cross-site benchmarking · AI-assisted threshold tuning · "
        "longitudinal pattern recognition · automated policy adjustment recommendations to "
        "governance committee. Current view shows simple counters and pattern flags."
        "</div>", unsafe_allow_html=True
    )

st.markdown("---")
fc1, fc2 = st.columns([3, 2])
with fc1:
    st.caption("(c) 2026 Minseong Kim. HCEE Trademark Application Pending")
    st.caption("KIPO 40-2026-0084368 / 40-2026-0084369 / 40-2026-0084370")
with fc2:
    st.caption("S3 Full HCEE · NetLogo v4 aligned · Multi-temporal architecture")
    st.caption("Based on Trigger-Control Rulebook (Table 4)")

if auto_run:
    time.sleep(speed)
    generate_signal()
    st.rerun()
