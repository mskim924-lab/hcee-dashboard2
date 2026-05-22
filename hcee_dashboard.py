"""
HCEE™ Closed-Loop Dashboard (v2 — NetLogo-aligned)
=====================================================
Real-time experience signals → TC trigger → Governance lever adjustment

This dashboard is rebuilt to exactly match:
- NetLogo v4 simulation model (HCEE_Governance_Simulation_v4_main.nlogox)
- Trigger-Control Rulebook (Table 4)
- Concept-Implementation Mapping Table

Key corrections vs. v1 prototype:
  • AAL baseline = 1.0 (not 0.6)
  • Sticky lever design: single SET, no auto-revert (TC Rule 단방향 고착)
  • TC-02 does NOT change AAL (matches rulebook: AAL: 변경 없음)
  • HOI is decomposed into penalty-coeff + rationale-prob (NetLogo variables)
  • S4 implements shock as error-mult=2.0 and adaptive learning as intensify-factor

How to run:
    pip install streamlit pandas numpy plotly
    streamlit run hcee_dashboard.py

Author: Minseong Kim (김민성)
HCEE™ Trademark Application Pending — KIPO 40-2026-0084368 / 0084369 / 0084370
"""

import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from datetime import datetime
import time

# =====================================================
#  PAGE CONFIG
# =====================================================
st.set_page_config(
    page_title="HCEE Closed-Loop Dashboard",
    layout="wide",
    initial_sidebar_state="expanded",
)

# =====================================================
#  CONSTANTS (from NetLogo v4 model)
# =====================================================
THRESHOLD_PXI = 70
THRESHOLD_EXI = 65
THRESHOLD_GAP = 15

# Baseline values — exactly matching NetLogo `setup` procedure (L123-127)
BASELINES = {
    "automation_level": 1.0,   # AAL — L123: set automation-level 1.0
    "interaction_mult": 1.0,   # IF base
    "penalty_coeff":    1.0,   # HOI component 1
    "rationale_prob":   0.5,   # HOI component 2 / TR
    "intensify_factor": 1.0,   # S4 adaptive amplification
    "error_mult":       1.0,   # baseline; S4 sets to 2.0
}

# Color scheme (matching the slide aesthetic)
COLOR_PXI    = "#5A7548"   # sage green
COLOR_EXI    = "#7A2E2E"   # burgundy
COLOR_TITLE  = "#3F4A35"   # dark olive
COLOR_BG     = "#F4F0E4"   # cream
COLOR_SUB    = "#7E776B"   # muted gray-brown
COLOR_TRIG_ON  = "#7A2E2E"
COLOR_TRIG_OFF = "#A8A398"

# Custom CSS for academic aesthetic
st.markdown(f"""
<style>
  .main {{ background-color: {COLOR_BG}; }}
  .stMetric label {{ color: {COLOR_SUB} !important; }}
  div[data-testid="stMetricValue"] {{ color: {COLOR_TITLE} !important; }}
  div[data-testid="stMetricDelta"] {{ font-size: 0.85em !important; }}
  .trigger-pill {{
    display: inline-block; padding: 4px 12px; border-radius: 12px;
    font-size: 0.85em; font-weight: 600; margin-right: 8px;
  }}
  .trigger-on {{ background: {COLOR_TRIG_ON}; color: white; }}
  .trigger-off {{ background: #E8E4D8; color: {COLOR_SUB}; }}
  .impl-card {{
    background: #FFFFFF; border: 1px solid #DCD6C6; border-radius: 6px;
    padding: 12px 14px; margin: 4px 0;
  }}
  .impl-label {{ font-size: 0.78em; color: {COLOR_SUB}; font-family: monospace; }}
  .impl-value {{ font-size: 1.4em; font-weight: 600; color: {COLOR_TITLE}; }}
  .impl-delta {{ font-size: 0.85em; color: {COLOR_TRIG_ON}; }}
</style>
""", unsafe_allow_html=True)

