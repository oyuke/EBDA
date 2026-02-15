import streamlit as st
import pandas as pd
import json
import yaml
from core.converter import DataConverter
import core.io
import importlib
importlib.reload(core.io)
from core.io import ConfigLoader, PreferenceManager
from data.models import DecisionCardConfig, DriverConfig
from core.templates import DataTemplates
from core.security import SecurityManager
from core.llm import LLMClient
import io

from core.i18n import I18nManager
from core.state_manager import StatePersistence

from core.sidebar import render_sidebar

st.set_page_config(page_title="Data Tools", layout="wide")
render_sidebar()

st.title(f"🛠️ {I18nManager.get('sidebar.data_tools', 'Data Management & Conversion')}")

st.markdown("Convert human-editable CSVs into JSON/YAML configuration for the app.")

tab1, tab2, tab3, tab4, tab5, tab6, tab7 = st.tabs(["1. Config Builder", "2. Data Converter", "3. Export Current", "4. Interactive Editor", "5. AI Generator", "6. 🔐 API Settings", "7. 🌐 Localization"])

# --- Tab 1: Config Builder ---
with tab1:
    st.subheader("Build Configuration from CSV")
    st.info("Download templates to see the required format.")
    
    c1, c2 = st.columns(2)
    with c1:
        st.download_button("📥 Download Drivers Template", 
                           DataTemplates.get_driver_template().to_csv(index=False), 
                           "template_drivers.csv")
    with c2:
        st.download_button("📥 Download Cards Template", 
                           DataTemplates.get_card_template().to_csv(index=False), 
                           "template_cards.csv")
    
    st.markdown("---")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("### Step A: Upload Drivers Definition (CSV)")
        uploaded_drivers = st.file_uploader("Upload Drivers CSV", type=["csv"], key="driver_csv")
        if uploaded_drivers:
            df_drivers = pd.read_csv(uploaded_drivers)
            st.dataframe(df_drivers.head())
            drivers_json = DataConverter.csv_to_drivers(df_drivers)
            st.success(f"Parsed {len(drivers_json)} drivers.")
            
    with col2:
        st.markdown("### Step B: Upload Decision Cards (CSV)")
        uploaded_cards = st.file_uploader("Upload Cards CSV", type=["csv"], key="card_csv")
        if uploaded_cards:
            df_cards = pd.read_csv(uploaded_cards)
            st.dataframe(df_cards.head())
            cards_json = DataConverter.csv_to_decision_card(df_cards)
            st.success(f"Parsed {len(cards_json)} cards.")

    if uploaded_drivers and uploaded_cards:
        st.markdown("### Step C: Generate YAML Config")
        if st.button("Generate Config File"):
            config_dict = {
                "version": "1.0",
                "customer_name": "New Project",
                "priority_weights": {"impact": 1.0, "urgency": 1.0, "uncertainty": 1.0},
                "quality_gates": {"min_n_count": 5, "max_missing_ratio": 0.2},
                "drivers": [d.dict() for d in drivers_json],
                "decision_cards": [c.dict() for c in cards_json]
            }
            yaml_str = yaml.dump(config_dict, sort_keys=False)
            st.download_button("Download config.yaml", yaml_str, "custom_config.yaml", "text/yaml")

# --- Tab 2: Data Converter ---
with tab2:
    st.subheader("Convert Evidence CSV to JSON")
    st.info("Feature coming in next update: Convert raw survey CSV to standardized JSON format.")

# --- Tab 3: Export Current ---
with tab3:
    if 'config' in st.session_state:
        st.subheader("Export Active Configuration")
        config = st.session_state.config
        
        # Drivers to CSV
        df_drivers = DataConverter.drivers_to_csv(config.drivers)
        st.download_button("Download Drivers CSV", df_drivers.to_csv(index=False), "drivers.csv", "text/csv")
        
        # Cards to CSV
        df_cards = DataConverter.decision_card_to_csv(config.decision_cards)
        st.download_button("Download Cards CSV", df_cards.to_csv(index=False), "cards.csv", "text/csv")
        
        # Full YAML
        full_yaml = yaml.dump(config.dict(), sort_keys=False)
        st.download_button("Download Full Config YAML", full_yaml, "full_config.yaml", "text/yaml")
    else:
        st.warning("No configuration loaded.")

