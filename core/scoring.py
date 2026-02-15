from typing import List, Dict, Any
import pandas as pd
from data.models import DecisionCardConfig

def compute_driver_scores(df: pd.DataFrame, drivers: List[Any]) -> Dict[str, float]:
    scores = {}
    if df is None: return scores
    for driver in drivers:
        cols = [c for c in driver.survey_items if c in df.columns]
        if cols:
            # Simple average of survey items (1-5 scale) across all respondents and items
            # Using mean(axis=1).mean() handles row-wise average then overall, robust to missing items per row
            try:
                scores[driver.id] = df[cols].mean(axis=1).mean()
            except:
                scores[driver.id] = 0.0
    return scores

def get_kpi_latest(df: pd.DataFrame, kpi_name: str) -> float:
    if df is None: return 0.0
    if kpi_name in df.columns:
        # Assuming sorted by date or taking last row
        return df[kpi_name].iloc[-1]
    return 0.0

def prepare_candidates(
    cards: List[DecisionCardConfig], 
    decision_engine: Any, 
    evidence_context: Dict[str, float], 
    quality_penalty: float,
    overrides: Dict[str, float] = None
) -> List[Dict[str, Any]]:
    """
    Prepare list of candidates with derived Impact/Urgency metrics for ranking.
    Consistent across Decision Board and Freeze Report.
    """
    candidates = []
    
    for card in cards:
        # Rule Evaluation
        state = decision_engine.evaluate_card(card, evidence_context)
        
        # Base Values Logic
        impact = 0.5 
        urgency = 0.5
        
        # Logic matches Decision_Board original implementation
        if state.status == "RED": impact = 0.9
        elif state.status == "YELLOW": impact = 0.6
        elif state.status == "GREEN": impact = 0.3
        
        # Keyword based urgency
        ev_str = str(state.key_evidence).lower()
        if "turnover" in ev_str: urgency = 0.9
        elif "overtime" in ev_str: urgency = 0.7
        elif "engagement" in ev_str: urgency = 0.6
        
        # Apply Persistent Overrides
        if card.simulation_impact is not None:
            impact = card.simulation_impact
        if card.simulation_urgency is not None:
            urgency = card.simulation_urgency
            
        # Legacy/Transient Overrides (Optional)
        if overrides:
            imp_key = f"sim_imp_{card.id}"
            urg_key = f"sim_urg_{card.id}"
            # Only apply if not already set on object? Or override object?
            # Object should be source of truth.
            pass 
            
        candidates.append({
            "id": card.id,
            "impact": impact,
            "urgency": urgency,
            "uncertainty": quality_penalty,
            "_card": card,
            "_state": state
        })
        
    return candidates