# =====================================================
#  SESSION STATE
# =====================================================
def reset_state(keep_scenario: bool = False):
    keep_s = st.session_state.get("scenario", 3) if keep_scenario else 3
    st.session_state.scenario        = keep_s
    st.session_state.tick            = 0
    # System indices (master paper §4: shared initial conditions PXI=69.88, EXI=65.10)
    st.session_state.PXI             = 69.88
    st.session_state.EXI             = 65.10
    # Implementation variables (NetLogo globals)
    st.session_state.automation_level = BASELINES["automation_level"]
    st.session_state.interaction_mult = BASELINES["interaction_mult"]
    st.session_state.penalty_coeff    = BASELINES["penalty_coeff"]
    st.session_state.rationale_prob   = BASELINES["rationale_prob"]
    st.session_state.intensify_factor = BASELINES["intensify_factor"]
    # Error multiplier (S4 starts at 2.0 — applied in setup-style at scenario switch)
    st.session_state.error_mult = 2.0 if keep_s == 4 else 1.0
    # 4-week intensify monitoring memory (S4)
    st.session_state.prev_pxi_4w = st.session_state.PXI
    st.session_state.prev_exi_4w = st.session_state.EXI
    # TC active flags
    st.session_state.tc01_active = False
    st.session_state.tc02_active = False
    st.session_state.tc03_active = False
    # History log
    st.session_state.history = []

if "scenario" not in st.session_state:
    reset_state()

# =====================================================
#  CONCEPTUAL LEVER COMPUTATION
#  (maps NetLogo implementation variables back to AAL / HOI / TR / IF)
# =====================================================
def conceptual_AAL():
    return st.session_state.automation_level

def conceptual_IF():
    return st.session_state.interaction_mult

def conceptual_HOI():
    """HOI = 0.5·(1 − penalty_coeff) + 0.5·rationale_prob
       Baseline 0.25 → after TC-02 fires (S3/S4): 1.00 (max oversight)."""
    s = st.session_state
    return 0.5 * (1.0 - s.penalty_coeff) + 0.5 * s.rationale_prob

def conceptual_TR():
    """TR is represented in v4 by rationale-prob (AI rationale display)."""
    return st.session_state.rationale_prob

# =====================================================
#  SIGNAL GENERATION
#  Simplified stochastic dynamics that mirror NetLogo causal directions.
#  (Not a full ABM replacement — a governance demonstrator.)
# =====================================================
def generate_signal():
    s = st.session_state
    s.tick += 1

    # ── Compute drift in PXI / EXI ──
    err_pressure_pxi   = -1.4 * s.automation_level * s.error_mult
    interaction_boost  = +6.0 * (s.interaction_mult - 1.0)
    intensify_boost    = +3.5 * (s.intensify_factor - 1.0)

    penalty_burden_exi = -0.9 * s.penalty_coeff
    rationale_relief   = +3.5 * (s.rationale_prob - 0.5)

    # Mean-reversion toward scenario equilibrium
    if s.scenario == 1:        eq_pxi, eq_exi = 58.0, 52.0   # S1 reference baseline
    elif s.scenario == 2:      eq_pxi, eq_exi = 65.5, 61.0   # S2 partial HCEE
    else:                      eq_pxi, eq_exi = 78.3, 74.5   # S3/S4 full HCEE
    revert_pxi = (eq_pxi - s.PXI) * 0.08
    revert_exi = (eq_exi - s.EXI) * 0.08

    noise_pxi = np.random.normal(0, 1.8)
    noise_exi = np.random.normal(0, 1.8)

    s.PXI += err_pressure_pxi + interaction_boost + intensify_boost + revert_pxi + noise_pxi
    s.EXI += penalty_burden_exi + rationale_relief + intensify_boost + revert_exi + noise_exi
    s.PXI = float(np.clip(s.PXI, 35, 100))
    s.EXI = float(np.clip(s.EXI, 35, 100))

    # ── Apply TC rules (sticky, NetLogo v4) ──
    apply_tc_rules()

    # ── S4 adaptive intensification (every 4 ticks) ──
    if s.scenario == 4 and s.tick % 4 == 0 and s.tick > 0:
        adaptive_intensify()

    # ── Record history ──
    s.history.append({
        "tick": s.tick,
        "time": datetime.now().strftime("%H:%M:%S"),
        "PXI": round(s.PXI, 2),
        "EXI": round(s.EXI, 2),
        "AAL": round(conceptual_AAL(), 2),
        "HOI": round(conceptual_HOI(), 2),
        "IF":  round(conceptual_IF(), 2),
        "TR":  round(conceptual_TR(), 2),
        "trigger": tc_status_string(),
        "action": describe_last_action(),
    })

