import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from core.decision import DecisionEngine
from core.priority import PriorityCalculator
from core.snapshot import SnapshotManager
from core.audit import AuditLogger
from core.io import ConfigLoader
from core.visualizer import CausalVisualizer
import graphviz


st.set_page_config(page_title="Decision Board", layout="wide")

# Helpers
def compute_driver_scores(df, drivers):
    scores = {}
    if df is None: return scores
    for driver in drivers:
        cols = [c for c in driver.survey_items if c in df.columns]
        if cols:
            # Simple average of items (1-5 scale)
            scores[driver.id] = df[cols].mean(axis=1).mean()
    return scores

def get_kpi_latest(df, kpi_name):
    if df is None: return None
    if kpi_name in df.columns:
        # Assuming sorted by date or taking last
        return df[kpi_name].iloc[-1]
    return 0.0

# 1. Initialization
if 'config' not in st.session_state:
    loader = ConfigLoader("configs/customer_default.yaml")
    st.session_state.config = loader.load_config()

config = st.session_state.config
survey_df = st.session_state.get('survey_data')
kpi_df = st.session_state.get('kpi_data')
quality_penalty = st.session_state.get('survey_quality', {}).get('penalty', 0.0)

# Engines
decision_engine = DecisionEngine()
priority_calc = PriorityCalculator(config.priority_weights)
audit_logger = AuditLogger()
snapshot_manager = SnapshotManager()

st.title("🚦 Decision Board")
st.markdown("Prioritized list of decision cards based on evidence.")

# Visualize Causal Graph (Transparency)
with st.expander("🕸️ Decision Architecture (Causal Graph)"):
    viz = CausalVisualizer(config.drivers, config.decision_cards)
    try:
        st.graphviz_chart(viz.render_causal_graph())
    except Exception as e:
        st.warning(f"Graphviz not installed or error: {e}")


# 2. Compute Evidence Context
evidence_context = compute_driver_scores(survey_df, config.drivers)
# Add KPIs
if kpi_df is not None:
    # MVP: specific mapping logic
    evidence_context['turnover_rate_junior'] = get_kpi_latest(kpi_df, 'turnover_rate_junior')
    evidence_context['avg_overtime_hours'] = get_kpi_latest(kpi_df, 'avg_overtime_hours')
    evidence_context['manager_overtime'] = get_kpi_latest(kpi_df, 'manager_overtime')

st.write("---")

# 3. Evaluate & Rank Cards
card_states = []
for card in config.decision_cards:
    # Rule Evaluation
    state = decision_engine.evaluate_card(card, evidence_context)
    
    # In real app, Impact comes from n-count or gap size.
    # Logic update: Use actual evidence if available, otherwise default to neutral to avoid 'fake' feeling
    impact = 0.5 # Default neutral
    urgency = 0.5
    
    # Simple Logic for Impact Transparency
    if state.status == "RED":
        impact = 0.9
    elif state.status == "YELLOW":
        impact = 0.6
    
    # Simple Logic for Urgency
    if "turnover" in str(state.key_evidence):
        urgency = 0.9
    elif "overtime" in str(state.key_evidence):
        urgency = 0.7
    
    # --- Simulation Mode ---
    with st.expander(f"🎛️ What-If Simulation ({card.id})"):
        sim_impact = st.slider("Simulate Impact", 0.0, 1.0, impact, 0.1, key=f"sim_imp_{card.id}")
        sim_urgency = st.slider("Simulate Urgency", 0.0, 1.0, urgency, 0.1, key=f"sim_urg_{card.id}")
        if sim_impact != impact or sim_urgency != urgency:
            impact = sim_impact
            urgency = sim_urgency
            st.caption("✨ Using simulated values")
    
    score_res = priority_calc.calculate_saw(impact, urgency, uncertainty)
    
    state.total_priority = score_res["score"]
    state.confidence_penalty = uncertainty
    # Store for display
    card_states.append((card, state, score_res, impact, urgency))

# Sort by Priority Descending
card_states.sort(key=lambda x: x[1].total_priority, reverse=True)

# 4. Display Loop
for card, state, score_res, final_impact, final_urgency in card_states:
    with st.container():
        # Header Row
        col1, col2, col3 = st.columns([1, 4, 2])
        status_color = "🔴" if state.status == "RED" else "🟡" if state.status == "YELLOW" else "🟢"
        
        with col1:
            st.markdown(f"## {status_color}")
        with col2:
            st.subheader(f"{card.title}")
            st.caption(f"Stakeholders: {', '.join(card.stakeholders)}")
        with col3:
            st.metric("Priority Score", f"{state.total_priority:.2f}")
            st.progress(max(0.0, min(1.0, state.total_priority / 3.0))) # Normalize approx

        # Details Expander
        with st.expander("🔍 See Evidence & Recommendation", expanded=(state.status=="RED")):
            tab1, tab2, tab3 = st.tabs(["Evidence", "Recommendation", "Scoring"])
            
            with tab1:
                st.write("**Key Evidence Triggered:**")
                for ev in state.key_evidence:
                    st.error(ev) if state.status == "RED" else st.info(ev)
                
                st.write("**Underlying Data:**")
                st.json(evidence_context) # Raw context for transparency

            with tab2:
                if state.recommendation_draft:
                    rec = state.recommendation_draft
                    st.markdown(f"**Draft Action**: {rec.action}")
                    st.warning(f"⚠️ **Risks**: {rec.risks}")
                    st.info(f"✅ **Success Metrics**: {rec.success_metrics}")
                    
                    # Implementation of Cooperative DSS
                    st.markdown("---")
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button(f"Approve Draft ({card.id})"):
                            st.success("Approved! Sent to Action Plan.")
                            audit_logger.log_action(card.id, "latest", "Approve", "Routine approval")
                    with col_act2:
                        reason = st.text_input("Override Reason", key=f"reason_{card.id}")
                        if st.button(f"Override / Reject ({card.id})"):
                            if not reason:
                                st.error("Reason required for override.")
                            else:
                                st.warning("Overridden by human.")
                                audit_logger.log_action(card.id, "latest", "Override", reason)
                else:
                    st.info("No recommendation needed (Green).")

            with tab3:
                st.subheader("White-box Score Calculation")
                st.markdown(f"**Formula**: `Priority = (Impact × {config.priority_weights['impact']}) + (Urgency × {config.priority_weights['urgency']}) - (Uncertainty × {config.priority_weights['uncertainty']})`")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Impact Input", f"{final_impact:.2f}", help="Derived from Gap Size / N-count (or Simulated)")
                c2.metric("Urgency Input", f"{final_urgency:.2f}", help="Derived from Trend / Variance (or Simulated)")
                c3.metric("Uncertainty (Penalty)", f"{uncertainty:.2f}", help="Derived from Data Q-Gate", delta_color="inverse")
                
                st.write("---")
                st.write("**Terms:**")
                breakdown = score_res["breakdown"]
                st.latex(f"{score_res['score']:.2f} = {breakdown['impact_term']:.2f} + {breakdown['urgency_term']:.2f} - {abs(breakdown['uncertainty_term']):.2f}")
                
                if quality_penalty > 0.1:
                    st.warning(f"⚠️ Confidence Penalty applied: -{quality_penalty:.2f} due to data quality issues.")

        st.json(state.model_dump(include={'status','total_priority','confidence_penalty'})) # Mini debug
        st.divider()

# Freeze Action moved to page 4_Freeze_Report
st.sidebar.markdown("### Actions")
st.sidebar.info("Go to 'Report & Freeze' page to finalize.")
