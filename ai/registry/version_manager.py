import json
import logging
import os
import shutil
from datetime import datetime, timezone

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class VersionManager:
    """
    Step 10: Model Versioning Manager for Deep Learning PyTorch Models.
    Registers semantic versions (e.g. v1.0.0) and creates version snapshot directories.
    """

    def __init__(self, registry_dir: str = "ai/registry"):
        self.registry_dir = registry_dir
        self.index_path = os.path.join(self.registry_dir, "registry_index.json")
        os.makedirs(self.registry_dir, exist_ok=True)
        self._init_index()

    def _init_index(self):
        if not os.path.exists(self.index_path):
            with open(self.index_path, "w", encoding="utf-8") as f:
                json.dump({"versions": []}, f, indent=4)

    def register_version(self, model_version: str, dataset_version: str, metrics: dict, models_dir: str = "ai/models") -> dict:
        """Create version snapshot under ai/registry/<version>/ and update registry index."""
        logger.info(f"Registering Deep Learning Model Version: {model_version}...")
        version_dir = os.path.join(self.registry_dir, model_version)
        os.makedirs(version_dir, exist_ok=True)

        if os.path.exists(models_dir):
            for item in os.listdir(models_dir):
                s = os.path.join(models_dir, item)
                d = os.path.join(version_dir, item)
                if os.path.isfile(s):
                    shutil.copy2(s, d)

        entry = {
            "model_version": model_version,
            "framework": "PyTorch",
            "training_date": datetime.now(tz=timezone.utc).isoformat(),
            "dataset_version": dataset_version,
            "metrics": metrics,
            "artifact_path": version_dir
        }

        with open(self.index_path, "r", encoding="utf-8") as f:
            index_data = json.load(f)

        index_data["versions"] = [v for v in index_data["versions"] if v.get("model_version") != model_version]
        index_data["versions"].append(entry)

        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(index_data, f, indent=4)

        logger.info(f"Registered version {model_version} in {self.index_path}")
        return entry
