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
            
        if item_type == "Survey Data":
            col_hint = "Columns: Determined by Driver definitions (e.g. Q1, Q2...)"
        else:
            col_hint = """
        Columns for Drivers: id, label, survey_items (comma-separated), range (e.g. 1-5)
        Columns for Cards: id, title, decision_question, stakeholders, drivers (ids), kpis, rules
            """

        system_prompt = f"""
        You are a Data Architect extension for a Decision Support System.
        Your task is to suggest additional {item_type} based on the existing configuration provided below.
        
        Output format: CSV rows only (no header, no markdown).
        {col_hint}
        
        Generate high-quality, relevant data rows.
        """
        
        user_prompt = f"Existing Configuration Context:\n{context}\n\nSuggest 2 new {item_type}:"
        
        try:
            if self.provider == "OpenAI" or self.provider == "OpenRouter":
                extra_headers = {"HTTP-Referer": "http://localhost:8501", "X-Title": "Evidence-Based DSS"} if self.provider == "OpenRouter" else None
                client = openai.OpenAI(
                    base_url="https://openrouter.ai/api/v1" if self.provider == "OpenRouter" else None,
                    api_key=self.api_key,
                    default_headers=extra_headers
                )
                
                
                messages = []
                # Google/Gemma models on OpenRouter often reject 'system' role
                if self.provider == "OpenRouter" and ("google" in self.model_name.lower() or "gemma" in self.model_name.lower()):
                    messages = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
                else:
                    messages = [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt}
                    ]

                try:
                    response = client.chat.completions.create(
                        model=self.model_name,
                        messages=messages,
                        temperature=0.7
                    )
                except openai.BadRequestError as e:
                    # Retry if standard call failed (likely due to system role support)
                    if "instruction" in str(e).lower() or "system" in str(e).lower() or "unsupported" in str(e).lower() or "400" in str(e):
                        fallback_msg = [{"role": "user", "content": f"{system_prompt}\n\n{user_prompt}"}]
                        response = client.chat.completions.create(
                            model=self.model_name,
                            messages=fallback_msg,
                            temperature=0.7
                        )
                    else:
                        raise e
                return response.choices[0].message.content
                
            elif self.provider == "Google (Gemini)":
                genai.configure(api_key=self.api_key)
                model = genai.GenerativeModel(self.model_name)
                response = model.generate_content(system_prompt + "\n" + user_prompt)
                return response.text
                
        except Exception as e:
            msg = str(e)
            if "429" in msg or "rate limit" in msg.lower():
                return f"⚠️ Model Busy (429): The selected model ({self.model_name}) is currently overloaded or rate-limited. Please try another model."
            return f"Error calling LLM: {msg}"
            
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
                # OpenRouter modls endpoint is public, but using key might show specific permissions
                # Try with key if present, else without
                headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
                try:
                    resp = requests.get("https://openrouter.ai/api/v1/models", headers=headers, timeout=10)
                    if resp.status_code == 200:
                        data = resp.json().get("data", [])
                        return sorted([m["id"] for m in data])
                    else:
                        st.error(f"OpenRouter API Error: {resp.status_code} - {resp.text}")
                        return []
                except Exception as ex:
                     st.error(f"Connection Error: {ex}")
                     return []
                    
        except Exception as e:
            st.error(f"Failed to fetch models: {e}")
            return []
            
        return []
