"""Model card metadata generation, serialization, and validation."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional


def get_git_sha() -> str:
    """Retrieve the current Git commit SHA or fallback to 'unknown'."""
    try:
        res = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return res.stdout.strip()
    except Exception:
        return "unknown"


@dataclass
class ModelCard:
    """Structured documentation card for AgriScope machine learning models."""

    model_id: str
    algorithm: str
    version: str
    feature_schema: str
    feature_names: List[str]
    hyperparameters: Dict[str, Any]
    dataset_id: str
    dataset_hash: str
    provenance: str
    is_synthetic: bool
    metrics: Dict[str, Any]
    conformal: Dict[str, Any]
    training_time_seconds: float
    git_sha: str
    created_at: str
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert card to dictionary representation."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Serialize card to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)

    def save(self, file_path: str | Path) -> Path:
        """Save model card to JSON file on disk."""
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            f.write(self.to_json())
        return p

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> ModelCard:
        """Create ModelCard instance from dictionary."""
        return cls(**data)

    @classmethod
    def load(cls, file_path: str | Path) -> ModelCard:
        """Load ModelCard from JSON file."""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return cls.from_dict(data)


def create_model_card(
    model_id: str,
    algorithm: str,
    version: str,
    feature_schema: str,
    feature_names: List[str],
    hyperparameters: Dict[str, Any],
    dataset_id: str,
    dataset_hash: str,
    provenance: str,
    is_synthetic: bool,
    metrics: Dict[str, Any],
    conformal: Dict[str, Any],
    training_time_seconds: float,
    description: Optional[str] = None,
    git_sha: Optional[str] = None,
) -> ModelCard:
    """Factory creating a fully-populated ModelCard."""
    sha = git_sha if git_sha is not None else get_git_sha()
    timestamp = datetime.now(timezone.utc).isoformat()

    return ModelCard(
        model_id=model_id,
        algorithm=algorithm,
        version=version,
        feature_schema=feature_schema,
        feature_names=feature_names,
        hyperparameters=hyperparameters,
        dataset_id=dataset_id,
        dataset_hash=dataset_hash,
        provenance=provenance,
        is_synthetic=is_synthetic,
        metrics=metrics,
        conformal=conformal,
        training_time_seconds=round(training_time_seconds, 2),
        git_sha=sha,
        created_at=timestamp,
        description=description,
    )
