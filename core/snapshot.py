import json
import os
from datetime import datetime
from data.models import Snapshot, Wave

SNAPSHOT_DIR = "snapshots"

class SnapshotManager:
    def __init__(self, output_dir: str = SNAPSHOT_DIR):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def freeze(self, wave: Wave, config_hash: str) -> Snapshot:
        timestamp = datetime.now()
        snap_id = f"{wave.id}_{timestamp.strftime('%Y%m%d_%H%M%S')}"

        # Create Snapshot Metadata
        snapshot = Snapshot(
            id=snap_id,
            wave_id=wave.id,
            created_at=timestamp,
            config_hash=config_hash,
            data_hash="dummy_hash", # Should hash data files
            wave_state=wave
        )

        # Save to file
        file_path = os.path.join(self.output_dir, f"{snap_id}.json")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(snapshot.model_dump_json(indent=2)) # Use pydantic json dump

        return snapshot

    def list_snapshots(self, wave_id: str) -> list[str]:
        # Return list of filenames for wave
        snaps = [f for f in os.listdir(self.output_dir) if f.startswith(wave_id)]
        return sorted(snaps, reverse=True)
