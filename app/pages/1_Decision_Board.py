import streamlit as st
import pandas as pd
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

import importlib
import core.priority
importlib.reload(core.priority)
from core.priority import PriorityCalculator

import core.io
importlib.reload(core.io)
from core.io import ConfigLoader

from core.decision import DecisionEngine
from core.snapshot import SnapshotManager
from core.audit import AuditLogger
import core.visualizer
importlib.reload(core.visualizer)
from core.visualizer import CausalVisualizer
from core.sidebar import render_sidebar
from core.i18n import I18nManager
from core.scoring import (
    prepare_candidates,
    compute_driver_scores,
    get_kpi_latest
)
import graphviz


st.set_page_config(page_title="Decision Board", layout="wide")
render_sidebar()

# Helpers
# ...
# Sidebar Config
st.sidebar.markdown("### Settings")
if "ranking_method" not in st.session_state: st.session_state.ranking_method = "SAW (Transparent)"
ranking_method = st.sidebar.radio("Ranking Algorithm", ["SAW (Transparent)", "WASPAS (Robust)", "TOPSIS (Relative)", "Composite (Ensemble)"], index=0, key="ranking_method_sel", on_change=lambda: st.session_state.update({"ranking_method": st.session_state.ranking_method_sel}))
# Ensure sync
ranking_method = st.session_state.get("ranking_method", ranking_method)

# Engines


from core.state_manager import StatePersistence

def on_sim_change(card_id, imp_key, urg_key):
    # Persist simulation changes to file immediately
    if 'config' in st.session_state:
        card = next((c for c in st.session_state.config.decision_cards if c.id == card_id), None)
        if card:
            # Update object state from widget state
            if imp_key in st.session_state:
                 card.simulation_impact = st.session_state[imp_key]
            if urg_key in st.session_state:
                 card.simulation_urgency = st.session_state[urg_key]
            StatePersistence.save(st.session_state.config)

def on_revert_sim(card_id, imp_key, urg_key):
    if 'config' in st.session_state:
        card = next((c for c in st.session_state.config.decision_cards if c.id == card_id), None)
        if card:
            card.simulation_impact = None
            card.simulation_urgency = None
            # Clear session state keys to refresh sliders to default
            if imp_key in st.session_state: del st.session_state[imp_key]
            if urg_key in st.session_state: del st.session_state[urg_key]
            StatePersistence.save(st.session_state.config)

# 1. Initialization
# Schema Migration / Validation
if 'config' in st.session_state:
    try:
        # Check if new fields exist on the first card
        if st.session_state.config.decision_cards and not hasattr(st.session_state.config.decision_cards[0], 'simulation_impact'):
             raise AttributeError("Old schema detected")
    except AttributeError:
        st.toast("Updating configuration schema...", icon="🔄")
        del st.session_state['config']

if 'config' not in st.session_state:
    # Try persistent state first
    saved_config = StatePersistence.load()
    if saved_config:
        st.session_state.config = saved_config
        st.toast("Restored previous session state.", icon="💾")
    else:
        loader = ConfigLoader("configs/customer_default.yaml")
        st.session_state.config = loader.load_config()
        # Initial save
        StatePersistence.save(st.session_state.config)

config = st.session_state.config
survey_df = st.session_state.get('survey_data')
kpi_df = st.session_state.get('kpi_data')
quality_penalty = st.session_state.get('survey_quality', {}).get('penalty', 0.0)



# Engines
decision_engine = DecisionEngine()
priority_calc = PriorityCalculator(config.priority_weights)
audit_logger = AuditLogger()
snapshot_manager = SnapshotManager()

st.title(f"🚦 {I18nManager.get('sidebar.decision_board', 'Decision Board')}")
st.markdown("Prioritized list of decision cards based on evidence.")

# 2. Compute Evidence Context (Moved Up)
evidence_context = compute_driver_scores(survey_df, config.drivers)
# Add KPIs
if kpi_df is not None:
    # MVP: specific mapping logic
    evidence_context['turnover_rate_junior'] = get_kpi_latest(kpi_df, 'turnover_rate_junior')
    evidence_context['avg_overtime_hours'] = get_kpi_latest(kpi_df, 'avg_overtime_hours')
    evidence_context['manager_overtime'] = get_kpi_latest(kpi_df, 'manager_overtime')

