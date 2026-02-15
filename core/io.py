import yaml
import pandas as pd
from typing import Dict, Any, List
from data.models import AppConfig, DecisionCardConfig, RuleConfig, DriverConfig

class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path

    def load_config(self) -> AppConfig:
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)

        # Convert simple types to Models
        drivers = [DriverConfig(**d) for d in data.get("drivers", [])]
        
        cards = []
        for c in data.get("decision_cards", []):
            rules = [RuleConfig(**r) for r in c.get("rules", [])]
            # Recommendation templates handled by Pydantic if recursive
            cards.append(DecisionCardConfig(
                **{k:v for k,v in c.items() if k != 'rules'},
                rules=rules
            ))

        return AppConfig(
            version=data.get("version", "1.0"),
            customer_name=data.get("customer_name", "Unknown"),
            priority_weights=data.get("priority_weights", {}),
            quality_gates=data.get("quality_gates", {}),
            decision_cards=cards,
            drivers=drivers
        )

class DataLoader:
    def load_csv(self, file_path: str) -> pd.DataFrame:
        try:
            return pd.read_csv(file_path)
        except FileNotFoundError:
            # For MVP, try creating dummy data if not found
            print(f"File {file_path} not found.")
            return pd.DataFrame() # Empty
