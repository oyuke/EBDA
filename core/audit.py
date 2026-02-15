from datetime import datetime
import os
import json

AUDIT_FILE = "audit_trail.log"

class AuditLogger:
    def __init__(self, output_file: str = AUDIT_FILE):
        self.output_file = output_file
        # Create file if not exists
        if not os.path.exists(output_file):
            with open(output_file, 'w') as f:
                pass

    def log_action(self, card_id: str, snapshot_id: str, action: str, reason: str, user_target: str = "Unknown"):
        timestamp = datetime.now()
        entry = {
            "timestamp": timestamp.isoformat(),
            "card_id": card_id,
            "snapshot_id": snapshot_id,
            "action": action, # e.g. "Override", "Approve", "Edit"
            "reason": reason,
            "user": user_target
        }
        
        with open(self.output_file, 'a', encoding='utf-8') as f:
            f.write(json.dumps(entry) + "\n")
