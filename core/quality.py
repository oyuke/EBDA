import pandas as pd
import numpy as np
from typing import List, Dict, Any, Tuple
from data.models import QualityCheckResult

class QualityGateway:
    def __init__(self, config: Dict[str, Any]):
        self.min_n = config.get("min_n_count", 5)
        self.max_missing = config.get("max_missing_ratio", 0.2)
        # self.min_alpha = config.get("min_cronbach_alpha", 0.7) # MVP: Future

    def check_survey_data(self, df: pd.DataFrame) -> Tuple[float, List[QualityCheckResult]]:
        """
        Returns (confidence_penalty, list_of_checks)
        penalty: 0.0 (Perfect) -> 1.0 (Unusable)
        """
        results = []
        penalty_score = 0.0

        # Check 1: Sample Size (n)
        n = len(df)
        if n < self.min_n:
            res = QualityCheckResult(
                name="Sample Size",
                passed=False,
                status="warn",
                message=f"Sample size n={n} is below threshold ({self.min_n}). Results are unstable.",
                details={"n": n, "threshold": self.min_n}
            )
            penalty_score += 0.4 # High penalty for low n
            results.append(res)
        else:
            results.append(QualityCheckResult(
                name="Sample Size", passed=True, status="pass", message=f"n={n} OK", details={"n": n}
            ))

        # Check 2: Missing Ratio
        # Calculate overall missing ratio in the dataframe
        missing_count = df.isnull().sum().sum()
        total_cells = df.size
        missing_ratio = missing_count / total_cells if total_cells > 0 else 1.0

        if missing_ratio > self.max_missing:
            res = QualityCheckResult(
                name="Missing Ratio",
                passed=False,
                status="warn",
                message=f"Missing data ratio {missing_ratio:.1%} exceeds threshold ({self.max_missing:.1%}).",
                details={"missing_ratio": missing_ratio}
            )
            penalty_score += 0.3
            results.append(res)
        else:
            results.append(QualityCheckResult(
                name="Missing Ratio", passed=True, status="pass", message=f"Missing {missing_ratio:.1%} OK", details={"missing_ratio": missing_ratio}
            ))

        # Cap penalty at 1.0
        return min(penalty_score, 1.0), results

    def check_kpi_series(self, series: List[float]) -> Tuple[float, List[QualityCheckResult]]:
        # Simple check for KPIs
        results = []
        penalty = 0.0
        
        # Check if list is empty
        if not series:
            return 1.0, [QualityCheckResult(name="KPI Data", passed=False, status="fail", message="No data provided")]

        # Check for outliers (basic z-score or just sanity) - MVP: skip
        
        return penalty, results