# --- Tab 4: Interactive Editor & LLM Assist ---
with tab4:
    if 'config' in st.session_state:
        st.subheader("Edit Active Configuration")
        config = st.session_state.config
        
        # LLM Assist UI
        with st.expander("✨ AI Copilot (Add new metrics/cards)", expanded=False):
            # Load Global Preferences
            active_provider = PreferenceManager.get("active_llm_provider", "OpenAI")
            # Default model fallbacks if not set
            default_model = "gpt-4o"
            if active_provider == "Google (Gemini)": default_model = "gemini-1.5-flash"
            elif active_provider == "OpenRouter": default_model = "google/gemini-2.0-flash-001"
            
            active_model = PreferenceManager.get(f"model_{active_provider}", default_model)
            
            st.info(f"Using Global Config: **{active_provider}** / **{active_model}** (Change in Tab 6)")
            
            api_key = SecurityManager.get_api_key(active_provider)

            if st.button("Initialize Copilot"):
                if api_key and active_model:
                    st.session_state['llm_client'] = LLMClient(active_provider, api_key, active_model)
                    st.success(f"Copilot Ready! ({active_model})")
                else:
                    st.error("Please configure API Key in Tab 6.")

        st.info("⚠️ Changes made here apply immediately to the session but must be Exported to persist.")
        
        # 1. Drivers Editor
        st.markdown("### 1. Drivers")
        col_d1, col_d2 = st.columns([3, 1])
        with col_d1:
            df_drivers_current = DataConverter.drivers_to_csv(config.drivers)
            edited_drivers_df = st.data_editor(df_drivers_current, num_rows="dynamic", key="editor_drivers_df")
        
        with col_d2:
            st.markdown("#### Copilot")
            if st.button("Suggest Drivers"):
                if 'llm_client' in st.session_state:
                    with st.spinner("Thinking..."):
                        suggestion = st.session_state['llm_client'].generate_suggestions(df_drivers_current.to_csv(), "Drivers")
                        st.session_state['driver_suggestion'] = suggestion
                else:
                    st.warning("Init Copilot first.")
            
            if 'driver_suggestion' in st.session_state:
                st.caption("Suggestion:")
                st.code(st.session_state['driver_suggestion'], language="csv")
                if st.button("Append Suggestion"):
                    import io
                    try:
                        # Clean markdown if present
                        raw_csv = st.session_state['driver_suggestion'].replace("```csv", "").replace("```", "").strip()
                        
                        new_rows = pd.read_csv(io.StringIO(raw_csv), header=None)
                        # Expect NO header in suggestion as per prompt, but if columns mismatch...
                        if len(new_rows.columns) == len(df_drivers_current.columns):
                            new_rows.columns = df_drivers_current.columns
                            combined = pd.concat([df_drivers_current, new_rows], ignore_index=True)
                            
                            # Update Config
                            new_drivers_obj = DataConverter.csv_to_drivers(combined)
                            st.session_state.config.drivers = new_drivers_obj
                            StatePersistence.save(st.session_state.config)
                            
                            del st.session_state['driver_suggestion']
                            st.success(f"Appended {len(new_rows)} drivers!")
                            st.rerun()
                        else:
                            st.error(f"Column count mismatch. Expected {len(df_drivers_current.columns)}, Got {len(new_rows.columns)}")
                    except Exception as e:
                        st.error(f"Error appending: {e}")

        if st.button("Apply Driver Changes"):
            try:
                new_drivers = DataConverter.csv_to_drivers(edited_drivers_df)
                st.session_state.config.drivers = new_drivers
                StatePersistence.save(st.session_state.config)
                st.success(f"Updated {len(new_drivers)} drivers!")
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing drivers: {e}")

        st.markdown("---")

        # 2. Cards Editor
        st.markdown("### 2. Decision Cards")
        
        col_c1, col_c2 = st.columns([3, 1])
        with col_c1:
            df_cards_current = DataConverter.decision_card_to_csv(config.decision_cards)
            edited_cards_df = st.data_editor(df_cards_current, num_rows="dynamic", key="editor_cards_df")
            
        with col_c2:
            st.markdown("#### Copilot")
            if st.button("Suggest Cards"):
                if 'llm_client' in st.session_state:
                    with st.spinner("Analyzing context..."):
                        suggestion = st.session_state['llm_client'].generate_suggestions(df_cards_current.to_csv(), "Decision Cards")
                        st.session_state['card_suggestion'] = suggestion
                else:
                    st.warning("Init Copilot first.")
            
            if 'card_suggestion' in st.session_state:
                st.caption("Suggestion:")
                st.code(st.session_state['card_suggestion'], language="csv")
                
                if st.button("Append Cards"):
                    import io
                    try:
                        raw_csv = st.session_state['card_suggestion'].replace("```csv", "").replace("```", "").strip()
                        new_rows = pd.read_csv(io.StringIO(raw_csv), header=None)
                        
                        if len(new_rows.columns) == len(df_cards_current.columns):
                            new_rows.columns = df_cards_current.columns
                            combined = pd.concat([df_cards_current, new_rows], ignore_index=True)
                            
                            new_cards_obj = DataConverter.csv_to_decision_card(combined)
                            
                            # Preserve
                            if st.session_state.config.decision_cards:
                                old_map = {c.id: c for c in st.session_state.config.decision_cards}
                                for nc in new_cards_obj:
                                    if nc.id in old_map:
                                        oc = old_map[nc.id]
                                        nc.simulation_impact = oc.simulation_impact
                                        nc.simulation_urgency = oc.simulation_urgency
                                        nc.manual_override_status = oc.manual_override_status
                                        nc.manual_override_reason = oc.manual_override_reason

                            st.session_state.config.decision_cards = new_cards_obj
                            StatePersistence.save(st.session_state.config)
                            
                            del st.session_state['card_suggestion']
                            st.success(f"Appended {len(new_rows)} cards!")
                            st.rerun()
                        else:
                            st.error(f"Mismatch: Expected {len(df_cards_current.columns)} cols, Got {len(new_rows.columns)}")
                    except Exception as e:
                        st.error(f"Error: {e}")

        if st.button("Apply Card Changes"):
            try:
                new_cards = DataConverter.csv_to_decision_card(edited_cards_df)
                
                # Preserve existing runtime state (simulation, overrides)
                if st.session_state.config.decision_cards:
                    old_map = {c.id: c for c in st.session_state.config.decision_cards}
                    for nc in new_cards:
                        if nc.id in old_map:
                            oc = old_map[nc.id]
                            nc.simulation_impact = oc.simulation_impact
                            nc.simulation_urgency = oc.simulation_urgency
                            nc.manual_override_status = oc.manual_override_status
                            nc.manual_override_reason = oc.manual_override_reason

                st.session_state.config.decision_cards = new_cards
                StatePersistence.save(st.session_state.config)
                st.success(f"Updated {len(new_cards)} decision cards!")
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing cards: {e}")

        # 3. Weights
        st.markdown("### 3. Priority Weights")
        c1, c2, c3 = st.columns(3)
        current_w = config.priority_weights
        w_imp = c1.number_input("Impact Weight", 0.1, 10.0, float(current_w.get("impact", 1.0)))
        w_urg = c2.number_input("Urgency Weight", 0.1, 10.0, float(current_w.get("urgency", 1.0)))
        w_unc = c3.number_input("Uncertainty Weight", 0.1, 10.0, float(current_w.get("uncertainty", 1.0)))
        
        if st.button("Update Weights"):
            st.session_state.config.priority_weights = {"impact": w_imp, "urgency": w_urg, "uncertainty": w_unc}
            StatePersistence.save(st.session_state.config)
            st.success("Weights Updated!")
            st.rerun()

    else:
        st.warning("No configuration loaded.")

