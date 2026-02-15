import pandas as pd
import json
import yaml
from typing import List, Dict, Any, Union
from data.models import DecisionCardConfig, DriverConfig, RuleConfig, CardStatus

class DataConverter:
    @staticmethod
    def csv_to_decision_card(df: pd.DataFrame) -> List[DecisionCardConfig]:
        """
        Converts a CSV with columns:
        [id, title, decision_question, drivers (comma-sep), kpis (comma-sep), rule_condition, rule_status, stakeholders]
        """
        # Group by ID since rules might span rows?
        # Assuming one row per card for simplicity in MVP, but rules are tricky.
        # Let's assume each row is a separate card, and rules are a JSON string or simpler.
        
        cards = []
        for _, row in df.iterrows():
            # Parse required evidence
            drivers = [x.strip() for x in str(row.get('drivers', '')).split(',') if x.strip()]
            kpis = [x.strip() for x in str(row.get('kpis', '')).split(',') if x.strip()]
            
            # Simple rule parsing: condition1:status1|condition2:status2
            rules_raw = str(row.get('rules', ''))
            rules_list = []
            if rules_raw:
                for rule_segment in rules_raw.split('|'):
                    parts = rule_segment.split(':', 2)
                    if len(parts) >= 2:
                        cond = parts[0].strip()
                        stat = parts[1].strip()
                        msg = parts[2].strip() if len(parts) > 2 else f"Rule triggered: {cond}"
                        rules_list.append(RuleConfig(
                            condition=cond,
                            status=CardStatus(stat.upper()) if stat.upper() in CardStatus.__members__ else CardStatus.UNKNOWN,
                            message=msg
                        ))
            
            stakeholders = [x.strip() for x in str(row.get('stakeholders', '')).split(',') if x.strip()]
            
            card = DecisionCardConfig(
                id=str(row['id']),
                title=str(row['title']),
                decision_question=str(row['decision_question']),
                stakeholders=stakeholders,
                required_evidence={"drivers": drivers, "kpis": kpis},
                rules=rules_list,
                recommendation_templates=[]
            )
            cards.append(card)
        return cards

    @staticmethod
    def decision_card_to_csv(cards: List[DecisionCardConfig]) -> pd.DataFrame:
        data = []
        for card in cards:
            # Flatten rules
            rules_str = "|".join([f"{r.condition}:{r.status.value}:{r.message}" for r in card.rules])
            drivers_str = ",".join(card.required_evidence.get('drivers', []))
            kpis_str = ",".join(card.required_evidence.get('kpis', []))
            stakeholders_str = ",".join(card.stakeholders)
            
            data.append({
                "id": card.id,
                "title": card.title,
                "decision_question": card.decision_question,
                "stakeholders": stakeholders_str,
                "drivers": drivers_str,
                "kpis": kpis_str,
                "rules": rules_str
            })
        return pd.DataFrame(data)

    @staticmethod
    def drivers_to_csv(drivers: List[DriverConfig]) -> pd.DataFrame:
        data = []
        for d in drivers:
            items_str = ",".join(d.survey_items)
            range_str = f"{d.range[0]}-{d.range[1]}"
            data.append({
                "id": d.id,
                "label": d.label,
                "survey_items": items_str,
                "range": range_str
            })
        return pd.DataFrame(data)

    @staticmethod
    def csv_to_drivers(df: pd.DataFrame) -> List[DriverConfig]:
        drivers = []
        for _, row in df.iterrows():
            items = [x.strip() for x in str(row.get('survey_items', '')).split(',') if x.strip()]
            range_raw = str(row.get('range', '1-5')).split('-')
            range_val = [float(range_raw[0]), float(range_raw[1])] if len(range_raw) == 2 else [1.0, 5.0]
            
            driver = DriverConfig(
                id=str(row['id']),
                label=str(row['label']),
                survey_items=items,
                range=range_val
            )
            drivers.append(driver)
        return drivers
