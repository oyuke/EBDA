import pandas as pd
import io

class DataTemplates:
    @staticmethod
    def get_driver_template() -> pd.DataFrame:
        data = [
            {"id": "DRV_001", "label": "Psychological Safety", "survey_items": "Q1,Q2,Q3", "range": "1-5"},
            {"id": "DRV_002", "label": "Workload Balance", "survey_items": "Q4,Q5", "range": "1-5"},
        ]
        return pd.DataFrame(data)

    @staticmethod
    def get_card_template() -> pd.DataFrame:
        data = [
            {
                "id": "D001",
                "title": "Prevent Junior Turnover",
                "decision_question": "Should we implement retention program?",
                "stakeholders": "HR, Dept Flight",
                "drivers": "DRV_001,DRV_002",
                "kpis": "turnover_rate, overtime_hours",
                "rules": "psychological_safety < 3.0 : RED : Safety is low | overtime_hours > 40 : YELLOW : High overtime"
            }
        ]
        return pd.DataFrame(data)

    @staticmethod
    def get_survey_template() -> pd.DataFrame:
        # Based on setup_sample_data.py
        data = [
            {"employee_id": "u001", "Q1": 4, "Q2": 5, "Q3": 4, "Q4": 3, "Q5": 2},
            {"employee_id": "u002", "Q1": 2, "Q2": 1, "Q3": 2, "Q4": 5, "Q5": 5},
        ]
        return pd.DataFrame(data)

    @staticmethod
    def get_llm_prompt_config() -> str:
        return """
You are an expert Data Architect for an Evidence-Based Decision System.
Please generate a CSV dataset for **Decision Drivers** and **Decision Cards** based on the user's domain.

Format 1: Drivers CSV
Columns: id, label, survey_items (comma-separated), range (e.g. 1-5)

Format 2: Decision Cards CSV
Columns: id, title, decision_question, stakeholders, drivers (ids), kpis, rules (condition:STATUS:message | ...)

Domain: [INSERT DOMAIN HERE]
        """

    @staticmethod
    def get_llm_prompt_survey(drivers_list: str) -> str:
        return f"""
You are a Data Generator. Create a CSV for Survey Responses.
The survey covers these drivers: {drivers_list}.
Assume 5-7 questions per driver (e.g. Q1..Qn).
Generate 10 rows of synthetic employee data.
Output ONLY the CSV.
        """
