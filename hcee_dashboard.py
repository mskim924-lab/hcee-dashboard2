"""HCEE Closed-Loop Dashboard (S3 Full HCEE)
Real-time experience signals -> TC trigger -> Governance lever adjustment.
Implements S3 from NetLogo v4 simulation and Table 4 rulebook.

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
SUSTAINED_TICKS = 5
RELEASE_AAL = 0.05
RELEASE_IF = 0.05
RELEASE_HOI = 0.25
RELEASE_TR = 0.125
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

st.markdown(f"""<style>
.main {{ background-color: {C_BG}; }}
.stMetric label {{ color: {C_SUB} !important; }}
div[data-testid="stMetricValue"] {{ color: {C_TITLE} !important; }}
div[data-testid="stMetricDelta"] {{ font-size: 0.85em !important; }}
.tpill {{ display: inline-block; padding: 5px 13px; border-radius: 12px;
  font-size: 0.88em; font-weight: 600; margin-right: 8px; }}
.ton  {{ background: {C_ON}; color: white; }}
.tstab {{ background: #B4953C; color: white; }}
.toff {{ background: #E8E4D8; color: {C_SUB}; }}
.icard {{ background: #FFFFFF; border: 1px solid #DCD6C6;
  border-radius: 6px; padding: 12px 14px; }}
.ilabel {{ font-size: 0.78em; color: {C_SUB}; font-family: monospace; }}
.ival {{ font-size: 1.4em; font-weight: 600; color: {C_TITLE}; }}
.idelta {{ font-size: 0.85em; color: {C_ON}; }}
.iloc {{ font-size: 0.72em; color: {C_SUB}; font-family: monospace; margin-top: 6px; }}
.badge {{ display: inline-block; padding: 3px 10px; border-radius: 4px;
  background: {C_TITLE}; color: white; font-size: 0.78em;
  font-weight: 600; margin-left: 8px; vertical-align: middle; }}
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


def trigger_string():
    s = st.session_state
    a = []
    if s.tc01_active: a.append("TC-01")
    if s.tc02_active: a.append("TC-02")
    if s.tc03_active: a.append("TC-03")
    return ", ".join(a) if a else "OFF"


def last_action():
    s = st.session_state
    parts = []
    if s.tc01_phase == "engaged":
        parts.append("TC-01 ENGAGED (AAL down, IF up)")
    elif s.tc01_phase == "stabilizing":
        parts.append("TC-01 releasing")
    if s.tc02_phase == "engaged":
        parts.append("TC-02 ENGAGED (HOI up)")
    elif s.tc02_phase == "stabilizing":
        parts.append("TC-02 releasing")
    if s.tc03_active:
        parts.append("TC-03 flagged")
    return " | ".join(parts) if parts else "Normal operation"


def interpretation():
    s = st.session_state
    if s.tc01_phase == "normal" and s.tc02_phase == "normal" and not s.tc03_active:
        return ("Normal operation. PXI >= 70 and EXI >= 65. "
                "All levers at baseline; no governance intervention required.")

    parts = []
    if s.tc01_phase == "engaged":
        parts.append(
            f"**TC-01 ENGAGED** - Active intervention. PXI = {s.PXI:.1f} < 70. "
            f"AAL = {c_AAL():.2f}, IF = {c_IF():.2f}. "
            f"Waiting for sustained PXI > {RECOVERY_PXI} to start release. "
            f"(Stable ticks so far: {s.tc01_stable_count}/{SUSTAINED_TICKS})"
        )
    elif s.tc01_phase == "stabilizing":
        parts.append(
            f"**TC-01 STABILIZING** - Recovery phase. PXI = {s.PXI:.1f} sustained above "
            f"{RECOVERY_PXI}. Levers gradually releasing: AAL = {c_AAL():.2f} -> 1.00, "
            f"IF = {c_IF():.2f} -> 1.00."
        )

    if s.tc02_phase == "engaged":
        parts.append(
            f"**TC-02 ENGAGED** - Active intervention. EXI = {s.EXI:.1f} < 65. "
            f"HOI = {c_HOI():.2f}, TR = {c_TR():.2f}. AAL unchanged. "
            f"Waiting for sustained EXI > {RECOVERY_EXI} to start release. "
            f"(Stable ticks so far: {s.tc02_stable_count}/{SUSTAINED_TICKS})"
        )
    elif s.tc02_phase == "stabilizing":
        parts.append(
            f"**TC-02 STABILIZING** - Recovery phase. EXI = {s.EXI:.1f} sustained above "
            f"{RECOVERY_EXI}. HOI = {c_HOI():.2f} -> 0.25, TR = {c_TR():.2f} -> 0.50 "
            "gradually returning to baseline."
        )

    if s.tc03_active:
        gap = abs(s.PXI - s.EXI)
        parts.append(
            f"**TC-03 flagged** (|PXI - EXI| = {gap:.1f} > 15). "
            "Cross-domain imbalance; rebalancing carried by TC-01/02 levers."
        )
    return "  \n\n".join(parts)


with st.sidebar:
    st.markdown("### Control Panel")
    if st.button("Generate one signal", use_container_width=True, type="primary"):
        generate_signal()
    auto_run = st.checkbox("Auto-run real-time signals")
    speed = st.slider("Speed (sec/tick)", 0.3, 3.0, 1.0, 0.1) if auto_run else 1.0
    if st.button("Reset", use_container_width=True):
        reset_state()
        st.rerun()
    st.markdown("---")
    with st.expander("Lever Baselines"):
        st.markdown(f"""
        | Lever | Normal | Engaged | Release Rate |
        | --- | --- | --- | --- |
        | **AAL** | 1.00 | 0.80 | +{RELEASE_AAL}/tick |
        | **HOI** | 0.25 | 1.00 | composite (see below) |
        | **IF**  | 1.00 | 1.20 | −{RELEASE_IF}/tick |
        | **TR**  | 0.50 | 1.00 | −{RELEASE_TR}/tick |
        """)
        st.caption(
            "Three-phase lifecycle: NORMAL → ENGAGED → STABILIZING → NORMAL. "
            f"Release starts after sustained recovery ({SUSTAINED_TICKS} ticks above "
            f"PXI={RECOVERY_PXI} or EXI={RECOVERY_EXI}). "
            "Note on HOI: HOI is composite of two sub-components — "
            f"the HOI-exclusive part releases at {RELEASE_HOI}/tick, and the "
            f"TR-shared part releases at {RELEASE_TR}/tick. Both must reach baseline for HOI = 0.25. "
            "AAL = AI Autonomy Level; HOI = Human Oversight Intensity; "
            "IF = Information Flow; TR = Trust Recalibration."
        )

st.markdown(
    "## HCEE Closed-Loop Dashboard "
    "<span class='badge'>S3 - Full HCEE</span>",
    unsafe_allow_html=True
)
st.caption("Real-time experience signals -> TC trigger -> Governance lever adjustment")
ct1, ct2 = st.columns([3, 1])
with ct1:
    st.caption(f"Current Date / Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with ct2:
    st.caption(f"Tick: {st.session_state.tick}")

s = st.session_state
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

st.markdown("### Trigger Status")
html = ""
for code, phase, desc in [("TC-01", s.tc01_phase, "PXI < 70"),
                          ("TC-02", s.tc02_phase, "EXI < 65")]:
    if phase == "engaged":
        cls, label = "ton", "ENGAGED"
    elif phase == "stabilizing":
        cls, label = "tstab", "STABILIZING"
    else:
        cls, label = "toff", "NORMAL"
    html += f"<span class='tpill {cls}'>{code}  .  {label}  .  {desc}</span>"
cls = "ton" if s.tc03_active else "toff"
label = "ACTIVE" if s.tc03_active else "OFF"
html += f"<span class='tpill {cls}'>TC-03  .  {label}  .  |PXI - EXI| &gt; 15</span>"
st.markdown(html, unsafe_allow_html=True)

st.markdown("### System Interpretation")
st.info(interpretation())

st.markdown("### Trigger Change History")
if s.history:
    df = pd.DataFrame(s.history[-25:])
    st.dataframe(df, use_container_width=True, hide_index=True,
                 column_config={
                     "tick": st.column_config.NumberColumn(width="small"),
                     "time": st.column_config.TextColumn(width="small"),
                     "PXI":  st.column_config.NumberColumn(format="%.2f"),
                     "EXI":  st.column_config.NumberColumn(format="%.2f"),
                     "AAL":  st.column_config.NumberColumn(format="%.2f"),
                     "HOI":  st.column_config.NumberColumn(format="%.2f"),
                     "IF":   st.column_config.NumberColumn(format="%.2f"),
                     "TR":   st.column_config.NumberColumn(format="%.2f"),
                 })
else:
    st.caption("No signals yet. Click 'Generate one signal' to begin.")

if s.history:
    st.markdown("### PXI / EXI Over Time")
    dfp = pd.DataFrame(s.history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=dfp["tick"], y=dfp["PXI"], name="PXI",
                             line=dict(color=C_PXI, width=2.5),
                             mode="lines+markers", marker=dict(size=5)))
    fig.add_trace(go.Scatter(x=dfp["tick"], y=dfp["EXI"], name="EXI",
                             line=dict(color=C_EXI, width=2.5),
                             mode="lines+markers", marker=dict(size=5)))
    fig.add_hline(y=TH_PXI, line_dash="dot", line_color=C_PXI, opacity=0.5,
                  annotation_text="PXI threshold (70)", annotation_position="right")
    fig.add_hline(y=TH_EXI, line_dash="dot", line_color=C_EXI, opacity=0.5,
                  annotation_text="EXI threshold (65)", annotation_position="right")
    fig.update_layout(height=380, margin=dict(l=20, r=20, t=30, b=30),
                      xaxis_title="tick", yaxis_title="index",
                      yaxis_range=[35, 100],
                      paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                      font=dict(family="Malgun Gothic, sans-serif", color=C_TITLE),
                      legend=dict(orientation="h", y=1.1, x=0.0))
    st.plotly_chart(fig, use_container_width=True)

st.markdown("---")
fc1, fc2 = st.columns([3, 2])
with fc1:
    st.caption("(c) 2026 Minseong Kim. HCEE Trademark Application Pending")
    st.caption("KIPO 40-2026-0084368 / 40-2026-0084369 / 40-2026-0084370")
with fc2:
    st.caption("S3 Full HCEE - NetLogo v4 aligned")
    st.caption("Based on Trigger-Control Rulebook (Table 4)")

if auto_run:
    time.sleep(speed)
    generate_signal()
    st.rerun()
