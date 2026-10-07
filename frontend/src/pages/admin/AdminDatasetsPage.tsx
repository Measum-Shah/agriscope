import React, { useEffect, useState } from 'react';
import { Upload, Trash2, Download, AlertTriangle, CheckCircle } from 'lucide-react';
import { adminApi, DatasetItem, DatasetUploadReport } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { useToast } from '../../components/ui/Toast';

export const AdminDatasetsPage: React.FC = () => {
  const { toast } = useToast();
  const [datasets, setDatasets] = useState<DatasetItem[]>([]);

  // Upload state
  const [uploadOpen, setUploadOpen] = useState(false);
  const [name, setName] = useState('');
  const [version, setVersion] = useState('');
  const [desc, setDesc] = useState('');
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [uploading, setUploading] = useState(false);
  const [report, setReport] = useState<DatasetUploadReport | null>(null);

  const loadDatasets = async () => {
    try {
      const data = await adminApi.listDatasets();
      setDatasets(data);
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to fetch datasets.' });
    }
  };

  useEffect(() => {
    loadDatasets();
  }, []);

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile || !name.trim() || !version.trim()) return;

    setUploading(true);
    const formData = new FormData();
    formData.append('name', name.trim());
    formData.append('version', version.trim());
    if (desc) formData.append('description', desc.trim());
    formData.append('file', selectedFile);

    try {
      const res = await adminApi.uploadDataset(formData);
      setReport(res);
      toast({
        type: res.status === 'validated' ? 'success' : 'warning',
        title: 'Upload Processed',
        description: res.message,
      });
      await loadDatasets();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upload failed';
      toast({ type: 'error', title: 'Upload Failed', description: msg });
    } finally {
      setUploading(false);
    }
  };

  const handleDelete = async (id: string, dName: string) => {
    if (!window.confirm(`Delete dataset ${dName}?`)) return;
    try {
      await adminApi.deleteDataset(id);
      toast({ type: 'success', title: 'Dataset Deleted', description: 'Record removed.' });
      await loadDatasets();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Deletion failed.' });
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">Dataset Management</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Upload CSV datasets, validate schemas and physics ranges, inspect outliers, and version training data.
          </p>
        </div>
        <Button onClick={() => { setReport(null); setUploadOpen(true); }} className="gap-2">
          <Upload className="h-4 w-4" /> Upload New Dataset
        </Button>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-muted/50 border-b text-xs uppercase font-semibold text-muted-foreground">
                <tr>
                  <th className="p-4">Dataset</th>
                  <th className="p-4">Version</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Provenance</th>
                  <th className="p-4">Uploaded</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {datasets.map((d) => (
                  <tr key={d.id} className="hover:bg-muted/20">
                    <td className="p-4">
                      <div className="font-semibold text-foreground">{d.name}</div>
                      <div className="text-xs text-muted-foreground truncate max-w-xs">{d.description || 'No description'}</div>
                    </td>
                    <td className="p-4 font-mono text-xs">{d.version}</td>
                    <td className="p-4">
                      <Badge variant={d.status === 'validated' ? 'default' : d.status === 'rejected' ? 'destructive' : 'secondary'} className="uppercase text-[10px]">
                        {d.status}
                      </Badge>
                    </td>
                    <td className="p-4 text-xs capitalize">{d.data_provenance}</td>
                    <td className="p-4 text-xs text-muted-foreground">
                      {new Date(d.created_at).toLocaleDateString()}
                    </td>
                    <td className="p-4 text-right space-x-1">
                      <Button variant="ghost" size="sm" onClick={() => window.open(`/api/v1/admin/datasets/${d.id}/download`)}>
                        <Download className="h-3.5 w-3.5" />
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => handleDelete(d.id, d.name)}>
                        <Trash2 className="h-3.5 w-3.5 text-destructive" />
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Upload and Validation Modal */}
      <Modal
        open={uploadOpen}
        onOpenChange={(open) => { setUploadOpen(open); if (!open) setReport(null); }}
        title={report ? 'Dataset Validation Report' : 'Upload Training Dataset'}
        description={report ? `Validation summary for ${report.name}` : 'Upload a CSV dataset with temp_max, temp_min, humidity, and wind_speed.'}
        size="lg"
      >
        {report ? (
          <div className="space-y-4 max-h-[70vh] overflow-y-auto">
            <div className="flex items-center gap-2 p-3 rounded border bg-muted/30">
              {report.status === 'validated' ? (
                <CheckCircle className="h-5 w-5 text-emerald-500" />
              ) : (
                <AlertTriangle className="h-5 w-5 text-amber-500" />
              )}
              <div>
                <span className="font-bold text-sm">{report.message}</span>
                <p className="text-xs text-muted-foreground">Rows: {report.row_count} • Columns: {report.columns.join(', ')}</p>
              </div>
            </div>

            {report.validation_errors.length > 0 && (
              <div className="p-3 bg-destructive/10 border border-destructive/20 rounded text-xs text-destructive space-y-1">
                <span className="font-bold">Validation Warnings:</span>
                {report.validation_errors.map((e, idx) => (
                  <p key={idx}>• {e}</p>
                ))}
              </div>
            )}

            <div>
              <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">First 10 Preview Rows</h4>
              <div className="overflow-x-auto border rounded text-xs">
                <table className="w-full text-left">
                  <thead className="bg-muted">
                    <tr>
                      {report.columns.map((c) => (
                        <th key={c} className="p-2 border-r last:border-r-0">{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {report.preview_rows.map((row, i) => (
                      <tr key={i} className="border-t">
                        {report.columns.map((c) => (
                          <td key={c} className="p-2 border-r last:border-r-0">{String(row[c] ?? '')}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <Button onClick={() => setUploadOpen(false)}>Done</Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleUpload} className="space-y-4">
            <Input label="Dataset Name" placeholder="e.g., Punjab Irrigated Stations 2026" value={name} onChange={(e) => setName(e.target.value)} required />
            <Input label="Version Tag" placeholder="e.g., v1.2" value={version} onChange={(e) => setVersion(e.target.value)} required />
            <Input label="Description (optional)" placeholder="Provenance details or sensor notes..." value={desc} onChange={(e) => setDesc(e.target.value)} />
            <div>
              <label className="text-sm font-medium text-foreground block mb-1">CSV File</label>
              <input type="file" accept=".csv" onChange={(e) => setSelectedFile(e.target.files?.[0] || null)} required className="text-sm file:mr-3 file:py-1.5 file:px-3 file:rounded file:border-0 file:bg-primary file:text-primary-foreground" />
            </div>
            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setUploadOpen(false)}>Cancel</Button>
              <Button type="submit" loading={uploading} disabled={!selectedFile || !name.trim()}>Upload & Validate</Button>
            </div>
          </form>
        )}
      </Modal>
    </div>
  );
};
