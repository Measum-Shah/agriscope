import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Trash2, RotateCcw } from 'lucide-react';
import { Button } from '../ui/Button';

interface FieldPolygonMapProps {
  initialPolygon?: number[][][]; // [ [ [lon, lat], ... ] ] GeoJSON Polygon coordinates
  onPolygonChange?: (coordinates: number[][][]) => void;
  readOnly?: boolean;
  height?: number;
}

export const FieldPolygonMap: React.FC<FieldPolygonMapProps> = ({
  initialPolygon,
  onPolygonChange,
  readOnly = false,
  height = 360,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const polygonLayerRef = useRef<L.Polygon | null>(null);
  const pointsLayerRef = useRef<L.LayerGroup | null>(null);

  // Array of [lat, lon] tuples for drawing
  const [points, setPoints] = useState<[number, number][]>(() => {
    if (initialPolygon && initialPolygon[0] && initialPolygon[0].length > 0) {
      return initialPolygon[0].map(([lon, lat]) => [lat, lon]);
    }
    return [];
  });

  // Keep callback reference updated
  const onChangeRef = useRef(onPolygonChange);
  useEffect(() => {
    onChangeRef.current = onPolygonChange;
  }, [onPolygonChange]);

  // Setup Leaflet Map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapRef.current) return;

    delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });

    const initialCenter: [number, number] =
      points.length > 0 ? points[0] : [31.5204, 74.3587]; // Default to Lahore, Pakistan

    const map = L.map(mapContainerRef.current).setView(initialCenter, 13);
    mapRef.current = map;

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 19,
    }).addTo(map);

    const pointsGroup = L.layerGroup().addTo(map);
    pointsLayerRef.current = pointsGroup;

    if (!readOnly) {
      map.on('click', (e: L.LeafletMouseEvent) => {
        const newCoord: [number, number] = [Number(e.latlng.lat.toFixed(6)), Number(e.latlng.lng.toFixed(6))];
        setPoints((prev) => [...prev, newCoord]);
      });
    }

    return () => {
      map.remove();
      mapRef.current = null;
    };
  }, [readOnly]);

  // Sync Polygon to Map when points change
  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;

    if (pointsLayerRef.current) {
      pointsLayerRef.current.clearLayers();
    }
    if (polygonLayerRef.current) {
      polygonLayerRef.current.remove();
      polygonLayerRef.current = null;
    }

    if (points.length > 0) {
      // Draw point markers
      points.forEach(([lat, lon], idx) => {
        const marker = L.circleMarker([lat, lon], {
          radius: 5,
          color: '#15803d',
          fillColor: '#22c55e',
          fillOpacity: 0.9,
        });
        marker.bindTooltip(`Point ${idx + 1}`);
        if (pointsLayerRef.current) {
          marker.addTo(pointsLayerRef.current);
        }
      });

      // Draw polygon if >= 3 points
      if (points.length >= 3) {
        const polygon = L.polygon(points, {
          color: '#166534',
          fillColor: '#4ade80',
          fillOpacity: 0.35,
          weight: 2,
        }).addTo(map);
        polygonLayerRef.current = polygon;
      }

      // Convert to GeoJSON coordinates: [ [ [lon, lat], ..., [lon_0, lat_0] ] ]
      if (!readOnly && points.length >= 3 && onChangeRef.current) {
        const coords = points.map(([lat, lon]) => [lon, lat]);
        // Close polygon ring if not closed
        const first = coords[0];
        const last = coords[coords.length - 1];
        if (first[0] !== last[0] || first[1] !== last[1]) {
          coords.push([first[0], first[1]]);
        }
        onChangeRef.current([coords]);
      }
    }
  }, [points, readOnly]);

  const handleReset = () => {
    setPoints([]);
    if (onChangeRef.current) {
      onChangeRef.current([]);
    }
  };

  const handleRemoveLast = () => {
    setPoints((prev) => {
      const next = prev.slice(0, -1);
      return next;
    });
  };

  return (
    <div className="relative flex flex-col gap-2">
      <div
        ref={mapContainerRef}
        style={{ height: `${height}px` }}
        className="w-full rounded-md border border-neutral-300 dark:border-neutral-700 overflow-hidden shadow-inner z-0"
      />

      {!readOnly && (
        <div className="flex items-center justify-between bg-neutral-50 dark:bg-neutral-800/80 p-2 rounded-md border border-neutral-200 dark:border-neutral-700 text-xs">
          <span className="text-neutral-600 dark:text-neutral-300">
            {points.length < 3
              ? `Click on map to place polygon boundary points (${points.length}/3 minimum)`
              : `Polygon defined (${points.length} vertices)`}
          </span>
          <div className="flex items-center gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleRemoveLast}
              disabled={points.length === 0}
              className="h-7 text-xs flex items-center gap-1"
            >
              <RotateCcw className="h-3 w-3" />
              Undo
            </Button>
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleReset}
              disabled={points.length === 0}
              className="h-7 text-xs flex items-center gap-1 text-red-600 hover:text-red-700"
            >
              <Trash2 className="h-3 w-3" />
              Clear
            </Button>
          </div>
        </div>
      )}
    </div>
  );
};
