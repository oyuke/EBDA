import streamlit as st
import pandas as pd
from core.decision import DecisionEngine
from core.priority import PriorityCalculator
from core.snapshot import SnapshotManager
from core.audit import AuditLogger
from core.io import ConfigLoader

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
    
    # Priority Calculation (Mock values for Impact/Urgency for MVP as they're not automated yet)
    # In real app, Impact comes from n-count or gap size.
    # Here we mock based on status for demo effect
    impact = 0.8 if state.status == "RED" else 0.4
    urgency = 0.9 if "turnover" in str(state.key_evidence) else 0.3
    
    # Use global quality penalty as uncertainty
    uncertainty = quality_penalty
    
    score_res = priority_calc.calculate_saw(impact, urgency, uncertainty)
    
    state.total_priority = score_res["score"]
    state.confidence_penalty = uncertainty
    # Store for display
    card_states.append((card, state, score_res))

# Sort by Priority Descending
card_states.sort(key=lambda x: x[1].total_priority, reverse=True)

# 4. Display Loop
for card, state, score_res in card_states:
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
                st.write("**SAW Score Breakdown**")
                st.write(score_res["breakdown"])
                if quality_penalty > 0.1:
                    st.warning(f"⚠️ Confidence Penalty applied: -{quality_penalty:.2f} due to data quality issues.")

        st.json(state.dict(include={'status','total_priority','confidence_penalty'})) # Mini debug
        st.divider()

# 5. Freeze Action
st.sidebar.markdown("### Actions")
if st.sidebar.button("❄️ Freeze Snapshot"):
    # Mock Wave object
    from data.models import Wave
    wave = Wave(id="W001", name="Current Wave")
    # Populate wave with states...
    
    snap = snapshot_manager.freeze(wave, "config_hash_123")
    st.sidebar.success(f"Snapshot Frozen: {snap.id}")
