import pytest
import pandas as pd
from core.quality import QualityGateway
from core.priority import PriorityCalculator, SAWCalculator
from core.decision import DecisionEngine, DecisionCardConfig, RuleConfig, CardStatus

def test_quality_gate_low_n():
    config = {"min_n_count": 5}
    gate = QualityGateway(config)
    
    # n=2, check warnings
    df = pd.DataFrame({"dummy": [1, 2]})
    penalty, checks = gate.check_survey_data(df)
    
    # Should get warning
    assert any("Sample Size" in c.name and c.status == "warn" for c in checks)
    assert penalty > 0.0

def test_quality_gate_missing():
    config = {"max_missing_ratio": 0.2}
    gate = QualityGateway(config)
    
    # 5 rows, 1 col, 3 missing -> 60% missing > 20%
    df = pd.DataFrame({"col": [1, None, None, None, 2]})
    penalty, checks = gate.check_survey_data(df)
    
    assert any("Missing Ratio" in c.name and c.status == "warn" for c in checks)
    assert penalty > 0.0

def test_priority_saw():
    weights = {"impact": 1.0, "urgency": 1.5, "uncertainty": 1.0}
    calc = PriorityCalculator(weights)
    
    # Simple calculation
    res = calc.calculate_saw(impact=0.8, urgency=0.6, uncertainty=0.2)
    
    # Score = (0.8 * 1.0) + (0.6 * 1.5) - (0.2 * 1.0) = 0.8 + 0.9 - 0.2 = 1.5
    assert res["score"] == pytest.approx(1.5)
    assert res["breakdown"]["uncertainty_term"] == pytest.approx(-0.2)

def test_decision_engine_red():
    card = DecisionCardConfig(
        id="test", title="T", decision_question="Q", stakeholders=[], required_evidence={},
        rules=[
            RuleConfig(condition="score < 50", status=CardStatus.RED, message="Low score")
        ]
    )
    engine = DecisionEngine()
    context = {"score": 40}
    state = engine.evaluate_card(card, context)
    
    assert state.status == CardStatus.RED
    assert "Low score" in state.key_evidence[0]
