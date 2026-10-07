import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Satellite, RefreshCw, Layers, Cloud, Droplets } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { fieldsApi } from '../../api/fields';
import { remoteSensingApi, AnalyzeFieldParams } from '../../api/remoteSensing';
import { VegetationIndicesChart } from '../../components/charts/VegetationIndicesChart';
import { EvapotranspirationComparisonChart } from '../../components/charts/EvapotranspirationComparisonChart';
import { FieldPolygonMap } from '../../components/maps/FieldPolygonMap';

export const RemoteSensingPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialFieldId = searchParams.get('field') || '';
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [selectedFieldId, setSelectedFieldId] = useState<string>(initialFieldId);
  const [daysWindow, setDaysWindow] = useState<number>(30);
  const [provider, setProvider] = useState<'sentinel' | 'gee' | 'mock'>('sentinel');
  const [maxCloudCover, setMaxCloudCover] = useState<number>(30);

  // Queries
  const { data: fields = [], isLoading: fieldsLoading } = useQuery({
    queryKey: ['fields'],
    queryFn: fieldsApi.getFields,
  });

  // Automatically select first field if none selected
  React.useEffect(() => {
    if (!selectedFieldId && fields.length > 0) {
      setSelectedFieldId(fields[0].id);
      setSearchParams({ field: fields[0].id });
    }
  }, [fields, selectedFieldId, setSearchParams]);

  const activeField = fields.find((f) => f.id === selectedFieldId);

  // Observations Query
  const {
    data: observations = [],
    isLoading: obsLoading,
  } = useQuery({
    queryKey: ['remote-sensing-obs', selectedFieldId],
    queryFn: () => (selectedFieldId ? remoteSensingApi.getObservations(selectedFieldId) : []),
    enabled: !!selectedFieldId,
  });

  // Analyze Mutation
  const analyzeMutation = useMutation({
    mutationFn: (params: AnalyzeFieldParams) =>
      remoteSensingApi.analyzeField(selectedFieldId, params),
    onSuccess: (res) => {
      queryClient.invalidateQueries({ queryKey: ['remote-sensing-obs', selectedFieldId] });
      toast({
        type: 'success',
        title: 'Satellite Analysis Complete',
        description: `Processed ${res.observations_count} scenes from ${res.provider} provider.`,
      });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Satellite analysis failed';
      toast({ type: 'error', title: 'Analysis Error', description: msg });
    },
  });

  const handleRunAnalysis = () => {
    if (!selectedFieldId) return;
    const end = new Date();
    const start = new Date();
    start.setDate(end.getDate() - daysWindow);

    analyzeMutation.mutate({
      start_date: start.toISOString().split('T')[0],
      end_date: end.toISOString().split('T')[0],
      max_cloud_cover: maxCloudCover,
      provider: provider,
    });
  };

  const latestObs = observations.length > 0 ? observations[observations.length - 1] : null;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <Satellite className="h-6 w-6 text-emerald-600" />
            Remote Sensing & Satellite Analytics
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Sentinel-2 L2A vegetation indices (NDVI, EVI, NDWI), SCL cloud masking, and Kc crop water needs.
          </p>
        </div>

        <div className="flex items-center gap-2">
          <Button
            onClick={handleRunAnalysis}
            disabled={!selectedFieldId || analyzeMutation.isPending}
            className="flex items-center gap-2"
          >
            <RefreshCw className={`h-4 w-4 ${analyzeMutation.isPending ? 'animate-spin' : ''}`} />
            {analyzeMutation.isPending ? 'Processing Scenes...' : 'Refresh Analysis'}
          </Button>
        </div>
      </div>

      {/* Field Selector & Controls Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-4 gap-4">
            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Target Parcel
              </label>
              <select
                className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
                value={selectedFieldId}
                onChange={(e) => {
                  setSelectedFieldId(e.target.value);
                  setSearchParams({ field: e.target.value });
                }}
                disabled={fieldsLoading || fields.length === 0}
              >
                {fields.length === 0 && <option value="">No fields created</option>}
                {fields.map((f) => (
                  <option key={f.id} value={f.id}>
                    {f.name} ({f.crop_name || 'No crop'} - {f.area_ha.toFixed(1)} ha)
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Historical Window
              </label>
              <select
                className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
                value={daysWindow}
                onChange={(e) => setDaysWindow(Number(e.target.value))}
              >
                <option value={14}>Last 14 Days</option>
                <option value={30}>Last 30 Days (Recommended)</option>
                <option value={60}>Last 60 Days</option>
                <option value={90}>Last 90 Days</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Satellite Source
              </label>
              <select
                className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
                value={provider}
                onChange={(e) => setProvider(e.target.value as any)}
              >
                <option value="sentinel">Sentinel-2 L2A (Open STAC)</option>
                <option value="gee">Google Earth Engine (MODIS ET)</option>
                <option value="mock">Deterministic Synthetic (Offline)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Max Cloud Cover ({maxCloudCover}%)
              </label>
              <input
                type="range"
                min={5}
                max={50}
                step={5}
                value={maxCloudCover}
                onChange={(e) => setMaxCloudCover(Number(e.target.value))}
                className="w-full mt-2"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* KPI Cards: Current Status */}
      {latestObs && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Latest NDVI (Vigor)</p>
                <h3 className="text-2xl font-bold text-emerald-600 mt-0.5">
                  {latestObs.ndvi !== null && latestObs.ndvi !== undefined
                    ? latestObs.ndvi.toFixed(2)
                    : '—'}
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">Observed {latestObs.observation_date}</p>
              </div>
              <Layers className="h-8 w-8 text-emerald-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Derived Kc Factor</p>
                <h3 className="text-2xl font-bold text-neutral-800 dark:text-neutral-100 mt-0.5">
                  {latestObs.kc !== null && latestObs.kc !== undefined
                    ? latestObs.kc.toFixed(2)
                    : '—'}
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">FAO-56 Stage / NDVI</p>
              </div>
              <Droplets className="h-8 w-8 text-blue-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Daily ETc Crop Need</p>
                <h3 className="text-2xl font-bold text-orange-600 mt-0.5">
                  {latestObs.etc !== null && latestObs.etc !== undefined
                    ? `${latestObs.etc.toFixed(2)} mm`
                    : '—'}
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">Ref ET₀: {latestObs.et0?.toFixed(2) || '—'} mm</p>
              </div>
              <Droplets className="h-8 w-8 text-orange-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Cloud Scene Filter</p>
                <h3 className="text-2xl font-bold text-neutral-700 dark:text-neutral-200 mt-0.5">
                  {latestObs.cloud_cover_pct !== null && latestObs.cloud_cover_pct !== undefined
                    ? `${latestObs.cloud_cover_pct.toFixed(1)}%`
                    : '—'}
                </h3>
                <p className="text-[10px] text-emerald-600 mt-1">Scene Passed Mask</p>
              </div>
              <Cloud className="h-8 w-8 text-neutral-400/20" />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Charts & Geometry Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Chart 1: NDVI / EVI / NDWI */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Canopy Vegetation Indices (NDVI / EVI / NDWI)</span>
              <Badge variant="outline">Sentinel-2 L2A</Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Multi-spectral reflectance tracks biomass vigor and canopy moisture over time.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {obsLoading ? (
              <div className="flex justify-center p-12"><Spinner size="md" /></div>
            ) : (
              <VegetationIndicesChart data={observations} height={280} />
            )}
          </CardContent>
        </Card>

        {/* Chart 2: ET0 vs ETc */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Evapotranspiration (ET₀ vs ETc) & Rain</span>
              <Badge variant="outline">FAO-56 Penman-Monteith</Badge>
            </CardTitle>
            <CardDescription className="text-xs">
              Actual crop water demand calculated by multiplying derived Kc by atmospheric ET₀.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {obsLoading ? (
              <div className="flex justify-center p-12"><Spinner size="md" /></div>
            ) : (
              <EvapotranspirationComparisonChart data={observations} height={280} />
            )}
          </CardContent>
        </Card>
      </div>

      {/* Field Boundary Overlay & Scene Observations Table */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Field Boundary Card */}
        <div className="lg:col-span-1">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">Field Geometry</CardTitle>
              <CardDescription className="text-xs">
                {activeField ? `${activeField.name} (${activeField.area_ha.toFixed(2)} ha)` : 'No field selected'}
              </CardDescription>
            </CardHeader>
            <CardContent>
              {activeField ? (
                <FieldPolygonMap
                  initialPolygon={activeField.geometry.coordinates}
                  readOnly={true}
                  height={260}
                />
              ) : (
                <div className="h-[260px] flex items-center justify-center text-xs text-neutral-400">
                  Select a field to preview polygon
                </div>
              )}
            </CardContent>
          </Card>
        </div>

        {/* Satellite Scene Table */}
        <div className="lg:col-span-2">
          <Card className="h-full">
            <CardHeader className="pb-2">
              <CardTitle className="text-base flex items-center justify-between">
                <span>Satellite Scenes Log</span>
                <span className="text-xs text-neutral-500">{observations.length} observations</span>
              </CardTitle>
              <CardDescription className="text-xs">
                Timestamped multi-spectral observations processed and stored in database.
              </CardDescription>
            </CardHeader>
            <CardContent>
              <div className="overflow-x-auto max-h-[260px]">
                <table className="w-full text-left text-xs">
                  <thead className="bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 sticky top-0">
                    <tr>
                      <th className="p-2">Date</th>
                      <th className="p-2">NDVI</th>
                      <th className="p-2">EVI</th>
                      <th className="p-2">NDWI</th>
                      <th className="p-2">Cloud %</th>
                      <th className="p-2">ET₀</th>
                      <th className="p-2">Kc</th>
                      <th className="p-2">ETc (mm)</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                    {observations.length === 0 ? (
                      <tr>
                        <td colSpan={8} className="p-4 text-center text-neutral-400">
                          No satellite scenes recorded yet. Click "Refresh Analysis" to trigger STAC scene ingestion.
                        </td>
                      </tr>
                    ) : (
                      observations.slice(-8).reverse().map((obs) => (
                        <tr key={obs.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                          <td className="p-2 font-medium">{obs.observation_date}</td>
                          <td className="p-2 text-emerald-600 font-semibold">
                            {obs.ndvi !== null && obs.ndvi !== undefined ? obs.ndvi.toFixed(3) : '—'}
                          </td>
                          <td className="p-2">{obs.evi !== null && obs.evi !== undefined ? obs.evi.toFixed(3) : '—'}</td>
                          <td className="p-2">{obs.ndwi !== null && obs.ndwi !== undefined ? obs.ndwi.toFixed(3) : '—'}</td>
                          <td className="p-2">{obs.cloud_cover_pct !== null && obs.cloud_cover_pct !== undefined ? `${obs.cloud_cover_pct.toFixed(1)}%` : '—'}</td>
                          <td className="p-2">{obs.et0 !== null && obs.et0 !== undefined ? obs.et0.toFixed(2) : '—'}</td>
                          <td className="p-2">{obs.kc !== null && obs.kc !== undefined ? obs.kc.toFixed(2) : '—'}</td>
                          <td className="p-2 font-semibold text-orange-600">{obs.etc !== null && obs.etc !== undefined ? `${obs.etc.toFixed(2)} mm` : '—'}</td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
};
