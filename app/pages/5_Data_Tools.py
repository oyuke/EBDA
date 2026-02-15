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

st.set_page_config(page_title="Data Tools", layout="wide")
st.title("🛠️ Data Management & Conversion")

st.markdown("Convert human-editable CSVs into JSON/YAML configuration for the app.")

tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs(["1. Config Builder", "2. Data Converter", "3. Export Current", "4. Interactive Editor", "5. AI Generator", "6. 🔐 API Settings"])

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
            c_prov, c_model = st.columns(2)
            
            with c_prov:
                # Preference loading
                saved_provider = PreferenceManager.get("copilot_provider", "OpenAI")
                prov_options = ["OpenAI", "Google (Gemini)", "OpenRouter"]
                try:
                    def_idx = prov_options.index(saved_provider)
                except:
                    def_idx = 0
                
                def on_prov_change():
                    # Check session state for the key 'copilot_provider'
                    if 'copilot_provider' in st.session_state:
                         PreferenceManager.save("copilot_provider", st.session_state.copilot_provider)

                llm_provider = st.selectbox("Select Provider", prov_options, index=def_idx, key="copilot_provider", on_change=on_prov_change)
                api_key = SecurityManager.get_api_key(llm_provider)
                
                if api_key:
                    if st.button("🔄 Fetch Models from API"):
                        with st.spinner(f"Fetching models for {llm_provider}..."):
                            try:
                                models = LLMClient.fetch_available_models(llm_provider, api_key)
                                st.session_state[f"models_{llm_provider}"] = models
                                if not models:
                                    st.error("No models found or API error.")
                            except AttributeError:
                                st.error("System update pending. Please stop and restart the app server.")
                            except Exception as e:
                                st.error(f"Error: {e}")
                else:
                    st.warning("Save API Key in Tab 6 first.")

            with c_model:
                # Get models from session or default
                model_list = st.session_state.get(f"models_{llm_provider}", [])
                
                if not model_list:
                    # Fallback defaults if not fetched
                    if llm_provider == "OpenAI":
                        model_list = ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"]
                    elif llm_provider == "Google (Gemini)":
                        model_list = ["gemini-1.5-flash", "gemini-1.5-pro"]
                    else: 
                        model_list = ["google/gemini-2.0-flash-001", "anthropic/claude-3-sonnet"]
                
                # Search/Filter
                search_query = st.text_input("Filter Models", placeholder="e.g. flash, gpt-4...")
                filtered_models = [m for m in model_list if search_query.lower() in m.lower()] if search_query else model_list
                
                selected_model = st.selectbox("Select Model", filtered_models, key="model_selector")

            if st.button("Initialize Copilot"):
                if api_key and selected_model:
                    st.session_state['llm_client'] = LLMClient(llm_provider, api_key, selected_model)
                    st.success(f"Copilot Ready! ({selected_model})")
                else:
                    st.error("Please configure Provider, Key, and Model.")

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
                            st.session_state.config.decision_cards = new_cards_obj
                            
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
                st.session_state.config.decision_cards = new_cards
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
            st.success("Weights Updated!")
            st.rerun()

    else:
        st.warning("No configuration loaded.")

# --- Tab 6: API Settings ---
with tab6:
    st.subheader("🔐 Secure API Key Management")
    st.markdown("Keys are encrypted (Fernet 256-bit) and stored locally in `.secrets/api_keys.enc`.")
    st.info("These keys are used for the AI Copilot features.")
    
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