# --- Tab 6: API Settings ---
# --- Tab 6: API & Model Settings ---
with tab6:
    st.subheader("🔐 Secure API Key Management")
    st.info("Keys are encrypted and stored locally. Configure your preferred models here to use across the app.")

    # 1. API Keys
    col_k1, col_k2, col_k3 = st.columns(3)
    
    with col_k1:
        st.markdown("### OpenAI")
        key_oa = st.text_input("API Key", type="password", key="key_oa")
        if st.button("Save OpenAI Key"):
            SecurityManager.save_api_key("OpenAI", key_oa)
            st.success("Saved!")
            
    with col_k2:
        st.markdown("### Google (Gemini)")
        key_gg = st.text_input("API Key", type="password", key="key_gg")
        if st.button("Save Gemini Key"):
            SecurityManager.save_api_key("Google (Gemini)", key_gg)
            st.success("Saved!")
            
    with col_k3:
        st.markdown("### OpenRouter")
        key_or = st.text_input("API Key", type="password", key="key_or")
        if st.button("Save OpenRouter Key"):
            SecurityManager.save_api_key("OpenRouter", key_or)
            st.success("Saved!")

    st.markdown("---")
    st.subheader("🤖 Global Model Configuration")
    
    # Active Provider
    current_provider = PreferenceManager.get("active_llm_provider", "OpenAI")
    prov_options = ["OpenAI", "Google (Gemini)", "OpenRouter"]
    
    def on_provider_change():
        PreferenceManager.save("active_llm_provider", st.session_state.global_provider_select)
        
    try: idx = prov_options.index(current_provider) 
    except: idx = 0
    
    selected_provider = st.selectbox("Active Provider (Used for all Copilot features)", 
                                     prov_options, 
                                     index=idx, 
                                     key="global_provider_select", 
                                     on_change=on_provider_change)
    
    # Model Selection for Active Provider
    st.markdown(f"#### Configure Model for {selected_provider}")
    
    api_key = SecurityManager.get_api_key(selected_provider)
    if not api_key:
        st.warning(f"Please save API Key for {selected_provider} above.")
    else:
        col_m1, col_m2 = st.columns([1, 3])
        with col_m1:
            if st.button("🔄 Fetch/Refresh Models"):
                with st.spinner("Fetching..."):
                    try:
                        models = LLMClient.fetch_available_models(selected_provider, api_key)
                        st.session_state[f"models_{selected_provider}"] = models
                        st.success(f"Fetched {len(models)} models.")
                    except Exception as e:
                        st.error(f"Error: {e}")
        
        with col_m2:
            # Load models
            models = st.session_state.get(f"models_{selected_provider}", [])
            if not models:
                # Defaults
                if selected_provider=="OpenAI": models=["gpt-4o", "gpt-4-turbo"]
                elif selected_provider=="Google (Gemini)": models=["gemini-1.5-flash"]
                elif selected_provider=="OpenRouter": models=["google/gemini-2.0-flash-001", "anthropic/claude-3-sonnet"]
            
            # Load saved model preference
            saved_model = PreferenceManager.get(f"model_{selected_provider}", models[0])
            
            # Filter
            search = st.text_input("Search Model", placeholder="e.g. gpt-4", label_visibility="collapsed")
            filtered = [m for m in models if search.lower() in m.lower()] if search else models
            
            try: m_idx = filtered.index(saved_model)
            except: m_idx = 0
            
            def on_model_change():
                PreferenceManager.save(f"model_{selected_provider}", st.session_state.global_model_select)
            
            st.selectbox("Select Default Model", filtered, index=m_idx, key="global_model_select", on_change=on_model_change)
            
            st.info(f"Currently Active: **{selected_provider}** / **{st.session_state.get('global_model_select', saved_model)}**")

    st.markdown("---")
    st.caption("Active Keys Status:")
    status = SecurityManager.verify_keys_exist()
    cols = st.columns(len(status) if status else 1)
    if status:
        for idx, (s, active) in enumerate(status.items()):
            cols[idx].markdown(f"- **{s}**: {'✅ Active' if active else '❌ Missing'}")

    else:
        st.info("No keys stored yet.")

