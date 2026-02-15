from typing import List, Dict, Any, Tuple
import math

class PriorityCalculator:
    def __init__(self, weights: Dict[str, float]):
        self.w_impact = weights.get("impact", 1.0)
        self.w_urgency = weights.get("urgency", 1.0)
        self.w_uncertainty = weights.get("uncertainty", 1.0)

    # --- Individual (Stateless) Calculations ---

    def calculate_saw(self, impact: float, urgency: float, uncertainty: float) -> Dict[str, Any]:
        """Simple Additive Weighting (SAW)"""
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
                "uncertainty_term": -term_risk
            },
            "inputs": {"impact": impact, "urgency": urgency, "uncertainty": uncertainty}
        }

    def calculate_waspas(self, impact: float, urgency: float, uncertainty: float) -> Dict[str, Any]:
        """WASPAS (Weighted Aggregated Sum Product Assessment)"""
        # 1. Base SAW
        saw_res = self.calculate_saw(impact, urgency, uncertainty)
        saw_score = saw_res["score"]
        
        # 2. WPM (Weighted Product Model)
        eps = 0.01
        certainty = 1.0 - uncertainty
        
        term1 = max(eps, impact) ** self.w_impact
        term2 = max(eps, urgency) ** self.w_urgency
        term3 = max(eps, certainty) ** self.w_uncertainty
        
        wpm_score = term1 * term2 * term3
        
        # 3. Combine
        lambda_val = 0.5
        waspas_score = (lambda_val * saw_score) + ((1 - lambda_val) * wpm_score)
        
        return {
            "score": waspas_score,
            "method": "WASPAS",
            "components": {"saw_score": saw_score, "wpm_score": wpm_score, "lambda": lambda_val},
            "breakdown": saw_res["breakdown"]
        }

    # --- Batch Ranking (Stateful/Relative) ---

    def rank_candidates(self, candidates: List[Dict[str, Any]], method: str = "SAW") -> List[Dict[str, Any]]:
        """
        Rank a full list of candidates.
        Candidates must have: 'id', 'impact', 'urgency', 'uncertainty'.
        Returns list with added 'score' and 'rank' keys.
        """
        # Sanitization
        processed = []
        for c in candidates:
            c['impact'] = max(0.0, min(1.0, c.get('impact', 0.0)))
            c['urgency'] = max(0.0, min(1.0, c.get('urgency', 0.0)))
            c['uncertainty'] = max(0.0, min(1.0, c.get('uncertainty', 0.0)))
            processed.append(c)

        if not processed:
             return []

        if "TOPSIS" in method:
            return self._calculate_topsis_batch(processed)
        elif "Composite" in method:
            return self._calculate_composite_batch(processed)
        elif "WASPAS" in method:
            # WASPAS is technically independent per row in this impl, but treating as batch for consistency
            for c in processed:
                res = self.calculate_waspas(c['impact'], c['urgency'], c['uncertainty'])
                c['score'] = res['score']
                c['_details'] = res
        else:
            # SAW Default
            for c in processed:
                res = self.calculate_saw(c['impact'], c['urgency'], c['uncertainty'])
                c['score'] = res['score']
                c['_details'] = res

        # Sort descending by score
        processed.sort(key=lambda x: x['score'], reverse=True)
        return processed

    def _calculate_topsis_batch(self, candidates: List[Dict]) -> List[Dict]:
        """
        Technique for Order of Preference by Similarity to Ideal Solution (TOPSIS)
        """
        if not candidates: return []
        
        # 1. Weights
        # We have 3 criteria: Impact (+), Urgency (+), Uncertainty (-)
        # Uncertainty is negative, but in TOPSIS usually all are benefit/cost.
        # We treat Uncertainty as COST criteria.
        
        # Construct decision matrix
        # Columns: [Impact, Urgency, Uncertainty]
        start_impacts = [c['impact'] for c in candidates]
        start_urgencies = [c['urgency'] for c in candidates]
        start_uncertainties = [c['uncertainty'] for c in candidates]
        
        # Norm weights
        w_sum = self.w_impact + self.w_urgency + self.w_uncertainty
        w1 = self.w_impact / w_sum if w_sum else 0.33
        w2 = self.w_urgency / w_sum if w_sum else 0.33
        w3 = self.w_uncertainty / w_sum if w_sum else 0.33
        
        # 2. Vector Normalization (x / sqrt(sum(x^2)))
        def normalize_vec(vec):
            denom = math.sqrt(sum(x*x for x in vec))
            return [x/denom if denom else 0 for x in vec]

        # Since inputs are 0-1, denom works.
        norm_imp = normalize_vec(start_impacts)
        norm_urg = normalize_vec(start_urgencies)
        norm_unc = normalize_vec(start_uncertainties)
        
        # 3. Weighted Normalized Matrix
        weighted_imp = [x * w1 for x in norm_imp]
        weighted_urg = [x * w2 for x in norm_urg]
        weighted_unc = [x * w3 for x in norm_unc]
        
        # 4. Determine Ideal (A*) and Negative-Ideal (A-) Solutions
        # Impact/Urgency = Benefit (Max is best)
        # Uncertainty = Cost (Min is best)
        
        ideal_imp = max(weighted_imp) if weighted_imp else 0
        ideal_urg = max(weighted_urg) if weighted_urg else 0
        ideal_unc = min(weighted_unc) if weighted_unc else 0 # Cost -> Min is ideal
        
        neg_ideal_imp = min(weighted_imp) if weighted_imp else 0
        neg_ideal_urg = min(weighted_urg) if weighted_urg else 0
        neg_ideal_unc = max(weighted_unc) if weighted_unc else 0 # Cost -> Max is worst
        
        # 5. Calculate Separation Measures
        for i, c in enumerate(candidates):
            # Distance to Ideal (S+)
            d_pos = math.sqrt(
                (weighted_imp[i] - ideal_imp)**2 +
                (weighted_urg[i] - ideal_urg)**2 +
                (weighted_unc[i] - ideal_unc)**2
            )
            # Distance to Negative Ideal (S-)
            d_neg = math.sqrt(
                (weighted_imp[i] - neg_ideal_imp)**2 +
                (weighted_urg[i] - neg_ideal_urg)**2 +
                (weighted_unc[i] - neg_ideal_unc)**2
            )
            
            # 6. Relative Closeness (C*)
            # Score = S- / (S+ + S-)
            if (d_pos + d_neg) == 0:
                score = 0
            else:
                score = d_neg / (d_pos + d_neg)
            
            c['score'] = score
            c['_details'] = {
                "method": "TOPSIS",
                "S+": d_pos,
                "S-": d_neg
            }
            
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates

    def _calculate_composite_batch(self, candidates: List[Dict]) -> List[Dict]:
        """
        Composite Rank: Aggregates ranks from SAW, WASPAS, and TOPSIS.
        Using Borda Count or Average Rank.
        """
        # Create copies to run independent rankings
        import copy
        
        # Run SAW
        c_saw = self.rank_candidates(copy.deepcopy(candidates), method="SAW")
        # Map ID to Rank (0-indexed)
        rank_map_saw = {x['id']: i for i, x in enumerate(c_saw)}
        
        # Run WASPAS
        c_waspas = self.rank_candidates(copy.deepcopy(candidates), method="WASPAS")
        rank_map_waspas = {x['id']: i for i, x in enumerate(c_waspas)}
        
        # Run TOPSIS
        c_topsis = self.rank_candidates(copy.deepcopy(candidates), method="TOPSIS")
        rank_map_topsis = {x['id']: i for i, x in enumerate(c_topsis)}
        
        # Aggregate
        # Lower rank is better (0=1st place)
        # Score = 1 / (1 + AvgRank) to normalize to 0-1ish for display, or just inverted rank sum.
        # Let's use simple Borda score: Points = (N - Rank). Sum points.
        N = len(candidates)
        
        for c in candidates:
            cid = c['id']
            r1 = rank_map_saw.get(cid, N)
            r2 = rank_map_waspas.get(cid, N)
            r3 = rank_map_topsis.get(cid, N)
            
            avg_rank = (r1 + r2 + r3) / 3.0
            
            # Normalize to a score 0-1 for compatibility with visualizers
            # A rank of 0 (best) should give score near 1.
            # A rank of N (worst) should give score near 0.
            # Linear interp: Score = 1 - (Rank / N)
            score = 1.0 - (avg_rank / N) if N > 0 else 0
            
            c['score'] = max(0.0, score)
            c['_details'] = {
                "method": "Composite",
                "ranks": {"SAW": r1+1, "WASPAS": r2+1, "TOPSIS": r3+1},
                "avg_rank": avg_rank + 1
            }
            
        candidates.sort(key=lambda x: x['score'], reverse=True)
        return candidates
