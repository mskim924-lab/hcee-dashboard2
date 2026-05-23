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

# Timeout thresholds for policy-layer escalation
# (single-episode auto-resolution boundary conditions)
TC_ENGAGED_TIMEOUT = 10   # ticks - escalate if TC-01/02 ENGAGED this long
TC03_ACTIVE_TIMEOUT = 5   # ticks - lower since TC-03 is already a warning flag

NETLOGO_BASELINES = {
    "automation_level": 1.0,
    "interaction_mult": 1.0,
    "penalty_coeff":    1.0,
    "rationale_prob":   0.5,
}
CONCEPT_BASELINES = {"AAL": 1.00, "HOI": 0.25, "IF": 1.00, "TR": 0.50}

# ===== AI Catalog (6 monitored AIs) =====
AI_CATALOG = [
    {
        "id": "AI-001",
        "name": "Medical Imaging AI",
        "name_kr": "영상 판독 AI",
        "category": "Chest X-ray, ultrasound interpretation",
        "category_kr": "흉부 X-ray·초음파 판독 보조",
        "tier": 1,
        "kfda_class": "KFDA 2등급 SaMD",
        "dept": "영상의학과",
        "dept_en": "Radiology",
        "base_activity": 142,
    },
    {
        "id": "AI-002",
        "name": "Early Warning AI",
        "name_kr": "환자 악화 조기 경보 AI",
        "category": "Sepsis & deterioration prediction",
        "category_kr": "패혈증·임상 악화 예측",
        "tier": 1,
        "kfda_class": "KFDA 2등급 SaMD",
        "dept": "내과·중환자실",
        "dept_en": "Internal Medicine · ICU",
        "base_activity": 28,
    },
    {
        "id": "AI-003",
        "name": "Medication Safety AI",
        "name_kr": "처방 안전 검토 AI",
        "category": "DDI, allergy, dose adjustment",
        "category_kr": "약물 상호작용·알러지·용량 검토",
        "tier": 1,
        "kfda_class": "KFDA 2등급 SaMD",
        "dept": "약제부",
        "dept_en": "Pharmacy",
        "base_activity": 245,
    },
    {
        "id": "AI-004",
        "name": "Clinical Documentation AI",
        "name_kr": "진료기록 자동화 AI",
        "category": "Voice-to-text, ICD auto-coding",
        "category_kr": "음성 인식·ICD 자동 코딩",
        "tier": 2,
        "kfda_class": "비의료기기 AI",
        "dept": "의무기록실",
        "dept_en": "Medical Records",
        "base_activity": 89,
    },
    {
        "id": "AI-005",
        "name": "Lab Result Interpretation AI",
        "name_kr": "검사 결과 해석 AI",
        "category": "Auto-flag abnormal lab values",
        "category_kr": "이상 검사값 자동 플래그",
        "tier": 2,
        "kfda_class": "비의료기기 AI",
        "dept": "진단검사의학과",
        "dept_en": "Laboratory Medicine",
        "base_activity": 314,
    },
    {
        "id": "AI-007",
        "name": "Resource Management AI",
        "name_kr": "자원 관리 AI",
        "category": "Bed, staffing, OR scheduling",
        "category_kr": "병상·인력·수술실 일정 최적화",
        "tier": 3,
        "kfda_class": "비의료기기 AI",
        "dept": "원무부·경영기획",
        "dept_en": "Administration",
        "base_activity": 12,
    },
]

# ===== PXI Sub-dimensions (6 dims, HIRA 환자경험평가 + AI-era extensions) =====
# Each sub-dim has its own data source and update cadence — this naturally
# embeds the multi-temporal architecture in the human-experience signal model.
PXI_SUBS = [
    {"id": "pxi_comm",     "name": "Communication Clarity",   "name_kr": "소통 명확성",
     "source": "Weekly Survey · HIRA",                "source_kr": "주간 설문 · HIRA",
     "cadence": "weekly",          "dept": "의국·간호부",       "color": "#5A7548"},
    {"id": "pxi_ai_trust", "name": "AI Decision Trust",       "name_kr": "AI 의사결정 신뢰",
     "source": "Weekly + Post-encounter Pulse",       "source_kr": "주간 + 진료 후 펄스",
     "cadence": "weekly+pulse",    "dept": "AI 위원회·IT부",    "color": "#4A6FA5"},
    {"id": "pxi_response", "name": "Responsiveness",          "name_kr": "응대 적시성",
     "source": "Daily EMR Metrics",                   "source_kr": "일일 EMR 지표",
     "cadence": "daily",           "dept": "원무부",             "color": "#2D7A60"},
    {"id": "pxi_symptom",  "name": "Symptom Management",      "name_kr": "증상 관리",
     "source": "Daily Clinical Data",                 "source_kr": "일일 임상 데이터",
     "cadence": "daily",           "dept": "약제부·통증관리팀",  "color": "#6B8E23"},
    {"id": "pxi_info",     "name": "Information Quality",     "name_kr": "정보 제공",
     "source": "Weekly + Discharge Feedback",         "source_kr": "주간 + 퇴원 피드백",
     "cadence": "weekly+pulse",    "dept": "의료진",             "color": "#4682B4"},
    {"id": "pxi_empathy",  "name": "Empathy & Dignity",       "name_kr": "공감·존중",
     "source": "Weekly Survey · HIRA",                "source_kr": "주간 설문 · HIRA",
     "cadence": "weekly",          "dept": "의료진 전체",        "color": "#3D6B47"},
]

