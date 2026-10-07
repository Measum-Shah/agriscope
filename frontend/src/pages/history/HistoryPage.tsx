import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import {
  History as HistoryIcon,
  Search,
  Trash2,
  Bookmark,
  BookmarkCheck,
  ChevronLeft,
  ChevronRight,
  TrendingUp,
  FileText,
  UploadCloud,
} from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { useToast } from '../../components/ui/Toast';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Badge } from '../../components/ui/Badge';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { historyApi, HistoryListResponse, HistoryStatsResponse } from '../../api/history';
import { PredictResponse } from '../../api/predict';
import { EtHistoryLineChart } from '../../components/charts/EtHistoryLineChart';

export const HistoryPage: React.FC = () => {
  const { user } = useAuth();
  const { toast } = useToast();
  const isFree = user?.plan === 'free' && user?.role !== 'admin';

  const [data, setData] = useState<HistoryListResponse | null>(null);
  const [stats, setStats] = useState<HistoryStatsResponse | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Filters state
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState('');
  const [classification, setClassification] = useState('');
  const [savedOnly, setSavedOnly] = useState(false);

  // Selection for bulk delete
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [deleteTargetId, setDeleteTargetId] = useState<string | null>(null);
  const [isBulkConfirmOpen, setIsBulkConfirmOpen] = useState(false);

  // Edit note dialog state
  const [editingItem, setEditingItem] = useState<PredictResponse | null>(null);
  const [editNote, setEditNote] = useState('');

  const fetchHistory = React.useCallback(async () => {
    setIsLoading(true);
    try {
      const res = await historyApi.list({
        page,
        per_page: 15,
        search: search.trim() || undefined,
        classification: classification || undefined,
        is_saved: savedOnly ? true : undefined,
      });
      setData(res);
      setSelectedIds([]);
    } catch {
      toast({ title: 'Failed to load history', type: 'error' });
    } finally {
      setIsLoading(false);
    }
  }, [page, search, classification, savedOnly, toast]);

  const fetchStats = async () => {
    try {
      const s = await historyApi.getStats();
      setStats(s);
    } catch {
      // Non-blocking stats
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [fetchHistory]);

  useEffect(() => {
    fetchStats();
  }, []);

  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setPage(1);
    fetchHistory();
  };

  const handleToggleBookmark = async (item: PredictResponse) => {
    if (!item.id) return;
    try {
      const nextSaved = !item.is_saved;
      await historyApi.update(item.id, { is_saved: nextSaved });
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((i) => (i.id === item.id ? { ...i, is_saved: nextSaved } : i)),
            }
          : null
      );
      toast({
        title: nextSaved ? 'Bookmarked' : 'Unsaved',
        type: 'success',
      });
    } catch {
      toast({ title: 'Update failed', type: 'error' });
    }
  };

  const handleDeleteSingle = async () => {
    if (!deleteTargetId) return;
    try {
      await historyApi.delete(deleteTargetId);
      setDeleteTargetId(null);
      fetchHistory();
      fetchStats();
      toast({ title: 'Prediction deleted', type: 'success' });
    } catch {
      toast({ title: 'Delete failed', type: 'error' });
    }
  };

  const handleBulkDelete = async () => {
    if (selectedIds.length === 0) return;
    try {
      const res = await historyApi.bulkDelete(selectedIds);
      setIsBulkConfirmOpen(false);
      setSelectedIds([]);
      fetchHistory();
      fetchStats();
      toast({
        title: 'Bulk Delete Completed',
        description: `Removed ${res.deleted_count} prediction records`,
        type: 'success',
      });
    } catch {
      toast({ title: 'Bulk delete failed', type: 'error' });
    }
  };

  const handleSaveNote = async () => {
    if (!editingItem?.id) return;
    try {
      await historyApi.update(editingItem.id, { note: editNote });
      setData((prev) =>
        prev
          ? {
              ...prev,
              items: prev.items.map((i) =>
                i.id === editingItem.id ? { ...i, note: editNote } : i
              ),
            }
          : null
      );
      setEditingItem(null);
      toast({ title: 'Note updated', type: 'success' });
    } catch {
      toast({ title: 'Failed to update note', type: 'error' });
    }
  };

  const toggleSelectAll = () => {
    if (!data?.items) return;
    if (selectedIds.length === data.items.length) {
      setSelectedIds([]);
    } else {
      setSelectedIds(data.items.filter((i) => i.id).map((i) => i.id!));
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header */}
      <div className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <HistoryIcon className="h-6 w-6 text-primary" />
            Prediction History & Trends
          </h1>
          <p className="text-sm text-muted-foreground">
            Audit log of all meteorological inference events with classification filters and 7-day ET trends.
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {isFree && (
            <Badge variant="warning" className="text-xs">
              Free Plan: Last 50 items
            </Badge>
          )}
          <Link to="/reports">
            <Button variant="outline" size="sm" className="flex items-center gap-1.5 text-xs">
              <FileText className="h-3.5 w-3.5" />
              Export & Reports
            </Button>
          </Link>
          <Link to="/batch">
            <Button variant="outline" size="sm" className="flex items-center gap-1.5 text-xs">
              <UploadCloud className="h-3.5 w-3.5" />
              Batch CSV
            </Button>
          </Link>
        </div>
      </div>

      {/* 7-Day ET Trend Chart Card */}
      {stats && stats.trend_7d && stats.trend_7d.length > 0 && (
        <Card>
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <div>
                <CardTitle className="text-sm font-semibold flex items-center gap-1.5">
                  <TrendingUp className="h-4 w-4 text-primary" />
                  Recent Daily Evapotranspiration Trend (ET₀)
                </CardTitle>
                <CardDescription className="text-xs">
                  Mean daily reference evapotranspiration with FAO-56 evaporative demand zones.
                </CardDescription>
              </div>
              <div className="text-right">
                <div className="text-xs text-muted-foreground">Historical Mean</div>
                <div className="text-base font-bold text-foreground">
                  {stats.mean_et.toFixed(2)} mm/day
                </div>
              </div>
            </div>
          </CardHeader>
          <CardContent className="pt-2">
            <EtHistoryLineChart data={stats.trend_7d} height={200} />
          </CardContent>
        </Card>
      )}

      {/* Filter and Bulk Action Controls */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <form onSubmit={handleSearchSubmit} className="flex items-center gap-2 flex-1 max-w-sm">
          <Input
            placeholder="Search notes, tags..."
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            className="text-xs h-9"
          />
          <Button type="submit" variant="secondary" size="sm" className="h-9">
            <Search className="h-3.5 w-3.5" />
          </Button>
        </form>

        <div className="flex flex-wrap items-center gap-2">
          {/* Classification selector */}
          <select
            value={classification}
            onChange={(e) => {
              setClassification(e.target.value);
              setPage(1);
            }}
            className="h-9 rounded-md border border-input bg-card px-2.5 py-1 text-xs text-foreground focus:outline-none focus:ring-1 focus:ring-ring"
          >
            <option value="">All Demand Classes</option>
            <option value="low">Low (&lt;2 mm)</option>
            <option value="moderate">Moderate (2–5 mm)</option>
            <option value="high">High (&gt;5 mm)</option>
          </select>

          {/* Saved toggle button */}
          <Button
            variant={savedOnly ? 'default' : 'outline'}
            size="sm"
            onClick={() => {
              setSavedOnly(!savedOnly);
              setPage(1);
            }}
            className="text-xs h-9 gap-1.5"
          >
            <Bookmark className="h-3.5 w-3.5" />
            {savedOnly ? 'Starred Only' : 'All'}
          </Button>

          {/* Bulk delete action */}
          {selectedIds.length > 0 && (
            <Button
              variant="destructive"
              size="sm"
              onClick={() => setIsBulkConfirmOpen(true)}
              className="text-xs h-9 gap-1.5"
            >
              <Trash2 className="h-3.5 w-3.5" />
              Delete ({selectedIds.length})
            </Button>
          )}
        </div>
      </div>

      {/* Main Table Card */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs">
              <thead className="bg-muted/40 font-medium text-muted-foreground border-b border-border">
                <tr>
                  <th className="p-3 w-8">
                    <input
                      type="checkbox"
                      checked={
                        data?.items &&
                        data.items.length > 0 &&
                        selectedIds.length === data.items.length
                      }
                      onChange={toggleSelectAll}
                      className="rounded accent-primary cursor-pointer"
                    />
                  </th>
                  <th className="p-3">ET₀ (mm/day)</th>
                  <th className="p-3">Classification</th>
                  <th className="p-3">Interval (90%)</th>
                  <th className="p-3">Model</th>
                  <th className="p-3">Date</th>
                  <th className="p-3">Note / Tags</th>
                  <th className="p-3 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-border">
                {isLoading ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground">
                      Loading prediction history...
                    </td>
                  </tr>
                ) : !data?.items || data.items.length === 0 ? (
                  <tr>
                    <td colSpan={8} className="p-8 text-center text-muted-foreground">
                      No matching prediction records found.
                    </td>
                  </tr>
                ) : (
                  data.items.map((item) => (
                    <tr key={item.id} className="hover:bg-muted/20 transition-colors">
                      <td className="p-3">
                        <input
                          type="checkbox"
                          checked={selectedIds.includes(item.id || '')}
                          onChange={(e) => {
                            if (!item.id) return;
                            setSelectedIds((prev) =>
                              e.target.checked
                                ? [...prev, item.id!]
                                : prev.filter((id) => id !== item.id)
                            );
                          }}
                          className="rounded accent-primary cursor-pointer"
                        />
                      </td>
                      <td className="p-3 font-semibold text-primary">
                        {item.et_value.toFixed(2)}
                      </td>
                      <td className="p-3">
                        <Badge
                          variant={
                            item.classification === 'low'
                              ? 'success'
                              : item.classification === 'moderate'
                              ? 'warning'
                              : 'destructive'
                          }
                          className="capitalize text-[10px]"
                        >
                          {item.classification}
                        </Badge>
                      </td>
                      <td className="p-3 text-muted-foreground">
                        [{item.interval_low.toFixed(2)}, {item.interval_high.toFixed(2)}]
                      </td>
                      <td className="p-3">
                        <div className="font-mono text-[11px]">{item.model_version}</div>
                        <div className="text-[10px] text-muted-foreground capitalize">
                          {item.model_algorithm}
                        </div>
                      </td>
                      <td className="p-3 text-muted-foreground whitespace-nowrap">
                        {item.created_at ? new Date(item.created_at).toLocaleDateString() : '—'}
                      </td>
                      <td className="p-3 max-w-xs truncate">
                        <div
                          className="cursor-pointer hover:underline text-muted-foreground"
                          onClick={() => {
                            setEditingItem(item);
                            setEditNote(item.note || '');
                          }}
                        >
                          {item.note || <span className="italic text-muted-foreground/60">+ Add note</span>}
                        </div>
                      </td>
                      <td className="p-3 text-right">
                        <div className="flex items-center justify-end gap-1">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0"
                            onClick={() => handleToggleBookmark(item)}
                          >
                            {item.is_saved ? (
                              <BookmarkCheck className="h-4 w-4 text-primary" />
                            ) : (
                              <Bookmark className="h-4 w-4 text-muted-foreground" />
                            )}
                          </Button>
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-7 w-7 p-0 text-destructive hover:bg-destructive/10"
                            onClick={() => setDeleteTargetId(item.id || null)}
                          >
                            <Trash2 className="h-3.5 w-3.5" />
                          </Button>
                        </div>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>

          {/* Pagination Footer */}
          {data && data.total_pages > 1 && (
            <div className="flex items-center justify-between border-t border-border p-3 text-xs">
              <span className="text-muted-foreground">
                Showing Page {data.page} of {data.total_pages} ({data.total} records)
              </span>
              <div className="flex items-center gap-2">
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  disabled={page <= 1}
                  onClick={() => setPage((p) => Math.max(1, p - 1))}
                >
                  <ChevronLeft className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  className="h-7 px-2"
                  disabled={page >= data.total_pages}
                  onClick={() => setPage((p) => p + 1)}
                >
                  <ChevronRight className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Single Delete Confirm */}
      <ConfirmDialog
        open={deleteTargetId !== null}
        onOpenChange={(op) => !op && setDeleteTargetId(null)}
        title="Delete Prediction Record"
        description="Are you sure you want to delete this prediction? This action cannot be undone."
        confirmText="Delete"
        confirmVariant="destructive"
        onConfirm={handleDeleteSingle}
      />

      {/* Bulk Delete Confirm */}
      <ConfirmDialog
        open={isBulkConfirmOpen}
        onOpenChange={(op) => !op && setIsBulkConfirmOpen(false)}
        title="Bulk Delete Predictions"
        description={`Permanently delete ${selectedIds.length} selected prediction records?`}
        confirmText="Bulk Delete"
        confirmVariant="destructive"
        onConfirm={handleBulkDelete}
      />

      {/* Note Edit Modal */}
      {editingItem && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
          <Card className="w-full max-w-md">
            <CardHeader>
              <CardTitle className="text-base">Edit Prediction Note</CardTitle>
              <CardDescription className="text-xs">
                Observation details for ET₀ {editingItem.et_value.toFixed(2)} mm/day
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <Input
                value={editNote}
                onChange={(e) => setEditNote(e.target.value)}
                placeholder="Observation or field notes..."
              />
              <div className="flex justify-end gap-2">
                <Button variant="ghost" size="sm" onClick={() => setEditingItem(null)}>
                  Cancel
                </Button>
                <Button size="sm" onClick={handleSaveNote}>
                  Save Note
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      )}
    </div>
  );
};