# --- Tab 5: AI Generator ---
with tab5:
    st.subheader("🤖 AI-Assisted Configuration")
    st.markdown("Generate initial CSV datasets using any LLM (ChatGPT, Claude, Gemini).")
    
    domain = st.text_input("Target Domain (e.g. 'SaaS Sales Team', 'Hospital ER Staffing')", "SaaS Customer Success")
    
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("### Step 1: Generate Prompt")
        base_prompt = DataTemplates.get_llm_prompt_config().replace("[INSERT DOMAIN HERE]", domain)
        st.text_area("Copy this prompt to ChatGPT:", base_prompt, height=250)
        
    with c2:
        st.markdown("### Step 2: Paste CSV Result")
        st.markdown("Paste the **Drivers CSV** generated by LLM here:")
        drivers_txt = st.text_area("Drivers CSV Content", height=100)
        st.markdown("Paste the **Cards CSV** generated by LLM here:")
        cards_txt = st.text_area("Cards CSV Content", height=100)
        
        if st.button("Parse & Load from AI"):
            import io
            try:
                if drivers_txt:
                    df_d = pd.read_csv(io.StringIO(drivers_txt))
                    new_drivers = DataConverter.csv_to_drivers(df_d)
                    st.session_state.config.drivers = new_drivers
                    st.success(f"Loaded {len(new_drivers)} drivers!")
                
                if cards_txt:
                    df_c = pd.read_csv(io.StringIO(cards_txt))
                    new_cards = DataConverter.csv_to_decision_card(df_c)
                    st.session_state.config.decision_cards = new_cards
                    st.success(f"Loaded {len(new_cards)} cards!")
                    
                st.rerun()
            except Exception as e:
                st.error(f"Error parsing AI output: {e}")