def apply_tc_rules():
    """NetLogo v4 TC rules — sticky design (단방향 고착).
       Once a lever drops, it does NOT auto-revert when PXI/EXI recover."""
    s = st.session_state

    # TC-01: PXI < 70
    if s.PXI < THRESHOLD_PXI and not s.tc01_active:
        s.tc01_active = True
        if s.scenario >= 3:
            s.automation_level = 0.80      # NetLogo L503
            s.interaction_mult = 1.20      # NetLogo L504
        elif s.scenario == 2:
            s.automation_level = 0.90      # NetLogo L509
            s.interaction_mult = 1.05

    # TC-02: EXI < 65  (does NOT change AAL — important difference from v1 dashboard)
    if s.EXI < THRESHOLD_EXI and not s.tc02_active:
        s.tc02_active = True
        if s.scenario >= 3:
            s.penalty_coeff  = 0.0         # NetLogo L529
            s.rationale_prob = 1.0         # NetLogo L530
        elif s.scenario == 2:
            s.rationale_prob = 0.75        # NetLogo L533

    # TC-03: |PXI − EXI| > 15 (status flag; cross-rebalancing handled by TC-01/02 firing)
    s.tc03_active = (abs(s.PXI - s.EXI) > THRESHOLD_GAP)

def adaptive_intensify():
    """S4-only: 4-week monitoring window adjusts intensify-factor toward max 1.5."""
    s = st.session_state
    expected = 2.0
    pxi_gain = s.PXI - s.prev_pxi_4w
    exi_gain = s.EXI - s.prev_exi_4w

    if s.tc01_active and pxi_gain < expected:
        s.intensify_factor = min(1.5, s.intensify_factor + 0.10)
    if s.tc02_active and exi_gain < expected:
        s.intensify_factor = min(1.5, s.intensify_factor + 0.05)
    if (not s.tc01_active) and pxi_gain >= 0:
        s.intensify_factor = max(1.0, s.intensify_factor - 0.05)

    s.prev_pxi_4w = s.PXI
    s.prev_exi_4w = s.EXI

def tc_status_string():
    s = st.session_state
    active = []
    if s.tc01_active: active.append("TC-01")
    if s.tc02_active: active.append("TC-02")
    if s.tc03_active: active.append("TC-03")
    return ", ".join(active) if active else "OFF"

def describe_last_action():
    s = st.session_state
    if not (s.tc01_active or s.tc02_active or s.tc03_active):
        return "Normal operation"
    parts = []
    if s.tc01_active: parts.append("AAL↓ + IF↑")
    if s.tc02_active: parts.append("HOI↑ (penalty↓·rationale↑)")
    if s.tc03_active: parts.append("Cross-gap flagged")
    return " | ".join(parts)

def generate_interpretation():
    s = st.session_state
    if not (s.tc01_active or s.tc02_active or s.tc03_active):
        return "🟢 **Normal operation.** System operating within target band. PXI ≥ 70 and EXI ≥ 65; no triggers active."

    parts = []
    if s.tc01_active:
        parts.append(
            f"🔴 **TC-01 active** (PXI = {s.PXI:.1f} < 70). "
            f"System reduced AAL to {s.automation_level:.2f} and increased IF to {s.interaction_mult:.2f} "
            f"to alleviate AI-driven patient burden."
        )
    if s.tc02_active:
        parts.append(
            f"🔴 **TC-02 active** (EXI = {s.EXI:.1f} < 65). "
            f"System reduced penalty-coeff to {s.penalty_coeff:.2f} and increased rationale-prob to "
            f"{s.rationale_prob:.2f} to strengthen human oversight. (AAL unchanged — EXI is workload-driven.)"
        )
    if s.tc03_active:
        gap = abs(s.PXI - s.EXI)
        parts.append(
            f"🟡 **TC-03 flagged** (|PXI − EXI| = {gap:.1f} > 15). "
            f"Cross-domain imbalance; rebalancing carried by TC-01/02 levers."
        )
    if s.scenario == 4 and s.intensify_factor > 1.0:
        parts.append(
            f"🔵 **Adaptive intensification active** (intensify-factor = {s.intensify_factor:.2f}). "
            f"4-week learning loop amplifying recovery response."
        )
    return "  \n\n".join(parts)

