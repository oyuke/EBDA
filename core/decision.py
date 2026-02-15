from typing import List, Dict, Any, Optional
from data.models import DecisionCardConfig, DecisionCardState, CardStatus, RecommendationTemplate

class DecisionEngine:
    def evaluate_card(self, card_config: DecisionCardConfig, evidence_context: Dict[str, float]) -> DecisionCardState:
        """
        Evaluate rules against evidence and return the card state.
        evidence_context: map of variable names to values (e.g. {'psychological_safety': 3.1})
        """
        state = DecisionCardState(card_id=card_config.id)
        
        # Default to GREEN if no rules trigger
        matched_status = CardStatus.GREEN
        matched_message = "No issues detected."

        # Iterate rules
        for rule in card_config.rules:
            try:
                # Security note: eval is used here for MVP flexibility. 
                # In production, use a safe expression parser like simpleeval.
                if eval(rule.condition, {"__builtins__": {}}, evidence_context):
                    matched_status = rule.status
                    matched_message = rule.message
                    state.key_evidence.append(f"Condition met: {rule.condition} ({matched_message})")
                    # Break on first match (priority based on order in config)
                    break 
            except Exception as e:
                # Log error or warning?
                print(f"Error evaluating rule '{rule.condition}': {e}")

        state.status = matched_status

        # Recommendation Logic (MVP: Default to first template if RED/YELLOW)
        if matched_status in [CardStatus.RED, CardStatus.YELLOW] and card_config.recommendation_templates:
            # Simple logic: pick the first one
            # Phase 2: Select best fit based on specific rule or driver
            state.recommendation_draft = card_config.recommendation_templates[0]
        
        return state