# 3. Evaluate & Rank Cards (Moved Up)
candidates = prepare_candidates(
    config.decision_cards,
    decision_engine,
    evidence_context,
    quality_penalty,
    overrides=st.session_state
)

# Batch Ranking Call
ranked_candidates = priority_calc.rank_candidates(candidates, method=ranking_method)

# Prepare for Display loop & Graph
card_states = []
for item in ranked_candidates:
    card = item["_card"]
    state = item["_state"]
    # Update state with calculated priority
    state.total_priority = item["score"]
    state.confidence_penalty = item["uncertainty"]
    
    # Pass details for rendering
    # storing (card, state, score_res, final_impact, final_urgency)
    # score_res is essentially item['_details'] + score
    score_res = item.get("_details", {"score": item["score"]})
    score_res["score"] = item["score"]
    
    card_states.append((card, state, score_res, item["impact"], item["urgency"]))

# Prepare scores for Graph
card_scores_map = {cs[0].id: cs[1].total_priority for cs in card_states}

# Visualize Causal Graph (Transparency)
with st.expander("🕸️ Decision Architecture (Causal Graph)"):
    viz = CausalVisualizer(config.drivers, config.decision_cards)
    try:
        # Pass scores to visualizer
        st.graphviz_chart(viz.render_causal_graph(driver_scores=evidence_context, card_scores=card_scores_map))
    except Exception as e:
        st.warning(f"Graphviz not installed or error: {e}")


