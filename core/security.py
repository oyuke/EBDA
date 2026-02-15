import os
import io
import json
from cryptography.fernet import Fernet
import streamlit as st

class SecurityManager:
    _key = None
    _secrets_file = ".secrets/api_keys.enc"
    _key_file = ".secrets/master.key"

    @classmethod
    def _get_master_key(cls):
        if cls._key: return cls._key
        
        # Ensure dir exists
        os.makedirs(".secrets", exist_ok=True)
        
        if os.path.exists(cls._key_file):
            with open(cls._key_file, "rb") as f:
                cls._key = f.read()
        else:
            cls._key = Fernet.generate_key()
            with open(cls._key_file, "wb") as f:
                f.write(cls._key)
        return cls._key

    @classmethod
    def save_api_key(cls, service: str, api_key: str):
        key = cls._get_master_key()
        f = Fernet(key)
        
        # Load existing
        secrets = cls._load_secrets()
        secrets[service] = api_key
        
        # Encrypt and Save
        content = json.dumps(secrets).encode()
        encrypted = f.encrypt(content)
        
        with open(cls._secrets_file, "wb") as file:
            file.write(encrypted)
            
    @classmethod
    def get_api_key(cls, service: str) -> str:
        secrets = cls._load_secrets()
        return secrets.get(service, "")
        
    @classmethod
    def _load_secrets(cls):
        if not os.path.exists(cls._secrets_file):
            return {}
        
        try:
            key = cls._get_master_key()
            f = Fernet(key)
            with open(cls._secrets_file, "rb") as file:
                encrypted = file.read()
            decrypted = f.decrypt(encrypted)
            return json.loads(decrypted.decode())
        except Exception as e:
            # Handle key mismatch or corruption
            return {}

    @classmethod
    def verify_keys_exist(cls):
        # Helper for UI status
        secrets = cls._load_secrets()
        return {k: bool(v) for k, v in secrets.items()}
