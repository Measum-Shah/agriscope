# Remote Sensing Pipeline & Vegetation Indices

This document details the satellite remote sensing formulation, indices, crop coefficient ($K_c$) relations, cloud masking protocols, spatial resolution, and known physical limitations implemented in AgriScope.

---

## 1. Optical Sensors & Data Sources

| Sensor | Constellation | Spatial Resolution | Revisit Interval | Radiometric Bands Utilized | Provider |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **Sentinel-2 MSI** | Sentinel-2A / 2B | 10 m (B2, B3, B4, B8)<br>20 m (B11, B12, SCL) | 5 days (equator)<br>2–3 days (mid-latitudes) | B02 (Blue, 490 nm)<br>B04 (Red, 665 nm)<br>B08 (NIR, 842 nm)<br>B11 (SWIR, 1610 nm) | STAC (Earth Search / Microsoft Planetary Computer) |
| **MODIS MOD16A2** | Terra / Aqua | 500 m | 8-day composite | Evapotranspiration product | Google Earth Engine |

---

## 2. Vegetation & Moisture Indices

### 2.1 Normalized Difference Vegetation Index (NDVI)
Quantifies vegetative canopy chlorophyll absorption and near-infrared scattering:
$$\text{NDVI} = \frac{B_{08} (\text{NIR}) - B_{04} (\text{Red})}{B_{08} (\text{NIR}) + B_{04} (\text{Red})}$$
- **Dynamic Range**: $-1.0$ to $+1.0$.
- **Agronomic Thresholds**:
  - $< 0.15$: Water, bare dry soil, or rock.
  - $0.20 - 0.40$: Sparse vegetation, emergence, or early vegetative stage.
  - $0.40 - 0.70$: Active vegetative growth, stem elongation.
  - $> 0.75$: Dense, closed green canopy (flowering, peak biomass).

### 2.2 Enhanced Vegetation Index (EVI)
Corrects for atmospheric aerosols and maintains sensitivity over high biomass / dense canopies where NDVI saturates:
$$\text{EVI} = 2.5 \times \frac{B_{08} (\text{NIR}) - B_{04} (\text{Red})}{B_{08} (\text{NIR}) + 6 \times B_{04} (\text{Red}) - 7.5 \times B_{02} (\text{Blue}) + 1.0}$$

### 2.3 Normalized Difference Water Index (NDWI - Gao 1996)
Measures liquid water content in the plant canopy:
$$\text{NDWI} = \frac{B_{08} (\text{NIR}) - B_{11} (\text{SWIR})}{B_{08} (\text{NIR}) + B_{11} (\text{SWIR})}$$
- Negative values indicate dry canopy moisture stress; positive values indicate turgid, hydrated foliage.

---

## 3. Crop Evapotranspiration Coupling ($K_c \times ET_0$)

### 3.1 NDVI to Crop Coefficient ($K_c$) Relation
Based on Choudhury et al. (1994) and Allen et al. (METRIC 2007), the actual basal crop coefficient scales proportionally with the fractional green canopy cover derived from NDVI:

$$K_c = K_{c,\min} + (K_{c,\max} - K_{c,\min}) \times \left( \frac{\text{NDVI} - \text{NDVI}_{\min}}{\text{NDVI}_{\max} - \text{NDVI}_{\min}} \right)$$

Where:
- $K_{c,\min} = 0.15$ (baseline bare dry soil evaporation).
- $K_{c,\max} = 1.25$ (peak transpiration capacity for full canopy).
- $\text{NDVI}_{\min} = 0.15$ (bare soil baseline).
- $\text{NDVI}_{\max} = 0.85$ (effective canopy saturation threshold).
- Physical clamp: $0.15 \le K_c \le 1.35$.

### 3.2 Crop Evapotranspiration ($ET_c$)
$$ET_c = K_c \times ET_0$$

Where $ET_0$ is the reference evapotranspiration calculated daily via the FAO-56 Penman-Monteith physics engine or AgriScope ML stacking ensemble.

---

## 4. Cloud Masking & Scene Quality Control

1. **Scene Cloud Threshold**: Scenes with overall scene cloud cover $> 30\%$ are rejected by default (configurable up to $100\%$).
2. **Scene Classification Layer (SCL)**:
   - SCL Classes 3 (Cloud Shadows), 8 (Cloud Medium Probability), 9 (Cloud High Probability), 10 (Thin Cirrus), and 11 (Snow/Ice) are masked from polygon zonal mean aggregations.
3. **Graceful Fallback**: If all scenes within a requested temporal window are occluded by cloud cover, the pipeline yields high-fidelity deterministic seasonal models, flagging `is_fallback: true` in the API payload.

---

## 5. Physical Limitations & Operational Guidance

- **Cloud Contamination during Monsoon**: In tropical and South Asian monsoon regions, prolonged cloud cover (July–August) can reduce cloud-free optical acquisitions. In such intervals, FAO-56 stage interpolation (`interpolate_kc_stage`) is leveraged alongside synthetic curves.
- **Soil Wetness Effect on NDVI**: High surface moisture immediately following rain or irrigation temporarily lowers surface reflectance and can dampen bare-soil NDVI.
- **Partial Pixel Mixing**: For field parcels $< 0.5\text{ ha}$ (5,000 m²), a 10m Sentinel-2 pixel contains boundary mixing with field roads or neighboring ditches. PostGIS polygon area calculation validates parcel size before analysis.
