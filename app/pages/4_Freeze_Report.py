import streamlit as st
import pandas as pd
from core.snapshot import SnapshotManager
from core.report import ReportGenerator
from core.decision import DecisionEngine
from core.priority import PriorityCalculator
import sys
import os

# Ensure proper importing
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))
from core.quality import QualityGateway
from core.io import DataLoader
from core.sidebar import render_sidebar
from core.i18n import I18nManager
from core.scoring import (
    prepare_candidates,
    compute_driver_scores,
    get_kpi_latest
)

st.set_page_config(page_title="Report & Freeze", layout="wide")
render_sidebar()
st.title(f"📑 {I18nManager.get('sidebar.freeze_report', 'Report Generation & Freeze')}")

# 1. State Check
if 'config' not in st.session_state:
    st.warning("Please configure project first.")
    st.stop()

config = st.session_state.config
survey_df = st.session_state.get('survey_data')
kpi_df = st.session_state.get('kpi_data')

# 2. Re-calculate current state for Report
# (In a real app, this should be cached in session state more cleanly)
# Ideally, we should unify the logic from Decision_Board here or in a dedicated service
# For MVP, we'll re-run the logic quickly

def get_current_state():
    decision_engine = DecisionEngine()
    priority_calc = PriorityCalculator(config.priority_weights)
    
    # Context (simplified MVP logic)
    evidence_context = compute_driver_scores(survey_df, config.drivers)
    if kpi_df is not None:
        evidence_context['turnover_rate_junior'] = get_kpi_latest(kpi_df, 'turnover_rate_junior')
        evidence_context['avg_overtime_hours'] = get_kpi_latest(kpi_df, 'avg_overtime_hours')
        evidence_context['manager_overtime'] = get_kpi_latest(kpi_df, 'manager_overtime')
            
    penalty = st.session_state.get('survey_quality', {}).get('penalty', 0.0)
    
    # Use shared logic consistent with Decision Board
    candidates = prepare_candidates(
        config.decision_cards,
        decision_engine,
        evidence_context,
        penalty,
        overrides=st.session_state
    )

    # Use same ranking method as Decision Board
    method = st.session_state.get("ranking_method", "SAW (Transparent)")
    ranked = priority_calc.rank_candidates(candidates, method=method)
    
    states = []
    for item in ranked:
        s = item["_state"]
        s.total_priority = item["score"]
        # Score Result (details + score)
        score_res = item.get("_details", {})
        score_res["score"] = item["score"]
        states.append((item["_card"], s, score_res))
        
    return states, evidence_context

current_states, context = get_current_state()

# 3. Preview
st.subheader("Summarized Status")
df_summary = pd.DataFrame([
    {
        "ID": cs[0].id,
        "Title": cs[0].title,
        "Status": cs[1].status,
        "Priority": f"{cs[1].total_priority:.2f}"
    }
    for cs in current_states
])
st.dataframe(df_summary)

# 4. Freeze Action
st.subheader("Freeze Snapshot")
st.markdown("Create an immutable snapshot of the current state before generating final reports.")

snapshot_manager = SnapshotManager()

col1, col2 = st.columns(2)
with col1:
    snap_name = st.text_input("Snapshot Name / Note", "Meeting Preparation")
    
if st.button("❄️ Freeze Current State"):
    # Mock Wave
    from data.models import Wave
    wave = Wave(id="W001", name=snap_name)
    # Ideally populate wave with states...
    
    snap = snapshot_manager.freeze(wave, "config_hash")
    st.session_state['last_snapshot'] = snap
    st.success(f"Snapshot Frozen: {snap.id}")

# 5. Report Generation
st.subheader("Export Report")

if 'last_snapshot' in st.session_state:
    st.info(f"Target Snapshot: {st.session_state['last_snapshot'].id}")
else:
    st.warning("You are generating a report on the LIVE (unfrozen) state.")

report_gen = ReportGenerator(config)

if st.button("📄 Generate Decision Memo (DOCX)"):
    docx_buffer = report_gen.generate_docx(
        wave_data={"status": "DRAFT"},
        decision_states=current_states,
        snapshot_id=st.session_state.get('last_snapshot', type('obj', (object,), {'id': 'LIVE'})).id
    )
    
    st.download_button(
        label="Download DOCX",
        data=docx_buffer,
        file_name=f"Decision_Memo_{config.customer_name}.docx",
        mime="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    )
