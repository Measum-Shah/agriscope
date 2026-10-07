import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Plus, Trash2, Sprout, MapPin, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Modal } from '../../components/ui/Modal';
import { Badge } from '../../components/ui/Badge';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { FieldPolygonMap } from '../../components/maps/FieldPolygonMap';
import { fieldsApi, FieldItem, CreateFieldPayload } from '../../api/fields';
import { useAuth } from '../../context/AuthContext';

export const FieldsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();
  const { user } = useAuth();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [selectedField, setSelectedField] = useState<FieldItem | null>(null);

  // Form State
  const [name, setName] = useState('');
  const [cropId, setCropId] = useState('');
  const [plantingDate, setPlantingDate] = useState('');
  const [polygonCoords, setPolygonCoords] = useState<number[][][]>([]);

  // Queries
  const { data: fields = [], isLoading: fieldsLoading } = useQuery({
    queryKey: ['fields'],
    queryFn: fieldsApi.getFields,
  });

  const { data: crops = [] } = useQuery({
    queryKey: ['crops'],
    queryFn: fieldsApi.getCrops,
  });

  // Create Field Mutation
  const createMutation = useMutation({
    mutationFn: (payload: CreateFieldPayload) => fieldsApi.createField(payload),
    onSuccess: (newField) => {
      queryClient.invalidateQueries({ queryKey: ['fields'] });
      toast({
        type: 'success',
        title: 'Field Created',
        description: `Field "${newField.name}" (${newField.area_ha.toFixed(2)} ha) was added successfully.`,
      });
      setIsCreateOpen(false);
      resetForm();
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to create field';
      toast({ type: 'error', title: 'Error', description: msg });
    },
  });

  // Delete Field Mutation
  const deleteMutation = useMutation({
    mutationFn: (fieldId: string) => fieldsApi.deleteField(fieldId),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['fields'] });
      toast({ type: 'success', title: 'Field Deleted', description: 'Field was removed.' });
      if (selectedField) setSelectedField(null);
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Failed to delete field';
      toast({ type: 'error', title: 'Error', description: msg });
    },
  });

  const resetForm = () => {
    setName('');
    setCropId('');
    setPlantingDate('');
    setPolygonCoords([]);
  };

  const handleCreateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) {
      toast({ type: 'warning', title: 'Name required', description: 'Please provide a field name.' });
      return;
    }
    if (polygonCoords.length === 0 || polygonCoords[0].length < 3) {
      toast({
        type: 'warning',
        title: 'Polygon required',
        description: 'Please draw at least 3 vertices on the map to define field boundaries.',
      });
      return;
    }

    createMutation.mutate({
      name: name.trim(),
      crop_id: cropId || null,
      planting_date: plantingDate || null,
      geometry: {
        type: 'Polygon',
        coordinates: polygonCoords,
      },
    });
  };

  const isFreePlan = user?.plan === 'free';
  const reachedFreeLimit = isFreePlan && fields.length >= 1;

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100">
            Fields & Parcels
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            PostGIS spatial boundaries, crop assignment, and parcel metrics.
          </p>
        </div>

        <Button
          onClick={() => setIsCreateOpen(true)}
          disabled={reachedFreeLimit}
          className="flex items-center gap-2"
        >
          <Plus className="h-4 w-4" />
          Add Field
        </Button>
      </div>

      {/* Free Plan Limit Notice */}
      {reachedFreeLimit && (
        <div className="flex items-center gap-3 p-4 bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800 rounded-lg text-amber-800 dark:text-amber-200 text-sm">
          <AlertCircle className="h-5 w-5 flex-shrink-0 text-amber-600" />
          <div>
            <span className="font-semibold">Free tier limit reached (1 field).</span> Upgrade to Pro for unlimited fields, STAC Sentinel-2 remote sensing, and automated weekly satellite updates.
          </div>
        </div>
      )}

      {/* Main Grid: Field List + Map Details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Fields List */}
        <div className="lg:col-span-1 space-y-3">
          <Card>
            <CardHeader className="pb-3">
              <CardTitle className="text-base flex items-center justify-between">
                <span>My Parcels</span>
                <Badge variant="outline">{fields.length} registered</Badge>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-2 p-3">
              {fieldsLoading ? (
                <div className="flex justify-center p-6">
                  <Spinner size="md" />
                </div>
              ) : fields.length === 0 ? (
                <div className="text-center py-8 text-neutral-500 text-sm">
                  No fields created yet. Click "Add Field" to draw your first boundary.
                </div>
              ) : (
                fields.map((field) => (
                  <div
                    key={field.id}
                    onClick={() => setSelectedField(field)}
                    className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedField?.id === field.id
                        ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20 dark:border-emerald-500'
                        : 'border-neutral-200 dark:border-neutral-800 hover:border-neutral-300 dark:hover:border-neutral-700'
                    }`}
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <h4 className="font-medium text-neutral-900 dark:text-neutral-100">
                          {field.name}
                        </h4>
                        <div className="text-xs text-neutral-500 flex items-center gap-1 mt-1">
                          <Sprout className="h-3 w-3" />
                          <span>{field.crop_name || 'No crop set'}</span>
                          <span>•</span>
                          <span>{field.area_ha.toFixed(2)} ha</span>
                        </div>
                      </div>
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={(e) => {
                          e.stopPropagation();
                          if (confirm(`Delete parcel "${field.name}"?`)) {
                            deleteMutation.mutate(field.id);
                          }
                        }}
                        className="h-7 w-7 p-0 text-red-600 hover:text-red-700 border-none"
                      >
                        <Trash2 className="h-3.5 w-3.5" />
                      </Button>
                    </div>
                  </div>
                ))
              )}
            </CardContent>
          </Card>
        </div>

        {/* Selected Field Viewer or Overview */}
        <div className="lg:col-span-2">
          {selectedField ? (
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between">
                  <div>
                    <CardTitle className="flex items-center gap-2">
                      <MapPin className="h-5 w-5 text-emerald-600" />
                      {selectedField.name}
                    </CardTitle>
                    <CardDescription>
                      Surface Area: {selectedField.area_ha.toFixed(2)} ha | Crop: {selectedField.crop_name || 'Unassigned'}
                      {selectedField.planting_date ? ` | Planted: ${selectedField.planting_date}` : ''}
                    </CardDescription>
                  </div>
                  <a
                    href={`/remote-sensing?field=${selectedField.id}`}
                    className="inline-flex items-center justify-center rounded-md text-xs font-medium bg-emerald-600 text-white hover:bg-emerald-700 px-3 py-1.5 transition-colors"
                  >
                    Analyze Satellite Data →
                  </a>
                </div>
              </CardHeader>
              <CardContent>
                <FieldPolygonMap
                  initialPolygon={selectedField.geometry.coordinates}
                  readOnly={true}
                  height={420}
                />
              </CardContent>
            </Card>
          ) : (
            <Card className="h-full flex flex-col justify-center items-center p-12 text-center text-neutral-500 border-dashed">
              <MapPin className="h-10 w-10 text-neutral-300 dark:text-neutral-600 mb-2" />
              <p className="font-medium text-sm">Select a parcel to view boundary geometry</p>
              <p className="text-xs text-neutral-400 mt-1">
                Draw parcel boundaries to calculate acreage and compute multi-temporal satellite NDVI/ETc indices.
              </p>
            </Card>
          )}
        </div>
      </div>

      {/* Add Field Modal */}
      <Modal
        open={isCreateOpen}
        onOpenChange={(open) => {
          setIsCreateOpen(open);
          if (!open) resetForm();
        }}
        title="Add Field Parcel"
      >
        <form onSubmit={handleCreateSubmit} className="space-y-4">
          <Input
            label="Field Name"
            placeholder="e.g. North Wheat Parcel 1"
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
          />

          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Crop (FAO-56)
              </label>
              <select
                className="w-full text-xs rounded-md border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-800 p-2 text-neutral-900 dark:text-neutral-100"
                value={cropId}
                onChange={(e) => setCropId(e.target.value)}
              >
                <option value="">None / Unassigned</option>
                {crops.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.name}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
                Planting Date
              </label>
              <Input
                type="date"
                value={plantingDate}
                onChange={(e) => setPlantingDate(e.target.value)}
              />
            </div>
          </div>

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-1">
              Field Boundary (Click map to draw vertices)
            </label>
            <FieldPolygonMap
              onPolygonChange={(coords) => setPolygonCoords(coords)}
              height={260}
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => {
                setIsCreateOpen(false);
                resetForm();
              }}
            >
              Cancel
            </Button>
            <Button type="submit" disabled={createMutation.isPending}>
              {createMutation.isPending ? 'Saving...' : 'Save Parcel'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
