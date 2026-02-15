import openai
import google.generativeai as genai
import os
import streamlit as st
from typing import List, Dict, Any

class LLMClient:
    def __init__(self, provider: str, api_key: str, model_name: str = "gpt-4o"):
        self.provider = provider
        self.api_key = api_key
        self.model_name = model_name
        
    def generate_suggestions(self, context: str, item_type: str) -> str:
        """
        Generate CSV rows for Drivers or Cards.
        """
        if not self.api_key:
            return "Error: No API Key provided."
            
        system_prompt = f"""
        You are a Data Architect extension for a Decision Support System.
        Your task is to suggest additional {item_type} based on the existing configuration provided below.
        
        Output format: CSV rows only (no header, no markdown).
        Columns for Drivers: id, label, survey_items (comma-separated), range (e.g. 1-5)
        Columns for Cards: id, title, decision_question, stakeholders, drivers (ids), kpis, rules
        
        Generate 2 high-quality, relevant suggestions that complement the existing set.
        Ensure IDs are unique (increment from existing max ID if possible, else use random suffix).
        """
        
        user_prompt = f"Existing Configuration Context:\n{context}\n\nSuggest 2 new {item_type}:"
        
        try:
            if self.provider == "OpenAI" or self.provider == "OpenRouter":
                client = openai.OpenAI(
                    base_url="https://openrouter.ai/api/v1" if self.provider == "OpenRouter" else None,
                    api_key=self.api_key
                )
                
                response = client.chat.completions.create(
                    model=self.model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ],
                    temperature=0.7
                )
                return response.choices[0].message.content
                
            elif self.provider == "Google (Gemini)":
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(system_prompt + "\n" + user_prompt)
                return response.text
                
        except Exception as e:
            return f"Error calling LLM: {str(e)}"
            
        return "Error: Provider not supported."

    @staticmethod
    def fetch_available_models(provider: str, api_key: str) -> List[str]:
        if not api_key: return []
        
        try:
            if provider == "OpenAI":
                client = openai.OpenAI(api_key=api_key)
                models = client.models.list()
                # Filter for chat models usually starting with gpt
                return sorted([m.id for m in models.data if "gpt" in m.id])
                
            elif provider == "Google (Gemini)":
                genai.configure(api_key=api_key)
                models = genai.list_models()
                # Filter for generateContent supported models
                return sorted([m.name.replace("models/", "") for m in models if "generateContent" in m.supported_generation_methods])
                
            elif provider == "OpenRouter":
                import requests
                headers = {"Authorization": f"Bearer {api_key}"}
                resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers)
                if resp.status_code == 200:
                    data = resp.json().get("data", [])
                    return sorted([m["id"] for m in data])
                    
        except Exception as e:
            st.error(f"Failed to fetch models: {e}")
            return []
            
        return []