# =====================================================
#  SIDEBAR — CONTROL PANEL
# =====================================================
with st.sidebar:
    st.markdown(f"### Control Panel")

    scenario_options = {
        1: "S1 — No Governance",
        2: "S2 — Partial HCEE (sense-only)",
        3: "S3 — Full HCEE (closed loop)",
        4: "S4 — Stress Test (S3 + shock)",
    }
    new_scenario = st.selectbox(
        "Scenario",
        options=list(scenario_options.keys()),
        format_func=lambda k: scenario_options[k],
        index=list(scenario_options.keys()).index(st.session_state.scenario),
    )
    if new_scenario != st.session_state.scenario:
        st.session_state.scenario = new_scenario
        reset_state(keep_scenario=True)
        st.rerun()

    st.markdown("---")
    if st.button("Generate one signal", use_container_width=True, type="primary"):
        generate_signal()

    auto_run = st.checkbox("Auto-run real-time signals")
    if auto_run:
        speed = st.slider("Speed (sec/tick)", 0.3, 3.0, 1.0, 0.1)
    else:
        speed = 1.0

    st.markdown("---")
    if st.button("Reset", use_container_width=True):
        reset_state(keep_scenario=True)
        st.rerun()

    st.markdown("---")
    with st.expander("ⓘ Baselines (NetLogo v4)"):
        st.markdown(f"""
        | Variable | Baseline |
        | --- | --- |
        | `automation-level` | 1.00 |
        | `interaction-mult` | 1.00 |
        | `penalty-coeff` | 1.00 |
        | `rationale-prob` | 0.50 |
        | `intensify-factor` | 1.00 |
        | `error-mult` (S4) | 2.00 |
        """)
        st.caption("Sticky design: levers do not auto-revert on PXI/EXI recovery.")

# =====================================================
#  MAIN — HEADER
# =====================================================
st.markdown(f"## HCEE™ Closed-Loop Dashboard")
st.caption("Real-time experience signals → TC trigger → Governance lever adjustment")
col_time, col_tick = st.columns([3, 1])
with col_time:
    st.caption(f"Current Date / Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with col_tick:
    st.caption(f"Tick: {st.session_state.tick} / Scenario: {scenario_options[st.session_state.scenario].split(' — ')[0]}")

# =====================================================
#  CONCEPTUAL LEVER VIEW (top metrics, matches original layout)
# =====================================================
st.markdown("### Conceptual Lever View")
s = st.session_state
mcols = st.columns(6)
mcols[0].metric("PXI",  f"{s.PXI:.2f}",            f"{s.PXI - 69.88:+.2f}")
mcols[1].metric("EXI",  f"{s.EXI:.2f}",            f"{s.EXI - 65.10:+.2f}")
mcols[2].metric("AAL",  f"{conceptual_AAL():.2f}", f"{conceptual_AAL() - 1.0:+.2f}" if conceptual_AAL() != 1.0 else None)
mcols[3].metric("HOI",  f"{conceptual_HOI():.2f}", f"{conceptual_HOI() - 0.25:+.2f}" if conceptual_HOI() != 0.25 else None)
mcols[4].metric("TR",   f"{conceptual_TR():.2f}",  f"{conceptual_TR() - 0.5:+.2f}"  if conceptual_TR()  != 0.5 else None)
mcols[5].metric("IF",   f"{conceptual_IF():.2f}",  f"{conceptual_IF() - 1.0:+.2f}"  if conceptual_IF()  != 1.0 else None)

# =====================================================
#  IMPLEMENTATION VARIABLE DETAIL (NetLogo globals)
# =====================================================
with st.expander("🔬 Implementation variables (NetLogo v4 globals)"):
    icols = st.columns(6)
    impl = [
        ("automation-level", s.automation_level, 1.0,  "L50, L123"),
        ("interaction-mult", s.interaction_mult, 1.0,  "L51, L124"),
        ("penalty-coeff",    s.penalty_coeff,    1.0,  "L52, L125"),
        ("rationale-prob",   s.rationale_prob,   0.5,  "L53, L126"),
        ("intensify-factor", s.intensify_factor, 1.0,  "L60, L127"),
        ("error-mult",       s.error_mult,       1.0,  "L54, L139-140"),
    ]
    for i, (name, val, base, loc) in enumerate(impl):
        delta = val - base
        delta_str = f"{delta:+.2f}" if abs(delta) > 1e-6 else "—"
        icols[i].markdown(
            f"<div class='impl-card'>"
            f"<div class='impl-label'>{name}</div>"
            f"<div class='impl-value'>{val:.2f}</div>"
            f"<div class='impl-delta'>{delta_str}</div>"
            f"<div class='impl-label' style='font-size:0.72em;margin-top:6px'>{loc}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

# =====================================================
#  TRIGGER STATUS
# =====================================================
st.markdown("### Trigger Status")
trig_html = ""
for code, active, desc in [
    ("TC-01", s.tc01_active, "PXI < 70"),
    ("TC-02", s.tc02_active, "EXI < 65"),
    ("TC-03", s.tc03_active, "|PXI−EXI| > 15"),
]:
    cls = "trigger-on" if active else "trigger-off"
    trig_html += f"<span class='trigger-pill {cls}'>{code}  ·  {desc}</span>"
if s.scenario == 4:
    trig_html += f"<span class='trigger-pill trigger-on'>S4 Shock · error-mult = {s.error_mult:.1f}</span>"
st.markdown(trig_html, unsafe_allow_html=True)

# =====================================================
#  SYSTEM INTERPRETATION
# =====================================================
st.markdown("### System Interpretation")
st.info(generate_interpretation())

# =====================================================
#  HISTORY LOG
# =====================================================
st.markdown("### Trigger Change History")
if s.history:
    df_hist = pd.DataFrame(s.history[-25:])
    st.dataframe(
        df_hist,
        use_container_width=True,
        hide_index=True,
        column_config={
            "tick":   st.column_config.NumberColumn(width="small"),
            "time":   st.column_config.TextColumn(width="small"),
            "PXI":    st.column_config.NumberColumn(format="%.2f"),
            "EXI":    st.column_config.NumberColumn(format="%.2f"),
            "AAL":    st.column_config.NumberColumn(format="%.2f"),
            "HOI":    st.column_config.NumberColumn(format="%.2f"),
            "IF":     st.column_config.NumberColumn(format="%.2f"),
            "TR":     st.column_config.NumberColumn(format="%.2f"),
        }
    )
else:
    st.caption("No signals yet. Click **Generate one signal** to begin.")

# =====================================================
#  PXI / EXI TIME SERIES PLOT
# =====================================================
if s.history:
    st.markdown("### PXI / EXI Over Time")
    df_plot = pd.DataFrame(s.history)
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=df_plot["tick"], y=df_plot["PXI"], name="PXI",
        line=dict(color=COLOR_PXI, width=2.5), mode="lines+markers", marker=dict(size=5)
    ))
    fig.add_trace(go.Scatter(
        x=df_plot["tick"], y=df_plot["EXI"], name="EXI",
        line=dict(color=COLOR_EXI, width=2.5), mode="lines+markers", marker=dict(size=5)
    ))
    fig.add_hline(y=THRESHOLD_PXI, line_dash="dot", line_color=COLOR_PXI,
                  opacity=0.5, annotation_text="PXI threshold (70)", annotation_position="right")
    fig.add_hline(y=THRESHOLD_EXI, line_dash="dot", line_color=COLOR_EXI,
                  opacity=0.5, annotation_text="EXI threshold (65)", annotation_position="right")
    fig.update_layout(
        height=380, margin=dict(l=20, r=20, t=30, b=30),
        xaxis_title="tick", yaxis_title="index",
        yaxis_range=[35, 100],
        paper_bgcolor=COLOR_BG, plot_bgcolor="#FFFFFF",
        font=dict(family="Malgun Gothic, sans-serif", color=COLOR_TITLE),
        legend=dict(orientation="h", y=1.1, x=0.0),
    )
    st.plotly_chart(fig, use_container_width=True)

