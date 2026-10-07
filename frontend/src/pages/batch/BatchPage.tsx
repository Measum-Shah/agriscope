import React, { useState } from 'react';
import { useMutation, useQuery } from '@tanstack/react-query';
import { Upload, Download, FileSpreadsheet, AlertCircle } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Badge } from '../../components/ui/Badge';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { jobsApi, BatchJobItem } from '../../api/jobs';

export const BatchPage: React.FC = () => {
  const { toast } = useToast();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);

  // Poll Job Status if active
  const { data: jobStatus } = useQuery({
    queryKey: ['batch-status', activeJobId],
    queryFn: () => (activeJobId ? jobsApi.getBatchStatus(activeJobId) : null),
    enabled: !!activeJobId,
    refetchInterval: (query) => {
      const data = query.state.data as BatchJobItem | null | undefined;
      return data?.status === 'processing' || data?.status === 'pending' ? 1500 : false;
    },
  });

  // Template Download Mutation
  const templateMutation = useMutation({
    mutationFn: () => jobsApi.getTemplate(),
    onSuccess: (data) => {
      const blob = new Blob([data.csv_content], { type: 'text/csv;charset=utf-8;' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.setAttribute('download', data.filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      toast({ type: 'success', title: 'Template Downloaded', description: 'CSV template is ready.' });
    },
  });

  // Upload Mutation
  const uploadMutation = useMutation({
    mutationFn: (file: File) => jobsApi.uploadBatchCsv(file),
    onSuccess: (res) => {
      setActiveJobId(res.job_id);
      setSelectedFile(null);
      toast({
        type: 'success',
        title: 'Batch Job Submitted',
        description: `Processing ${res.total_rows} rows asynchronously in the background.`,
      });
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Batch upload failed';
      toast({ type: 'error', title: 'Upload Error', description: msg });
    },
  });

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
    }
  };

  const handleUploadSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedFile) return;
    uploadMutation.mutate(selectedFile);
  };

  const handleDownloadResults = async () => {
    if (!activeJobId) return;
    try {
      const res = await jobsApi.getBatchDownloadUrl(activeJobId);
      window.open(res.download_url, '_blank');
    } catch (err: any) {
      toast({ type: 'error', title: 'Download Error', description: 'Could not obtain download link.' });
    }
  };

  return (
    <div className="space-y-6">
      {/* Page Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <FileSpreadsheet className="h-6 w-6 text-emerald-600" />
            Asynchronous Batch Prediction
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Upload CSV datasets (up to 10,000 rows) for high-throughput parallel inference and conformal bounds.
          </p>
        </div>

        <Button
          variant="outline"
          onClick={() => templateMutation.mutate()}
          disabled={templateMutation.isPending}
          className="flex items-center gap-2"
        >
          <Download className="h-4 w-4" />
          Download CSV Template
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Upload Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">Upload Dataset</CardTitle>
            <CardDescription className="text-xs">
              Columns required: temperature (°C), humidity (%), wind_speed (m/s), solar_radiation (MJ/m²/d).
            </CardDescription>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleUploadSubmit} className="space-y-4">
              <div className="border-2 border-dashed border-neutral-300 dark:border-neutral-700 rounded-lg p-6 text-center hover:border-emerald-500 transition-colors">
                <input
                  type="file"
                  accept=".csv"
                  id="batch-csv-input"
                  className="hidden"
                  onChange={handleFileChange}
                />
                <label
                  htmlFor="batch-csv-input"
                  className="cursor-pointer flex flex-col items-center justify-center space-y-2"
                >
                  <Upload className="h-8 w-8 text-neutral-400 hover:text-emerald-600" />
                  <span className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                    {selectedFile ? selectedFile.name : 'Click to select CSV dataset'}
                  </span>
                  <span className="text-[11px] text-neutral-400">
                    {selectedFile ? `${(selectedFile.size / 1024).toFixed(1)} KB` : 'Max 10,000 rows (15 MB)'}
                  </span>
                </label>
              </div>

              <div className="flex justify-end">
                <Button
                  type="submit"
                  disabled={!selectedFile || uploadMutation.isPending}
                  className="flex items-center gap-2"
                >
                  {uploadMutation.isPending ? <Spinner size="sm" /> : <Upload className="h-4 w-4" />}
                  Submit Batch Job
                </Button>
              </div>
            </form>
          </CardContent>
        </Card>

        {/* Live Job Progress & Results Card */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base flex items-center justify-between">
              <span>Job Execution Status</span>
              {jobStatus && (
                <Badge
                  variant="outline"
                  className={
                    jobStatus.status === 'completed'
                      ? 'bg-emerald-50 text-emerald-700 border-emerald-300'
                      : jobStatus.status === 'failed'
                      ? 'bg-red-50 text-red-700 border-red-300'
                      : 'bg-amber-50 text-amber-700 border-amber-300'
                  }
                >
                  {jobStatus.status.toUpperCase()}
                </Badge>
              )}
            </CardTitle>
            <CardDescription className="text-xs">
              Real-time worker processing progress and error summaries.
            </CardDescription>
          </CardHeader>
          <CardContent>
            {!jobStatus ? (
              <div className="h-48 flex flex-col items-center justify-center text-xs text-neutral-400 text-center">
                <FileSpreadsheet className="h-8 w-8 mb-2 opacity-40" />
                Upload a CSV file to monitor processing progress here.
              </div>
            ) : (
              <div className="space-y-4">
                {/* Progress Bar */}
                <div className="space-y-1">
                  <div className="flex justify-between text-xs font-medium text-neutral-700 dark:text-neutral-300">
                    <span>Progress: {jobStatus.processed_rows} / {jobStatus.total_rows} rows</span>
                    <span>
                      {jobStatus.total_rows > 0
                        ? `${Math.round((jobStatus.processed_rows / jobStatus.total_rows) * 100)}%`
                        : '0%'}
                    </span>
                  </div>
                  <div className="w-full bg-neutral-200 dark:bg-neutral-800 rounded-full h-2.5 overflow-hidden">
                    <div
                      className="bg-emerald-600 h-2.5 rounded-full transition-all duration-300"
                      style={{
                        width: `${
                          jobStatus.total_rows > 0
                            ? (jobStatus.processed_rows / jobStatus.total_rows) * 100
                            : 0
                        }%`,
                      }}
                    />
                  </div>
                </div>

                {/* Error Summary if any */}
                {jobStatus.error_summary?.failed_count && jobStatus.error_summary.failed_count > 0 ? (
                  <div className="p-3 bg-red-50 dark:bg-red-950/20 border border-red-200 dark:border-red-800 rounded-md text-xs text-red-700 dark:text-red-300">
                    <div className="font-semibold flex items-center gap-1 mb-1">
                      <AlertCircle className="h-3.5 w-3.5" />
                      {jobStatus.error_summary.failed_count} rows failed physical validation
                    </div>
                    <ul className="list-disc pl-4 space-y-0.5 text-[11px]">
                      {jobStatus.error_summary.errors_sample?.slice(0, 3).map((err, i) => (
                        <li key={i}>Row {err.row}: {err.error}</li>
                      ))}
                    </ul>
                  </div>
                ) : null}

                {/* Download Button */}
                {jobStatus.status === 'completed' && (
                  <div className="pt-2">
                    <Button onClick={handleDownloadResults} className="w-full flex items-center justify-center gap-2">
                      <Download className="h-4 w-4" />
                      Download Result CSV (with ML ET₀ & Bounds)
                    </Button>
                  </div>
                )}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
