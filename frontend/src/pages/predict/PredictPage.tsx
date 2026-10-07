import React, { useState, useEffect } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import {
  Calculator,
  RotateCcw,
  Sparkles,
  Lock,
  ChevronDown,
  ChevronUp,
  MapPin,
  CloudSun,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/ui/Toast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import {
  predictApi,
  PredictRequest,
  PredictResponse,
  ComparePredictResponse,
  ExplainPredictResponse,
} from '../../api/predict';
import { historyApi } from '../../api/history';
import { PredictResultPanel } from '../../components/predict/PredictResultPanel';
import { WhatIfSandbox } from '../../components/predict/WhatIfSandbox';
import { ShapBarChart } from '../../components/charts/ShapBarChart';
import { ModelComparisonChart } from '../../components/charts/ModelComparisonChart';
import { LocationModeSelector } from '../../components/predict/LocationModeSelector';
import { WeatherForecastWorkspace } from '../../components/predict/WeatherForecastWorkspace';

const predictSchema = z.object({
  temperature: z.number().min(-10).max(50),
  humidity: z.number().min(0).max(100),
  wind_speed: z.number().min(0).max(30),
  solar_radiation: z.number().min(0).max(35),
  tmin: z.number().min(-10).max(50).optional(),
  tmax: z.number().min(-10).max(50).optional(),
  latitude: z.number().min(-90).max(90).optional(),
  elevation: z.number().min(-500).max(9000).optional(),
  doy: z.number().int().min(1).max(366).optional(),
  note: z.string().max(500).optional(),
  is_saved: z.boolean().optional(),
});

type PredictFormValues = z.infer<typeof predictSchema>;

export const PredictPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const isPro = user?.plan === 'pro' || user?.role === 'admin';

  const [inputMode, setInputMode] = useState<'manual' | 'location'>('manual');
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [result, setResult] = useState<PredictResponse | null>(null);

  // Tabs state
  const [activeTab, setActiveTab] = useState<'result' | 'whatif' | 'explain' | 'compare' | 'forecast'>('result');

  // Explainability & Compare states
  const [explainData, setExplainData] = useState<ExplainPredictResponse | null>(null);
  const [isExplaining, setIsExplaining] = useState(false);
  const [compareData, setCompareData] = useState<ComparePredictResponse | null>(null);
  const [isComparing, setIsComparing] = useState(false);

  // What-if sandbox live state
  const [whatIfValues, setWhatIfValues] = useState({
    temperature: 28.0,
    humidity: 50.0,
    wind_speed: 2.2,
    solar_radiation: 22.0,
  });
  const [liveEt, setLiveEt] = useState<number | null>(null);
  const [liveCls, setLiveCls] = useState<string>('moderate');

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<PredictFormValues>({
    resolver: zodResolver(predictSchema),
    defaultValues: {
      temperature: 28.0,
      humidity: 50.0,
      wind_speed: 2.2,
      solar_radiation: 22.0,
      elevation: 100.0,
      is_saved: false,
    },
  });

  const onSubmit = async (values: PredictFormValues) => {
    setIsLoading(true);
    try {
      const res = await predictApi.predict(values as PredictRequest, true);
      setResult(res);
      setActiveTab('result');
      toast({
        title: 'ET₀ Calculated',
        description: `Reference ET₀: ${res.et_value.toFixed(2)} mm/day (${res.classification})`,
        type: 'success',
      });
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      toast({
        title: 'Inference Failed',
        description: msg || 'Failed to compute evapotranspiration',
        type: 'error',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const loadSampleData = async () => {
    try {
      const sample = await predictApi.getSample();
      setValue('temperature', sample.temperature);
      setValue('humidity', sample.humidity);
      setValue('wind_speed', sample.wind_speed);
      setValue('solar_radiation', sample.solar_radiation);
      setValue('tmin', sample.tmin);
      setValue('tmax', sample.tmax);
      setValue('latitude', sample.latitude);
      setValue('elevation', sample.elevation);
      setValue('doy', sample.doy);
      setShowAdvanced(true);
      toast({
        title: 'Sample Data Loaded',
        description: `${sample.location_name}: ${sample.description}`,
        type: 'info',
      });
    } catch {
      toast({
        title: 'Sample Unavailable',
        description: 'Using local meteorological default preset.',
        type: 'warning',
      });
      reset({
        temperature: 28.5,
        humidity: 45.0,
        wind_speed: 2.4,
        solar_radiation: 23.5,
        tmin: 22.0,
        tmax: 35.0,
        latitude: 31.5,
        elevation: 213.0,
        doy: 180,
      });
      setShowAdvanced(true);
    }
  };

  // What-if debounced effect
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const res = await predictApi.predict(
          {
            temperature: whatIfValues.temperature,
            humidity: whatIfValues.humidity,
            wind_speed: whatIfValues.wind_speed,
            solar_radiation: whatIfValues.solar_radiation,
          },
          false
        );
        setLiveEt(res.et_value);
        setLiveCls(res.classification);
      } catch {
        // Debounce errors silent in UI
      }
    }, 250);
    return () => clearTimeout(timer);
  }, [whatIfValues]);

  // Handle bookmark toggle on existing result
  const toggleBookmark = async () => {
    if (!result?.id) return;
    try {
      const nextSaved = !result.is_saved;
      await historyApi.update(result.id, { is_saved: nextSaved });
      setResult({ ...result, is_saved: nextSaved });
      toast({
        title: nextSaved ? 'Prediction Bookmarked' : 'Bookmark Removed',
        description: nextSaved ? 'Saved to starred history' : 'Removed from bookmarks',
        type: 'success',
      });
    } catch {
      toast({ title: 'Bookmark Update Failed', type: 'error' });
    }
  };

  // Fetch SHAP explainability
  const loadExplainability = async () => {
    if (!isPro) return;
    setIsExplaining(true);
    try {
      const formVals = watch();
      const res = await predictApi.explain(formVals as PredictRequest);
      setExplainData(res);
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      toast({
        title: 'Explainability Failed',
        description: msg || 'SHAP feature attribution failed',
        type: 'error',
      });
    } finally {
      setIsExplaining(false);
    }
  };

  // Fetch model comparison
  const loadComparison = async () => {
    if (!isPro) return;
    setIsComparing(true);
    try {
      const formVals = watch();
      const res = await predictApi.compare(formVals as PredictRequest);
      setCompareData(res);
    } catch (err) {
      const msg =
        err && typeof err === 'object' && 'response' in err
          ? (err as { response?: { data?: { detail?: string } } }).response?.data?.detail
          : undefined;
      toast({
        title: 'Comparison Failed',
        description: msg || 'Multi-model inference failed',
        type: 'error',
      });
    } finally {
      setIsComparing(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Calculator className="h-6 w-6 text-primary" />
            Evapotranspiration Estimation
          </h1>
          <p className="text-sm text-muted-foreground">
            Estimate daily reference evapotranspiration ($ET_0$) with ML ensembles and FAO-56 Penman-Monteith physics.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Button variant="outline" size="sm" onClick={loadSampleData} className="gap-1.5 text-xs">
            <Sparkles className="h-3.5 w-3.5 text-amber-500" />
            Load Sample Data
          </Button>
          <Button
            variant="ghost"
            size="sm"
            onClick={() => reset()}
            className="gap-1.5 text-xs text-muted-foreground"
          >
            <RotateCcw className="h-3.5 w-3.5" />
            Reset
          </Button>
        </div>
      </div>

      <div className="grid gap-6 lg:grid-cols-12 items-start">
        {/* Left Form: 5 cols */}
        <div className="lg:col-span-5 space-y-4">
          {/* Mode Switch Tabs */}
          <div className="flex rounded-lg bg-muted p-1 text-xs">
            <button
              type="button"
              onClick={() => setInputMode('manual')}
              className={`flex-1 py-1.5 rounded-md font-medium transition-colors ${
                inputMode === 'manual'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              Manual Inputs
            </button>
            <button
              type="button"
              onClick={() => setInputMode('location')}
              className={`flex-1 py-1.5 rounded-md font-medium transition-colors flex items-center justify-center gap-1.5 ${
                inputMode === 'location'
                  ? 'bg-card text-foreground shadow-sm'
                  : 'text-muted-foreground hover:text-foreground'
              }`}
            >
              <MapPin className="h-3 w-3 text-primary" />
              Use Location & Weather
            </button>
          </div>

          {inputMode === 'location' ? (
            <LocationModeSelector
              onApplyWeather={(weather, lat, lon, placeName) => {
                setValue('temperature', weather.temperature);
                setValue('humidity', weather.humidity);
                setValue('wind_speed', weather.wind_speed);
                setValue('solar_radiation', weather.solar_radiation);
                if (weather.tmin !== undefined && weather.tmin !== null) setValue('tmin', weather.tmin);
                if (weather.tmax !== undefined && weather.tmax !== null) setValue('tmax', weather.tmax);
                setValue('latitude', lat);
                setValue('note', `Location: ${placeName || `${lat}, ${lon}`} on ${weather.date}`);
                setInputMode('manual');
                // Automatically submit prediction with source=location
                handleSubmit((vals) => {
                  return predictApi
                    .predict({ ...vals, latitude: lat, source: 'location' } as PredictRequest, true)
                    .then((res) => {
                      setResult(res);
                      setActiveTab('result');
                      toast({
                        title: 'Location ET₀ Calculated',
                        description: `Prediction: ${res.et_value.toFixed(2)} mm/day (${res.classification})`,
                        type: 'success',
                      });
                    });
                })();
              }}
            />
          ) : (
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base">Meteorological Parameters</CardTitle>
                <CardDescription className="text-xs">
                  Fill core 4-parameter envelope or expand advanced coordinates.
                </CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
                {/* 4 Core Features */}
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="text-xs font-medium text-foreground">Temperature (°C)</label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="28.0"
                      {...register('temperature', { valueAsNumber: true })}
                      error={errors.temperature?.message}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-foreground">Relative Humidity (%)</label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="50.0"
                      {...register('humidity', { valueAsNumber: true })}
                      error={errors.humidity?.message}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-foreground">Wind Speed (m/s)</label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="2.2"
                      {...register('wind_speed', { valueAsNumber: true })}
                      error={errors.wind_speed?.message}
                    />
                  </div>
                  <div>
                    <label className="text-xs font-medium text-foreground">Solar Rad (MJ/m²/d)</label>
                    <Input
                      type="number"
                      step="0.1"
                      placeholder="22.0"
                      {...register('solar_radiation', { valueAsNumber: true })}
                      error={errors.solar_radiation?.message}
                    />
                  </div>
                </div>

                {/* Advanced parameters accordian toggle */}
                <div className="pt-1">
                  <Button
                    type="button"
                    variant="ghost"
                    size="sm"
                    className="w-full justify-between text-xs text-muted-foreground h-8 px-2"
                    onClick={() => setShowAdvanced(!showAdvanced)}
                  >
                    <span>Advanced FAO-56 Coordinates & Physics</span>
                    {showAdvanced ? (
                      <ChevronUp className="h-3.5 w-3.5" />
                    ) : (
                      <ChevronDown className="h-3.5 w-3.5" />
                    )}
                  </Button>

                  {showAdvanced && (
                    <div className="grid grid-cols-2 gap-3 pt-3 mt-1 border-t border-border/50 text-xs">
                      <div>
                        <label className="text-[11px] font-medium text-muted-foreground">Tmin (°C)</label>
                        <Input
                          type="number"
                          step="0.1"
                          placeholder="22.0"
                          {...register('tmin', { valueAsNumber: true })}
                        />
                      </div>
                      <div>
                        <label className="text-[11px] font-medium text-muted-foreground">Tmax (°C)</label>
                        <Input
                          type="number"
                          step="0.1"
                          placeholder="34.0"
                          {...register('tmax', { valueAsNumber: true })}
                        />
                      </div>
                      <div>
                        <label className="text-[11px] font-medium text-muted-foreground">Latitude (°)</label>
                        <Input
                          type="number"
                          step="0.01"
                          placeholder="31.5"
                          {...register('latitude', { valueAsNumber: true })}
                        />
                      </div>
                      <div>
                        <label className="text-[11px] font-medium text-muted-foreground">Elevation (m)</label>
                        <Input
                          type="number"
                          step="1"
                          placeholder="100"
                          {...register('elevation', { valueAsNumber: true })}
                        />
                      </div>
                      <div className="col-span-2">
                        <label className="text-[11px] font-medium text-muted-foreground">Day of Year (1–366)</label>
                        <Input
                          type="number"
                          step="1"
                          placeholder="180"
                          {...register('doy', { valueAsNumber: true })}
                        />
                      </div>
                    </div>
                  )}
                </div>

                {/* Optional Note */}
                <div>
                  <label className="text-xs font-medium text-muted-foreground">Observation Note (Optional)</label>
                  <Input
                    type="text"
                    placeholder="e.g. Field A pivot test during noon peak"
                    {...register('note')}
                  />
                </div>

                <Button type="submit" disabled={isLoading} className="w-full gap-2">
                  <Calculator className="h-4 w-4" />
                  {isLoading ? 'Computing Inference...' : 'Calculate Evapotranspiration'}
                </Button>
              </form>
            </CardContent>
          </Card>
          )}
        </div>

        {/* Right Output: 7 cols */}
        <div className="lg:col-span-7 space-y-4">
          <Tabs
            value={activeTab}
            onValueChange={(val: string) =>
              setActiveTab(val as 'result' | 'whatif' | 'explain' | 'compare' | 'forecast')
            }
          >
            <TabsList className="grid grid-cols-5 w-full">
              <TabsTrigger value="result" className="text-xs">
                Result
              </TabsTrigger>
              <TabsTrigger value="forecast" className="text-xs gap-1">
                <CloudSun className="h-3 w-3" />
                Forecast
              </TabsTrigger>
              <TabsTrigger value="whatif" className="text-xs">
                What-If
              </TabsTrigger>
              <TabsTrigger
                value="explain"
                className="text-xs gap-1"
                onClick={() => {
                  if (isPro && !explainData) loadExplainability();
                }}
              >
                SHAP {!isPro && <Lock className="h-3 w-3 text-muted-foreground" />}
              </TabsTrigger>
              <TabsTrigger
                value="compare"
                className="text-xs gap-1"
                onClick={() => {
                  if (isPro && !compareData) loadComparison();
                }}
              >
                Compare {!isPro && <Lock className="h-3 w-3 text-muted-foreground" />}
              </TabsTrigger>
            </TabsList>

            {/* TAB 1: Main Result */}
            <TabsContent value="result" className="pt-3">
              {result ? (
                <PredictResultPanel
                  result={result}
                  onBookmarkToggle={toggleBookmark}
                />
              ) : (
                <Card className="border-dashed py-12 text-center text-muted-foreground">
                  <Calculator className="h-10 w-10 mx-auto text-muted-foreground/40 mb-3" />
                  <div className="text-sm font-medium">No Prediction Computed Yet</div>
                  <div className="text-xs max-w-sm mx-auto mt-1">
                    Fill the meteorological parameters on the left or click "Load Sample Data" to run ML inference.
                  </div>
                </Card>
              )}
            </TabsContent>

            {/* TAB: Weather Forecast & Climatology */}
            <TabsContent value="forecast" className="pt-3">
              <WeatherForecastWorkspace />
            </TabsContent>

            {/* TAB 2: What-if Sandbox */}
            <TabsContent value="whatif" className="pt-3">
              <WhatIfSandbox
                values={whatIfValues}
                onChange={(key, val) =>
                  setWhatIfValues((prev) => ({ ...prev, [key]: val }))
                }
                liveEt={liveEt}
                liveClassification={liveCls}
              />
            </TabsContent>

            {/* TAB 3: SHAP Explainability (Pro gated) */}
            <TabsContent value="explain" className="pt-3">
              {!isPro ? (
                <Card className="border-dashed p-8 text-center space-y-3">
                  <Lock className="h-8 w-8 mx-auto text-amber-500" />
                  <div className="text-base font-semibold">Pro Feature: SHAP Feature Attributions</div>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    Inspect exact local feature contributions (e.g. how high solar radiation or dry humidity drives evaporative demand) using TreeExplainer SHAP values.
                  </p>
                  <Button variant="default" size="sm">
                    Upgrade to Pro Plan
                  </Button>
                </Card>
              ) : isExplaining ? (
                <Card className="p-8 text-center text-sm text-muted-foreground">
                  Calculating SHAP feature attributions...
                </Card>
              ) : explainData ? (
                <Card className="p-4 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Local Feature Attributions</h3>
                    <p className="text-xs text-muted-foreground">
                      Additive SHAP explanations for prediction {explainData.et_value.toFixed(2)} mm/day
                    </p>
                  </div>
                  <ShapBarChart
                    contributions={explainData.contributions}
                    baseValue={explainData.base_value}
                  />
                </Card>
              ) : (
                <Card className="p-8 text-center space-y-3">
                  <p className="text-xs text-muted-foreground">Click below to generate feature attributions for current form values.</p>
                  <Button size="sm" onClick={loadExplainability}>Generate SHAP Analysis</Button>
                </Card>
              )}
            </TabsContent>

            {/* TAB 4: Multi-Model Comparison (Pro gated) */}
            <TabsContent value="compare" className="pt-3">
              {!isPro ? (
                <Card className="border-dashed p-8 text-center space-y-3">
                  <Lock className="h-8 w-8 mx-auto text-amber-500" />
                  <div className="text-base font-semibold">Pro Feature: Multi-Model Comparison</div>
                  <p className="text-xs text-muted-foreground max-w-md mx-auto">
                    Run inference simultaneously across RandomForest, LightGBM, SVR, MLP, and Stacking Ensemble to evaluate model divergence and consensus.
                  </p>
                  <Button variant="default" size="sm">
                    Upgrade to Pro Plan
                  </Button>
                </Card>
              ) : isComparing ? (
                <Card className="p-8 text-center text-sm text-muted-foreground">
                  Running multi-model inference across model registry...
                </Card>
              ) : compareData ? (
                <Card className="p-4 space-y-4">
                  <div>
                    <h3 className="text-sm font-semibold text-foreground">Multi-Model Ensemble Comparison</h3>
                    <p className="text-xs text-muted-foreground">
                      Side-by-side estimates, 90% conformal intervals, and performance metrics.
                    </p>
                  </div>
                  <ModelComparisonChart data={compareData} />
                </Card>
              ) : (
                <Card className="p-8 text-center space-y-3">
                  <p className="text-xs text-muted-foreground">Click below to run all models on current form parameters.</p>
                  <Button size="sm" onClick={loadComparison}>Run Multi-Model Comparison</Button>
                </Card>
              )}
            </TabsContent>
          </Tabs>
        </div>
      </div>
    </div>
  );
};
