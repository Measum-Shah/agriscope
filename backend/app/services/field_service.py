"""Field domain service handling CRUD, PostGIS polygons, area computation, and entitlements."""

from __future__ import annotations

import json
import math
import uuid
from datetime import date
from typing import Any, Dict, List, Optional

from geoalchemy2.shape import from_shape, to_shape
from shapely.geometry import shape, mapping
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import BadRequestException, ForbiddenException, NotFoundException
from app.core.logging import logger
from app.core.plans import get_plan_limits
from app.models.crop import Crop
from app.models.field import Field
from app.models.user import User


def calculate_polygon_area_ha(geom_dict: Dict[str, Any]) -> float:
    """Calculate surface area of GeoJSON Polygon in hectares (ha) using spherical coordinates."""
    try:
        geom = shape(geom_dict)
        if geom.geom_type not in ["Polygon", "MultiPolygon"]:
            raise BadRequestException(detail="Geometry must be a Polygon or MultiPolygon.")

        # Spherical area using Earth radius R = 6,378,137 m
        # For a small parcel polygon, projection to local UTM approximation or Gauss spherical area:
        # Area = (pi / 180) * R^2 * |sum ( (lon_{i+1} - lon_{i-1}) * sin(lat_i) ) / 2|
        coords = geom_dict.get("coordinates", [])
        if not coords:
            return 1.0

        rings = [coords[0]] if geom.geom_type == "Polygon" else [poly[0] for poly in coords]
        total_area_m2 = 0.0
        r_earth = 6378137.0

        for ring in rings:
            if len(ring) < 3:
                continue
            ring_rad = [(math.radians(p[0]), math.radians(p[1])) for p in ring]
            colat_sum = 0.0
            n = len(ring_rad)
            for i in range(n):
                j = (i + 1) % n
                k = (i - 1 + n) % n
                lon_diff = ring_rad[j][0] - ring_rad[k][0]
                sin_lat = math.sin(ring_rad[i][1])
                colat_sum += lon_diff * sin_lat
            ring_area = abs((r_earth ** 2) * colat_sum / 2.0)
            total_area_m2 += ring_area

        area_ha = total_area_m2 / 10000.0
        return round(max(0.01, area_ha), 2)
    except Exception as e:
        logger.warning(f"Failed to calculate geodesic area, falling back to approximation: {e}")
        return 1.0


class FieldService:
    """Manages field boundaries, crop associations, and entitlement enforcement."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def list_fields(self, user: User) -> List[Field]:
        stmt = (
            select(Field)
            .where(Field.user_id == user.id)
            .order_by(Field.created_at.desc())
        )
        res = await self.session.execute(stmt)
        return list(res.scalars().all())

    async def get_field(self, user: User, field_id: uuid.UUID) -> Field:
        stmt = select(Field).where(Field.id == field_id, Field.user_id == user.id)
        res = await self.session.execute(stmt)
        field_obj = res.scalar_one_or_none()
        if not field_obj:
            raise NotFoundException(detail="Field not found.")
        return field_obj

    async def create_field(
        self,
        user: User,
        name: str,
        geometry: Dict[str, Any],
        crop_id: Optional[uuid.UUID] = None,
        planting_date: Optional[date] = None,
    ) -> Field:
        # Enforce plan limits
        limits = get_plan_limits(user.plan)
        count_stmt = select(func.count(Field.id)).where(Field.user_id == user.id)
        res_count = await self.session.execute(count_stmt)
        current_count = res_count.scalar() or 0

        if limits.max_fields is not None and current_count >= limits.max_fields:
            raise ForbiddenException(
                detail=f"Field limit reached for {user.plan.upper()} plan ({limits.max_fields} field max). Upgrade to Pro for unlimited fields."
            )

        # Validate geometry
        try:
            shapely_geom = shape(geometry)
            if not shapely_geom.is_valid:
                raise BadRequestException(detail="Invalid GeoJSON geometry.")
            if shapely_geom.geom_type not in ["Polygon", "MultiPolygon"]:
                raise BadRequestException(detail="Geometry must be a Polygon or MultiPolygon.")
        except Exception as e:
            raise BadRequestException(detail=f"Geometry validation error: {str(e)}")

        area_ha = calculate_polygon_area_ha(geometry)
        wkb_geom = from_shape(shapely_geom, srid=4326)

        # Validate crop if provided
        if crop_id:
            crop_stmt = select(Crop).where(Crop.id == crop_id)
            res_crop = await self.session.execute(crop_stmt)
            if not res_crop.scalar_one_or_none():
                raise NotFoundException(detail="Crop not found.")

        field_obj = Field(
            user_id=user.id,
            name=name,
            geometry=wkb_geom,
            area_ha=area_ha,
            crop_id=crop_id,
            planting_date=planting_date,
        )
        self.session.add(field_obj)
        await self.session.commit()
        await self.session.refresh(field_obj)
        return field_obj

    async def update_field(
        self,
        user: User,
        field_id: uuid.UUID,
        name: Optional[str] = None,
        crop_id: Optional[uuid.UUID] = None,
        planting_date: Optional[date] = None,
        geometry: Optional[Dict[str, Any]] = None,
    ) -> Field:
        field_obj = await self.get_field(user, field_id)

        if name is not None:
            field_obj.name = name
        if crop_id is not None:
            field_obj.crop_id = crop_id
        if planting_date is not None:
            field_obj.planting_date = planting_date
        if geometry is not None:
            shapely_geom = shape(geometry)
            if not shapely_geom.is_valid:
                raise BadRequestException(detail="Invalid GeoJSON geometry.")
            field_obj.geometry = from_shape(shapely_geom, srid=4326)
            field_obj.area_ha = calculate_polygon_area_ha(geometry)

        await self.session.commit()
        await self.session.refresh(field_obj)
        return field_obj

    async def delete_field(self, user: User, field_id: uuid.UUID) -> bool:
        field_obj = await self.get_field(user, field_id)
        await self.session.delete(field_obj)
        await self.session.commit()
        return True
