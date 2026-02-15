import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.quality import QualityGateway
from core.io import DataLoader, PreferenceManager
from core.templates import DataTemplates
from core.llm import LLMClient
from core.security import SecurityManager

st.set_page_config(page_title="Evidence Input", layout="wide")
st.title("📥 Evidence Ingestion & Quality Gate")

# 1. Initialize Quality Gateway
if 'config' not in st.session_state:
    st.warning("Please load config from Home page first.")
    st.stop()

gateway = QualityGateway(st.session_state.config.quality_gates)
data_loader = DataLoader()

# --- Tabs ---
tab1, tab2, tab3, tab4 = st.tabs(["1. Upload Survey", "2. Upload KPI", "3. ✏️ Edit & AI Copilot", "4. Quality Report"])

# --- Tab 1: Survey Upload ---
with tab1:
    st.subheader("1. Survey Data (Quantitative)")
    
    with st.expander("ℹ️ Help & Templates"):
        st.markdown("### CSV Format")
        st.markdown("- Columns: Driver IDs (e.g. D1, D2). Rows: Respondents.")
        st.download_button("📥 Download Sample Survey", 
                           DataTemplates.get_survey_template().to_csv(index=False), 
                           "sample_survey.csv")

    uploaded_survey = st.file_uploader("Upload Survey CSV", type=["csv"], key="survey_upl")
    if uploaded_survey:
        df_survey = pd.read_csv(uploaded_survey)
        st.write(f"Loaded {len(df_survey)} responses.")
        
        # Initial Check
        penalty, checks = gateway.check_survey_data(df_survey)
        st.metric("Structure Confidence", f"{(1.0 - penalty):.0%}")
        
        if st.button("Ingest Survey Data", key="ingest_survey"):
            st.session_state.survey_data = df_survey
            
            drivers = st.session_state.config.drivers
            alpha_penalty, alpha_checks = gateway.check_cronbach_alpha(df_survey, drivers)
            final_penalty = min(penalty + alpha_penalty, 1.0)
            checks.extend(alpha_checks)
            
            st.session_state.survey_quality = {"penalty": final_penalty, "checks": checks}
            st.success(f"Ingested {len(df_survey)} responses.")
            st.rerun()

    if 'survey_data' in st.session_state:
        st.info(f"✅ Active Data: {len(st.session_state.survey_data)} records loaded.")

# --- Tab 2: KPI Upload ---
with tab2:
    st.subheader("2. KPI Data (Facts)")
    uploaded_kpi = st.file_uploader("Upload KPI CSV", type=["csv"], key="kpi_upl")
    if uploaded_kpi:
        df_kpi = pd.read_csv(uploaded_kpi)
        st.write(f"Loaded {len(df_kpi)} records.")
        if st.button("Ingest KPI Data", key="ingest_kpi"):
            st.session_state.kpi_data = df_kpi
            st.success(f"Ingested {len(df_kpi)} records.")
            st.rerun()