st.write("---")

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
            tab1, tab2, tab3, tab4 = st.tabs(["Evidence", "Recommendation", "Scoring", "Causal Graph"])
            
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
                    # Implementation of Cooperative DSS (Persistent)
                    st.markdown("---")
                    
                    if card.manual_override_status:
                        st.info(f"Human Audit Status: **{card.manual_override_status}**")
                        if card.manual_override_reason:
                            st.caption(f"Reason: {card.manual_override_reason}")
                    
                    col_act1, col_act2 = st.columns(2)
                    with col_act1:
                        if st.button(f"Approve Draft ({card.id})"):
                            card.manual_override_status = "APPROVED"
                            card.manual_override_reason = "Routine Approval"
                            StatePersistence.save(st.session_state.config)
                            audit_logger.log_action(card.id, "latest", "Approve", "Routine approval")
                            st.success("Approved! Saved.")
                            st.rerun()
                            
                    with col_act2:
                        reason = st.text_input("Override Reason", key=f"reason_{card.id}", value=card.manual_override_reason or "")
                        if st.button(f"Override / Reject ({card.id})"):
                            if not reason:
                                st.error("Reason required for override.")
                            else:
                                card.manual_override_status = "REJECTED"
                                card.manual_override_reason = reason
                                StatePersistence.save(st.session_state.config)
                                audit_logger.log_action(card.id, "latest", "Override", reason)
                                st.warning("Overridden! Saved.")
                                st.rerun()
                    st.info("No recommendation needed (Green).")

            with tab3:
                st.subheader("Scoring & What-If Simulation")
                
                # --- Simulation Controls (Persistent) ---
                col_s1, col_s2, col_s3 = st.columns([2, 5, 2])
                with col_s2:
                    st.caption("Adjust sliders to simulate different scenarios (Auto-saved):")
                    sim_imp_key = f"sim_imp_{card.id}"
                    sim_urg_key = f"sim_urg_{card.id}"
                    
                    st.slider(
                        f"Impact ({card.id})", 0.0, 1.0, float(final_impact), 0.05, 
                        key=sim_imp_key, 
                        on_change=on_sim_change, 
                        args=(card.id, sim_imp_key, sim_urg_key)
                    )
                    st.slider(
                        f"Urgency ({card.id})", 0.0, 1.0, float(final_urgency), 0.05,
                        key=sim_urg_key,
                        on_change=on_sim_change,
                        args=(card.id, sim_imp_key, sim_urg_key)
                    )
                    
                    # Revert Logic
                    is_simulated = (card.simulation_impact is not None) or (card.simulation_urgency is not None)
                    if is_simulated:
                        st.button(
                            "Revert to Actuals", 
                            key=f"reset_{card.id}", 
                            on_click=on_revert_sim, 
                            args=(card.id, sim_imp_key, sim_urg_key)
                        )


                st.markdown("---")
                
                st.subheader("Calculation Details")
                st.markdown(f"**Method**: {ranking_method}")
                
                c1, c2, c3 = st.columns(3)
                c1.metric("Impact Input", f"{final_impact:.2f}", help="Derived from Gap Size / N-count (or Simulated)")
                c2.metric("Urgency Input", f"{final_urgency:.2f}", help="Derived from Trend / Variance (or Simulated)")
                c3.metric("Uncertainty (Penalty)", f"{state.confidence_penalty:.2f}", help="Derived from Data Q-Gate", delta_color="inverse")
                
                st.write("---")
                st.write("---")
                if "WASPAS" in ranking_method and "components" in score_res:
                    st.write("**Components:**")
                    comps = score_res["components"]
                    st.latex(f"Q = 0.5 \\times {comps['saw_score']:.2f} (SAW) + 0.5 \\times {comps['wpm_score']:.2f} (WPM)")
                
                elif "TOPSIS" in ranking_method:
                    st.write("**TOPSIS Distances:**")
                    s_pos = score_res.get("S+", 0)
                    s_neg = score_res.get("S-", 0)
                    st.markdown(f"- Distance to Ideal ($S^+$): `{s_pos:.4f}`")
                    st.markdown(f"- Distance to Anti-Ideal ($S^-$): `{s_neg:.4f}`")
                    if (s_pos + s_neg) > 0:
                        st.latex(f"Score = \\frac{{S^-}}{{S^+ + S^-}} = \\frac{{{s_neg:.4f}}}{{{s_pos+s_neg:.4f}}}")
                
                elif "Composite" in ranking_method:
                    st.write("**Ensemble Rankings:**")
                    ranks = score_res.get("ranks", {})
                    cols_r = st.columns(3)
                    cols_r[0].metric("SAW Rank", ranks.get("SAW", "-"))
                    cols_r[1].metric("WASPAS Rank", ranks.get("WASPAS", "-"))
                    cols_r[2].metric("TOPSIS Rank", ranks.get("TOPSIS", "-"))
                    st.caption(f"Average Rank: {score_res.get('avg_rank', 0):.2f}")
                
                elif "breakdown" in score_res:
                    st.write("**Breakdown (SAW):**")
                    breakdown = score_res.get("breakdown", {})
                    inputs = score_res.get("inputs", {})
                    
                    if breakdown:
                         term_imp = breakdown.get("impact_term", 0)
                         term_urg = breakdown.get("urgency_term", 0)
                         term_unc = breakdown.get("uncertainty_term", 0)
                         
                         # Get inputs if available for transparency
                         val_imp = inputs.get("impact", final_impact)
                         val_urg = inputs.get("urgency", final_urgency)
                         val_unc = inputs.get("uncertainty", state.confidence_penalty)
                         
                         w_imp = priority_calc.w_impact
                         w_urg = priority_calc.w_urgency
                         w_unc = priority_calc.w_uncertainty
                         
                         st.latex(f"({val_imp:.2f} \\times {w_imp:.1f}) + ({val_urg:.2f} \\times {w_urg:.1f}) - ({val_unc:.2f} \\times {w_unc:.1f})")
                         st.latex(f"= {term_imp:.2f} + {term_urg:.2f} - {abs(term_unc):.2f} = {score_res['score']:.2f}")
                
                if quality_penalty > 0.1:
                    st.warning(f"⚠️ Confidence Penalty applied: -{quality_penalty:.2f} due to data quality issues.")

            with tab4:
                st.subheader("Decision Architecture")
                st.caption("Contextual Causal Graph for this Decision")
                try:
                    # Renders focused view for specific card
                    mini_dot = viz.render_causal_graph(
                        driver_scores=evidence_context, 
                        card_scores=card_scores_map,
                        target_card_id=card.id
                    )
                    st.graphviz_chart(mini_dot)
                except Exception as e:
                    st.error(f"Visualization Error: {e}")

        st.json(state.model_dump(include={'status','total_priority','confidence_penalty'})) # Mini debug
        st.divider()

# Freeze Action moved to page 4_Freeze_Report
st.sidebar.markdown("### Actions")
st.sidebar.info("Go to 'Report & Freeze' page to finalize.")