# --- Tab 7: Localization ---
with tab7:
    st.subheader("🌐 Language & Localization")
    
    # 1. Global Language Selector
    current_lang = PreferenceManager.get("language", "en")
    avail_langs = I18nManager.available_languages()
    
    # Session State Init
    if "lang_select" not in st.session_state:
        st.session_state.lang_select = current_lang
    
    def on_lang_change():
        new_lang = st.session_state.editor_lang_key
        PreferenceManager.save("language", new_lang)
        st.session_state["language"] = new_lang
        st.toast(f"Language changed to {new_lang}!", icon="🌍")

    try: 
        l_idx = avail_langs.index(current_lang)
    except: 
        l_idx = 0
    
    selected = st.selectbox("Display Language", avail_langs, index=l_idx, key="editor_lang_key", on_change=on_lang_change)
    
    st.markdown("---")
    
    # 2. JSON Editor
    st.markdown("### 📝 Edit Translations")
    st.caption("Edit the JSON below to add new languages or modify text. Changes apply immediately upon saving.")
    
    current_data = I18nManager.load()
    
    text_val = json.dumps(current_data, indent=2, ensure_ascii=False)
    edited_json = st.text_area("Locales JSON Configuration", 
                               value=text_val, 
                               height=600)
    
    c1, c2 = st.columns([1, 4])
    with c1:
        if st.button("💾 Save Changes"):
            try:
                new_data = json.loads(edited_json)
                I18nManager.save(new_data)
                st.success("Translations saved successfully! Reloading...")
                st.rerun()
            except Exception as e:
                st.error(f"Invalid JSON: {e}")
    
    with c2:
        if st.button("🔄 Reset to Defaults"):
            I18nManager.save(I18nManager._get_default_structure())
            st.success("Reset to defaults.")
            st.rerun()