# --- Tab 3: Edit & Copilot ---
with tab3:
    st.subheader("Interactive Editor & AI Copilot")
    
    # Determine Active DataFrame
    if 'survey_data' in st.session_state:
        df_active = st.session_state.survey_data
    else:
        st.warning("No survey data loaded yet. You can generate synthetic data below.")
        
        # Infer columns from Drivers
        drivers = st.session_state.config.drivers
        cols = []
        for d in drivers:
             if d.survey_items:
                 cols.extend(d.survey_items)
             else:
                 cols.append(d.id)
        # Unique cols while preserving order
        cols = list(dict.fromkeys(cols))
        df_active = pd.DataFrame(columns=cols)

    # --- AI Copilot Section ---
    with st.expander("✨ AI Copilot (Generate/Augment Data)", expanded=False):
        # Provider Selection (Shared Prefs)
        saved_provider = PreferenceManager.get("copilot_provider", "OpenAI")
        prov_options = ["OpenAI", "Google (Gemini)", "OpenRouter"]
        try:
            def_idx = prov_options.index(saved_provider)
        except:
            def_idx = 0
            
        def on_prov_change():
            if 'evidence_copilot_provider' in st.session_state:
                 PreferenceManager.save("copilot_provider", st.session_state.evidence_copilot_provider)

        llm_provider = st.selectbox("LLM Provider", prov_options, index=def_idx, key="evidence_copilot_provider", on_change=on_prov_change)
        
        # Model Selection
        api_key = SecurityManager.get_api_key(llm_provider)
        if api_key:
            if st.button("🔄 Fetch Models", key="fetch_models_ev"):
                with st.spinner("Fetching..."):
                    try:
                        models = LLMClient.fetch_available_models(llm_provider, api_key)
                        st.session_state[f"models_{llm_provider}_ev"] = models
                    except: st.error("Fetch failed.")
            
            model_list = st.session_state.get(f"models_{llm_provider}_ev", [])
            if not model_list:
                # Default fallbacks
                if llm_provider=="OpenAI": model_list=["gpt-4o", "gpt-4-turbo"]
                elif llm_provider=="Google (Gemini)": model_list=["gemini-1.5-flash"]
                else: model_list=["google/gemini-2.0-flash-001"]
            
            selected_model = st.selectbox("Model", model_list, key="evidence_model_sel")
            
            if st.button("Initialize Copilot", key="init_copilot_ev"):
                 st.session_state['ev_llm'] = LLMClient(llm_provider, api_key, selected_model)
                 st.success(f"Ready ({selected_model})!")
        else:
            st.error("API Key missing (Set in Data Tools).")
            
        st.markdown("---")

        # Generate Action
        st.markdown("#### Generate Synthetic Responses")
        n_samples = st.number_input("Number of samples", 1, 50, 10, key="n_samples_ev")
        
        if st.button("Generate Responses"):
            if 'ev_llm' in st.session_state:
                current_drivers = [d.id for d in st.session_state.config.drivers]
                base_prompt = DataTemplates.get_llm_prompt_survey(str(current_drivers))
                # Explicitly request CSV format compatible with df_active columns if possible
                cols_str = ",".join(list(df_active.columns)) if not df_active.empty else "Q1,Q2..."
                prompt = base_prompt + f"\n\nTASK: Generate exactly {n_samples} CSV rows (no header) representing realistic survey answers (1-5 scale). Columns should match the drivers."
                
                with st.spinner("Generating..."):
                    try:
                        res = st.session_state['ev_llm'].generate_suggestions(str(df_active.head().to_csv()), "Survey Data") 
                        st.session_state['ev_suggestion'] = res
                    except Exception as e:
                        st.error(f"Error: {e}")
            else:
                st.warning("Init Copilot first.")
        
        if 'ev_suggestion' in st.session_state:
            st.caption("Suggestion:")
            st.code(st.session_state['ev_suggestion'], language="csv")
            
            if st.button("Append to Active Data"):
                import io
                try:
                    raw_csv = st.session_state['ev_suggestion'].replace("```csv", "").replace("```", "").strip()
                    new_rows = pd.read_csv(io.StringIO(raw_csv), header=None)
                    
                    # Ensure matching columns logic
                    if len(df_active.columns) > 0:
                        if len(new_rows.columns) == len(df_active.columns):
                            new_rows.columns = df_active.columns
                            combined = pd.concat([df_active, new_rows], ignore_index=True)
                        else:
                             st.warning(f"Column mismatch. Active: {len(df_active.columns)}, Generated: {len(new_rows.columns)}. Trying to match by position.")
                             new_rows.columns = df_active.columns 
                             combined = pd.concat([df_active, new_rows], ignore_index=True)
                    else:
                        combined = new_rows # First load
                    
                    st.session_state.survey_data = combined
                    del st.session_state['ev_suggestion']
                    st.success(f"Appended {len(new_rows)} rows!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error parsing: {e}")

    # --- Editor ---
    st.markdown("### Active Data Editor")
    edited_df = st.data_editor(df_active, num_rows="dynamic", key="editor_survey_ev_main")
    
    if st.button("Save Changes & Re-Validate"):
        if not edited_df.empty:
            penalty, checks = gateway.check_survey_data(edited_df)
            drivers = st.session_state.config.drivers
            alpha_penalty, alpha_checks = gateway.check_cronbach_alpha(edited_df, drivers)
            
            full_penalty = min(penalty + alpha_penalty, 1.0)
            checks.extend(alpha_checks)
            
            st.session_state.survey_data = edited_df
            st.session_state.survey_quality = {"penalty": full_penalty, "checks": checks}
            st.success("Saved!")
            st.rerun()
        else:
            st.warning("Data is empty.")

# --- Tab 4: Quality Report ---
with tab4:
    if 'survey_quality' in st.session_state:
        q = st.session_state.survey_quality
        st.metric("Overall Quality Score", f"{(1.0 - q['penalty']):.0%}")
        for c in q['checks']:
            icon = "🔴" if c.status=="fail" else "🟠" if c.status=="warn" else "🟢"
            st.markdown(f"{icon} **{c.name}**: {c.message}")
    else:
        st.info("No data ingested yet.")

st.markdown("---")
if st.button("🗑️ Clear All Data"):
    for k in ['survey_data', 'kpi_data', 'survey_quality']:
        if k in st.session_state: del st.session_state[k]
    st.rerun()
