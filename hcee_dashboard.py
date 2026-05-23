"""HCEE Closed-Loop Dashboard (S3 Full HCEE) - Multi-Temporal View
Real-time experience signals -> TC trigger -> Governance lever adjustment.

Multi-temporal architecture (4 tabs):
  Tab 1: Daily Governance Loop (core closed-loop, TC-01/02/03)
  Tab 2: Weekly Experience Surveys (PROMs source layer)
  Tab 3: Real-time AI Monitoring (operational consequence)
  Tab 4: Adaptive Learning (longitudinal patterns)

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

# ===== Parameters =====
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

# ===== Colors =====
C_PXI, C_EXI = "#5A7548", "#7A2E2E"
C_TC03 = "#8B6A3A"
C_TITLE, C_BG, C_SUB, C_ON = "#3F4A35", "#F4F0E4", "#7E776B", "#7A2E2E"
C_STAB = "#B4953C"

# ===== CSS =====
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
.bil-title-en {{
  font-size: 1.7em; font-weight: 600; color: {C_TITLE};
  margin-bottom: 0px; line-height: 1.2;
}}
.bil-title-kr {{
  font-size: 0.75em; color: {C_SUB};
  margin-top: 0px; margin-bottom: 6px; line-height: 1.2;
}}
.bil-h3-en {{
  font-size: 1.18em; font-weight: 600; color: {C_TITLE};
  margin-top: 14px; margin-bottom: 1px; line-height: 1.3;
}}
.bil-h3-kr {{
  font-size: 0.78em; color: {C_SUB};
  margin-bottom: 8px; line-height: 1.3;
}}
.bil-cap-en {{
  font-size: 0.86em; color: {C_SUB};
  margin-bottom: 1px; line-height: 1.4;
}}
.bil-cap-kr {{
  font-size: 0.74em; color: {C_SUB}; opacity: 0.82;
  margin-bottom: 10px; line-height: 1.3;
}}
.bil-label-en {{
  font-size: 1em; font-weight: 600; color: {C_TITLE};
  margin-top: 10px; margin-bottom: 0px;
}}
.bil-label-kr {{
  font-size: 0.74em; color: {C_SUB};
  margin-bottom: 6px; line-height: 1.2;
}}
.analysis-box {{
  background: linear-gradient(135deg, #FAF6E8 0%, #F4F0E4 100%);
  border: 2px solid {C_STAB};
  border-left: 6px solid {C_STAB};
  border-radius: 8px;
  padding: 12px 18px;
  margin: 18px 0;
}}
.analysis-box summary {{
  font-weight: 600;
  font-size: 1.05em;
  color: {C_TITLE};
  cursor: pointer;
  padding: 4px 0;
  outline: none;
  list-style: none;
}}
.analysis-box summary::-webkit-details-marker {{ display: none; }}
.analysis-box summary::after {{
  content: " ▼ click to expand";
  font-size: 0.72em;
  font-weight: 400;
  color: {C_STAB};
  margin-left: 12px;
}}
.analysis-box[open] summary::after {{ content: " ▲ collapse"; }}
.analysis-box summary:hover {{ color: {C_ON}; }}
.analysis-content {{
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #D8C99A;
}}
.analysis-section {{ margin-bottom: 14px; }}
.analysis-section:last-child {{ margin-bottom: 0; }}
.analysis-section-title {{
  font-weight: 600;
  font-size: 0.92em;
  color: {C_TITLE};
  margin-bottom: 5px;
}}
.analysis-en {{
  font-size: 0.86em;
  color: {C_TITLE};
  margin-bottom: 4px;
  line-height: 1.5;
}}
.analysis-kr {{
  font-size: 0.78em;
  color: {C_SUB};
  line-height: 1.4;
  padding-left: 12px;
  border-left: 2px solid #C9B68A;
  margin-bottom: 4px;
}}
.analysis-rec {{
  background: rgba(255, 255, 255, 0.5);
  border-radius: 4px;
  padding: 8px 12px;
  margin-bottom: 8px;
}}
</style>""", unsafe_allow_html=True)


# ===== Bilingual helpers =====
def bil_title(en, kr, badge=""):
    st.markdown(
        f"<div class='bil-title-en'>{en}{badge}</div>"
        f"<div class='bil-title-kr'>{kr}</div>",
        unsafe_allow_html=True
    )

def bil_h3(en, kr):
    st.markdown(
        f"<div class='bil-h3-en'>{en}</div>"
        f"<div class='bil-h3-kr'>{kr}</div>",
        unsafe_allow_html=True
    )

def bil_caption(en, kr):
    st.markdown(
        f"<div class='bil-cap-en'>{en}</div>"
        f"<div class='bil-cap-kr'>{kr}</div>",
        unsafe_allow_html=True
    )

def bil_label(en, kr):
    st.markdown(
        f"<div class='bil-label-en'>{en}</div>"
        f"<div class='bil-label-kr'>{kr}</div>",
        unsafe_allow_html=True
    )


# ===== State =====
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
    st.session_state.tc03_engagements = 0
    st.session_state.history = []

