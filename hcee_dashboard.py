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
.lever-row {{
  display: flex;
  gap: 12px;
  margin-bottom: 10px;
  padding: 8px 10px;
  background: rgba(255, 255, 255, 0.55);
  border-radius: 4px;
  border-left: 3px solid {C_STAB};
}}
.lever-badge {{
  flex-shrink: 0;
  width: 78px;
  font-weight: 700;
  font-size: 0.88em;
  color: {C_TITLE};
  border-right: 1px solid #D8C99A;
  padding-right: 10px;
}}
.lever-badge-val {{
  display: block;
  font-weight: 400;
  font-size: 0.78em;
  color: {C_SUB};
  margin-top: 2px;
}}
.lever-text {{ flex: 1; }}
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
    """Generate structured bilingual analysis showing concrete operational
    meaning, lever clinical translation, self-governance posture, and
    regulatory alignment with Korean medical AI principles."""
    s = st.session_state
    tc01 = s.tc01_phase
    tc02 = s.tc02_phase
    tc03 = s.tc03_active

    # ===== Section 1: Operational Mode (what AI is actually doing) =====
    if tc01 == "normal" and tc02 == "normal" and not tc03:
        op_en = (
            "AI is operating in full autonomous mode across clinical workflows. "
            "Image diagnosis, prescription suggestions, EMR auto-population, and "
            "patient triage proceed without elevated human review. Patient experience "
            "(PXI) and employee experience (EXI) are both within target bands. "
            "The hospital's HCEE multi-layer observability continues to sample "
            "experience signals without active intervention."
        )
        op_kr = (
            "AI가 임상 워크플로우 전반에서 완전 자율 운영 중입니다. 영상 판독, 처방 추천, "
            "EMR 자동 입력, 환자 트리아지가 추가 인간 검토 없이 진행됩니다. 환자 경험(PXI)과 "
            "직원 경험(EXI) 모두 목표 대역 내에 있습니다. 병원의 HCEE 다층 관찰성이 "
            "적극적 개입 없이 경험 신호를 지속 표본화합니다."
        )
    elif tc01 == "engaged" and tc02 == "engaged":
        op_en = (
            "AI is operating in restricted-autonomy + enhanced-oversight mode due to "
            "simultaneous degradation of both patient (PXI < 70) and employee (EXI < 65) "
            "experience signals. Image diagnosis and prescription decisions now require "
            "clinician verification. Clinical rounds frequency increased by 20%. All AI "
            "decisions automatically provide reasoning. Staff can challenge AI without "
            "procedural friction. The hospital is autonomously responding to a "
            "dual-domain experience signal."
        )
        op_kr = (
            "환자(PXI < 70)와 직원(EXI < 65) 경험 신호의 동시 악화로 인해 AI가 제한 자율 + "
            "강화 감독 모드로 운영되고 있습니다. 영상 판독 및 처방 결정에 임상의 확인이 "
            "필수입니다. 임상 회진 빈도가 20% 증가했습니다. 모든 AI 의사결정에 근거가 자동 "
            "제공됩니다. 직원이 절차적 부담 없이 AI에 이의를 제기할 수 있습니다. 병원이 "
            "양방향 경험 신호에 자율적으로 대응 중입니다."
        )
    elif tc01 == "engaged":
        op_en = (
            "AI is operating in restricted-autonomy mode due to patient experience "
            "signal degradation (PXI < 70). Image diagnosis results now require "
            "radiologist primary verification before delivery (AAL: 1.00 → 0.80). "
            "Patient-facing AI suggestions are screened by nursing staff. Clinical "
            "rounds frequency increased by 20% (IF: 1.00 → 1.20 — e.g., 3.0 → 3.6 "
            "contacts/patient/day). The hospital is autonomously protecting patient "
            "experience without external directive."
        )
        op_kr = (
            "환자 경험 신호 악화(PXI < 70)로 인해 AI가 제한 자율 모드로 운영되고 있습니다. "
            "영상 판독 결과는 영상의학과 전문의 1차 확인을 거칩니다(AAL: 1.00 → 0.80). 환자 "
            "대상 AI 추천은 간호 인력 검토를 거칩니다. 임상 회진 빈도가 20% 증가했습니다"
            "(IF: 1.00 → 1.20, 예: 환자당 일 3.0 → 3.6회 접촉). 병원이 외부 지침 없이 "
            "자율적으로 환자 경험을 보호 중입니다."
        )
    elif tc02 == "engaged":
        op_en = (
            "AI is operating under enhanced oversight mode due to employee experience "
            "signal degradation (EXI < 65). Penalty for staff challenging AI decisions "
            "has been zeroed (penalty: 1.0 → 0.0). All AI decisions now provide "
            "automatic rationale (TR: 0.50 → 1.00). HOI composite: 0.25 → 1.00. Staff "
            "can flag AI errors without procedural friction. The hospital is "
            "autonomously restoring staff trust in AI systems."
        )
        op_kr = (
            "직원 경험 신호 악화(EXI < 65)로 인해 AI가 강화 감독 모드로 운영되고 있습니다. "
            "직원의 AI 의사결정 이의 제기 비용이 zero로 조정되었습니다(penalty: 1.0 → 0.0). "
            "모든 AI 의사결정에 근거가 자동 표시됩니다(TR: 0.50 → 1.00). HOI 합성치: "
            "0.25 → 1.00. 직원이 AI 오류를 절차적 부담 없이 즉시 플래그할 수 있습니다. "
            "병원이 자율적으로 AI 시스템에 대한 직원 신뢰를 회복 중입니다."
        )
    elif tc01 == "stabilizing" or tc02 == "stabilizing":
        op_en = (
            "System is in recovery phase. Levers are gradually releasing back to "
            "baseline as PXI/EXI return to target bands. AI autonomy is being "
            "restored stepwise, not abruptly — patient experience and staff trust "
            "must be confirmed sustained before AI returns to full autonomous "
            "operation. This phased recovery design prevents premature de-escalation "
            "and aligns with High Reliability Organization (HRO) principles."
        )
        op_kr = (
            "시스템이 회복 단계에 있습니다. PXI/EXI가 목표 대역으로 복귀함에 따라 레버가 "
            "점진적으로 baseline으로 풀려나고 있습니다. AI 자율성은 급격하지 않게 단계적으로 "
            "복원됩니다 — 환자 경험과 직원 신뢰가 지속적으로 회복되었음이 확인된 후에야 "
            "AI가 완전 자율 운영으로 복귀합니다. 이 단계적 회복 설계는 조기 해제를 방지하며 "
            "고신뢰성 조직(HRO) 원칙과 일치합니다."
        )
    else:
        op_en = (
            "Cross-domain divergence detected (|PXI − EXI| > 15) without simultaneous "
            "trigger activation. This indicates asymmetric experience signals — one "
            "domain is significantly better than the other. Observability flag for "
            "governance committee review."
        )
        op_kr = (
            "동시 트리거 활성 없이 도메인 간 격차(|PXI − EXI| > 15)가 감지되었습니다. "
            "이는 한 도메인이 다른 도메인보다 유의미하게 양호한 비대칭 경험 신호를 "
            "의미합니다. 거버넌스 위원회 검토를 위한 관찰성 플래그."
        )

    # ===== Section 2: Lever Clinical Translation =====
    lever_rows = []

    aal_val = c_AAL()
    if abs(aal_val - 1.0) < 0.01:
        aal_en = "Full autonomy: image read, prescription suggestion, EMR auto-fill proceed automatically."
        aal_kr = "완전 자율: 영상 판독, 처방 추천, EMR 자동 입력이 자동 진행됩니다."
    elif aal_val >= 0.85:
        aal_en = f"Slight restriction: most workflows automated; selective verification on flagged cases."
        aal_kr = f"경미한 제한: 대부분 자동화, 플래그된 사례만 선별 확인."
    else:
        aal_en = "Restricted autonomy: image diagnosis requires radiologist primary verification; prescription suggestions require physician review."
        aal_kr = "제한 자율: 영상 판독에 영상의학과 전문의 1차 확인 필수, 처방 추천에 의사 검토 필수."
    lever_rows.append(("AAL", f"{aal_val:.2f}", aal_en, aal_kr))

    if_val = c_IF()
    if abs(if_val - 1.0) < 0.01:
        if_en = "Routine clinical rounds and patient contact frequency maintained."
        if_kr = "평시 임상 회진 및 환자 접촉 빈도 유지."
    elif if_val >= 1.10:
        pct = round((if_val - 1) * 100)
        if_en = f"Increased patient contact: {if_val:.2f}× baseline (+{pct}% more rounds and bedside touchpoints)."
        if_kr = f"환자 접촉 증가: baseline의 {if_val:.2f}배(회진 및 침상 접촉 +{pct}%)."
    else:
        if_en = f"Slight contact increase: {if_val:.2f}× baseline."
        if_kr = f"접촉 경미 증가: baseline의 {if_val:.2f}배."
    lever_rows.append(("IF", f"{if_val:.2f}", if_en, if_kr))

    hoi_val = c_HOI()
    if hoi_val <= 0.30:
        hoi_en = "Standard double-check protocol: major AI decisions verified before action."
        hoi_kr = "표준 더블체크 프로토콜: 주요 AI 결정을 행동 전 확인."
    elif hoi_val >= 0.75:
        hoi_en = "Full oversight mode: staff can challenge AI without procedural penalty; all AI decisions reviewed and explained."
        hoi_kr = "전면 감독 모드: 직원이 AI에 절차적 부담 없이 이의 가능, 모든 AI 결정을 검토 및 설명."
    else:
        hoi_en = f"Elevated oversight: enhanced verification on AI-flagged cases."
        hoi_kr = f"상향된 감독: AI 플래그 사례에 강화 확인."
    lever_rows.append(("HOI", f"{hoi_val:.2f}", hoi_en, hoi_kr))

    tr_val = c_TR()
    if abs(tr_val - 0.5) < 0.01:
        tr_en = "Rationale provided for major decisions only (efficiency-transparency balance)."
        tr_kr = "주요 결정에만 근거 제공 (효율성-투명성 균형)."
    elif tr_val >= 0.85:
        tr_en = "Full transparency: every AI decision displays its reasoning chain; clinicians can audit AI logic in real time."
        tr_kr = "전면 투명성: 모든 AI 결정에 추론 체인 표시, 임상의가 실시간으로 AI 로직 감사 가능."
    else:
        pct = round(tr_val * 100)
        tr_en = f"Elevated transparency: reasoning shown for ~{pct}% of decisions."
        tr_kr = f"투명성 상향: 약 {pct}%의 결정에 근거 표시."
    lever_rows.append(("TR", f"{tr_val:.2f}", tr_en, tr_kr))

    # ===== Section 3: Self-Governance Posture (regulatory alignment) =====
    if tc01 == "normal" and tc02 == "normal" and not tc03:
        sg_en = (
            "Nominal self-monitoring posture. The HCEE multi-layer observability "
            "(Daily, Weekly, AI, Learning) continuously samples experience signals "
            "without active intervention. This satisfies post-market surveillance "
            "requirements of KFDA medical AI guidelines without active regulatory "
            "inquiry. No reporting trigger to MOHW Patient Safety Reporting System "
            "is currently met. Hospital governance committee receives quarterly "
            "summary; no ad-hoc reporting required."
        )
        sg_kr = (
            "정상 자기 모니터링 위상. HCEE 다층 관찰성(일·주·AI·학습)이 적극적 개입 없이 "
            "경험 신호를 지속 표본화합니다. 이는 식약처 의료 AI 가이드라인의 시판 후 감시 "
            "요건을 적극적 규제 조회 없이 충족합니다. 현 시점에서 보건복지부 환자안전 보고 "
            "시스템 보고 트리거 미발생. 병원 거버넌스 위원회는 분기별 요약만 받으며, "
            "임시 보고 불필요."
        )
    elif tc01 == "engaged":
        sg_en = (
            "Autonomous patient-safety response posture. HCEE has automatically "
            "restricted AI autonomy in response to a patient experience signal, "
            "consistent with the 'patient safety primacy' principle of Korean medical "
            "AI governance (KFDA, MOHW). This intervention is logged for the hospital's "
            "quarterly governance committee. Importantly, this autonomous response "
            "demonstrates active accountability — the hospital is enforcing the "
            "national safety principle without waiting for external directive, "
            "reducing the inspection load on national regulators."
        )
        sg_kr = (
            "자율 환자안전 대응 위상. HCEE가 환자 경험 신호에 자동 대응해 AI 자율성을 "
            "제한했으며, 이는 한국 의료 AI 거버넌스(식약처·보건복지부)의 '환자안전 우선' "
            "원칙과 일치합니다. 본 개입은 병원 분기별 거버넌스 위원회에 기록됩니다. "
            "중요한 점은 이 자율 대응이 능동적 책임 이행을 보여준다는 것입니다 — 병원이 "
            "외부 지침을 기다리지 않고 국가 안전 원칙을 자체적으로 집행하고 있으며, "
            "이로 인해 국가 규제기관의 점검 부담이 경감됩니다."
        )
    elif tc02 == "engaged":
        sg_en = (
            "Autonomous staff-trust restoration posture. HCEE has automatically "
            "elevated oversight (HOI) and transparency (TR), implementing the "
            "'explainability' and 'human accountability' principles of Korean medical "
            "AI guidelines without external mandate. This is logged for the hospital "
            "medical ethics committee. The fact that the hospital can demonstrate this "
            "autonomous compliance — with audit trail — reduces the regulatory burden "
            "on KFDA/MOHW oversight and supports a lower inspection-frequency posture."
        )
        sg_kr = (
            "자율 직원 신뢰 회복 위상. HCEE가 자동으로 감독(HOI)과 투명성(TR)을 강화했으며, "
            "한국 의료 AI 가이드라인의 '설명 가능성' 및 '인간 책임' 원칙을 외부 지시 없이 "
            "이행하고 있습니다. 본 사항은 병원 의료윤리위원회에 기록됩니다. 병원이 이 자율 "
            "준수를 — 감사 추적과 함께 — 입증할 수 있다는 사실이 식약처·보건복지부 감독의 "
            "규제 부담을 감소시키며, 점검 빈도 완화 위상을 뒷받침합니다."
        )
    elif tc01 == "stabilizing" or tc02 == "stabilizing":
        sg_en = (
            "Post-intervention recovery posture. The hospital is demonstrating phased "
            "de-escalation rather than abrupt return to baseline. This sustained-recovery "
            "design (2-tick confirmation before stabilizing) aligns with High Reliability "
            "Organization principles required by patient safety regulations. Documentation "
            "of recovery trajectory is captured in the Adaptive Learning layer and will "
            "be included in the next governance committee report as evidence of structured "
            "incident response."
        )
        sg_kr = (
            "개입 후 회복 위상. 병원이 baseline으로의 급격한 복귀가 아닌 단계적 해제를 "
            "수행하고 있습니다. 이 지속 회복 설계(안정화 전 2-tick 확인)는 환자안전 법규가 "
            "요구하는 고신뢰성 조직 원칙과 일치합니다. 회복 궤적은 Adaptive Learning 레이어에 "
            "기록되며, 구조화된 사고 대응의 증거로 다음 거버넌스 위원회 보고에 포함됩니다."
        )
    else:
        sg_en = (
            "Cross-domain anomaly posture. The HCEE observability layer has flagged "
            "a significant asymmetric experience signal — one that conventional "
            "single-domain monitoring (e.g., patient satisfaction surveys alone) would "
            "miss. This rare-event detection itself demonstrates the depth of HCEE's "
            "regulatory compliance, going beyond minimum required monitoring and "
            "providing the hospital with early-warning capability."
        )
        sg_kr = (
            "도메인 간 이상 위상. HCEE 관찰성 레이어가 유의미한 비대칭 경험 신호를 "
            "포착했으며 — 기존 단일 도메인 모니터링(예: 환자 만족도 조사만)은 놓칠 수 있는 "
            "신호입니다. 이 희소 사건 감지 자체가 최소 요구 모니터링을 넘어선 HCEE의 규제 "
            "준수 깊이를 보여주며, 병원에 조기 경보 역량을 제공합니다."
        )

    # ===== Section 4: Trajectory & Action =====
    trend_en = ""
    trend_kr = ""
    if len(s.history) >= 5:
        recent = s.history[-5:]
        pxi_change = recent[-1]["PXI"] - recent[0]["PXI"]
        exi_change = recent[-1]["EXI"] - recent[0]["EXI"]
        if abs(pxi_change) < 1.5 and abs(exi_change) < 1.5:
            trend_en = f"Stable trajectory (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "
            trend_kr = f"안정 추이 (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "
        elif pxi_change > 1.5 and exi_change > 1.5:
            trend_en = f"Rising recovery trajectory (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "
            trend_kr = f"상승 회복 추이 (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "
        elif pxi_change < -1.5 or exi_change < -1.5:
            trend_en = f"Declining trajectory (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}); pre-trigger conditions may emerge. "
            trend_kr = f"하락 추이 (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}); 트리거 조건 형성 가능. "
        else:
            trend_en = f"Mixed trajectory (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "
            trend_kr = f"혼재 추이 (ΔPXI={pxi_change:+.1f}, ΔEXI={exi_change:+.1f}). "

    if tc01 == "normal" and tc02 == "normal" and not tc03:
        action_en = trend_en + (
            "Expected continued nominal operation. No interventions anticipated in the "
            "next 1-2 weeks based on Daily Loop dynamics. Action: continue routine "
            "quarterly governance committee review; no ad-hoc reporting required."
        )
        action_kr = trend_kr + (
            "정상 운영 지속 예상. Daily Loop 다이내믹스에 기반해 향후 1-2주 내 개입 예상 "
            "없음. 조치: 분기별 거버넌스 위원회 정기 검토 지속, 임시 보고 불필요."
        )
    elif tc01 == "engaged" or tc02 == "engaged":
        action_en = trend_en + (
            "Expected recovery: PXI/EXI returning to recovery thresholds (75/70) within "
            "3-5 ticks under current lever response. Total intervention episode "
            "estimated 5-8 ticks. Action: continue automated monitoring; prepare "
            "incident summary for next governance committee meeting; verify EMR audit "
            "trail completeness; tag episode for Adaptive Learning meta-analysis."
        )
        action_kr = trend_kr + (
            "예상 회복: 현재 레버 대응 하에 3-5 tick 내 PXI/EXI가 회복 임계값(75/70)에 "
            "도달. 총 개입 에피소드 5-8 tick 추정. 조치: 자동 모니터링 지속, 다음 거버넌스 "
            "위원회 회의를 위한 사건 요약 준비, EMR 감사 추적 완전성 확인, Adaptive Learning "
            "메타 분석을 위한 에피소드 태깅."
        )
    else:
        action_en = trend_en + (
            "Recovery in progress. Levers are releasing toward baseline. Action: "
            "confirm sustained recovery before final de-escalation; document episode "
            "for cross-episode learning; include in next quarterly governance report."
        )
        action_kr = trend_kr + (
            "회복 진행 중. 레버가 baseline 방향으로 해제 중. 조치: 최종 해제 전 지속 회복 "
            "확인, 에피소드 간 학습용 문서화, 다음 분기별 거버넌스 보고에 포함."
        )

    return {
        "op_mode": (op_en, op_kr),
        "lever_rows": lever_rows,
        "self_gov": (sg_en, sg_kr),
        "action": (action_en, action_kr),
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

    # Analysis box (collapsible, color-coded, operationally grounded)
    _analysis = generate_overview_analysis()
    _op_en, _op_kr = _analysis["op_mode"]
    _sg_en, _sg_kr = _analysis["self_gov"]
    _ac_en, _ac_kr = _analysis["action"]

    _lever_html = ""
    for _lv, _val, _le, _lk in _analysis["lever_rows"]:
        _lever_html += (
            f"<div class='lever-row'>"
            f"<div class='lever-badge'>{_lv}<span class='lever-badge-val'>{_val}</span></div>"
            f"<div class='lever-text'>"
            f"<div class='analysis-en'>{_le}</div>"
            f"<div class='analysis-kr'>{_lk}</div>"
            f"</div>"
            f"</div>"
        )

    _analysis_html = (
        "<details class='analysis-box'>"
        "<summary>📊 System Analysis · 시스템 분석</summary>"
        "<div class='analysis-content'>"

        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>"
        "① Operational Mode · 현재 운영 모드 "
        "<span style='font-weight:400; font-size:0.85em; color:#7E776B;'>"
        "(what AI is actually doing in clinical workflows)</span>"
        "</div>"
        f"<div class='analysis-en'>{_op_en}</div>"
        f"<div class='analysis-kr'>{_op_kr}</div>"
        "</div>"

        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>"
        "② Lever Clinical Translation · 레버의 임상적 의미 "
        "<span style='font-weight:400; font-size:0.85em; color:#7E776B;'>"
        "(what each lever value means at the bedside)</span>"
        "</div>"
        f"{_lever_html}"
        "</div>"

        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>"
        "③ Self-Governance Posture · 자율 거버넌스 위상 "
        "<span style='font-weight:400; font-size:0.85em; color:#7E776B;'>"
        "(how this aligns with Korean medical AI regulation)</span>"
        "</div>"
        f"<div class='analysis-en'>{_sg_en}</div>"
        f"<div class='analysis-kr'>{_sg_kr}</div>"
        "</div>"

        "<div class='analysis-section'>"
        "<div class='analysis-section-title'>"
        "④ Trajectory &amp; Action · 추이 및 조치사항 "
        "<span style='font-weight:400; font-size:0.85em; color:#7E776B;'>"
        "(what's expected next and what to do)</span>"
        "</div>"
        f"<div class='analysis-en'>{_ac_en}</div>"
        f"<div class='analysis-kr'>{_ac_kr}</div>"
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
