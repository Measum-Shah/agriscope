"""Pydantic schemas for Crop and CropStage entities."""

import uuid
from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class CropStageRead(BaseModel):
    id: uuid.UUID
    stage_name: str
    duration_days: int

    model_config = ConfigDict(from_attributes=True)


class CropRead(BaseModel):
    id: uuid.UUID
    name: str
    scientific_name: Optional[str] = None
    kc_ini: float
    kc_mid: float
    kc_end: float
    description: Optional[str] = None
    stages: List[CropStageRead] = []

    model_config = ConfigDict(from_attributes=True)