# =====================================================
#  S4 THREE-PHASE DYNAMICS INDICATOR
# =====================================================
if s.scenario == 4 and s.tick > 0:
    st.markdown("### S4 Three-Phase Dynamics")
    if s.tick <= 4:
        phase = "I. Disruption"
        desc = "Shock impact; PXI/EXI declining"
    elif s.PXI < 78 or s.EXI < 70:
        phase = "II. Rapid Recovery"
        desc = "TC-01/02 active; closed-loop response"
    else:
        phase = "III. Re-stabilization"
        desc = "Adaptive intensification; new attractor"
    st.success(f"**Current phase: {phase}**  ·  {desc}")

# =====================================================
#  FOOTER
# =====================================================
st.markdown("---")
fcol1, fcol2 = st.columns([3, 2])
with fcol1:
    st.caption("© 2026 Minseong Kim. HCEE™ Trademark Application Pending")
    st.caption("KIPO 40-2026-0084368 / 40-2026-0084369 / 40-2026-0084370")
with fcol2:
    st.caption("v2 — NetLogo v4 aligned")
    st.caption("Based on Trigger-Control Rulebook (Table 4)")

# =====================================================
#  AUTO-RUN LOOP
# =====================================================
if auto_run:
    time.sleep(speed)
    generate_signal()
    st.rerun()
