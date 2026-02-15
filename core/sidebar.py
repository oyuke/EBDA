import streamlit as st
from core.i18n import I18nManager

def render_sidebar():
    with st.sidebar:
        st.title(I18nManager.get("sidebar.home", "Home"))
        
        # Navigation
        st.page_link("main.py", label=I18nManager.get("sidebar.home", "Home"), icon="🏠")
        st.page_link("pages/1_Decision_Board.py", label=I18nManager.get("sidebar.decision_board", "Decision Board"), icon="🚦")
        st.page_link("pages/2_Evidence_Input.py", label=I18nManager.get("sidebar.evidence_input", "Evidence Input"), icon="📝")
        st.page_link("pages/3_Settings.py", label=I18nManager.get("sidebar.settings", "Settings"), icon="⚙️")
        st.page_link("pages/4_Freeze_Report.py", label=I18nManager.get("sidebar.freeze_report", "Freeze Report"), icon="📑")
        st.page_link("pages/5_Data_Tools.py", label=I18nManager.get("sidebar.data_tools", "Data Tools"), icon="🛠️")
        
        st.markdown("---")
        
        # Config Status
        if "config" in st.session_state:
            ctx = st.session_state.config.customer_name
            st.caption(f"Active: **{ctx}**")
        else:
            st.caption("No Config Loaded")
