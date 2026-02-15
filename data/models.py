from datetime import datetime
from enum import Enum
from typing import List, Dict, Optional, Any
from pydantic import BaseModel, Field

class WaveStatus(str, Enum):
    DRAFT = "draft"
    COLLECTING = "collecting"
    ANALYZING = "analyzing"
    FROZEN = "frozen"
    CLOSED = "closed"

class CardStatus(str, Enum):
    RED = "RED"
    YELLOW = "YELLOW"
    GREEN = "GREEN"
    UNKNOWN = "UNKNOWN"

class ConfidenceLevel(str, Enum):
    HIGH = "High"
    MEDIUM = "Med"
    LOW = "Low"

# Configuration Models
class RuleConfig(BaseModel):
    condition: str
    status: CardStatus
    message: str

class RecommendationTemplate(BaseModel):
    id: str
    action: str
    preconditions: Optional[str] = None
    risks: Optional[str] = None
    success_metrics: Optional[str] = None

class DriverConfig(BaseModel):
    id: str
    label: str
    survey_items: List[str]
    range: List[float] # [min, max]

class DecisionCardConfig(BaseModel):
    id: str
    title: str
    decision_question: str
    stakeholders: List[str]
    required_evidence: Dict[str, List[str]] # e.g. {"drivers": ["..."], "kpis": ["..."]}
    rules: List[RuleConfig]
    recommendation_templates: List[RecommendationTemplate] = []

class AppConfig(BaseModel):
    version: str
    customer_name: str
    priority_weights: Dict[str, float]
    quality_gates: Dict[str, Any]
    decision_cards: List[DecisionCardConfig]
    drivers: List[DriverConfig]

# Runtime Data Models
class QualityCheckResult(BaseModel):
    name: str # e.g. "Sampling Bias", "Missing Ratio"
    passed: bool
    status: str # "pass", "warn", "fail"
    message: str
    details: Dict[str, Any] = {}

class Evidence(BaseModel):
    source_type: str # "survey", "kpi", "interview"
    data_id: str
    timestamp: datetime
    quality_checks: List[QualityCheckResult] = []
    confidence_penalty: float = 0.0 # 0.0 to 1.0 (1.0 = highly penalized/uncertain)
    raw_data: Any = None # Keep simple for MVP

class MetricValue(BaseModel):
    metric_id: str
    value: float
    n_count: int = 0
    missing_ratio: float = 0.0

class DecisionCardState(BaseModel):
    card_id: str
    status: CardStatus = CardStatus.UNKNOWN
    confidence: ConfidenceLevel = ConfidenceLevel.LOW
    confidence_penalty: float = 0.0
    
    score_impact: float = 0.0
    score_urgency: float = 0.0
    score_uncertainty: float = 0.0
    total_priority: float = 0.0

    key_evidence: List[str] = [] # e.g. ["Rule matched: turnover > 0.15"]
    recommendation_draft: Optional[RecommendationTemplate] = None
    
    human_override_reason: Optional[str] = None
    human_decision_status: Optional[str] = None # "Approve", "Edit", "Override"
    final_decision_text: Optional[str] = None

class Wave(BaseModel):
    id: str
    name: str
    status: WaveStatus = WaveStatus.DRAFT
    created_at: datetime = Field(default_factory=datetime.now)
    cards: Dict[str, DecisionCardState] = {} # Map card_id to state
    evidence_refs: List[str] = []

class Snapshot(BaseModel):
    id: str
    wave_id: str
    created_at: datetime
    config_hash: str
    data_hash: str
    wave_state: Wave
