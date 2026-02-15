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
        # WASPAS Logic: Q = lambda * SAW + (1-lambda) * WPM
        # WPM (Weighted Product Model): Product of (Value^Weight)
        # Note: uncertainty is "negative" criteria. In WPM, negative criteria is usually (Value^-Weight) 
        # But here we treat uncertainty as Penalty. 
        # To avoid complex numbers or division by zero, we'll transform Uncertainty to "Certainty" (1 - Uncertainty)
        
        # 1. Calculate SAW (Base)
        saw_res = self.calculate_saw(impact, urgency, uncertainty)
        saw_score = saw_res["score"]
        
        # 2. Calculate WPM
        # Impact/Urgency are benefit criteria: Value^Weight
        # Quantities must be > 0. Let's clamp at a small epsilon.
        eps = 0.01
        
        # Transform Uncertainty to Certainty (Benefit criterion) for Multiplicative model
        certainty = 1.0 - uncertainty
        
        term1 = max(eps, impact) ** self.w_impact
        term2 = max(eps, urgency) ** self.w_urgency
        term3 = max(eps, certainty) ** self.w_uncertainty # Treated as benefit now
        
        wpm_score = term1 * term2 * term3
        
        # 3. Combine (Lambda = 0.5 usually)
        lambda_val = 0.5
        waspas_score = (lambda_val * saw_score) + ((1 - lambda_val) * wpm_score)
        
        return {
            "score": waspas_score,
            "method": "WASPAS",
            "components": {
                "saw_score": saw_score,
                "wpm_score": wpm_score,
                "lambda": lambda_val
            },
            "breakdown": saw_res["breakdown"] # Keep SAW breakdown for explanation as it's easier
        }