# ===== EXI Sub-dimensions (6 dims, Maslach + AI-era extensions) =====
EXI_SUBS = [
    {"id": "exi_workload",  "name": "Cognitive Workload",      "name_kr": "인지 부담",
     "source": "Daily EMR Usage Logs",                "source_kr": "일일 EMR 사용 로그",
     "cadence": "daily",           "dept": "각 진료과",          "color": "#7A2E2E"},
    {"id": "exi_usability", "name": "AI Tool Usability",       "name_kr": "AI 도구 사용성",
     "source": "Real-time EMR Telemetry",             "source_kr": "실시간 EMR 텔레메트리",
     "cadence": "realtime",        "dept": "IT부·EMR 운영팀",    "color": "#C2410C"},
    {"id": "exi_autonomy",  "name": "Clinical Autonomy",       "name_kr": "임상 자율성",
     "source": "Weekly Pulse Survey",                 "source_kr": "주간 펄스 설문",
     "cadence": "weekly",          "dept": "의무위·인사부",      "color": "#B4953C"},
    {"id": "exi_safety",    "name": "Psychological Safety",    "name_kr": "심리적 안전",
     "source": "Quarterly Anonymous Survey",          "source_kr": "분기별 익명 설문",
     "cadence": "quarterly",       "dept": "의료윤리위·인사부",  "color": "#8B4513"},
    {"id": "exi_ai_trust",  "name": "Trust in AI",             "name_kr": "AI 신뢰",
     "source": "Weekly Pulse Survey",                 "source_kr": "주간 펄스 설문",
     "cadence": "weekly",          "dept": "AI 위원회",          "color": "#A0522D"},
    {"id": "exi_team",      "name": "Team Coordination",       "name_kr": "팀 협업",
     "source": "Daily Rounds + Monthly Survey",       "source_kr": "일일 라운드 + 월간 설문",
     "cadence": "daily+monthly",   "dept": "각 진료과",          "color": "#CD853F"},
]

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
.decision-block {{
  background: linear-gradient(135deg, #FFF8E8 0%, #FAF0DC 100%);
  border: 2px solid {C_ON};
  border-radius: 6px;
  padding: 12px 14px;
  margin-bottom: 14px;
}}
.decision-block-title {{
  font-weight: 700;
  font-size: 1.02em;
  color: {C_ON};
  margin-bottom: 10px;
  letter-spacing: 0.02em;
}}
.decision-item {{
  display: flex;
  gap: 10px;
  align-items: flex-start;
  margin-bottom: 8px;
  padding: 7px 9px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 4px;
}}
.decision-item:last-child {{ margin-bottom: 0; }}
.priority-badge {{
  flex-shrink: 0;
  display: inline-block;
  min-width: 92px;
  text-align: center;
  font-size: 0.72em;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 3px;
  letter-spacing: 0.04em;
  color: white;
}}
.prio-urgent     {{ background: #B91C1C; }}
.prio-immediate  {{ background: #C2410C; }}
.prio-today      {{ background: {C_STAB}; }}
.prio-thisweek   {{ background: {C_PXI}; }}
.prio-reporting  {{ background: {C_TITLE}; }}
.decision-text-en {{
  font-size: 0.86em;
  color: {C_TITLE};
  line-height: 1.45;
}}
.decision-text-kr {{
  font-size: 0.78em;
  color: {C_SUB};
  line-height: 1.4;
  padding-left: 10px;
  border-left: 2px solid #C9B68A;
  margin-top: 2px;
}}
.evidence-divider {{
  margin: 14px 0 10px 0;
  padding: 4px 0;
  font-size: 0.85em;
  font-weight: 600;
  color: {C_SUB};
  text-transform: uppercase;
  letter-spacing: 0.08em;
  border-top: 1px dashed #C9B68A;
  border-bottom: 1px dashed #C9B68A;
  text-align: center;
}}
.ai-card {{
  background: #FFFFFF;
  border-radius: 6px;
  border-left: 6px solid #BFBFBF;
  padding: 12px 16px;
  margin-bottom: 12px;
  box-shadow: 0 1px 2px rgba(0,0,0,0.04);
}}
.ai-card-green       {{ border-left-color: {C_PXI}; }}
.ai-card-amber       {{ border-left-color: {C_STAB}; }}
.ai-card-amber-light {{ border-left-color: #D4B670; }}
.ai-card-red         {{ border-left-color: {C_ON}; }}
.ai-card-violet      {{ border-left-color: #7B4CBF; }}
.ai-card-header {{
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 4px;
  flex-wrap: wrap;
  gap: 6px;
}}
.ai-card-id {{
  font-weight: 700;
  font-size: 0.78em;
  color: {C_SUB};
  letter-spacing: 0.03em;
  margin-right: 8px;
}}
.ai-card-name {{
  font-weight: 600;
  font-size: 1.0em;
  color: {C_TITLE};
}}
.ai-card-name-kr {{
  font-size: 0.78em;
  color: {C_SUB};
  margin-left: 6px;
}}
.ai-card-tier {{
  flex-shrink: 0;
  font-size: 0.72em;
  font-weight: 700;
  padding: 3px 8px;
  border-radius: 3px;
  color: white;
}}
.ai-tier-1 {{ background: {C_ON}; }}
.ai-tier-2 {{ background: {C_STAB}; }}
.ai-tier-3 {{ background: {C_PXI}; }}
.ai-card-meta {{
  font-size: 0.78em;
  color: {C_SUB};
  margin-bottom: 8px;
  line-height: 1.4;
}}
.ai-card-status-row {{
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
  padding: 6px 8px;
  background: #FAF6E8;
  border-radius: 4px;
  margin-bottom: 6px;
}}
.ai-status-badge {{
  font-weight: 600;
  font-size: 0.86em;
}}
.ai-status-green       {{ color: {C_PXI}; }}
.ai-status-amber       {{ color: {C_STAB}; }}
.ai-status-amber-light {{ color: #A0832E; }}
.ai-status-red         {{ color: {C_ON}; }}
.ai-status-violet      {{ color: #7B4CBF; }}
.ai-aal-display {{
  font-size: 0.84em;
  color: {C_TITLE};
}}
.ai-card-stats {{
  font-size: 0.8em;
  color: {C_SUB};
  margin-bottom: 4px;
}}
.ai-card-footer {{
  font-size: 0.74em;
  color: {C_SUB};
  opacity: 0.85;
}}
.ai-summary-bar {{
  background: linear-gradient(135deg, #F4F0E4 0%, #FAF6E8 100%);
  border-radius: 6px;
  padding: 10px 14px;
  margin-bottom: 14px;
  font-size: 0.88em;
  color: {C_TITLE};
}}
.ai-summary-bar strong {{ color: {C_ON}; }}
/* Sub-dimension display */
.subdim-row {{
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 7px 10px;
  margin-bottom: 5px;
  background: #FFFFFF;
  border-left: 3px solid #BFBFBF;
  border-radius: 4px;
}}
.subdim-row-driver {{
  border-left-color: {C_ON};
  background: #FCEBEB;
}}
.subdim-row-low {{
  border-left-color: {C_STAB};
  background: #FAF6E8;
}}
.subdim-color-dot {{
  width: 10px;
  height: 10px;
  border-radius: 50%;
  flex-shrink: 0;
}}
.subdim-name-block {{
  flex: 1.6;
  min-width: 0;
}}
.subdim-name {{
  font-weight: 600;
  font-size: 0.86em;
  color: {C_TITLE};
}}
.subdim-name-kr {{
  font-size: 0.72em;
  color: {C_SUB};
  margin-left: 4px;
}}
.subdim-value {{
  flex-shrink: 0;
  width: 50px;
  text-align: right;
  font-weight: 700;
  font-size: 0.98em;
  color: {C_TITLE};
}}
.subdim-driver-flag {{
  flex-shrink: 0;
  font-size: 0.7em;
  font-weight: 700;
  color: {C_ON};
  padding: 2px 6px;
  background: #FFE0E0;
  border-radius: 3px;
  letter-spacing: 0.05em;
}}
.subdim-source {{
  flex: 1.4;
  font-size: 0.7em;
  color: {C_SUB};
  font-style: italic;
  text-align: right;
}}
.subdim-composite {{
  margin-top: 6px;
  padding: 6px 10px;
  background: #F4F0E4;
  border-radius: 4px;
  font-size: 0.86em;
  color: {C_TITLE};
  font-weight: 600;
  border-left: 3px solid {C_TITLE};
}}
.subdim-block-title {{
  font-weight: 700;
  font-size: 0.95em;
  color: {C_TITLE};
  margin-top: 14px;
  margin-bottom: 6px;
  padding-bottom: 4px;
  border-bottom: 1px solid #C9B68A;
}}
.subdim-block-title-kr {{
  font-size: 0.75em;
  color: {C_SUB};
  margin-left: 6px;
  font-weight: 400;
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
    # Duration counters for timeout-based policy-layer escalation
    st.session_state.tc01_engaged_duration = 0
    st.session_state.tc02_engaged_duration = 0
    st.session_state.tc03_active_duration = 0
    st.session_state.history = []
    # Per-AI effective AAL (single source of truth, initialized to 1.0).
    # On TC engagement the user (or operator) can override; Reset button
    # in each AI card resyncs to current auto value.
    for ai in AI_CATALOG:
        st.session_state[f"ai_aal_slider_{ai['id']}"] = 1.0
    # Sub-dimension values (12 sub-dims, init to composite initial values)
    for sub in PXI_SUBS:
        st.session_state[f"sub_{sub['id']}"] = INIT_PXI
    for sub in EXI_SUBS:
        st.session_state[f"sub_{sub['id']}"] = INIT_EXI
    # Driver assignment — which sub-dim is the primary driver of the
    # current TC episode (None when not engaged).
    st.session_state.tc01_driver = None
    st.session_state.tc02_driver = None

if "tick" not in st.session_state:
    reset_state()


# ===== Conceptual levers =====
def c_AAL(): return st.session_state.automation_level
def c_IF():  return st.session_state.interaction_mult
def c_HOI():
    s = st.session_state
    return 0.5 * (1.0 - s.penalty_coeff) + 0.5 * s.rationale_prob
def c_TR():  return st.session_state.rationale_prob


# ===== AI Monitoring helpers =====
def compute_ai_auto_aal(ai_tier):
    """Auto-computed effective AAL for an AI of given tier based on global TC state.
    Tier 1 (patient-safety critical) follows TC-01 most strongly.
    Tier 2 (clinical workflow) follows TC-02 most strongly.
    Tier 3 (operational) is affected mildly by any engagement."""
    s = st.session_state
    if ai_tier == 1:
        if s.tc01_phase == "engaged":
            return 0.80
        if s.tc01_phase == "stabilizing":
            return min(1.0, s.automation_level)
        return 1.00
    if ai_tier == 2:
        if s.tc02_phase == "engaged":
            return 0.85
        if s.tc02_phase == "stabilizing":
            return 0.95
        return 1.00
    # tier 3
    if s.tc01_phase == "engaged" or s.tc02_phase == "engaged":
        return 0.90
    return 1.00


def get_effective_ai_aal(ai):
    """Effective AAL = current slider value (single source of truth).
    Slider key is initialized in reset_state(); also lazy-init here."""
    key = f"ai_aal_slider_{ai['id']}"
    if key not in st.session_state:
        st.session_state[key] = compute_ai_auto_aal(ai["tier"])
    return st.session_state[key]


def is_ai_manual_override(ai):
    """True if effective AAL differs from current auto AAL."""
    auto = compute_ai_auto_aal(ai["tier"])
    eff = get_effective_ai_aal(ai)
    return abs(eff - auto) > 0.01


def get_ai_status(ai):
    """Return (status_en, status_kr, color_key, badge_symbol) for an AI."""
    s = st.session_state
    if is_ai_manual_override(ai):
        return ("Manual Override", "수동 조정", "violet", "◈")
    if s.tc03_active:
        return ("Under Review", "검토 중", "red", "⚠")
    if ai["tier"] == 1:
        if s.tc01_phase == "engaged":
            return ("Restricted", "제한 모드", "amber", "◐")
        if s.tc01_phase == "stabilizing":
            return ("Stabilizing", "회복 중", "amber-light", "◑")
    if ai["tier"] == 2:
        if s.tc02_phase == "engaged":
            return ("Enhanced Review", "강화 감독", "amber", "◐")
        if s.tc02_phase == "stabilizing":
            return ("Stabilizing", "회복 중", "amber-light", "◑")
    if ai["tier"] == 3:
        if s.tc01_phase == "engaged" or s.tc02_phase == "engaged":
            return ("Minor Restriction", "경미한 제한", "amber-light", "◑")
    return ("Active", "정상 운영", "green", "●")


def get_ai_24h_stats(ai):
    """Deterministic per-tick 24h activity stats for an AI."""
    s = st.session_state
    seed = (s.tick * 1000) + sum(ord(c) for c in ai["id"]) * 7
    rng = np.random.default_rng(seed)
    eff_aal = get_effective_ai_aal(ai)
    activity = ai["base_activity"] + int(rng.integers(-12, 13))
    escalations = int(rng.poisson(0.4 + (1 - eff_aal) * 6))
    errors = int(rng.poisson(0.2 + (1 - eff_aal) * 2))
    second_opinions = int(rng.poisson(0.6 + (1 - eff_aal) * 3))
    return {
        "activity": max(0, activity),
        "escalations": escalations,
        "errors": errors,
        "second_opinions": second_opinions,
    }


def get_ai_specific_recommendations():
    """Per-AI recommendations based on 24h stats thresholds.
    Returns list of (priority, en, kr) tuples."""
    recs = []
    for ai in AI_CATALOG:
        stats = get_ai_24h_stats(ai)
        if stats["errors"] >= 3:
            recs.append((
                "IMMEDIATE",
                f"{ai['name']} ({ai['dept_en']}) — 24h errors ≥ 3. Pause non-critical use and request vendor incident report.",
                f"{ai['name_kr']} ({ai['dept']}) — 24h 오류 3건 이상. 비핵심 사용 일시 중단, 벤더 사고 보고서 요청."
            ))
        elif stats["escalations"] >= 5:
            recs.append((
                "TODAY",
                f"{ai['name']} ({ai['dept_en']}) — 24h escalations ≥ 5. Schedule departmental review meeting.",
                f"{ai['name_kr']} ({ai['dept']}) — 24h escalation 5건 이상. 부서 정기 회의 안건 상정 권고."
            ))
        elif stats["escalations"] >= 3 and ai["tier"] == 1:
            recs.append((
                "THIS WEEK",
                f"{ai['name']} ({ai['dept_en']}) — Tier 1 AI with elevated escalations. Include in next quality review.",
                f"{ai['name_kr']} ({ai['dept']}) — Tier 1 AI escalation 증가. 차주 품질 검토 회의 포함 권고."
            ))
    return recs


# ===== Sub-dimension dynamics + driver detection =====
def update_sub_dimensions():
    """Update all 12 sub-dimension values per tick.
    Sub-dims hover around the composite (PXI or EXI) with sub-specific noise.
    The currently-assigned driver sub-dim (tc01_driver / tc02_driver) receives
    an extra negative offset to visibly lead the composite drop."""
    s = st.session_state
    # PXI sub-dimensions
    for sub in PXI_SUBS:
        sub_key = f"sub_{sub['id']}"
        seed = (s.tick * 1000) + sum(ord(c) for c in sub['id'])
        rng = np.random.default_rng(seed)
        noise = float(rng.normal(0, 1.5))
        driver_offset = 0.0
        if s.tc01_driver == sub['id']:
            if s.tc01_phase == "engaged":
                driver_offset = -8.0
            elif s.tc01_phase == "stabilizing":
                driver_offset = -4.0
        target = s.PXI + driver_offset
        current = st.session_state.get(sub_key, s.PXI)
        new_val = current + (target - current) * 0.25 + noise
        st.session_state[sub_key] = float(np.clip(new_val, 30, 100))
    # EXI sub-dimensions
    for sub in EXI_SUBS:
        sub_key = f"sub_{sub['id']}"
        seed = (s.tick * 1000) + sum(ord(c) for c in sub['id']) + 99
        rng = np.random.default_rng(seed)
        noise = float(rng.normal(0, 1.5))
        driver_offset = 0.0
        if s.tc02_driver == sub['id']:
            if s.tc02_phase == "engaged":
                driver_offset = -8.0
            elif s.tc02_phase == "stabilizing":
                driver_offset = -4.0
        target = s.EXI + driver_offset
        current = st.session_state.get(sub_key, s.EXI)
        new_val = current + (target - current) * 0.25 + noise
        st.session_state[sub_key] = float(np.clip(new_val, 30, 100))


def get_pxi_driver():
    """Return (sub_dict, value) of the currently-lowest PXI sub-dim."""
    values = {sub['id']: st.session_state.get(f"sub_{sub['id']}", st.session_state.PXI)
              for sub in PXI_SUBS}
    low_id = min(values, key=values.get)
    sub = next(s for s in PXI_SUBS if s['id'] == low_id)
    return sub, values[low_id]


def get_exi_driver():
    """Return (sub_dict, value) of the currently-lowest EXI sub-dim."""
    values = {sub['id']: st.session_state.get(f"sub_{sub['id']}", st.session_state.EXI)
              for sub in EXI_SUBS}
    low_id = min(values, key=values.get)
    sub = next(s for s in EXI_SUBS if s['id'] == low_id)
    return sub, values[low_id]


def pick_random_driver(sub_list, seed_offset=0):
    """Pick a random sub-dim ID from a sub_list, deterministic per tick."""
    s = st.session_state
    rng = np.random.default_rng(s.tick + 12345 + seed_offset)
    return sub_list[int(rng.integers(0, len(sub_list)))]['id']


# ===== Signal dynamics =====
def generate_signal():
    s = st.session_state
    s.tick += 1
    pxi_target = 72 + (1 - s.automation_level) * 15.75 + (s.interaction_mult - 1) * 15.75
    exi_target = 67 + (1 - s.penalty_coeff) * 5 + (s.rationale_prob - 0.5) * 5
    s.PXI = float(np.clip(s.PXI + (pxi_target - s.PXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    s.EXI = float(np.clip(s.EXI + (exi_target - s.EXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    apply_tc_rules()
    update_sub_dimensions()
    _hist = {
        "tick":  s.tick,
        "time":  datetime.now().strftime("%H:%M:%S"),
        "PXI":   round(s.PXI, 2), "EXI": round(s.EXI, 2),
        "AAL":   round(c_AAL(), 2), "HOI": round(c_HOI(), 2),
        "IF":    round(c_IF(), 2),  "TR":  round(c_TR(), 2),
        "TC-01": s.tc01_phase,
        "TC-02": s.tc02_phase,
        "TC-03": "active" if s.tc03_active else "off",
        "action": last_action(),
    }
    # Add all sub-dim values to history for charting
    for sub in PXI_SUBS + EXI_SUBS:
        _hist[sub['id']] = round(st.session_state.get(f"sub_{sub['id']}", 0), 2)
    s.history.append(_hist)


def force_exi_shock(magnitude=15):
    """Demo-only: drop EXI by magnitude to demonstrate TC-3 activation
    (cross-domain divergence scenario)."""
    s = st.session_state
    s.tick += 1
    pxi_target = 72 + (1 - s.automation_level) * 15.75 + (s.interaction_mult - 1) * 15.75
    s.PXI = float(np.clip(s.PXI + (pxi_target - s.PXI) * 0.15 + np.random.normal(0, 1.5), 35, 100))
    s.EXI = float(np.clip(s.EXI - magnitude, 35, 100))
    apply_tc_rules()
    update_sub_dimensions()
    _hist = {
        "tick":  s.tick,
        "time":  datetime.now().strftime("%H:%M:%S"),
        "PXI":   round(s.PXI, 2), "EXI": round(s.EXI, 2),
        "AAL":   round(c_AAL(), 2), "HOI": round(c_HOI(), 2),
        "IF":    round(c_IF(), 2),  "TR":  round(c_TR(), 2),
        "TC-01": s.tc01_phase,
        "TC-02": s.tc02_phase,
        "TC-03": "active" if s.tc03_active else "off",
        "action": f"EXI SHOCK -{magnitude} (demo) | {last_action()}",
    }
    for sub in PXI_SUBS + EXI_SUBS:
        _hist[sub['id']] = round(st.session_state.get(f"sub_{sub['id']}", 0), 2)
    s.history.append(_hist)


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
            s.tc01_driver = pick_random_driver(PXI_SUBS, seed_offset=s.tc01_engagements)
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
            s.tc01_driver = pick_random_driver(PXI_SUBS, seed_offset=s.tc01_engagements)
        else:
            s.automation_level = min(1.0, s.automation_level + RELEASE_AAL)
            s.interaction_mult = max(1.0, s.interaction_mult - RELEASE_IF)
            if s.automation_level >= 1.0 and s.interaction_mult <= 1.0:
                s.tc01_phase = "normal"
                s.automation_level = 1.0
                s.interaction_mult = 1.0
                s.tc01_stable_count = 0
                s.tc01_driver = None

    # TC-02 phase machine
    if s.tc02_phase == "normal":
        if s.EXI < TH_EXI:
            s.tc02_phase = "engaged"
            s.penalty_coeff = 0.0
            s.rationale_prob = 1.0
            s.tc02_stable_count = 0
            s.tc02_engagements += 1
            s.tc02_driver = pick_random_driver(EXI_SUBS, seed_offset=s.tc02_engagements + 50)
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
            s.tc02_driver = pick_random_driver(EXI_SUBS, seed_offset=s.tc02_engagements + 50)
        else:
            s.penalty_coeff = min(1.0, s.penalty_coeff + RELEASE_HOI)
            s.rationale_prob = max(0.5, s.rationale_prob - RELEASE_TR)
            if s.penalty_coeff >= 1.0 and s.rationale_prob <= 0.5:
                s.tc02_phase = "normal"
                s.penalty_coeff = 1.0
                s.rationale_prob = 0.5
                s.tc02_stable_count = 0
                s.tc02_driver = None

    # TC-03 status flag (binary; track transitions)
    prev_tc03 = s.tc03_active
    s.tc01_active = (s.tc01_phase == "engaged")
    s.tc02_active = (s.tc02_phase == "engaged")
    s.tc03_active = abs(s.PXI - s.EXI) > TH_GAP
    if s.tc03_active and not prev_tc03:
        s.tc03_engagements += 1

    # Track engagement duration for policy-layer timeout escalation
    if s.tc01_phase == "engaged":
        s.tc01_engaged_duration += 1
    else:
        s.tc01_engaged_duration = 0
    if s.tc02_phase == "engaged":
        s.tc02_engaged_duration += 1
    else:
        s.tc02_engaged_duration = 0
    if s.tc03_active:
        s.tc03_active_duration += 1
    else:
        s.tc03_active_duration = 0


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
            "AI governance (KFDA, MOHW). This is the Operational Layer in action — "
            "no internal policy layer escalation required yet. The hospital's "
            "internal policy layer (governance committee composed of members fluent "
            "in KFDA/MOHW principles) is informed for the next quarterly review, but "
            "no ad-hoc convening is needed unless the engagement exceeds the "
            "auto-resolution timeout. Importantly, this autonomous response "
            "demonstrates active accountability — the hospital is enforcing the "
            "national safety principle through its operational layer alone, reducing "
            "the load on both internal policy committees and national regulators."
        )
        sg_kr = (
            "자율 환자안전 대응 위상. HCEE가 환자 경험 신호에 자동 대응해 AI 자율성을 "
            "제한했으며, 이는 한국 의료 AI 거버넌스(식약처·복지부)의 '환자안전 우선' "
            "원칙과 일치합니다. 이는 운영 레이어가 작동 중인 상태이며 — 내부 정책 레이어 "
            "escalation은 아직 불필요. 병원의 내부 정책 레이어(식약처·복지부 원칙에 정통한 "
            "거버넌스 위원회 구성원)는 차기 분기별 검토를 위해 인지되어 있으나, "
            "auto-resolution timeout을 초과하지 않는 한 임시 소집은 필요 없습니다. "
            "중요한 점은 이 자율 대응이 능동적 책임 이행을 보여준다는 것입니다 — 병원이 "
            "운영 레이어만으로 국가 안전 원칙을 집행하고 있으며, 이로 인해 내부 정책 위원회와 "
            "국가 규제기관 양쪽의 부담이 모두 경감됩니다."
        )
    elif tc02 == "engaged":
        sg_en = (
            "Autonomous staff-trust restoration posture. HCEE has automatically "
            "elevated oversight (HOI) and transparency (TR), implementing the "
            "'explainability' and 'human accountability' principles of Korean medical "
            "AI guidelines without external mandate. This is the Operational Layer "
            "handling the issue — the internal policy layer (governance committee + "
            "medical ethics committee) is informed but not actively convened unless "
            "auto-resolution fails. The fact that the hospital can demonstrate this "
            "autonomous compliance — with audit trail — reduces the regulatory "
            "burden on KFDA/MOHW oversight and supports a lower inspection-frequency "
            "posture."
        )
        sg_kr = (
            "자율 직원 신뢰 회복 위상. HCEE가 자동으로 감독(HOI)과 투명성(TR)을 강화했으며, "
            "한국 의료 AI 가이드라인의 '설명 가능성' 및 '인간 책임' 원칙을 외부 지시 없이 "
            "이행하고 있습니다. 이는 운영 레이어가 처리 중인 상태이며 — 내부 정책 레이어"
            "(거버넌스 위원회 + 의료윤리위원회)는 인지되어 있으나 auto-resolution이 실패하지 "
            "않는 한 적극 소집되지 않습니다. 병원이 이 자율 준수를 — 감사 추적과 함께 — "
            "입증할 수 있다는 사실이 식약처·복지부 감독의 규제 부담을 감소시키며, 점검 "
            "빈도 완화 위상을 뒷받침합니다."
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
        "decision_support": _build_decision_support(s),
        "op_mode": (op_en, op_kr),
        "lever_rows": lever_rows,
        "self_gov": (sg_en, sg_kr),
        "action": (action_en, action_kr),
    }


def _build_decision_support(s):
    """Build the Decision Support items list — priority-tagged actionable
    recommendations combining (a) threshold-based TC counters and
    (b) per-AI 24h activity thresholds.
    Returns list of dicts: {priority, en, kr}."""
    items = []
    tc01 = s.tc01_phase
    tc02 = s.tc02_phase
    tc03 = s.tc03_active

    # ----- State-based immediate actions -----
    if tc03:
        items.append({
            "priority": "URGENT",
            "en": "Cross-domain divergence detected (TC-03). Notify hospital governance committee (internal policy layer) within 24h per HCEE protocol.",
            "kr": "도메인 간 격차 감지 (TC-03). HCEE 프로토콜에 따라 24시간 이내 병원 거버넌스 위원회(내부 정책 레이어) 통지 필수."
        })

    # ----- Policy-layer timeout escalation (auto-resolution boundary) -----
    # When auto-resolution layer fails to recover within timeout, escalate to
    # the internal policy layer — a committee of organization members fluent
    # in national medical AI principles (KFDA/MOHW guidelines, Patient Safety
    # Act, Medical Service Act). This is the subsidiarity principle of
    # multi-layer governance: handle issues at the lowest competent layer.
    if s.tc01_engaged_duration >= TC_ENGAGED_TIMEOUT:
        items.append({
            "priority": "URGENT",
            "en": (
                f"TC-01 has been ENGAGED for {s.tc01_engaged_duration} ticks without recovery — "
                f"auto-resolution boundary exceeded (timeout = {TC_ENGAGED_TIMEOUT} ticks). "
                "Escalate to internal policy layer (governance committee with members fluent in "
                "KFDA/MOHW principles) for root-cause investigation. The Operational Layer alone "
                "is no longer sufficient — human policy judgment is required."
            ),
            "kr": (
                f"TC-01이 {s.tc01_engaged_duration} tick째 회복 없이 ENGAGED 지속 — "
                f"자동 해결 경계 초과 (timeout {TC_ENGAGED_TIMEOUT} tick). "
                "근본 원인 조사를 위해 내부 정책 레이어(식약처·복지부 원칙에 정통한 거버넌스 "
                "위원회 구성원)에 escalate. 운영 레이어 단독으로는 더 이상 충분하지 않음 — "
                "인간의 정책 판단이 필요."
            ),
        })
    if s.tc02_engaged_duration >= TC_ENGAGED_TIMEOUT:
        items.append({
            "priority": "URGENT",
            "en": (
                f"TC-02 has been ENGAGED for {s.tc02_engaged_duration} ticks without recovery — "
                "staff trust restoration failing beyond AI lever scope. Escalate to internal "
                "policy layer for organizational intervention (training redesign, workflow "
                "audit, transparent communication campaign). AI levers alone cannot restore "
                "human trust at this duration."
            ),
            "kr": (
                f"TC-02가 {s.tc02_engaged_duration} tick째 회복 없이 ENGAGED 지속 — "
                "AI 레버 범위를 넘어선 직원 신뢰 회복 실패. 조직적 개입(교육 재설계, 워크플로우 "
                "감사, 투명 소통 캠페인)을 위해 내부 정책 레이어에 escalate. 이 지속 기간에서는 "
                "AI 레버만으로 인간 신뢰를 회복할 수 없음."
            ),
        })
    if s.tc03_active_duration >= TC03_ACTIVE_TIMEOUT:
        items.append({
            "priority": "URGENT",
            "en": (
                f"TC-03 cross-domain divergence has persisted for {s.tc03_active_duration} ticks "
                f"(threshold {TC03_ACTIVE_TIMEOUT}). Structural imbalance confirmed — escalate "
                "to internal policy layer for joint PXI-EXI signal recalibration review and "
                "potential root-cause investigation. This pattern suggests a systemic, not "
                "episodic, issue."
            ),
            "kr": (
                f"TC-03 도메인 격차가 {s.tc03_active_duration} tick째 지속 (임계값 "
                f"{TC03_ACTIVE_TIMEOUT}). 구조적 불균형 확정 — PXI-EXI 신호 공동 보정 검토 및 "
                "근본 원인 조사를 위해 내부 정책 레이어에 escalate. 이 패턴은 산발적이 아닌 "
                "시스템적 이슈를 시사함."
            ),
        })

    if tc01 == "engaged":
        items.append({
            "priority": "IMMEDIATE",
            "en": "Verify AAL restriction is applied to Tier 1 patient-safety AIs (Medical Imaging, Early Warning, Medication Safety) — effective AAL should be 0.80.",
            "kr": "Tier 1 환자안전 핵심 AI(영상판독·조기경보·처방안전)에 AAL 제한 적용 확인 — 유효 AAL 0.80이어야 함."
        })
        items.append({
            "priority": "TODAY",
            "en": "Brief nursing staff on increased clinical rounds protocol (IF +20% — e.g., 3.0 → 3.6 contacts/patient/day).",
            "kr": "간호 인력에 회진 빈도 증가 프로토콜 안내 (IF +20% — 예: 환자당 일 3.0 → 3.6회 접촉)."
        })
    if tc02 == "engaged":
        items.append({
            "priority": "IMMEDIATE",
            "en": "Confirm EMR rationale-display module is active across all AI decision points (TR = 1.00). Verify with random EMR audit.",
            "kr": "EMR 근거 표시 모듈이 모든 AI 의사결정 지점에서 활성화되었는지 확인 (TR = 1.00). EMR 무작위 감사 수행."
        })
        items.append({
            "priority": "TODAY",
            "en": "Hospital-wide notice: AI challenge protocol is now in zero-penalty mode (HOI = 1.00). Staff can flag AI decisions without procedural friction.",
            "kr": "병원 전체 공지: AI 이의제기 프로토콜이 무비용 모드로 전환 (HOI = 1.00). 직원이 절차적 부담 없이 AI 결정에 이의 가능."
        })
        items.append({
            "priority": "THIS WEEK",
            "en": "Schedule staff focus session on AI trust restoration. Document outcomes for next quarterly governance report.",
            "kr": "직원 대상 AI 신뢰 회복 포커스 세션 일정 수립. 결과를 차기 분기별 거버넌스 보고에 문서화."
        })
    if tc01 == "stabilizing" or tc02 == "stabilizing":
        items.append({
            "priority": "TODAY",
            "en": "Recovery in progress — confirm sustained PXI/EXI recovery (2-tick rule) before final lever de-escalation. Do not interrupt.",
            "kr": "회복 진행 중 — 최종 레버 해제 전 지속 회복 확인(2-tick 규칙) 필수. 중단 금지."
        })

    # ----- Threshold-based counter recommendations -----
    if s.tc01_engagements >= 3:
        items.append({
            "priority": "THIS WEEK",
            "en": f"TC-01 has fired {s.tc01_engagements} times — convene AAL baseline review with AI committee. Consider upstream AI configuration audit.",
            "kr": f"TC-01이 {s.tc01_engagements}회 발화 — AI 위원회와 AAL baseline 재검토 회의 소집. 상류 AI 설정 감사 검토."
        })
    if s.tc02_engagements >= 3:
        items.append({
            "priority": "THIS WEEK",
            "en": f"TC-02 has fired {s.tc02_engagements} times — review staff workload patterns and AI decision rationale clarity.",
            "kr": f"TC-02가 {s.tc02_engagements}회 발화 — 직원 부담 패턴 및 AI 의사결정 설명 명확성 검토."
        })
    if s.tc03_engagements >= 2:
        items.append({
            "priority": "REPORTING",
            "en": f"TC-03 has activated {s.tc03_engagements} times — cross-domain imbalance recurring. Include in next medical ethics committee report; consider joint PXI-EXI signal calibration review.",
            "kr": f"TC-03이 {s.tc03_engagements}회 활성 — 도메인 간 격차 반복 발생. 차기 의료윤리위원회 보고 포함; PXI-EXI 신호 보정 공동 검토 권장."
        })

    # ----- Per-AI activity-based recommendations -----
    items.extend([{"priority": p, "en": en, "kr": kr}
                  for p, en, kr in get_ai_specific_recommendations()])

    # ----- Reporting requirements -----
    if tc01 == "normal" and tc02 == "normal" and not tc03:
        items.append({
            "priority": "REPORTING",
            "en": "No external regulator notification required. Quarterly governance committee summary only.",
            "kr": "외부 규제기관 통지 불필요. 분기별 거버넌스 위원회 요약만 작성."
        })
    elif tc02 == "engaged":
        items.append({
            "priority": "REPORTING",
            "en": "Medical ethics committee notification recommended (not mandatory). KFDA/MOHW reporting threshold not yet met.",
            "kr": "의료윤리위원회 통지 권장 (의무 아님). 식약처·복지부 보고 임계점 미충족."
        })

    # Default fallback
    if not items:
        items.append({
            "priority": "THIS WEEK",
            "en": "No immediate action required. Continue routine monitoring across all four temporal layers.",
            "kr": "즉각 조치 불필요. 4개 시간 척도 레이어 전반에 걸친 정기 모니터링 지속."
        })

    return items


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
tab_overview, tab_loop, tab_ai, tab_learning = st.tabs([
    "Overview · 종합 대시보드",
    "Daily Governance Loop · 거버넌스 루프",
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
        bil_label("Current Drivers · 현재 driver 차원",
                  "Lowest sub-dimensions in PXI and EXI")
        _pxi_d, _pxi_dv = get_pxi_driver()
        _exi_d, _exi_dv = get_exi_driver()
        # Show top-3 lowest in each side
        _pxi_sorted = sorted(
            [(sub, st.session_state.get(f"sub_{sub['id']}", s.PXI)) for sub in PXI_SUBS],
            key=lambda x: x[1]
        )[:3]
        _exi_sorted = sorted(
            [(sub, st.session_state.get(f"sub_{sub['id']}", s.EXI)) for sub in EXI_SUBS],
            key=lambda x: x[1]
        )[:3]

        _drv_html = "<div style='font-size:0.82em; line-height:1.5;'>"
        _drv_html += f"<div style='color:{C_PXI}; font-weight:700; margin-bottom:4px;'>PXI side · 환자경험</div>"
        for i, (sub, val) in enumerate(_pxi_sorted):
            _flag = " ⚠ DRIVER" if i == 0 and val < TH_PXI else (" ⓘ low" if val < TH_PXI else "")
            _drv_html += (
                f"<div style='padding:2px 0;'>"
                f"<span style='display:inline-block; width:8px; height:8px; "
                f"background:{sub['color']}; border-radius:50%; margin-right:6px;'></span>"
                f"<span style='color:{C_TITLE};'>{sub['name']} · {sub['name_kr']}</span>"
                f"&nbsp;&nbsp;<strong>{val:.1f}</strong>"
                f"<span style='color:{C_ON}; font-size:0.85em;'>{_flag}</span>"
                f"</div>"
            )
        _drv_html += f"<div style='color:{C_EXI}; font-weight:700; margin-top:8px; margin-bottom:4px;'>EXI side · 직원경험</div>"
        for i, (sub, val) in enumerate(_exi_sorted):
            _flag = " ⚠ DRIVER" if i == 0 and val < TH_EXI else (" ⓘ low" if val < TH_EXI else "")
            _drv_html += (
                f"<div style='padding:2px 0;'>"
                f"<span style='display:inline-block; width:8px; height:8px; "
                f"background:{sub['color']}; border-radius:50%; margin-right:6px;'></span>"
                f"<span style='color:{C_TITLE};'>{sub['name']} · {sub['name_kr']}</span>"
                f"&nbsp;&nbsp;<strong>{val:.1f}</strong>"
                f"<span style='color:{C_ON}; font-size:0.85em;'>{_flag}</span>"
                f"</div>"
            )
        # Cross-domain pattern detection
        _ai_related_low = (
            ("pxi_ai_trust" in [sub['id'] for sub, _ in _pxi_sorted[:2]]) and
            (("exi_ai_trust" in [sub['id'] for sub, _ in _exi_sorted[:2]]) or
             ("exi_usability" in [sub['id'] for sub, _ in _exi_sorted[:2]]))
        )
        if _ai_related_low:
            _drv_html += (
                "<div style='margin-top:8px; padding:5px 8px; background:#FCEBEB; "
                f"border-left:3px solid {C_ON}; border-radius:3px; font-size:0.8em;'>"
                "<strong>Cross-domain pattern:</strong> AI-related dimensions weak on "
                "both sides → suggests EMR-AI integration friction."
                "</div>"
            )
        _drv_html += "</div>"
        st.markdown(_drv_html, unsafe_allow_html=True)

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

    # Analysis box (collapsible, color-coded, with Decision Support at top)
    _analysis = generate_overview_analysis()
    _op_en, _op_kr = _analysis["op_mode"]
    _sg_en, _sg_kr = _analysis["self_gov"]
    _ac_en, _ac_kr = _analysis["action"]

    # Build Decision Support items HTML
    _ds_items_html = ""
    for _item in _analysis["decision_support"]:
        _prio = _item["priority"]
        _prio_cls = "prio-" + _prio.lower().replace(" ", "")
        _ds_items_html += (
            f"<div class='decision-item'>"
            f"<span class='priority-badge {_prio_cls}'>{_prio}</span>"
            f"<div style='flex:1;'>"
            f"<div class='decision-text-en'>{_item['en']}</div>"
            f"<div class='decision-text-kr'>{_item['kr']}</div>"
            f"</div>"
            f"</div>"
        )

    # Lever rows HTML
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
        "<details class='analysis-box' open>"
        "<summary>📊 System Analysis · 시스템 분석</summary>"
        "<div class='analysis-content'>"

        # ===== Decision Support (TOP) =====
        "<div class='decision-block'>"
        "<div class='decision-block-title'>🎯 DECISION SUPPORT · 의사결정 지원</div>"
        f"{_ds_items_html}"
        "</div>"

        # ===== Divider =====
        "<div class='evidence-divider'>Evidence Base · 근거 자료</div>"

        # ===== 4 evidence sections =====
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
        "④ Trajectory · 추이 "
        "<span style='font-weight:400; font-size:0.85em; color:#7E776B;'>"
        "(where the system is heading)</span>"
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

    # ===== Sub-Dimension Breakdown · 인간 경험 차원 분해 =====
    st.markdown(
        "<div style='margin-top:18px; padding:10px 14px; "
        "background:linear-gradient(135deg, #F4F0E4 0%, #FAF6E8 100%); "
        f"border-left:5px solid {C_TITLE}; border-radius:6px;'>"
        f"<div style='font-weight:700; font-size:1.0em; color:{C_TITLE};'>"
        "🔍 Human Experience Sub-Dimensions · 인간 경험 차원 분해"
        "</div>"
        f"<div style='font-size:0.78em; color:{C_SUB}; margin-top:2px;'>"
        "PXI / EXI composite의 12개 sub-dimension 분해 · 차원별 신호 출처와 갱신 주기 표시 · "
        "driver 자동 식별"
        "</div>"
        "</div>",
        unsafe_allow_html=True
    )

    def _render_sub_block(sub_list, composite_value, composite_label, threshold,
                          color_composite, driver_sub_id):
        """Render a sub-dimension block: rows + multi-line chart."""
        # Get current values + sort
        rows = []
        for sub in sub_list:
            val = st.session_state.get(f"sub_{sub['id']}", composite_value)
            rows.append((sub, val))
        # Identify driver (lowest below threshold, OR the assigned driver)
        lowest = min(rows, key=lambda x: x[1])
        # Build HTML rows
        rows_html = ""
        for sub, val in rows:
            is_driver = (sub['id'] == driver_sub_id) or (
                sub['id'] == lowest[0]['id'] and val < threshold
            )
            is_low = (not is_driver) and (val < threshold)
            cls = "subdim-row-driver" if is_driver else (
                "subdim-row-low" if is_low else "")
            driver_flag = "<span class='subdim-driver-flag'>DRIVER</span>" if is_driver else (
                "<span class='subdim-driver-flag' style='background:#FAF6E8; color:#A0832E;'>LOW</span>"
                if is_low else ""
            )
            rows_html += (
                f"<div class='subdim-row {cls}'>"
                f"<div class='subdim-color-dot' style='background:{sub['color']};'></div>"
                f"<div class='subdim-name-block'>"
                f"<span class='subdim-name'>{sub['name']}</span>"
                f"<span class='subdim-name-kr'>{sub['name_kr']}</span>"
                f"</div>"
                f"<div class='subdim-value'>{val:.1f}</div>"
                f"{driver_flag}"
                f"<div class='subdim-source'>{sub['source']}<br/>{sub['source_kr']}</div>"
                f"</div>"
            )
        # Composite footer
        rows_html += (
            f"<div class='subdim-composite'>"
            f"Composite {composite_label}: {composite_value:.2f} "
            f"<span style='font-weight:400; font-size:0.85em; color:{C_SUB};'>"
            f"(threshold = {threshold})</span>"
            f"</div>"
        )
        return rows_html

    sub_col_pxi, sub_col_exi = st.columns(2)

    with sub_col_pxi:
        st.markdown(
            "<div class='subdim-block-title'>PXI · 6 Dimensions"
            "<span class='subdim-block-title-kr'>환자 경험 6 차원</span></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            _render_sub_block(PXI_SUBS, s.PXI, "PXI", TH_PXI, C_PXI, s.tc01_driver),
            unsafe_allow_html=True
        )

    with sub_col_exi:
        st.markdown(
            "<div class='subdim-block-title'>EXI · 6 Dimensions"
            "<span class='subdim-block-title-kr'>직원 경험 6 차원</span></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            _render_sub_block(EXI_SUBS, s.EXI, "EXI", TH_EXI, C_EXI, s.tc02_driver),
            unsafe_allow_html=True
        )

    # Multi-line time-series charts for sub-dimensions
    if s.history and len(s.history) >= 3:
        df_h_full = pd.DataFrame(s.history)
        sub_chart_col_pxi, sub_chart_col_exi = st.columns(2)

        with sub_chart_col_pxi:
            fig_psub = go.Figure()
            for sub in PXI_SUBS:
                if sub['id'] in df_h_full.columns:
                    is_driver = (sub['id'] == s.tc01_driver)
                    fig_psub.add_trace(go.Scatter(
                        x=df_h_full["tick"],
                        y=df_h_full[sub['id']],
                        name=sub['name'],
                        line=dict(color=sub['color'],
                                  width=3.5 if is_driver else 1.5),
                        mode="lines",
                        opacity=1.0 if is_driver else 0.7,
                    ))
            fig_psub.add_hline(y=TH_PXI, line_dash="dot",
                               line_color=C_PXI, opacity=0.4)
            fig_psub.update_layout(
                height=280, margin=dict(l=20, r=10, t=30, b=30),
                title=dict(text="PXI 6 차원 시계열", font=dict(size=12)),
                xaxis_title="tick", yaxis_title="value",
                yaxis_range=[35, 100],
                paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                font=dict(color=C_TITLE, size=10),
                legend=dict(orientation="v", y=1.0, x=1.02,
                            font=dict(size=9), bgcolor="rgba(255,255,255,0.8)"),
            )
            st.plotly_chart(fig_psub, use_container_width=True)

        with sub_chart_col_exi:
            fig_esub = go.Figure()
            for sub in EXI_SUBS:
                if sub['id'] in df_h_full.columns:
                    is_driver = (sub['id'] == s.tc02_driver)
                    fig_esub.add_trace(go.Scatter(
                        x=df_h_full["tick"],
                        y=df_h_full[sub['id']],
                        name=sub['name'],
                        line=dict(color=sub['color'],
                                  width=3.5 if is_driver else 1.5),
                        mode="lines",
                        opacity=1.0 if is_driver else 0.7,
                    ))
            fig_esub.add_hline(y=TH_EXI, line_dash="dot",
                               line_color=C_EXI, opacity=0.4)
            fig_esub.update_layout(
                height=280, margin=dict(l=20, r=10, t=30, b=30),
                title=dict(text="EXI 6 차원 시계열", font=dict(size=12)),
                xaxis_title="tick", yaxis_title="value",
                yaxis_range=[35, 100],
                paper_bgcolor=C_BG, plot_bgcolor="#FFFFFF",
                font=dict(color=C_TITLE, size=10),
                legend=dict(orientation="v", y=1.0, x=1.02,
                            font=dict(size=9), bgcolor="rgba(255,255,255,0.8)"),
            )
            st.plotly_chart(fig_esub, use_container_width=True)
    else:
        st.caption("Run 3+ ticks to see sub-dimension time-series.")

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


# ----- Tab 3: Real-time AI Monitoring -----
with tab_ai:
    bil_h3("Real-time AI Monitoring", "실시간 AI 모니터링")
    bil_caption(
        "Per-AI operational status · effective AAL · 24h activity · governance posture",
        "AI별 운영 상태 · 유효 AAL · 24h 활동 · 거버넌스 위상"
    )

    # ===== Summary bar =====
    _status_count = {"green": 0, "amber": 0, "amber-light": 0, "red": 0, "violet": 0}
    _total_activity = 0
    _total_escalations = 0
    _total_errors = 0
    _ai_details = []
    for _ai in AI_CATALOG:
        _st_en, _st_kr, _color, _sym = get_ai_status(_ai)
        _stats = get_ai_24h_stats(_ai)
        _eff_aal = get_effective_ai_aal(_ai)
        _status_count[_color] = _status_count.get(_color, 0) + 1
        _total_activity += _stats["activity"]
        _total_escalations += _stats["escalations"]
        _total_errors += _stats["errors"]
        _ai_details.append((_ai, _st_en, _st_kr, _color, _sym, _stats, _eff_aal))

    _active = _status_count["green"]
    _restricted = _status_count["amber"] + _status_count["amber-light"]
    _review = _status_count["red"]
    _override = _status_count["violet"]

    _tier_count = {1: 0, 2: 0, 3: 0}
    for _ai in AI_CATALOG:
        _tier_count[_ai["tier"]] += 1

    _summary_html = (
        "<div class='ai-summary-bar'>"
        f"Total monitored: <strong>{len(AI_CATALOG)} AIs</strong> "
        f"&nbsp;|&nbsp; Tier 1 (Critical): {_tier_count[1]} "
        f"&nbsp;|&nbsp; Tier 2 (Standard): {_tier_count[2]} "
        f"&nbsp;|&nbsp; Tier 3 (Operational): {_tier_count[3]}"
        "<br/>"
        f"Status: <strong style='color:#5A7548;'>● Active {_active}</strong> "
        f"&nbsp;|&nbsp; <strong style='color:#B4953C;'>◐ Restricted {_restricted}</strong> "
        f"&nbsp;|&nbsp; <strong style='color:#7A2E2E;'>⚠ Under Review {_review}</strong> "
        f"&nbsp;|&nbsp; <strong style='color:#7B4CBF;'>◈ Manual Override {_override}</strong>"
        "<br/>"
        f"24h totals: <strong>{_total_activity:,}</strong> operations "
        f"&nbsp;|&nbsp; <strong>{_total_escalations}</strong> escalations "
        f"&nbsp;|&nbsp; <strong>{_total_errors}</strong> errors"
        "</div>"
    )
    st.markdown(_summary_html, unsafe_allow_html=True)

    # ===== Per-AI cards =====
    for _ai, _st_en, _st_kr, _color, _sym, _stats, _eff_aal in _ai_details:
        _auto_aal = compute_ai_auto_aal(_ai["tier"])
        _slider_key = f"ai_aal_slider_{_ai['id']}"
        # Lazy-init slider state if missing
        if _slider_key not in st.session_state:
            st.session_state[_slider_key] = _auto_aal
        _is_manual = abs(_eff_aal - _auto_aal) > 0.01
        _override_note = ""
        if _is_manual:
            _override_note = (
                f"<span style='color:#7B4CBF; font-size:0.78em;'>"
                f"&nbsp;(manual; auto would be {_auto_aal:.2f})</span>"
            )

        _card_html = (
            f"<div class='ai-card ai-card-{_color}'>"
            f"<div class='ai-card-header'>"
            f"<div>"
            f"<span class='ai-card-id'>{_ai['id']}</span>"
            f"<span class='ai-card-name'>{_ai['name']}</span>"
            f"<span class='ai-card-name-kr'>· {_ai['name_kr']}</span>"
            f"</div>"
            f"<span class='ai-card-tier ai-tier-{_ai['tier']}'>"
            f"Tier {_ai['tier']} · {_ai['kfda_class']}"
            f"</span>"
            f"</div>"
            f"<div class='ai-card-meta'>"
            f"{_ai['category']}<br/>{_ai['category_kr']} · 책임 부서: {_ai['dept']}"
            f"</div>"
            f"<div class='ai-card-status-row'>"
            f"<span class='ai-status-badge ai-status-{_color}'>"
            f"{_sym} {_st_en} · {_st_kr}"
            f"</span>"
            f"<span class='ai-aal-display'>"
            f"Effective AAL: <strong>{_eff_aal:.2f}</strong>{_override_note}"
            f"</span>"
            f"</div>"
            f"<div class='ai-card-stats'>"
            f"24h: {_stats['activity']} operations · {_stats['escalations']} escalations · "
            f"{_stats['errors']} errors · {_stats['second_opinions']} second-opinion requests"
            f"</div>"
            f"<div class='ai-card-footer'>"
            f"{_ai['kfda_class']} · {_ai['dept_en']} · "
            f"Auto AAL (from TC state): {_auto_aal:.2f}"
            f"</div>"
            f"</div>"
        )
        st.markdown(_card_html, unsafe_allow_html=True)

        # Per-AI AAL slider + Sync-to-Auto button
        _slider_col, _reset_col = st.columns([5, 1])
        with _slider_col:
            st.slider(
                f"AAL · {_ai['id']}",
                min_value=0.0, max_value=1.0,
                step=0.05,
                key=_slider_key,
                label_visibility="collapsed",
                help=f"Manual AAL for {_ai['name']}. Auto value (from TC state): {_auto_aal:.2f}. Click 'Auto' to sync."
            )
        with _reset_col:
            if st.button("Auto", key=f"ai_reset_{_ai['id']}",
                         use_container_width=True,
                         help=f"Sync AAL to current auto value ({_auto_aal:.2f})"):
                st.session_state[_slider_key] = _auto_aal
                st.rerun()





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
