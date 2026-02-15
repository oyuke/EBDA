from typing import Dict, Any

class PriorityCalculator:
    def __init__(self, weights: Dict[str, float]):
        self.w_impact = weights.get("impact", 1.0)
        self.w_urgency = weights.get("urgency", 1.0)
        self.w_uncertainty = weights.get("uncertainty", 1.0)

    def calculate_saw(self, impact: float, urgency: float, uncertainty: float) -> Dict[str, Any]:
        """
        Simple Additive Weighting (SAW)
        Score = (Impact * w1) + (Urgency * w2) - (Uncertainty * w3)
        All inputs should be 0.0 to 1.0 (normalized).
        """
        # Ensure inputs are 0-1
        impact = max(0.0, min(1.0, impact))
        urgency = max(0.0, min(1.0, urgency))
        uncertainty = max(0.0, min(1.0, uncertainty))

        term_impact = impact * self.w_impact
        term_urgency = urgency * self.w_urgency
        term_risk = uncertainty * self.w_uncertainty # Subtract this

        score = term_impact + term_urgency - term_risk

        return {
            "score": score,
            "breakdown": {
                "impact_term": term_impact,
                "urgency_term": term_urgency,
                "uncertainty_term": -term_risk # Explicitly show it's negative
            },
            "inputs": {
                "impact": impact,
                "urgency": urgency,
                "uncertainty": uncertainty
            }
        }

    # Placeholder for WASPAS (Weighted Aggregated Sum Product Assessment) - Phase 2
    def calculate_waspas(self, impact: float, urgency: float, uncertainty: float) -> Dict[str, Any]:
        # Q = 0.5 * SAW + 0.5 * WPM (Weighted Product Model)
        # Not implemented for MVP
        return self.calculate_saw(impact, urgency, uncertainty)
