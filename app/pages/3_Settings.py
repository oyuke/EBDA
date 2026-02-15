import streamlit as st
import yaml
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))


st.set_page_config(page_title="Settings", layout="wide")
st.title("⚙️ Helper & Configuration")

if 'config' in st.session_state:
    config = st.session_state.config
    st.subheader(f"Current Config: {config.customer_name}")
    st.info(f"Version: {config.version}")
    
    st.subheader("Priority Weights (SAW)")
    st.json(config.priority_weights)
    
    st.subheader("Quality Gates")
    st.json(config.quality_gates)
    
    with st.expander("Show Full Configuration (YAML)"):
        # Reload raw yaml for display
        with open("configs/customer_default.yaml", "r", encoding="utf-8") as f:
            st.code(f.read(), language="yaml")
else:
    st.warning("Config not loaded.")

st.markdown("---")
st.subheader("System Actions")
if st.button("Reset Session State"):
    for key in list(st.session_state.keys()):
        del st.session_state[key]
    st.experimental_rerun()
