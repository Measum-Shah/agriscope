"""Model artifact registry with filesystem and MinIO/S3 backends and SHA-256 integrity verification."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import joblib
import pandas as pd

from .model_card import ModelCard


def compute_file_sha256(path: Path | str) -> str:
    """Compute SHA-256 checksum of a file on disk."""
    hasher = hashlib.sha256()
    with open(path, "rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


@dataclass
class ModelBundle:
    """Bundle containing model pipeline, conformal calibrator, card, and background samples."""

    model_id: str
    version: str
    pipeline: Any
    conformal_predictor: Any
    model_card: ModelCard
    background_data: Optional[pd.DataFrame] = None
    checksums: Optional[Dict[str, str]] = None


class FilesystemStore:
    """Filesystem-backed artifact storage."""

    def __init__(self, root_dir: str | Path = "./artifacts"):
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def get_bundle_dir(self, model_id: str, version: str) -> Path:
        return self.root_dir / model_id / version

    def save(self, bundle: ModelBundle) -> Dict[str, str]:
        bundle_dir = self.get_bundle_dir(bundle.model_id, bundle.version)
        bundle_dir.mkdir(parents=True, exist_ok=True)

        # Save pipeline and conformal
        model_path = bundle_dir / "model.joblib"
        joblib.dump(bundle.pipeline, model_path)

        conformal_path = bundle_dir / "conformal.joblib"
        joblib.dump(bundle.conformal_predictor, conformal_path)

        # Save background data if present
        if bundle.background_data is not None:
            bg_path = bundle_dir / "background.parquet"
            bundle.background_data.to_parquet(bg_path, index=False)

        # Save model card
        card_path = bundle_dir / "model_card.json"
        bundle.model_card.save(card_path)

        # Compute checksums
        checksums: Dict[str, str] = {}
        for f in bundle_dir.iterdir():
            if f.name != "checksums.json" and f.is_file():
                checksums[f.name] = compute_file_sha256(f)

        chk_path = bundle_dir / "checksums.json"
        with open(chk_path, "w", encoding="utf-8") as fp:
            json.dump(checksums, fp, indent=2)

        return checksums

    def load(self, model_id: str, version: str, verify: bool = True) -> ModelBundle:
        bundle_dir = self.get_bundle_dir(model_id, version)
        if not bundle_dir.exists():
            raise FileNotFoundError(f"Model {model_id}:{version} not found at {bundle_dir}")

        # Verify integrity
        chk_path = bundle_dir / "checksums.json"
        checksums: Dict[str, str] = {}
        if chk_path.exists():
            with open(chk_path, "r", encoding="utf-8") as fp:
                checksums = json.load(fp)

        if verify and checksums:
            for filename, expected_hash in checksums.items():
                f_path = bundle_dir / filename
                if not f_path.exists():
                    raise FileNotFoundError(f"Missing artifact file: {filename}")
                actual_hash = compute_file_sha256(f_path)
                if actual_hash != expected_hash:
                    raise ValueError(
                        f"Integrity check failed for {filename}! Expected {expected_hash}, got {actual_hash}"
                    )

        pipeline = joblib.load(bundle_dir / "model.joblib")
        conformal = joblib.load(bundle_dir / "conformal.joblib")
        model_card = ModelCard.load(bundle_dir / "model_card.json")

        bg_path = bundle_dir / "background.parquet"
        bg_data = pd.read_parquet(bg_path) if bg_path.exists() else None

        return ModelBundle(
            model_id=model_id,
            version=version,
            pipeline=pipeline,
            conformal_predictor=conformal,
            model_card=model_card,
            background_data=bg_data,
            checksums=checksums,
        )

    def list_models(self) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        if not self.root_dir.exists():
            return results
        for model_dir in self.root_dir.iterdir():
            if model_dir.is_dir():
                for ver_dir in model_dir.iterdir():
                    if ver_dir.is_dir() and (ver_dir / "model_card.json").exists():
                        try:
                            card = ModelCard.load(ver_dir / "model_card.json")
                            results.append(
                                {
                                    "model_id": model_dir.name,
                                    "version": ver_dir.name,
                                    "algorithm": card.algorithm,
                                    "provenance": card.provenance,
                                    "metrics": card.metrics,
                                    "path": str(ver_dir),
                                }
                            )
                        except Exception:
                            pass
        return results


class S3ArtifactStore:
    """MinIO / S3-backed artifact store."""

    def __init__(
        self,
        bucket: str = "agriscope-models",
        endpoint_url: Optional[str] = None,
        aws_access_key_id: Optional[str] = None,
        aws_secret_access_key: Optional[str] = None,
        region_name: str = "us-east-1",
    ):
        import boto3

        self.bucket = bucket
        ep = endpoint_url or os.getenv("MINIO_ENDPOINT", "http://localhost:9000")
        key = aws_access_key_id or os.getenv("MINIO_ROOT_USER", "minioadmin")
        secret = aws_secret_access_key or os.getenv("MINIO_ROOT_PASSWORD", "minioadmin")

        self.s3 = boto3.client(
            "s3",
            endpoint_url=ep,
            aws_access_key_id=key,
            aws_secret_access_key=secret,
            region_name=region_name,
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        try:
            self.s3.head_bucket(Bucket=self.bucket)
        except Exception:
            try:
                self.s3.create_bucket(Bucket=self.bucket)
            except Exception:
                pass

    def upload_file(self, local_path: Path, s3_key: str) -> None:
        self.s3.upload_file(str(local_path), self.bucket, s3_key)

    def download_file(self, s3_key: str, local_path: Path) -> None:
        local_path.parent.mkdir(parents=True, exist_ok=True)
        self.s3.download_file(self.bucket, s3_key, str(local_path))


class ModelRegistry:
    """Unified model registry managing model bundles with integrity verification."""

    def __init__(
        self,
        store_type: str = "filesystem",
        root_dir: str | Path = "./artifacts",
        s3_bucket: str = "agriscope-models",
    ):
        self.store_type = store_type.lower()
        self.fs_store = FilesystemStore(root_dir=root_dir)
        self.s3_store: Optional[S3ArtifactStore] = None
        if self.store_type in ("s3", "minio"):
            try:
                self.s3_store = S3ArtifactStore(bucket=s3_bucket)
            except Exception:
                pass

    def register_model(self, bundle: ModelBundle) -> Dict[str, str]:
        """Save and register model bundle, recording checksums."""
        checksums = self.fs_store.save(bundle)

        if self.s3_store is not None:
            bundle_dir = self.fs_store.get_bundle_dir(bundle.model_id, bundle.version)
            prefix = f"{bundle.model_id}/{bundle.version}"
            for f in bundle_dir.iterdir():
                if f.is_file():
                    self.s3_store.upload_file(f, f"{prefix}/{f.name}")

        return checksums

    def get_model(self, model_id: str, version: str, verify: bool = True) -> ModelBundle:
        """Retrieve model bundle with optional integrity verification."""
        return self.fs_store.load(model_id, version, verify=verify)

    def list_models(self) -> List[Dict[str, Any]]:
        """List registered models and versions."""
        return self.fs_store.list_models()
