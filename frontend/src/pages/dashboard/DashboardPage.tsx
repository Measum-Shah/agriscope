import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import {
  Sun,
  Calculator,
  MapPin,
  Satellite,
  ArrowUpRight,
  TrendingUp,
  History,
  Activity,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { historyApi, HistoryStatsResponse } from '../../api/history';
import { EtHistoryLineChart } from '../../components/charts/EtHistoryLineChart';

export const DashboardPage: React.FC = () => {
  const { user, entitlements } = useAuth();
  const [stats, setStats] = useState<HistoryStatsResponse | null>(null);

  useEffect(() => {
    historyApi.getStats().then(setStats).catch(() => {});
  }, []);

  return (
    <div className="space-y-8">
      {/* Welcome Banner */}
      <div className="flex flex-col gap-4 md:flex-row md:items-center md:justify-between rounded-xl bg-gradient-to-r from-agri-900 via-agri-800 to-agri-700 p-6 text-white shadow-md">
        <div className="space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="rounded bg-white/20 px-2 py-0.5 text-xs font-medium uppercase tracking-wide">
              {user?.role || 'Farmer'}
            </span>
            <span className="text-xs text-white/80">
              Plan: <strong>{user?.plan || 'Free'}</strong>
            </span>
          </div>
          <h2 className="text-2xl font-bold tracking-tight sm:text-3xl">
            Welcome back, {user?.name || 'Researcher'}
          </h2>
          <p className="text-sm text-white/90 max-w-xl">
            AgriScope meteorological inference pipeline is operational. Monitor reference
            evapotranspiration ($ET_0$) and crop water consumption ($ET_c$) across your fields.
          </p>
        </div>

        <div className="flex flex-wrap gap-2">
          <Link to="/predict">
            <Button
              variant="secondary"
              className="bg-white text-agri-900 hover:bg-white/90 font-semibold gap-1.5 shadow-sm"
            >
              <Calculator className="h-4 w-4" />
              New ET Calculation
            </Button>
          </Link>
          <Link to="/history">
            <Button
              variant="outline"
              className="border-white/40 text-white bg-transparent hover:bg-white/10 gap-1.5"
            >
              <History className="h-4 w-4" />
              History
            </Button>
          </Link>
        </div>
      </div>

      {/* Metric Cards Grid */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {/* Daily Quota */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Daily Inference Quota
            </CardTitle>
            <TrendingUp className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {stats?.quota_remaining_today === null
                ? 'Unlimited'
                : `${stats?.quota_remaining_today ?? entitlements?.predictions_remaining_today ?? 30} Left`}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              {stats?.today_predictions ?? entitlements?.predictions_used_today ?? 0} inferences run today
            </p>
          </CardContent>
        </Card>

        {/* Latest ET */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Latest Reference ET₀
            </CardTitle>
            <Sun className="h-4 w-4 text-amber-500" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {stats?.latest_et !== null && stats?.latest_et !== undefined
                ? `${stats.latest_et.toFixed(2)} mm/day`
                : '—'}
            </div>
            <p className="text-xs text-muted-foreground mt-1">
              Mean: {stats?.mean_et ? `${stats.mean_et.toFixed(2)} mm/day` : '4.10 mm/day'}
            </p>
          </CardContent>
        </Card>

        {/* Total Inferences */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Total Inferences
            </CardTitle>
            <Activity className="h-4 w-4 text-emerald-600" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">
              {stats?.total_predictions ?? 0}
            </div>
            <p className="text-xs text-muted-foreground mt-1">Audited predictions stored</p>
          </CardContent>
        </Card>

        {/* Monitored Fields */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <CardTitle className="text-xs font-medium text-muted-foreground">
              Active Fields
            </CardTitle>
            <MapPin className="h-4 w-4 text-primary" />
          </CardHeader>
          <CardContent>
            <div className="text-2xl font-bold text-foreground">0 Parcels</div>
            <p className="text-xs text-muted-foreground mt-1">
              <Link to="/fields" className="text-primary hover:underline">
                Create boundaries &rarr;
              </Link>
            </p>
          </CardContent>
        </Card>
      </div>

      {/* 7-Day ET Trend Line Chart on Dashboard */}
      {stats && stats.trend_7d && stats.trend_7d.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-base font-semibold flex items-center gap-2">
                  <TrendingUp className="h-5 w-5 text-primary" />
                  7-Day Evapotranspiration Activity
                </CardTitle>
                <CardDescription className="text-xs">
                  Daily mean reference evaporative demand calculated across recent queries.
                </CardDescription>
              </div>
              <Link to="/history">
                <Button variant="ghost" size="sm" className="text-xs text-primary gap-1">
                  Full History <ArrowUpRight className="h-3.5 w-3.5" />
                </Button>
              </Link>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <EtHistoryLineChart data={stats.trend_7d} height={200} />
          </CardContent>
        </Card>
      )}

      {/* Quick Launch Cards */}
      <div className="grid gap-6 md:grid-cols-2">
        <Card className="hover:border-primary/40 transition-colors">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Calculator className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Calculate Crop ET (ETc)</CardTitle>
                  <CardDescription>FAO-56 Penman-Monteith physics calculation</CardDescription>
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Input temperature (-10..50°C), relative humidity (0..100%), wind speed (0..30 m/s),
              and solar radiation (0..35 MJ/m²/day) to calculate daily water requirements.
            </p>
            <Link to="/predict">
              <Button variant="default" size="sm" className="w-full">
                Open ET Calculator
              </Button>
            </Link>
          </CardContent>
        </Card>

        <Card className="hover:border-primary/40 transition-colors">
          <CardHeader>
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2">
                <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary/10 text-primary">
                  <Satellite className="h-5 w-5" />
                </div>
                <div>
                  <CardTitle className="text-base">Remote Sensing Pipeline</CardTitle>
                  <CardDescription>Sentinel-2 MSI Vegetation Indices</CardDescription>
                </div>
              </div>
              <ArrowUpRight className="h-4 w-4 text-muted-foreground" />
            </div>
          </CardHeader>
          <CardContent className="space-y-3">
            <p className="text-xs text-muted-foreground">
              Derive NDVI, EVI, and NDWI indices for field polygons and track multi-temporal canopy
              development coupled with crop coefficient ($K_c$) curves.
            </p>
            <Link to="/remote-sensing">
              <Button variant="secondary" size="sm" className="w-full">
                Open Remote Sensing
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
