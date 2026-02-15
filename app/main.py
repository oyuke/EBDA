import streamlit as st
import pandas as pd
import os
import sys

# Add project root to sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from core.io import ConfigLoader, PreferenceManager
from core.i18n import I18nManager
from core.quality import QualityGateway
from core.decision import DecisionEngine
from core.priority import PriorityCalculator

st.set_page_config(
    page_title="Evidence-Based DSS",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize Language Session State
if "language" not in st.session_state:
    st.session_state["language"] = PreferenceManager.get("language", "en")

# Initialize Session State
if 'config' in st.session_state:
    st.info(f"✅ {I18nManager.get('home.status_loaded', 'Loaded Configuration')}: {st.session_state.config.customer_name} (v{st.session_state.config.version})")
else:
    st.warning(f"⚠️ {I18nManager.get('home.status_missing', 'No configuration loaded. Please initialize the project.')}")
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("A. Load Demo Project")
        if st.button(I18nManager.get("home.action_load", "Load Default Demo (Sample)")):
            loader = ConfigLoader("configs/customer_default.yaml")
            st.session_state.config = loader.load_config()
            st.success("Demo configuration loaded!")
            st.rerun()
            
    with col2:
        st.subheader("B. Upload Configuration")
        uploaded_config = st.file_uploader("Upload config.yaml", type=["yaml", "yml"])
        if uploaded_config:
            # Need to implement loader from stream or save temp
            content = uploaded_config.read()
            # For MVP, simple parsing using ConfigLoader logic but from string?
            # ConfigLoader takes path. Let's make a temp adapter or just parse here.
            import yaml
            from data.models import AppConfig
            try:
                data = yaml.safe_load(content)
                config = AppConfig(**data)
                st.session_state.config = config
                st.success(f"Configuration '{config.customer_name}' loaded successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Failed to parse config: {e}")

    # Stop execution until config is loaded
    st.stop()

if 'waves' not in st.session_state:
    st.session_state.waves = {} # Load from DB or file later check snapshot

from core.sidebar import render_sidebar

# ... (inside config check) ...

# Render Custom Sidebar
render_sidebar()

st.title(I18nManager.get("home.title", "🛡️ Evidence-Based Decision Support System"))
st.markdown(I18nManager.get("home.subtitle", """
> **Paradigm Shift**: From "Measurement" to "Decision Making".
> This system supports transparent, evidence-based decision making with quality gates.
"""))

st.info(f"{I18nManager.get('home.status_loaded', 'Loaded Configuration')}: {st.session_state.config.customer_name} (v{st.session_state.config.version})")

# Navigation helper (simulated)
st.markdown(f"### {I18nManager.get('home.quick_nav', 'Quick Navigation')}")
col1, col2, col3 = st.columns(3)
with col1:
    if st.button(I18nManager.get("sidebar.decision_board", "Go to Decision Board"), use_container_width=True):
        st.switch_page("pages/1_Decision_Board.py")
with col2:
    if st.button(I18nManager.get("sidebar.evidence_input", "Input Evidence"), use_container_width=True):
        st.switch_page("pages/2_Evidence_Input.py")
with col3:
    if st.button(I18nManager.get("sidebar.settings", "Manage Settings"), use_container_width=True):
        st.switch_page("pages/3_Settings.py")

# Debug info (optional)
with st.expander("Debug: Current State"):
    st.write(st.session_state)
