import React, { useState } from 'react';
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { FileText, Download, Plus, FileSpreadsheet, Image as ImageIcon } from 'lucide-react';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';
import { jobsApi } from '../../api/jobs';

export const ReportsPage: React.FC = () => {
  const queryClient = useQueryClient();
  const { toast } = useToast();

  const [isCreateOpen, setIsCreateOpen] = useState(false);
  const [title, setTitle] = useState('');
  const [format, setFormat] = useState<'pdf' | 'csv' | 'xlsx' | 'png'>('pdf');

  // Queries
  const { data: reports = [], isLoading: reportsLoading } = useQuery({
    queryKey: ['reports'],
    queryFn: jobsApi.listReports,
  });

  // Generate Report Mutation
  const generateMutation = useMutation({
    mutationFn: (payload: { title: string; format: string }) =>
      jobsApi.generateReport(payload),
    onSuccess: (newReport) => {
      queryClient.invalidateQueries({ queryKey: ['reports'] });
      toast({
        type: 'success',
        title: 'Report Generated',
        description: `Your ${newReport.format.toUpperCase()} report is ready for download.`,
      });
      setIsCreateOpen(false);
      setTitle('');
    },
    onError: (err: any) => {
      const msg = err.response?.data?.detail || 'Report generation failed';
      toast({ type: 'error', title: 'Error', description: msg });
    },
  });

  const handleGenerateSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      toast({ type: 'warning', title: 'Title required', description: 'Please provide a report title.' });
      return;
    }
    generateMutation.mutate({ title: title.trim(), format });
  };

  const getFormatBadge = (fmt: string) => {
    switch ((fmt || '').toLowerCase()) {
      case 'pdf':
        return <Badge variant="outline" className="bg-red-50 text-red-700 border-red-300">PDF</Badge>;
      case 'xlsx':
        return <Badge variant="outline" className="bg-emerald-50 text-emerald-700 border-emerald-300">XLSX</Badge>;
      case 'csv':
        return <Badge variant="outline" className="bg-blue-50 text-blue-700 border-blue-300">CSV</Badge>;
      case 'png':
        return <Badge variant="outline" className="bg-purple-50 text-purple-700 border-purple-300">PNG</Badge>;
      default:
        return <Badge variant="outline">{(fmt || 'FILE').toUpperCase()}</Badge>;
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <FileText className="h-6 w-6 text-emerald-600" />
            Reports & Analytical Exports
          </h1>
          <p className="text-sm text-neutral-600 dark:text-neutral-400">
            Export branded PDFs, Excel workbooks (XLSX), CSV data, and high-resolution chart snapshots.
          </p>
        </div>

        <Button onClick={() => setIsCreateOpen(true)} className="flex items-center gap-2">
          <Plus className="h-4 w-4" />
          Generate Report
        </Button>
      </div>

      {/* Reports Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base flex items-center justify-between">
            <span>Generated Reports</span>
            <span className="text-xs text-neutral-500">{reports.length} files available</span>
          </CardTitle>
          <CardDescription className="text-xs">
            Exported documents stored securely with expiring download tokens.
          </CardDescription>
        </CardHeader>
        <CardContent>
          {reportsLoading ? (
            <div className="flex justify-center p-12"><Spinner size="md" /></div>
          ) : reports.length === 0 ? (
            <div className="text-center py-12 text-neutral-400 text-xs">
              No reports generated yet. Click "Generate Report" to export a PDF summary or XLSX workbook.
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs">
                <thead className="bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300">
                  <tr>
                    <th className="p-3">Title</th>
                    <th className="p-3">Format</th>
                    <th className="p-3">File Size</th>
                    <th className="p-3">Created At</th>
                    <th className="p-3 text-right">Download</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-neutral-200 dark:divide-neutral-800">
                  {reports.map((rep) => (
                    <tr key={rep.id} className="hover:bg-neutral-50 dark:hover:bg-neutral-800/50">
                      <td className="p-3 font-medium text-neutral-900 dark:text-neutral-100">
                        {rep.title}
                      </td>
                      <td className="p-3">{getFormatBadge(rep.format)}</td>
                      <td className="p-3 text-neutral-500">
                        {(rep.file_size_bytes / 1024).toFixed(1)} KB
                      </td>
                      <td className="p-3 text-neutral-500">
                        {new Date(rep.created_at).toLocaleString()}
                      </td>
                      <td className="p-3 text-right">
                        {rep.download_url && (
                          <a
                            href={rep.download_url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="inline-flex items-center gap-1.5 px-3 py-1 rounded bg-neutral-100 dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 hover:bg-emerald-50 hover:text-emerald-700 transition-colors"
                          >
                            <Download className="h-3 w-3" />
                            Download
                          </a>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Generate Modal */}
      <Modal
        open={isCreateOpen}
        onOpenChange={setIsCreateOpen}
        title="Generate Analytical Export"
      >
        <form onSubmit={handleGenerateSubmit} className="space-y-4">
          <Input
            label="Report Title"
            placeholder="e.g. October 2026 Evapotranspiration Summary"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            required
          />

          <div>
            <label className="block text-xs font-medium text-neutral-700 dark:text-neutral-300 mb-2">
              Export Format
            </label>
            <div className="grid grid-cols-2 gap-3">
              <div
                onClick={() => setFormat('pdf')}
                className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                  format === 'pdf'
                    ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20'
                    : 'border-neutral-200 dark:border-neutral-800'
                }`}
              >
                <FileText className="h-5 w-5 text-red-600" />
                <div>
                  <div className="text-xs font-semibold">Branded PDF</div>
                  <div className="text-[10px] text-neutral-500">With embedded charts</div>
                </div>
              </div>

              <div
                onClick={() => setFormat('xlsx')}
                className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                  format === 'xlsx'
                    ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20'
                    : 'border-neutral-200 dark:border-neutral-800'
                }`}
              >
                <FileSpreadsheet className="h-5 w-5 text-emerald-600" />
                <div>
                  <div className="text-xs font-semibold">Excel Workbook</div>
                  <div className="text-[10px] text-neutral-500">Styled XLSX spreadsheet</div>
                </div>
              </div>

              <div
                onClick={() => setFormat('csv')}
                className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                  format === 'csv'
                    ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20'
                    : 'border-neutral-200 dark:border-neutral-800'
                }`}
              >
                <FileSpreadsheet className="h-5 w-5 text-blue-600" />
                <div>
                  <div className="text-xs font-semibold">Sanitized CSV</div>
                  <div className="text-[10px] text-neutral-500">Protected against injection</div>
                </div>
              </div>

              <div
                onClick={() => setFormat('png')}
                className={`p-3 rounded-lg border cursor-pointer flex items-center gap-3 transition-colors ${
                  format === 'png'
                    ? 'border-emerald-600 bg-emerald-50/50 dark:bg-emerald-950/20'
                    : 'border-neutral-200 dark:border-neutral-800'
                }`}
              >
                <ImageIcon className="h-5 w-5 text-purple-600" />
                <div>
                  <div className="text-xs font-semibold">Chart Snapshot</div>
                  <div className="text-[10px] text-neutral-500">High-res PNG render</div>
                </div>
              </div>
            </div>
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setIsCreateOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" disabled={generateMutation.isPending}>
              {generateMutation.isPending ? 'Generating...' : 'Create Export'}
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
