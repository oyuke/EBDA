import streamlit as st
import pandas as pd
import json
import yaml
from core.converter import DataConverter
from data.models import DecisionCardConfig, DriverConfig
from core.templates import DataTemplates

st.set_page_config(page_title="Data Tools", layout="wide")
st.title("🛠️ Data Management & Conversion")

st.markdown("Convert human-editable CSVs into JSON/YAML configuration for the app.")

tab1, tab2, tab3, tab4, tab5 = st.tabs(["1. Config Builder", "2. Data Converter", "3. Export Current", "4. Interactive Editor", "5. 🤖 AI Generator"])

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

# --- Tab 4: Interactive Editor ---
with tab4:
    if 'config' in st.session_state:
        st.subheader("Edit Active Configuration")
        config = st.session_state.config
        
        st.info("⚠️ Changes made here apply immediately to the session but must be Exported to persist.")
        
        # 1. Drivers Editor
        st.markdown("### 1. Drivers")
        df_drivers_current = DataConverter.drivers_to_csv(config.drivers)
        edited_drivers_df = st.data_editor(df_drivers_current, num_rows="dynamic", key="editor_drivers_df")
        
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
        df_cards_current = DataConverter.decision_card_to_csv(config.decision_cards)
        edited_cards_df = st.data_editor(df_cards_current, num_rows="dynamic", key="editor_cards_df")
        
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