if "tick" not in st.session_state:
    reset_state()


# ===== Conceptual levers =====
def c_AAL(): return st.session_state.automation_level
def c_IF():  return st.session_state.interaction_mult
def c_HOI():
    s = st.session_state
    return 0.5 * (1.0 - s.penalty_coeff) + 0.5 * s.rationale_prob
def c_TR():  return st.session_state.rationale_prob


# ===== Signal dynamics =====
def generate_signal():
    s = st.session_state
    s.tick += 1
    pxi_target = 72 + (1 - s.automation_level) * 15.75 + (s.interaction_mult - 1) * 15.75
    exi_target = 67 + (1 - s.penalty_coeff) * 5 + (s.rationale_prob - 0.5) * 5
    s.PXI = float(np.clip(s.PXI + (pxi_target - s.PXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    s.EXI = float(np.clip(s.EXI + (exi_target - s.EXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    apply_tc_rules()
    s.history.append({
        "tick":  s.tick,
        "time":  datetime.now().strftime("%H:%M:%S"),
        "PXI":   round(s.PXI, 2), "EXI": round(s.EXI, 2),
        "AAL":   round(c_AAL(), 2), "HOI": round(c_HOI(), 2),
        "IF":    round(c_IF(), 2),  "TR":  round(c_TR(), 2),
        "TC-01": s.tc01_phase,
        "TC-02": s.tc02_phase,
        "TC-03": "active" if s.tc03_active else "off",
        "action": last_action(),
    })


def force_exi_shock(magnitude=15):
    """Demo-only: drop EXI by magnitude to demonstrate TC-3 activation
    (cross-domain divergence scenario)."""
    s = st.session_state
    s.tick += 1
    pxi_target = 72 + (1 - s.automation_level) * 15.75 + (s.interaction_mult - 1) * 15.75
    s.PXI = float(np.clip(s.PXI + (pxi_target - s.PXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    s.EXI = float(np.clip(s.EXI - magnitude, 35, 100))
    apply_tc_rules()
    s.history.append({
        "tick":  s.tick,
        "time":  datetime.now().strftime("%H:%M:%S"),
        "PXI":   round(s.PXI, 2), "EXI": round(s.EXI, 2),
        "AAL":   round(c_AAL(), 2), "HOI": round(c_HOI(), 2),
        "IF":    round(c_IF(), 2),  "TR":  round(c_TR(), 2),
        "TC-01": s.tc01_phase,
        "TC-02": s.tc02_phase,
        "TC-03": "active" if s.tc03_active else "off",
        "action": f"EXI SHOCK -{magnitude} (demo) | {last_action()}",
    })


def apply_tc_rules():
    s = st.session_state

    # TC-01 phase machine
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

    # TC-02 phase machine
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

    # TC-03 status flag (binary; track transitions)
    prev_tc03 = s.tc03_active
    s.tc01_active = (s.tc01_phase == "engaged")
    s.tc02_active = (s.tc02_phase == "engaged")
    s.tc03_active = abs(s.PXI - s.EXI) > TH_GAP
    if s.tc03_active and not prev_tc03:
        s.tc03_engagements += 1


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
            f"**TC-01 ENGAGED** - Active intervention. PXI = {s.PXI:.1f} < 70. "
            f"AAL = {c_AAL():.2f}, IF = {c_IF():.2f}. "
            f"Waiting for sustained PXI > {RECOVERY_PXI} "
            f"({s.tc01_stable_count}/{SUSTAINED_TICKS} ticks)."
        )
    elif s.tc01_phase == "stabilizing":
        parts.append(
            f"**TC-01 STABILIZING** - Recovery phase. PXI = {s.PXI:.1f}. "
            f"Releasing: AAL = {c_AAL():.2f} → 1.00, IF = {c_IF():.2f} → 1.00."
        )
    if s.tc02_phase == "engaged":
        parts.append(
            f"**TC-02 ENGAGED** - Active intervention. EXI = {s.EXI:.1f} < 65. "
            f"HOI = {c_HOI():.2f}, TR = {c_TR():.2f}. AAL unchanged. "
            f"Waiting for sustained EXI > {RECOVERY_EXI} "
            f"({s.tc02_stable_count}/{SUSTAINED_TICKS} ticks)."
        )
    elif s.tc02_phase == "stabilizing":
        parts.append(
            f"**TC-02 STABILIZING** - Recovery phase. EXI = {s.EXI:.1f}. "
            f"Releasing: HOI = {c_HOI():.2f} → 0.25, TR = {c_TR():.2f} → 0.50."
        )
    if s.tc03_active:
        gap = abs(s.PXI - s.EXI)
        parts.append(
            f"**TC-03 ACTIVE** - Cross-domain imbalance (|PXI − EXI| = {gap:.1f} > {TH_GAP}). "
            "Observability flag — rebalancing carried by TC-01/02 conditional activation."
        )
    return "  \n\n".join(parts)


def generate_overview_analysis():
    """Generate structured bilingual analysis for the Overview tab."""
    s = st.session_state

    # Section 1: Current Status
    if s.tc01_phase == "normal" and s.tc02_phase == "normal" and not s.tc03_active:
        status_en = (
            "The HCEE governance system is currently in nominal operation. "
            "All four levers (AAL, HOI, IF, TR) are at baseline values, and both "
            "PXI and EXI remain above their trigger thresholds. No closed-loop "
            "intervention is required at this time."
        )
        status_kr = (
            "HCEE 거버넌스 시스템이 현재 정상 운영 상태입니다. 4개 레버(AAL, HOI, IF, TR)가 "
            "모두 baseline 값에 있고, PXI와 EXI 모두 트리거 임계값 위에 머물러 있습니다. "
            "현재 폐쇄루프 개입이 필요하지 않습니다."
        )
    else:
        active_en, active_kr = [], []
        if s.tc01_phase == "engaged":
            active_en.append("TC-01 (PXI safeguard, ENGAGED)")
            active_kr.append("TC-01 (PXI 보호, 발화중)")
        elif s.tc01_phase == "stabilizing":
            active_en.append("TC-01 (recovery phase)")
            active_kr.append("TC-01 (회복 단계)")
        if s.tc02_phase == "engaged":
            active_en.append("TC-02 (EXI safeguard, ENGAGED)")
            active_kr.append("TC-02 (EXI 보호, 발화중)")
        elif s.tc02_phase == "stabilizing":
            active_en.append("TC-02 (recovery phase)")
            active_kr.append("TC-02 (회복 단계)")
        if s.tc03_active:
            active_en.append("TC-03 (cross-domain divergence flag)")
            active_kr.append("TC-03 (도메인 격차 플래그)")
        status_en = (
            f"Active governance interventions: {', '.join(active_en)}. "
            f"Levers are adjusted accordingly to bring experience indices back to "
            f"target bands (PXI ≥ 70, EXI ≥ 65)."
        )
        status_kr = (
            f"활성 거버넌스 개입: {', '.join(active_kr)}. "
            f"경험 지수를 목표 대역(PXI ≥ 70, EXI ≥ 65)으로 회복시키기 위해 "
            f"레버가 조정 중입니다."
        )

    # Section 2: Recent Trend
    if len(s.history) >= 5:
        recent = s.history[-5:]
        pxi_change = recent[-1]["PXI"] - recent[0]["PXI"]
        exi_change = recent[-1]["EXI"] - recent[0]["EXI"]
        if abs(pxi_change) < 1.5 and abs(exi_change) < 1.5:
            trend_en = (
                f"Over the last 5 ticks, both indices are stable "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"System is in equilibrium."
            )
            trend_kr = (
                f"최근 5 tick 동안 두 지표가 안정적입니다 "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"시스템이 평형 상태입니다."
            )
        elif pxi_change > 1.5 and exi_change > 1.5:
            trend_en = (
                f"Over the last 5 ticks, both indices are rising "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"Recovery trajectory is underway."
            )
            trend_kr = (
                f"최근 5 tick 동안 두 지표가 모두 상승 중 "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"회복 궤도에 있습니다."
            )
        elif pxi_change < -1.5 or exi_change < -1.5:
            trend_en = (
                f"Over the last 5 ticks, at least one index is declining "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"Pre-trigger conditions may emerge soon."
            )
            trend_kr = (
                f"최근 5 tick 동안 최소 하나의 지표가 하락 중 "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f}). "
                f"곧 트리거 조건이 형성될 수 있습니다."
            )
        else:
            trend_en = (
                f"Over the last 5 ticks, indices show mixed movement "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f})."
            )
            trend_kr = (
                f"최근 5 tick 동안 지표 움직임 혼재 "
                f"(ΔPXI = {pxi_change:+.1f}, ΔEXI = {exi_change:+.1f})."
            )
    else:
        trend_en = "Insufficient data for trend analysis (need at least 5 ticks)."
        trend_kr = "추이 분석을 위한 데이터 부족 (최소 5 tick 필요)."

    # Section 3: Cross-Layer Insight
    if s.tc01_phase == "engaged":
        insight_en = (
            "Cross-layer insight: TC-01 has reduced AI autonomy (Daily Loop layer), "
            "which is reducing AI operational load (visible in Real-time AI tab). "
            "Expected outcome: improved PXI in next weekly survey window "
            "(Weekly Surveys tab), contributing to lower trigger frequency over time "
            "(Adaptive Learning tab)."
        )
        insight_kr = (
            "레이어 간 인사이트: TC-01이 AI 자율성을 감소시켰고(Daily Loop) 이는 AI 운영 "
            "부담을 줄이고 있습니다(Real-time AI 탭). 예상 결과: 다음 주간 설문 주기에서 "
            "PXI 개선(Weekly Surveys 탭), 장기적으로 트리거 빈도 저감"
            "(Adaptive Learning 탭)."
        )
    elif s.tc02_phase == "engaged":
        insight_en = (
            "Cross-layer insight: TC-02 has raised oversight (HOI) and transparency "
            "(TR) in the Daily Loop. Real-time AI shows higher intervention rate. "
            "Reflection in Weekly Surveys typically takes 1-2 weeks; longitudinal "
            "patterns will appear in Adaptive Learning."
        )
        insight_kr = (
            "레이어 간 인사이트: TC-02가 Daily Loop에서 감독(HOI)과 투명성(TR)을 강화. "
            "Real-time AI에서 개입 비율이 높아집니다. 주간 설문 반영은 일반적으로 "
            "1-2주 후이며, 장기 패턴은 Adaptive Learning에 나타납니다."
        )
    elif s.tc03_active:
        insight_en = (
            "Cross-layer insight: TC-03 indicates significant cross-domain divergence "
            "(|PXI − EXI| > 15). The Weekly Surveys layer should be reviewed for "
            "asymmetric signal sources — e.g., one domain hit by an acute incident "
            "while the other remained stable."
        )
        insight_kr = (
            "레이어 간 인사이트: TC-03이 유의미한 도메인 간 격차(|PXI − EXI| > 15)를 "
            "신호하고 있습니다. 주간 설문 레이어에서 비대칭 신호 원천 — 예: 한 도메인은 "
            "급성 사건의 영향을 받았으나 다른 도메인은 안정적이었는지 — 를 검토해야 합니다."
        )
    elif s.tc01_phase == "stabilizing" or s.tc02_phase == "stabilizing":
        insight_en = (
            "Cross-layer insight: System is in recovery phase. Levers are gradually "
            "releasing back to baseline. Adaptive Learning will capture this episode "
            "for cross-episode learning."
        )
        insight_kr = (
            "레이어 간 인사이트: 시스템이 회복 단계에 있습니다. 레버가 점진적으로 "
            "baseline으로 복귀 중입니다. Adaptive Learning이 이 에피소드를 "
            "에피소드 간 학습용으로 기록합니다."
        )
    else:
        insight_en = (
            "Cross-layer insight: System is in stable equilibrium across all four "
            "temporal layers. Real-time AI is operating at full autonomy, Weekly "
            "Surveys are within target bands, and Adaptive Learning shows no "
            "intervention pattern."
        )
        insight_kr = (
            "레이어 간 인사이트: 시스템이 4개 시간 척도 레이어 모두에서 안정 평형 상태입니다. "
            "Real-time AI는 완전 자율 운영 중이며, Weekly Surveys는 목표 대역 내, "
            "Adaptive Learning은 개입 패턴이 없습니다."
        )

    # Section 4: Recommendations
    recs = []
    if s.tc01_engagements >= 3:
        recs.append((
            "TC-01 has fired ≥3 times — consider AAL baseline review or "
            "upstream AI configuration inspection.",
            "TC-01이 3회 이상 발화 — AAL baseline 재검토 또는 상류 AI 설정 점검 권장."
        ))
    if s.tc02_engagements >= 3:
        recs.append((
            "TC-02 has fired ≥3 times — review staff workload patterns and AI "
            "decision rationale clarity.",
            "TC-02가 3회 이상 발화 — 직원 부담 패턴 및 AI 의사결정 설명 명확성 검토."
        ))
    if s.tc03_engagements >= 2:
        recs.append((
            "TC-03 has activated ≥2 times — cross-domain imbalance is recurring; "
            "consider joint review of PXI and EXI signal calibration.",
            "TC-03이 2회 이상 활성 — 도메인 간 격차 반복 발생; PXI와 EXI 신호 보정 "
            "공동 검토 권장."
        ))
    total_eng = s.tc01_engagements + s.tc02_engagements + s.tc03_engagements
    if s.tick >= 20 and total_eng == 0:
        recs.append((
            "No trigger activations observed in 20+ ticks — system may be over-stable. "
            "Consider tightening thresholds for finer governance sensitivity.",
            "20 tick 이상 트리거 발화 없음 — 시스템 과안정 가능. 더 세밀한 감도를 위해 "
            "임계값 조정 고려."
        ))
    if not recs:
        recs.append((
            "No immediate action required. Continue monitoring through the "
            "Daily Governance Loop and Weekly Surveys tabs.",
            "즉각 조치 불필요. Daily Governance Loop 및 Weekly Surveys 탭을 통해 "
            "모니터링 지속."
        ))

    return {
        "status": (status_en, status_kr),
        "trend": (trend_en, trend_kr),
        "insight": (insight_en, insight_kr),
        "recs": recs,
    }


# ===== Sidebar =====
with st.sidebar:
    st.markdown("### Control Panel")
    if st.button("Generate signal", use_container_width=True, type="primary"):
        generate_signal()
    auto_run = st.checkbox("Auto-run")
    speed = st.slider("Speed (sec/tick)", 0.3, 3.0, 0.8, 0.1) if auto_run else 0.8
    if st.button("Reset", use_container_width=True):
        reset_state()
        st.rerun()
    st.markdown("---")
    st.markdown("**Demo Controls**")
    st.caption("Force asymmetric event to demonstrate TC-03")
    if st.button("EXI shock (−15)", use_container_width=True):
        force_exi_shock()
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
    with st.expander("Lever Activation Matrix"):
        st.markdown(r"""
| Trigger | Condition | Activated Levers |
| --- | --- | --- |
| **TC-01** | PXI < 70 | AAL ↓ (1.00 → 0.80), IF ↑ (1.00 → 1.20) |
| **TC-02** | EXI < 65 | HOI ↑ (0.25 → 1.00), **TR ↑ (0.50 → 1.00)** *paired* |
| **TC-03** | \|PXI − EXI\| > 15 | *observability flag* — emergent from TC-01/02 |
        """)
        st.caption(
            "TR is paired with TC-02 because EXI deterioration includes trust erosion. "
            "Transparency (TR) is the mechanism for trust restoration "
            "(Lee & See, 2004). TC-03 is an observability flag, not an independent "
            "trigger — the cross-rebalancing it represents emerges from TC-01/02 "
            "when one experience domain falls significantly lower than the other."
        )
    with st.expander("Parameter Provenance"):
        st.markdown("""
**3-Layer Architecture**

| Layer | Type | Source |
| --- | --- | --- |
| Layer 3 | Theory | AI governance literature, MCID, HRO theory |
| Layer 2 | Simulation | NetLogo v4 + BehaviorSpace 180 runs + 1,000 Monte Carlo |
| Layer 1 | Implementation | This dashboard (mirrors Layer 2 directly) |

**Key Parameter Justifications**

| Parameter | Value | Primary Source |
| --- | --- | --- |
| TH_PXI | 70 | 80 − 2×MCID (5pt) · PROMs literature |
| TH_EXI | 65 | HRO burnout-warning cutoff |
| TH_GAP | 15 | Two-threshold diff + 1.5 SD margin · rulebook standard |
| AAL engaged | 0.80 | Moderate intervention literature (−20%) |
| IF engaged | 1.20 | AAL inverse-symmetric compensation |
| HOI engaged | 1.00 | HRO defense-in-depth (max oversight) |
| TR engaged | 1.00 | Lee & See full transparency for recovery |
| RECOVERY thresholds | +5 from TH | 1 MCID hysteresis margin |
| SUSTAINED_TICKS | 2 | SPC stable-signal confirmation |
        """)
        st.caption(
            "Full defense scripts and references: HCEE_Parameter_Defense_Script.docx. "
            "All values cross-validated through 180-run BehaviorSpace sensitivity analysis "
            "and 1,000-run Monte Carlo robustness testing "
            "(Cohen's d 2.18–2.41 between scenarios S1 vs S3)."
        )


# ===== Main page header =====
bil_title(
    "HCEE Closed-Loop Dashboard",
    "HCEE 폐쇄루프 거버넌스 대시보드",
    " <span class='badge'>S3 · Full HCEE · Multi-Temporal</span>"
)
bil_caption(
    "Experience inputs (PXI/EXI) → TC trigger evaluation → Governance lever adjustment",
    "경험 입력값 (PXI/EXI) → TC 트리거 평가 → 거버넌스 레버 작동"
)

ct1, ct2 = st.columns([3, 1])
with ct1:
    st.caption(f"Current Date / Time · 현재 시각: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
with ct2:
    st.caption(f"Tick · 시점: {st.session_state.tick}")

s = st.session_state

# ===== Tabs =====
tab_overview, tab_loop, tab_surveys, tab_ai, tab_learning = st.tabs([
    "Overview · 종합 대시보드",
    "Daily Governance Loop · 거버넌스 루프",
    "Weekly Surveys · 주간 설문",
    "Real-time AI · 실시간 AI",
    "Adaptive Learning · 적응 학습"
])

# ----- Tab 0: Comprehensive Overview -----
with tab_overview:
    bil_h3("Comprehensive Overview", "종합 대시보드")
    bil_caption(
        "Single-screen summary across all four temporal layers",
        "4개 시간 척도 레이어의 한 화면 종합"
    )

    # Core metrics
    om = st.columns(6)
    om[0].metric("PXI", f"{s.PXI:.2f}", f"{s.PXI - INIT_PXI:+.2f}")
    om[1].metric("EXI", f"{s.EXI:.2f}", f"{s.EXI - INIT_EXI:+.2f}")
    om[2].metric("AAL", f"{c_AAL():.2f}",
                 f"{c_AAL() - CONCEPT_BASELINES['AAL']:+.2f}" if c_AAL() != CONCEPT_BASELINES['AAL'] else None)
    om[3].metric("HOI", f"{c_HOI():.2f}",
                 f"{c_HOI() - CONCEPT_BASELINES['HOI']:+.2f}" if c_HOI() != CONCEPT_BASELINES['HOI'] else None)
    om[4].metric("IF",  f"{c_IF():.2f}",
                 f"{c_IF() - CONCEPT_BASELINES['IF']:+.2f}" if c_IF() != CONCEPT_BASELINES['IF'] else None)
    om[5].metric("TR",  f"{c_TR():.2f}",
                 f"{c_TR() - CONCEPT_BASELINES['TR']:+.2f}" if c_TR() != CONCEPT_BASELINES['TR'] else None)

    # Trigger Status pills
    bil_label("Trigger Status", "트리거 상태")
    o_html = ""
    for code, phase, desc in [("TC-01", s.tc01_phase, "PXI < 70"),
                              ("TC-02", s.tc02_phase, "EXI < 65")]:
        if phase == "engaged":
            cls, label = "ton", "ENGAGED"
        elif phase == "stabilizing":
            cls, label = "tstab", "STABILIZING"
        else:
            cls, label = "toff", "NORMAL"
        o_html += f"<span class='tpill {cls}'>{code} · {label} · {desc}</span>"
    cls = "ton" if s.tc03_active else "toff"
    label = "ACTIVE" if s.tc03_active else "OFF"
    o_html += f"<span class='tpill {cls}'>TC-03 · {label} · |PXI−EXI| &gt; {TH_GAP}</span>"
    st.markdown(o_html, unsafe_allow_html=True)

    # System Interpretation
    bil_label("System Interpretation", "시스템 해석")
    st.info(interpretation())

    st.markdown("---")

    # 2x2 grid: each tab's key mini-view
    r1c1, r1c2 = st.columns(2)

    with r1c1:
        bil_label("Daily Governance · Last 30 ticks", "일일 거버넌스 · 최근 30 tick")
        if s.history:
            df_p = pd.DataFrame(s.history[-30:])
            fig_p = go.Figure()
            fig_p.add_trace(go.Scatter(x=df_p["tick"], y=df_p["PXI"], name="PXI",
                                       line=dict(color=C_PXI, width=2),
                                       mode="lines", showlegend=True))
            fig_p.add_trace(go.Scatter(x=df_p["tick"], y=df_p["EXI"], name="EXI",
                                       line=dict(color=C_EXI, width=2),
                                       mode="lines", showlegend=True))
            fig_p.add_hline(y=TH_PXI, line_dash="dot", line_color=C_PXI, opacity=0.4)
            fig_p.add_hline(y=TH_EXI, line_dash="dot", line_color=C_EXI, opacity=0.4)
            fig_p.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=20),
                                xaxis_title="", yaxis_title="",
                                yaxis_range=[40, 95],
                                paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                                font=dict(color=C_TITLE, size=10),
                                legend=dict(orientation="h", y=1.12, x=0.0,
                                            font=dict(size=10)))
            st.plotly_chart(fig_p, use_container_width=True)
        else:
            st.caption("(Generate signals to populate)")

    with r1c2:
        bil_label("Weekly Surveys · Last 4 weeks", "주간 설문 · 최근 4주")
        if len(s.history) >= 7:
            df_w = pd.DataFrame(s.history)
            df_w["week"] = (df_w["tick"] - 1) // 7 + 1
            weekly = df_w.groupby("week").agg(
                PXI=("PXI", "mean"), EXI=("EXI", "mean")
            ).reset_index().tail(4)
            fig_w = go.Figure()
            fig_w.add_trace(go.Bar(x=weekly["week"], y=weekly["PXI"],
                                   name="PXI", marker_color=C_PXI))
            fig_w.add_trace(go.Bar(x=weekly["week"], y=weekly["EXI"],
                                   name="EXI", marker_color=C_EXI))
            fig_w.update_layout(height=210, margin=dict(l=10, r=10, t=10, b=20),
                                xaxis_title="", yaxis_title="",
                                barmode="group", yaxis_range=[40, 95],
                                paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                                font=dict(color=C_TITLE, size=10),
                                legend=dict(orientation="h", y=1.12, x=0.0,
                                            font=dict(size=10)))
            st.plotly_chart(fig_w, use_container_width=True)
        else:
            st.caption(f"(Need 7+ ticks; currently {len(s.history)})")

    r2c1, r2c2 = st.columns(2)

    with r2c1:
        bil_label("Real-time AI Operations", "실시간 AI 운영")
        o_rng = np.random.default_rng(s.tick * 1000 + 7)
        o_errors = int(max(0, (1 - c_AAL()) * 30 + o_rng.poisson(2)))
        o_latency = round(0.8 + (1 - c_AAL()) * 1.5, 2)
        o_intervention = round((1 - c_AAL()) * 100, 1)
        o_safety = 1 if c_AAL() < 0.85 and o_rng.random() < 0.15 else 0
        oa = st.columns(4)
        oa[0].metric("Errors/24h", o_errors)
        oa[1].metric("Latency", f"{o_latency}s")
        oa[2].metric("Interv.", f"{o_intervention}%")
        oa[3].metric("Safety", o_safety)
        st.caption("Operational metrics derived from current AAL state.")

    with r2c2:
        bil_label("Adaptive Learning · Cumulative", "적응적 학습 · 누적")
        ol = st.columns(4)
        ol[0].metric("TC-01", s.tc01_engagements)
        ol[1].metric("TC-02", s.tc02_engagements)
        ol[2].metric("TC-03", s.tc03_engagements)
        ol[3].metric("Ticks", s.tick)
        # Quick alert summary
        total_engagements = s.tc01_engagements + s.tc02_engagements + s.tc03_engagements
        if s.tc01_engagements >= 3 or s.tc02_engagements >= 3 or s.tc03_engagements >= 3:
            st.caption("⚠ Policy review recommended — see Adaptive Learning tab")
        elif s.tick >= 20 and total_engagements == 0:
            st.caption("ℹ System appears over-stable — see Adaptive Learning tab")
        else:
            st.caption("System monitoring nominal")

    # Analysis box (collapsible, color-coded)
    _analysis = generate_overview_analysis()
    _se, _sk = _analysis["status"]
    _te, _tk = _analysis["trend"]
    _ie, _ik = _analysis["insight"]
    _recs_html = ""
    for _re, _rk in _analysis["recs"]:
        _recs_html += (
            f"<div class='analysis-rec'>"
            f"<div class='analysis-en'>{_re}</div>"
            f"<div class='analysis-kr'>{_rk}</div>"
            f"</div>"
        )
    _analysis_html = (
        "<details class='analysis-box'>"
        "<summary>📊 System Analysis · 시스템 분석</summary>"
        "<div class='analysis-content'>"
        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>Current Status · 현재 상태</div>"
        f"<div class='analysis-en'>{_se}</div>"
        f"<div class='analysis-kr'>{_sk}</div>"
        "</div>"
        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>Recent Trend (last 5 ticks) · 최근 추이</div>"
        f"<div class='analysis-en'>{_te}</div>"
        f"<div class='analysis-kr'>{_tk}</div>"
        "</div>"
        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>Cross-Layer Insight · 레이어 간 인사이트</div>"
        f"<div class='analysis-en'>{_ie}</div>"
        f"<div class='analysis-kr'>{_ik}</div>"
        "</div>"
        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>Recommendations · 권고사항</div>"
        f"{_recs_html}"
        "</div>"
        "</div>"
        "</details>"
    )
    st.markdown(_analysis_html, unsafe_allow_html=True)


# ----- Tab 1: Daily Governance Loop -----
with tab_loop:
    bil_h3("Daily Governance Loop · Core", "일일 거버넌스 루프 · 핵심")
    bil_caption(
        "Experience inputs (PXI/EXI) → TC trigger evaluation → Lever adjustment · daily cadence",
        "경험 입력값 → TC 트리거 평가 → 레버 작동 · 일 단위"
    )
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

    bil_label("Trigger Status", "트리거 상태")
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
    html += f"<span class='tpill {cls}'>TC-03 · {label} · |PXI−EXI| &gt; {TH_GAP}</span>"
    st.markdown(html, unsafe_allow_html=True)

    bil_label("System Interpretation", "시스템 해석")
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
        bil_label("Governance Event Timeline", "거버넌스 이벤트 타임라인")
        bil_caption(
            "All ticks shown. Phase transitions are color-highlighted: "
            "pink = activation (trigger fires), amber = stabilizing, green = return to baseline.",
            "전체 tick 표시. phase 전환은 색상 강조: "
            "분홍 = 트리거 발화, 황색 = 안정화 진입, 녹색 = 정상 복귀."
        )

        df_h = pd.DataFrame(s.history).copy()
        events = []
        prev_tc01 = "normal"
        prev_tc02 = "normal"
        prev_tc03 = "off"
        for _, row in df_h.iterrows():
            evs = []
            if row["TC-01"] != prev_tc01:
                evs.append(f"TC-01 {prev_tc01}→{row['TC-01']}")
            if row["TC-02"] != prev_tc02:
                evs.append(f"TC-02 {prev_tc02}→{row['TC-02']}")
            if row["TC-03"] != prev_tc03:
                evs.append(f"TC-03 {prev_tc03}→{row['TC-03']}")
            events.append("  ·  ".join(evs) if evs else "")
            prev_tc01 = row["TC-01"]
            prev_tc02 = row["TC-02"]
            prev_tc03 = row["TC-03"]
        df_h["event"] = events

        cols = ["tick", "PXI", "EXI", "AAL", "HOI", "IF", "TR",
                "TC-01", "TC-02", "TC-03", "event"]
        df_display = df_h[cols]

        def hl(row):
            ev = str(row.get("event", ""))
            if "→engaged" in ev or "→active" in ev:
                return ['background-color: #FCEBEB'] * len(row)
            if "→stabilizing" in ev:
                return ['background-color: #FAEEDA'] * len(row)
            if "→normal" in ev or "→off" in ev:
                return ['background-color: #EAF3DE'] * len(row)
            return [''] * len(row)

        styled = df_display.style.apply(hl, axis=1).format({
            "PXI": "{:.2f}", "EXI": "{:.2f}",
            "AAL": "{:.2f}", "HOI": "{:.2f}",
            "IF":  "{:.2f}", "TR":  "{:.2f}",
        })
        st.dataframe(styled, use_container_width=True, hide_index=True, height=460)
    else:
        st.caption("No signals yet · 아직 신호 없음. Click 'Generate signal' to begin.")


# ----- Tab 2: Weekly Surveys -----
with tab_surveys:
    bil_h3("Weekly Experience Surveys", "주간 경험 설문")
    bil_caption(
        "Upstream input source · where PXI/EXI signals originate · PROMs + pulse survey (Phase 2)",
        "입력 신호 원천 · PXI/EXI 발생 지점 · PROMs + 직원 펄스 설문 (Phase 2)"
    )
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


# ----- Tab 3: Real-time AI Monitoring -----
with tab_ai:
    bil_h3("Real-time AI Monitoring", "실시간 AI 모니터링")
    bil_caption(
        "Operational consequence layer · how AI behaves under current lever settings (Phase 2)",
        "운영 결과 레이어 · 현재 레버 설정 하의 AI 작동 양상 (Phase 2)"
    )
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
        "hourly operational telemetry that feeds back into AAL/IF lever calibration. "
        "Current view shows simulated AI load derived from AAL state."
        "</div>", unsafe_allow_html=True
    )


# ----- Tab 4: Adaptive Learning -----
with tab_learning:
    bil_h3("Adaptive Learning", "적응적 학습")
    bil_caption(
        "Meta-level · longitudinal pattern analysis · policy recommendations (Phase 3)",
        "메타 레벨 · 시간 흐름에 따른 패턴 분석 · 거버넌스 정책 권고 (Phase 3)"
    )
    d = st.columns(4)
    d[0].metric("TC-01 activations", s.tc01_engagements)
    d[1].metric("TC-02 activations", s.tc02_engagements)
    d[2].metric("TC-03 activations", s.tc03_engagements)
    if s.history:
        tot = len(s.history)
        eng_ticks = sum(1 for h in s.history
                        if h["TC-01"] == "engaged" or h["TC-02"] == "engaged"
                        or h["TC-03"] == "active")
        eng_ratio = round(eng_ticks / tot * 100, 1) if tot > 0 else 0
        d[3].metric("Active ticks ratio", f"{eng_ratio}%")
    else:
        d[3].metric("Active ticks ratio", "—")

    if s.history and len(s.history) >= 5:
        df_l = pd.DataFrame(s.history)
        df_l["tc01_engaged"] = (df_l["TC-01"] == "engaged").astype(int)
        df_l["tc02_engaged"] = (df_l["TC-02"] == "engaged").astype(int)
        df_l["tc03_active"]  = (df_l["TC-03"] == "active").astype(int)
        fig_l = go.Figure()
        fig_l.add_trace(go.Scatter(x=df_l["tick"], y=df_l["tc01_engaged"] * 1.0,
                                   name="TC-01 engaged",
                                   line=dict(color=C_PXI, shape="hv", width=2),
                                   fill="tozeroy"))
        fig_l.add_trace(go.Scatter(x=df_l["tick"], y=df_l["tc02_engaged"] * 0.66,
                                   name="TC-02 engaged",
                                   line=dict(color=C_EXI, shape="hv", width=2),
                                   fill="tozeroy"))
        fig_l.add_trace(go.Scatter(x=df_l["tick"], y=df_l["tc03_active"] * 0.33,
                                   name="TC-03 active",
                                   line=dict(color=C_TC03, shape="hv", width=2),
                                   fill="tozeroy"))
        fig_l.update_layout(height=240, margin=dict(l=20, r=20, t=20, b=30),
                            xaxis_title="tick", yaxis_title="active",
                            yaxis_range=[0, 1.2], yaxis_showticklabels=False,
                            paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                            font=dict(color=C_TITLE),
                            legend=dict(orientation="h", y=1.18, x=0.0))
        st.plotly_chart(fig_l, use_container_width=True)
    else:
        st.caption("(Run more signals to see activation patterns)")

    bil_label("Policy Recommendations (derived from observed patterns)",
              "정책 권고 (관찰 패턴 기반 자동 생성)")
    recs = []
    if s.tc01_engagements >= 3:
        recs.append("TC-01 has fired ≥3 times — consider raising AAL baseline review "
                    "or investigating upstream AI configuration.")
    if s.tc02_engagements >= 3:
        recs.append("TC-02 has fired ≥3 times — review staff workload patterns and AI "
                    "decision rationale clarity.")
    if s.tc03_engagements >= 3:
        recs.append("TC-03 has activated ≥3 times — cross-domain imbalance recurring; "
                    "consider joint review of PXI and EXI signal calibration.")
    if s.tick >= 20 and s.tc01_engagements == 0 and s.tc02_engagements == 0 \
       and s.tc03_engagements == 0:
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


# ===== Footer =====
st.markdown("---")
fc1, fc2 = st.columns([3, 2])
with fc1:
    st.caption("(c) 2026 Minseong Kim · 김민성. HCEE™ Trademark Application Pending")
    st.caption("KIPO 40-2026-0084368 / 40-2026-0084369 / 40-2026-0084370")
with fc2:
    st.caption("S3 Full HCEE · NetLogo v4 aligned · Multi-temporal architecture")
    st.caption("Based on Trigger-Control Rulebook (Table 4)")


# ===== Auto-run loop =====
if auto_run:
    time.sleep(speed)
    generate_signal()
    st.rerun()
