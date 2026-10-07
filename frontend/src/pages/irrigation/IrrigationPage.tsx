import React, { useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import {
  Droplets,
  Plus,
  Trash2,
  Calendar as CalendarIcon,
  AlertTriangle,
  CheckCircle2,
  Activity,
  Sprout,
  Waves,
} from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { fieldsApi } from '../../api/fields';
import { irrigationApi, LogIrrigationPayload } from '../../api/irrigation';
import { SoilWaterDepletionChart } from '../../components/charts/SoilWaterDepletionChart';

export const IrrigationPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const initialFieldId = searchParams.get('field') || '';
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [selectedFieldId, setSelectedFieldId] = useState<string>(initialFieldId);
  const [soilType, setSoilType] = useState<string>('loam');
  const [madFraction, setMadFraction] = useState<number>(0.5);
  const [isLogModalOpen, setIsLogModalOpen] = useState<boolean>(false);

  // Form State for Event Logging
  const [eventDate, setEventDate] = useState<string>(new Date().toISOString().split('T')[0]);
  const [waterApplied, setWaterApplied] = useState<string>('25');
  const [method, setMethod] = useState<string>('drip');
  const [notes, setNotes] = useState<string>('');

  // Queries
  const { data: fields = [], isLoading: fieldsLoading } = useQuery({
    queryKey: ['fields'],
    queryFn: fieldsApi.getFields,
  });

  React.useEffect(() => {
    if (!selectedFieldId && fields.length > 0) {
      setSelectedFieldId(fields[0].id);
      setSearchParams({ field: fields[0].id });
    }
  }, [fields, selectedFieldId, setSearchParams]);

  const { data: plan, isLoading: planLoading } = useQuery({
    queryKey: ['irrigation-plan', selectedFieldId, soilType, madFraction],
    queryFn: () =>
      selectedFieldId
        ? irrigationApi.getPlan(selectedFieldId, {
            soil_type: soilType,
            mad_fraction: madFraction,
            forecast_days: 7,
          })
        : null,
    enabled: !!selectedFieldId,
  });

  // Log Event Mutation
  const logEventMutation = useMutation({
    mutationFn: (payload: LogIrrigationPayload) =>
      irrigationApi.logEvent(selectedFieldId, payload),
    onSuccess: (ev) => {
      queryClient.invalidateQueries({ queryKey: ['irrigation-plan', selectedFieldId] });
      toast({
        type: 'success',
        title: 'Irrigation Event Logged',
        description: `Applied ${ev.water_applied_mm} mm via ${ev.method} on ${ev.event_date}. Soil water balance updated.`,
      });
      setIsLogModalOpen(false);
      setNotes('');
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to log irrigation event';
      toast({ type: 'error', title: 'Error', description: msg });
    },
  });

  // Delete Event Mutation
  const deleteEventMutation = useMutation({
    mutationFn: (eventId: string) => irrigationApi.deleteEvent(selectedFieldId, eventId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['irrigation-plan', selectedFieldId] });
      toast({
        type: 'success',
        title: 'Event Deleted',
        description: 'Irrigation event removed and balance re-calculated.',
      });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to delete event';
      toast({ type: 'error', title: 'Error', description: msg });
    },
  });

  const handleLogSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const amount = parseFloat(waterApplied);
    if (isNaN(amount) || amount <= 0) {
      toast({
        type: 'warning',
        title: 'Invalid Depth',
        description: 'Please enter a valid irrigation depth (mm).',
      });
      return;
    }
    logEventMutation.mutate({
      event_date: eventDate,
      water_applied_mm: amount,
      method,
      notes: notes.trim() || undefined,
    });
  };

  const getStatusBadge = (status: string) => {
    switch (status) {
      case 'optimal':
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300">Optimal Moisture</Badge>;
      case 'caution':
        return <Badge variant="outline" className="bg-amber-50 text-amber-700 border-amber-300">Approaching RAW</Badge>;
      case 'stress':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">Water Stress</Badge>;
      case 'saturated':
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">Field Capacity</Badge>;
      default:
        return <Badge variant="outline">{status}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <Droplets className="h-6 w-6 text-emerald-600" />
            Crop Water Requirement & Irrigation Scheduling
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Daily root-zone soil water balance, RAW depletion thresholds, and 7-day forecast-aware schedule.
          </p>
        </div>

        <Button
          onClick={() => setIsLogModalOpen(true)}
          disabled={!selectedFieldId}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Log Applied Irrigation
        </Button>
      </div>

      {/* Field & Soil Controls Bar */}
      <Card>
        <CardContent className="p-4">
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
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
                Soil Texture Preset (FAO-56 Table 19)
              </label>
              <select
                className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
                value={soilType}
                onChange={(e) => setSoilType(e.target.value)}
              >
                <option value="sand">Sand (TAW: 80 mm/m)</option>
                <option value="loamy_sand">Loamy Sand (TAW: 100 mm/m)</option>
                <option value="sandy_loam">Sandy Loam (TAW: 130 mm/m)</option>
                <option value="loam">Loam (TAW: 160 mm/m - Recommended)</option>
                <option value="silt_loam">Silt Loam (TAW: 180 mm/m)</option>
                <option value="clay_loam">Clay Loam (TAW: 170 mm/m)</option>
                <option value="clay">Clay (TAW: 160 mm/m)</option>
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Management Allowed Depletion: {Math.round(madFraction * 100)}%
              </label>
              <input
                type="range"
                min={0.2}
                max={0.8}
                step={0.05}
                value={madFraction}
                onChange={(e) => setMadFraction(parseFloat(e.target.value))}
                className="w-full mt-2"
              />
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Summary KPI Cards */}
      {plan && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Moisture Status</p>
                <div className="mt-1.5">{getStatusBadge(plan.summary.status)}</div>
                <p className="text-[10px] text-neutral-400 mt-1.5">
                  Depletion: {plan.summary.current_depletion_mm.toFixed(1)} mm / RAW {plan.summary.raw_mm.toFixed(1)} mm
                </p>
              </div>
              <Activity className="h-8 w-8 text-emerald-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Net Irrigation Req (NIR)</p>
                <h3 className="text-2xl font-bold text-orange-600 mt-0.5">
                  {plan.summary.net_irrigation_requirement_mm.toFixed(1)} mm
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">
                  Season ETc: {plan.summary.total_etc_mm.toFixed(1)} mm
                </p>
              </div>
              <Droplets className="h-8 w-8 text-orange-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Total Applied Water</p>
                <h3 className="text-2xl font-bold text-blue-600 mt-0.5">
                  {plan.summary.total_irrigation_applied_mm.toFixed(1)} mm
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">
                  {plan.events.length} logged events
                </p>
              </div>
              <Waves className="h-8 w-8 text-blue-500/20" />
            </CardContent>
          </Card>

          <Card>
            <CardContent className="p-4 flex items-center justify-between">
              <div>
                <p className="text-xs text-neutral-500 font-medium">Effective Rainfall</p>
                <h3 className="text-2xl font-bold text-teal-600 mt-0.5">
                  {plan.summary.total_effective_rain_mm.toFixed(1)} mm
                </h3>
                <p className="text-[10px] text-neutral-400 mt-1">
                  Gross: {plan.summary.total_rainfall_mm.toFixed(1)} mm
                </p>
              </div>
              <Sprout className="h-8 w-8 text-teal-500/20" />
            </CardContent>
          </Card>
        </div>
      )}

      {/* Main Depletion Chart */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span>Soil Root-Zone Water Depletion (Dr) & Stress Limit</span>
            <Badge variant="outline">FAO-56 Daily Water Balance</Badge>
          </CardTitle>
          <CardDescription className="text-xs">
            Depletion increasing above the red dashed RAW threshold causes crop moisture stress and triggers irrigation recommendations.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {planLoading ? (
            <div className="flex justify-center p-12"><Spinner size="md" /></div>
          ) : (
            <SoilWaterDepletionChart data={plan?.daily_balance || []} height={300} />
          )}
        </CardContent>
      </Card>

      {/* Recommended Forecast Schedule & Logged Events Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* 7-Day Forecast Schedule Table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>7-Day Irrigation Schedule</span>
              <CalendarIcon className="h-4 w-4 text-neutral-500" />
            </CardTitle>
            <CardDescription className="text-xs">
              Forecast-aware water application recommendations.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300">
                  <tr>
                    <th className="p-2">Date</th>
                    <th className="p-2">Depletion</th>
                    <th className="p-2">Status</th>
                    <th className="p-2">Depth (mm)</th>
                    <th className="p-2">Vol (m³)</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {!plan || plan.schedule.length === 0 ? (
                    <tr><td colSpan={5} className="p-4 text-center text-neutral-400">No schedule generated</td></tr>
                  ) : (
                    plan.schedule.map((item) => (
                      <tr
                        key={item.date}
                        className={item.is_irrigation_due ? 'bg-amber-50/50 dark:bg-amber-950/20 font-medium' : ''}
                      >
                        <td className="p-2">
                          <div>{item.date}</div>
                          <div className="text-[10px] text-neutral-400">{item.day_name}</div>
                        </td>
                        <td className="p-2">{item.depletion_mm.toFixed(1)} mm</td>
                        <td className="p-2">
                          {item.is_irrigation_due ? (
                            <span className="inline-flex items-center gap-1 text-amber-700 dark:text-amber-300 text-[11px]">
                              <AlertTriangle className="h-3 w-3" /> Due
                            </span>
                          ) : (
                            <span className="inline-flex items-center gap-1 text-emerald-600 text-[11px]">
                              <CheckCircle2 className="h-3 w-3" /> OK
                            </span>
                          )}
                        </td>
                        <td className="p-2 font-semibold">
                          {item.is_irrigation_due ? `${item.recommended_depth_mm} mm` : '—'}
                        </td>
                        <td className="p-2 text-neutral-600 dark:text-neutral-300">
                          {item.is_irrigation_due ? `${item.recommended_volume_m3_total} m³` : '—'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>

        {/* Logged Irrigation Events History */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Applied Water Events</span>
              <span className="text-xs text-neutral-500">{plan?.events.length || 0} events</span>
            </CardTitle>
            <CardDescription className="text-xs">
              History of water applied to field. Logging resets root zone depletion.
            </CardDescription>
          </CardHeader>
          <CardContent>
            <div className="overflow-x-auto max-h-[280px]">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 sticky top-0">
                  <tr>
                    <th className="p-2">Date</th>
                    <th className="p-2">Depth (mm)</th>
                    <th className="p-2">Method</th>
                    <th className="p-2">Notes</th>
                    <th className="p-2 text-right">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {!plan || plan.events.length === 0 ? (
                    <tr>
                      <td colSpan={5} className="p-6 text-center text-neutral-400">
                        No irrigation events logged yet.
                      </td>
                    </tr>
                  ) : (
                    plan.events.map((ev) => (
                      <tr key={ev.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                        <td className="p-2 font-medium">{ev.event_date}</td>
                        <td className="p-2 text-blue-600 font-semibold">{ev.water_applied_mm} mm</td>
                        <td className="p-2 capitalize">{ev.method}</td>
                        <td className="p-2 text-neutral-500 truncate max-w-[120px]">{ev.notes || '—'}</td>
                        <td className="p-2 text-right">
                          <Button
                            variant="outline"
                            size="sm"
                            onClick={() => {
                              if (confirm('Delete this irrigation event?')) {
                                deleteEventMutation.mutate(ev.id);
                              }
                            }}
                            className="h-6 w-6 p-0 text-red-600 hover:text-red-700 border-none"
                          >
                            <Trash2 className="h-3 w-3" />
                          </Button>
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Log Irrigation Modal */}
      <Modal
        open={isLogModalOpen}
        onOpenChange={setIsLogModalOpen}
        title="Log Applied Irrigation"
      >
        <form onSubmit={handleLogSubmit} className="space-y-4">
          <Input
            type="date"
            label="Date Applied"
            value={eventDate}
            onChange={(e) => setEventDate(e.target.value)}
            required
          />

          <Input
            type="number"
            step="0.5"
            label="Water Depth Applied (mm)"
            placeholder="e.g. 25"
            value={waterApplied}
            onChange={(e) => setWaterApplied(e.target.value)}
            required
          />

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Application Method
            </label>
            <select
              className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
              value={method}
              onChange={(e) => setMethod(e.target.value)}
            >
              <option value="drip">Drip Irrigation (High efficiency)</option>
              <option value="sprinkler">Sprinkler System</option>
              <option value="furrow">Furrow Irrigation</option>
              <option value="flood">Flood / Basin</option>
            </select>
          </div>

          <Input
            label="Notes / Operator Reference"
            placeholder="e.g. Pump station #2 morning cycle"
            value={notes}
            onChange={(e) => setNotes(e.target.value)}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setIsLogModalOpen(false)}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={logEventMutation.isPending}>
              {logEventMutation.isPending ? 'Saving...' : 'Record Irrigation'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
