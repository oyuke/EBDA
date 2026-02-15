import json
import os
import streamlit as st
from typing import Dict, List

class I18nManager:
    _default_locale = "en"
    _file_path = "configs/locales.json"
    _cache = {}

    @classmethod
    def load(cls) -> Dict:
        """Load locales from file. If missing, return defaults."""
        if not cls._cache:
            if os.path.exists(cls._file_path):
                try:
                    with open(cls._file_path, "r", encoding="utf-8") as f:
                        cls._cache = json.load(f)
                except Exception as e:
                    st.error(f"Error loading locales: {e}")
                    cls._cache = cls._get_default_structure()
            else:
                cls._cache = cls._get_default_structure()
                cls.save(cls._cache)
        return cls._cache

    @classmethod
    def save(cls, data: Dict):
        """Save updated locales to file."""
        os.makedirs(os.path.dirname(cls._file_path), exist_ok=True)
        with open(cls._file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        cls._cache = data

    @classmethod
    def get(cls, key: str, default: str = None) -> str:
        """Get translated string. Key format: 'category.subcategory.item'"""
        lang = st.session_state.get("language", cls._default_locale)
        data = cls.load()
        
        # Helper to traverse dict
        def traverse(d, k_parts):
            curr = d
            for p in k_parts:
                if isinstance(curr, dict) and p in curr:
                    curr = curr[p]
                else:
                    return None
            return curr if isinstance(curr, str) else None

        parts = key.split(".")
        
        # 1. Try active language
        val = traverse(data.get(lang, {}), parts)
        if val is not None: return val
        
        # 2. Fallback to English
        if lang != "en":
            val = traverse(data.get("en", {}), parts)
            if val is not None: return val
            
        # 3. Fallback to default arg or key itself
        return default or key

    @classmethod
    def available_languages(cls) -> List[str]:
        return list(cls.load().keys())

    @staticmethod
    def _get_default_structure():
        """Default seed data"""
        return {
            "en": {
                "sidebar": {
                    "home": "Home",
                    "decision_board": "Decision Board",
                    "evidence_input": "Evidence Input",
                    "data_tools": "Settings & Data",
                    "quality_report": "Quality Report"
                },
                "home": {
                    "title": "Welcome to Evidence-Based DSS",
                    "subtitle": "Rational Decision Making Support System",
                    "load_config": "Load Configuration",
                    "status_loaded": "Configuration Loaded",
                    "status_missing": "Configuration Missing",
                    "action_load": "Load Default Config"
                },
                "common": {
                    "save": "Save",
                    "cancel": "Cancel",
                    "error": "Error",
                    "success": "Success"
                }
            },
            "ja": {
                "sidebar": {
                    "home": "ホーム",
                    "decision_board": "意思決定ボード",
                    "evidence_input": "エビデンス入力",
                    "data_tools": "設定とデータ",
                    "quality_report": "品質レポート"
                },
                "home": {
                    "title": "エビデンスに基づく意思決定支援システムへようこそ",
                    "subtitle": "合理的思考を支援するプラットフォーム",
                    "load_config": "設定ロード",
                    "status_loaded": "設定読込済み",
                    "status_missing": "設定未ロード",
                    "action_load": "デフォルト設定をロード"
                },
                "common": {
                    "save": "保存",
                    "cancel": "キャンセル",
                    "error": "エラー",
                    "success": "成功"
                }

            }
        }
