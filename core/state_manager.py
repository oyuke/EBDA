import os
import json
from data.models import AppConfig

class StatePersistence:
    DEFAULT_PATH = "data/runtime_state.json"
    
    @staticmethod
    def save(config: AppConfig, path: str = DEFAULT_PATH):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(config.model_dump_json(indent=2))
            
    @staticmethod
    def load(path: str = DEFAULT_PATH) -> AppConfig:
        if not os.path.exists(path):
            return None
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppConfig(**data)
        except Exception as e:
            # If load fails (e.g. schema mismatch), return None so main can reload default
            print(f"Failed to load state: {e}")
            return None
            
    @staticmethod
    def clear(path: str = DEFAULT_PATH):
        if os.path.exists(path):
            os.remove(path)
