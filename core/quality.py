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

    def _calculate_cronbach_alpha(self, df: pd.DataFrame) -> float:
        """
        Calculate Cronbach's alpha manually.
        alpha = (k / (k-1)) * (1 - (sum(var_items) / var_total))
        """
        item_scores = df
        k = item_scores.shape[1]
        
        if k < 2:
            return 0.0 # Cannot calculate correlation for <2 items
            
        # Variance of each item
        var_items = item_scores.var(ddof=1)
        sum_var_items = var_items.sum()
        
        # Variance of total score
        total_scores = item_scores.sum(axis=1)
        var_total = total_scores.var(ddof=1)
        
        if var_total == 0:
            return 0.0
            
        alpha = (k / (k - 1)) * (1 - (sum_var_items / var_total))
        return alpha

    def check_cronbach_alpha(self, df: pd.DataFrame, drivers: List[Any]) -> Tuple[float, List[QualityCheckResult]]:
        """
        Check alpha for each driver with multiple items.
        Returns penalty accumulator.
        """
        results = []
        penalty = 0.0
        min_alpha = 0.7 # Hardcoded default if not in config
        
        for driver in drivers:
            items = driver.survey_items
            if len(items) < 2:
                # Need at least 2 items to check consistency
                continue
                
            cols_present = [c for c in items if c in df.columns]
            if len(cols_present) < 2:
                continue
            
            sub_df = df[cols_present].dropna()
            if len(sub_df) < 5: 
                # Too few samples to calculate alpha reliably
                continue
                
            alpha = self._calculate_cronbach_alpha(sub_df)
            
            if alpha < min_alpha:
                res = QualityCheckResult(
                    name=f"Reliability ({driver.label})",
                    passed=False,
                    status="warn",
                    message=f"Cronbach's alpha {alpha:.2f} < {min_alpha} for '{driver.label}' (Inconsistent responses).",
                    details={"alpha": alpha, "driver": driver.id}
                )
                penalty += 0.1 # Mild penalty per unreliable driver
                results.append(res)
            else:
                results.append(QualityCheckResult(
                    name=f"Reliability ({driver.label})",
                    passed=True,
                    status="pass",
                    message=f"Alpha {alpha:.2f} OK",
                    details={"alpha": alpha}
                ))
        
        return penalty, results

    def check_kpi_series(self, series: List[float]) -> Tuple[float, List[QualityCheckResult]]:
        # Simple check for KPIs
        results = []
        penalty = 0.0
        
        # Check if list is empty
        if not series:
            return 1.0, [QualityCheckResult(name="KPI Data", passed=False, status="fail", message="No data provided")]

        # Check for outliers (basic z-score or just sanity) - MVP: skip
        
        return penalty, results
