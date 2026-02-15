import streamlit as st
import pandas as pd
import os
from core.io import ConfigLoader
from core.quality import QualityGateway
from core.decision import DecisionEngine
from core.priority import PriorityCalculator

st.set_page_config(
    page_title="Evidence-Based DSS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Session State
if 'config' not in st.session_state:
    loader = ConfigLoader("configs/customer_default.yaml")
    st.session_state.config = loader.load_config()

if 'waves' not in st.session_state:
    st.session_state.waves = {} # Load from DB or file later check snapshot

st.title("🛡️ Evidence-Based Decision Support System")
st.markdown("""
> **Paradigm Shift**: From "Measurement" to "Decision Making".
> This system supports transparent, evidence-based decision making with quality gates.
""")

st.info(f"Loaded Configuration: {st.session_state.config.customer_name} (v{st.session_state.config.version})")

# Navigation helper (simulated)
st.markdown("### Quick Navigation")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button("Go to Decision Board", use_container_width=True):
        st.switch_page("pages/1_Decision_Board.py")
with col2:
    if st.button("Input Evidence", use_container_width=True):
        st.switch_page("pages/2_Evidence_Input.py")
with col3:
    if st.button("Manage Settings", use_container_width=True):
        st.switch_page("pages/3_Settings.py")

# Debug info (optional)
with st.expander("Debug: Current State"):
    st.write(st.session_state)
