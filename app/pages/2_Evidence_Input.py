import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.quality import QualityGateway
from core.io import DataLoader
import os

st.set_page_config(page_title="Evidence Input", layout="wide")
st.title("📥 Evidence Ingestion & Quality Gate")

# 1. Initialize Quality Gateway
if 'config' not in st.session_state:
    st.warning("Please load config from Home page first.")
    st.stop()

gateway = QualityGateway(st.session_state.config.quality_gates)
data_loader = DataLoader()

# 2. Upload Survey Data
st.subheader("1. Survey Data (Quantitative)")
uploaded_survey = st.file_uploader("Upload Survey CSV", type=["csv"])

if uploaded_survey:
    df_survey = pd.read_csv(uploaded_survey)
    st.write(f"Loaded {len(df_survey)} responses.")
    
    # Run Quality Check
    penalty, checks = gateway.check_survey_data(df_survey)
    
    # Check Cronbach's Alpha for drivers
    drivers = st.session_state.config.drivers
    alpha_penalty, alpha_checks = gateway.check_cronbach_alpha(df_survey, drivers)
    
    penalty += alpha_penalty
    penalty = min(penalty, 1.0) # Cap
    checks.extend(alpha_checks)
    
    # Display Checks
    col1, col2 = st.columns([1, 3])
    with col1:
        st.metric("Structure Confidence", f"{(1.0 - penalty):.0%}", delta=f"-{penalty:.0%}" if penalty > 0 else "OK")
    
    with col2:
        for check in checks:
            color = "red" if check.status == "fail" else "orange" if check.status == "warn" else "green"
            st.markdown(f":{color}[**{check.name}**]: {check.message}")
            
    # Save to session (even if warned)
    if st.button("Ingest Survey Data"):
        st.session_state.survey_data = df_survey
        st.session_state.survey_quality = {"penalty": penalty, "checks": checks}
        st.success("Survey data ingested for analysis.")

# 3. Upload KPI Data
st.subheader("2. KPI Data (Facts)")
uploaded_kpi = st.file_uploader("Upload KPI CSV", type=["csv"])
if uploaded_kpi:
    df_kpi = pd.read_csv(uploaded_kpi)
    st.write(f"Loaded {len(df_kpi)} records.")
    
    if st.button("Ingest KPI Data"):
        st.session_state.kpi_data = df_kpi
        st.success("KPI data ingested.")

# 4. Qualitative Inputs (Interviews) - MVP Placeholder
st.subheader("3. Interview Notes (Qualitative)")
st.info("Qualitative input module coming in Phase 2.")

st.markdown("---")
if st.button("🗑️ Clear All Ingested Data"):
    if 'survey_data' in st.session_state: del st.session_state['survey_data']
    if 'kpi_data' in st.session_state: del st.session_state['kpi_data']
    if 'survey_quality' in st.session_state: del st.session_state['survey_quality']
    st.success("All data cleared from session.")
    st.rerun()
