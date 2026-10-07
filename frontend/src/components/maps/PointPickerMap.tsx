import React, { useEffect, useRef, useState } from 'react';
import L from 'leaflet';
import { Search, MapPin, Loader2 } from 'lucide-react';
import { Input } from '../ui/Input';
import { Button } from '../ui/Button';
import { weatherApi, GeocodingResultItem } from '../../api/weather';

interface PointPickerMapProps {
  latitude: number;
  longitude: number;
  onLocationSelect: (lat: number, lon: number, placeName?: string) => void;
  height?: number;
}

export const PointPickerMap: React.FC<PointPickerMapProps> = ({
  latitude,
  longitude,
  onLocationSelect,
  height = 300,
}) => {
  const mapContainerRef = useRef<HTMLDivElement>(null);
  const mapRef = useRef<L.Map | null>(null);
  const markerRef = useRef<L.Marker | null>(null);

  const [searchQuery, setSearchQuery] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<GeocodingResultItem[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);

  const onSelectRef = useRef(onLocationSelect);
  useEffect(() => {
    onSelectRef.current = onLocationSelect;
  }, [onLocationSelect]);

  // Initialize Leaflet map
  useEffect(() => {
    if (!mapContainerRef.current) return;
    if (mapRef.current) return;

    // Fix leaflet marker icon URLs in bundler
    delete (L.Icon.Default.prototype as { _getIconUrl?: unknown })._getIconUrl;
    L.Icon.Default.mergeOptions({
      iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
      iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
      shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
    });

    const map = L.map(mapContainerRef.current).setView([latitude, longitude], 9);

    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '&copy; OpenStreetMap contributors',
      maxZoom: 18,
    }).addTo(map);

    const marker = L.marker([latitude, longitude], { draggable: true }).addTo(map);

    marker.on('dragend', () => {
      const pos = marker.getLatLng();
      onSelectRef.current(roundCoord(pos.lat), roundCoord(pos.lng));
    });

    map.on('click', (e: L.LeafletMouseEvent) => {
      marker.setLatLng(e.latlng);
      onSelectRef.current(roundCoord(e.latlng.lat), roundCoord(e.latlng.lng));
    });

    mapRef.current = map;
    markerRef.current = marker;

    return () => {
      map.remove();
      mapRef.current = null;
      markerRef.current = null;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Sync marker position when props change externally
  useEffect(() => {
    if (mapRef.current && markerRef.current) {
      const cur = markerRef.current.getLatLng();
      if (Math.abs(cur.lat - latitude) > 0.001 || Math.abs(cur.lng - longitude) > 0.001) {
        markerRef.current.setLatLng([latitude, longitude]);
        mapRef.current.panTo([latitude, longitude]);
      }
    }
  }, [latitude, longitude]);

  const roundCoord = (val: number) => Math.round(val * 10000) / 10000;

  const handleSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    try {
      const results = await weatherApi.geocode(searchQuery.trim());
      setSearchResults(results);
      setShowDropdown(true);
    } catch {
      setSearchResults([]);
    } finally {
      setIsSearching(false);
    }
  };

  const handleSelectPlace = (item: GeocodingResultItem) => {
    setShowDropdown(false);
    setSearchQuery(`${item.name}, ${item.country}`);
    onLocationSelect(roundCoord(item.latitude), roundCoord(item.longitude), `${item.name}, ${item.country}`);
    if (mapRef.current && markerRef.current) {
      markerRef.current.setLatLng([item.latitude, item.longitude]);
      mapRef.current.setView([item.latitude, item.longitude], 10);
    }
  };

  return (
    <div className="space-y-2">
      {/* Search Input Bar */}
      <form onSubmit={handleSearch} className="relative flex items-center gap-1.5">
        <div className="relative flex-1">
          <Input
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            placeholder="Search city or agricultural region..."
            className="text-xs h-8 pl-7"
          />
          <MapPin className="absolute left-2 top-2 h-3.5 w-3.5 text-muted-foreground" />
        </div>
        <Button type="submit" variant="secondary" size="sm" className="h-8 px-2.5 text-xs" disabled={isSearching}>
          {isSearching ? <Loader2 className="h-3.5 w-3.5 animate-spin" /> : <Search className="h-3.5 w-3.5" />}
        </Button>

        {/* Autocomplete Dropdown */}
        {showDropdown && searchResults.length > 0 && (
          <div className="absolute top-9 left-0 right-10 z-[1000] rounded-md border border-border bg-card shadow-lg max-h-48 overflow-y-auto">
            {searchResults.map((r, i) => (
              <div
                key={i}
                onClick={() => handleSelectPlace(r)}
                className="p-2 text-xs hover:bg-muted/50 cursor-pointer flex justify-between items-center"
              >
                <span className="font-medium">{r.name}, {r.country}</span>
                <span className="text-[10px] text-muted-foreground">
                  {r.latitude.toFixed(2)}°, {r.longitude.toFixed(2)}°
                </span>
              </div>
            ))}
          </div>
        )}
      </form>

      {/* Map Container */}
      <div
        ref={mapContainerRef}
        style={{ height }}
        className="w-full rounded-lg border border-border overflow-hidden z-0"
      />

      <div className="flex justify-between items-center text-[11px] text-muted-foreground px-1">
        <span>Click on map or drag marker to select location</span>
        <span className="font-mono">
          {latitude.toFixed(4)}° N, {longitude.toFixed(4)}° E
        </span>
      </div>
    </div>
  );
};
