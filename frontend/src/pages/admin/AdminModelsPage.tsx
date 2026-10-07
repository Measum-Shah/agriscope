import React, { useState, useEffect } from 'react';
import { Cpu, Plus, RotateCcw, Check, X, Eye, Radio, Loader2 } from 'lucide-react';
import { Button } from '../../components/ui/Button';
import {
  MLModelItem, listModels, approveModel, rejectModel, rollbackModel,
  toggleShadowMode, getShadowReport, getJobStatus, ShadowReport, TrainingJobProgress,
  compareModels, ModelComparisonResponse
} from '../../api/models';
import { TrainModelModal } from '../../components/admin/TrainModelModal';
import { ModelCardModal } from '../../components/admin/ModelCardModal';
import { ModelDriftTab } from '../../components/admin/ModelDriftTab';
import { ApproveModal, RejectModal } from '../../components/admin/ApproveRejectModals';
import { ModelComparisonMatrix } from '../../components/admin/ModelComparisonMatrix';
import { ShadowReportView } from '../../components/admin/ShadowReportView';

export const AdminModelsPage: React.FC = () => {
  const [models, setModels] = useState<MLModelItem[]>([]);
  const [activeTab, setActiveTab] = useState<'registry' | 'compare' | 'drift' | 'shadow'>('registry');
  const [error, setError] = useState<string | null>(null);

  const [trainModalOpen, setTrainModalOpen] = useState(false);
  const [cardModel, setCardModel] = useState<MLModelItem | null>(null);
  const [approveTarget, setApproveTarget] = useState<MLModelItem | null>(null);
  const [rejectTarget, setRejectTarget] = useState<MLModelItem | null>(null);
  const [shadowReport, setShadowReport] = useState<ShadowReport | null>(null);
  const [activeShadowModel, setActiveShadowModel] = useState<MLModelItem | null>(null);
  const [selectedForCompare, setSelectedForCompare] = useState<string[]>([]);
  const [comparisonResult, setComparisonResult] = useState<ModelComparisonResponse | null>(null);
  const [activeJobId, setActiveJobId] = useState<string | null>(null);
  const [jobProgress, setJobProgress] = useState<TrainingJobProgress | null>(null);

  const fetchModels = async () => {
    try {
      const res = await listModels();
      setModels(res);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Failed to fetch models');
    }
  };

  useEffect(() => { fetchModels(); }, []);

  useEffect(() => {
    if (!activeJobId) return;
    const interval = setInterval(async () => {
      try {
        const prog = await getJobStatus(activeJobId);
        setJobProgress(prog);
        if (prog.state === 'SUCCESS' || prog.state === 'FAILURE') {
          setActiveJobId(null);
          fetchModels();
        }
      } catch { setActiveJobId(null); }
    }, 2000);
    return () => clearInterval(interval);
  }, [activeJobId]);

  const handleApprove = async (force: boolean) => {
    if (!approveTarget) return;
    try {
      await approveModel(approveTarget.id, force);
      setApproveTarget(null);
      fetchModels();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Approval failed'); }
  };

  const handleReject = async (reason: string) => {
    if (!rejectTarget) return;
    try {
      await rejectModel(rejectTarget.id, reason);
      setRejectTarget(null);
      fetchModels();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Rejection failed'); }
  };

  const handleRollback = async () => {
    if (!confirm('Are you sure you want to rollback to the previous active model version?')) return;
    try {
      await rollbackModel();
      fetchModels();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Rollback failed'); }
  };

  const handleShadowToggle = async (m: MLModelItem) => {
    const isEnabled = m.metrics_json?.shadow_mode === true;
    try {
      await toggleShadowMode(m.id, !isEnabled);
      fetchModels();
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Shadow toggle failed'); }
  };

  const handleViewShadowReport = async (m: MLModelItem) => {
    setActiveShadowModel(m);
    setActiveTab('shadow');
    try {
      const rep = await getShadowReport(m.id);
      setShadowReport(rep);
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Could not fetch shadow report'); }
  };

  const handleRunCompare = async () => {
    if (selectedForCompare.length < 2) return;
    try {
      const res = await compareModels(selectedForCompare);
      setComparisonResult(res);
      setActiveTab('compare');
    } catch (e: unknown) { setError(e instanceof Error ? e.message : 'Model comparison failed'); }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b pb-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground flex items-center gap-2">
            <Cpu className="h-6 w-6 text-primary" /> ML Model Registry & Lifecycle
          </h2>
          <p className="text-xs text-muted-foreground mt-1">
            Zero-downtime hot swap, automated metric gates, shadow traffic testing, and drift surveillance.
          </p>
        </div>
        <div className="flex items-center space-x-2">
          <Button variant="outline" size="sm" onClick={handleRollback}>
            <RotateCcw className="mr-1.5 h-3.5 w-3.5" /> Rollback Active
          </Button>
          <Button size="sm" onClick={() => setTrainModalOpen(true)}>
            <Plus className="mr-1.5 h-3.5 w-3.5" /> Train Model
          </Button>
        </div>
      </div>

      {error && <div className="rounded-md bg-destructive/15 p-3 text-xs text-destructive">{error}</div>}

      {jobProgress && (
        <div className="rounded-lg border border-primary/40 bg-primary/5 p-4 text-xs">
          <div className="flex items-center justify-between font-semibold">
            <span className="flex items-center text-primary">
              <Loader2 className="mr-2 h-4 w-4 animate-spin" /> Training: {jobProgress.current_step}
            </span>
            <span>{jobProgress.progress.toFixed(0)}%</span>
          </div>
          <div className="mt-2 h-2 w-full overflow-hidden rounded-full bg-muted">
            <div className="h-full bg-primary transition-all" style={{ width: `${jobProgress.progress}%` }} />
          </div>
        </div>
      )}

      <div className="flex space-x-2 border-b text-xs font-medium">
        <button
          onClick={() => setActiveTab('registry')}
          className={`pb-2.5 px-3 border-b-2 font-semibold transition ${
            activeTab === 'registry' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Model Registry ({models.length})
        </button>
        <button
          onClick={() => { if (selectedForCompare.length >= 2) handleRunCompare(); else setActiveTab('compare'); }}
          className={`pb-2.5 px-3 border-b-2 font-semibold transition ${
            activeTab === 'compare' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Comparison Matrix {selectedForCompare.length > 0 && `(${selectedForCompare.length})`}
        </button>
        <button
          onClick={() => setActiveTab('drift')}
          className={`pb-2.5 px-3 border-b-2 font-semibold transition ${
            activeTab === 'drift' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
          }`}
        >
          Drift Monitoring
        </button>
        {activeShadowModel && (
          <button
            onClick={() => setActiveTab('shadow')}
            className={`pb-2.5 px-3 border-b-2 font-semibold transition ${
              activeTab === 'shadow' ? 'border-primary text-primary' : 'border-transparent text-muted-foreground hover:text-foreground'
            }`}
          >
            Shadow Report ({activeShadowModel.version})
          </button>
        )}
      </div>

      {activeTab === 'registry' && (
        <div className="overflow-hidden rounded-lg border bg-card">
          <table className="w-full text-left text-xs">
            <thead className="border-b bg-muted/50 text-[11px] uppercase text-muted-foreground">
              <tr>
                <th className="p-3 w-8">Comp</th>
                <th className="p-3">Model & Version</th>
                <th className="p-3">Architecture</th>
                <th className="p-3">Status</th>
                <th className="p-3">R² Score</th>
                <th className="p-3">RMSE</th>
                <th className="p-3">Shadow Mode</th>
                <th className="p-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {models.map((m) => {
                const r2 = m.metrics_json?.random_split?.r2;
                const rmse = m.metrics_json?.random_split?.rmse;
                const isChecked = selectedForCompare.includes(m.id);
                const isShadow = m.metrics_json?.shadow_mode === true;
                return (
                  <tr key={m.id} className={`hover:bg-muted/30 ${m.status === 'active' ? 'bg-primary/5 font-medium' : ''}`}>
                    <td className="p-3">
                      <input
                        type="checkbox"
                        checked={isChecked}
                        onChange={() => setSelectedForCompare((prev) => isChecked ? prev.filter((id) => id !== m.id) : [...prev, m.id])}
                        className="rounded text-primary"
                      />
                    </td>
                    <td className="p-3">
                      <div className="font-semibold text-foreground">{m.name}</div>
                      <span className="font-mono text-[10px] text-muted-foreground">{m.version}</span>
                    </td>
                    <td className="p-3 capitalize">{m.algorithm}</td>
                    <td className="p-3">
                      <span className={`inline-block rounded px-2 py-0.5 text-[10px] font-bold uppercase ${
                        m.status === 'active' ? 'bg-green-500/20 text-green-700 dark:text-green-300' :
                        m.status === 'pending_approval' ? 'bg-blue-500/20 text-blue-700 dark:text-blue-300' :
                        m.status === 'rejected' ? 'bg-destructive/20 text-destructive' : 'bg-muted text-muted-foreground'
                      }`}>
                        {m.status}
                      </span>
                    </td>
                    <td className="p-3 font-mono">{r2 !== undefined ? r2.toFixed(3) : '—'}</td>
                    <td className="p-3 font-mono">{rmse !== undefined ? rmse.toFixed(3) : '—'}</td>
                    <td className="p-3">
                      {m.status === 'pending_approval' && (
                        <button
                          onClick={() => handleShadowToggle(m)}
                          className={`rounded px-2 py-1 text-[10px] font-semibold border ${
                            isShadow ? 'border-primary bg-primary/20 text-primary' : 'border-border text-muted-foreground'
                          }`}
                        >
                          <Radio className="inline mr-1 h-3 w-3" /> {isShadow ? 'Enabled' : 'Disabled'}
                        </button>
                      )}
                      {isShadow && (
                        <button onClick={() => handleViewShadowReport(m)} className="ml-2 text-primary hover:underline text-[10px]">
                          Report
                        </button>
                      )}
                    </td>
                    <td className="p-3 text-right space-x-1">
                      <Button variant="ghost" size="sm" data-testid={`card-btn-${m.id}`} onClick={() => setCardModel(m)}>
                        <Eye className="h-3.5 w-3.5 mr-1" /> Card
                      </Button>
                      {m.status === 'pending_approval' && (
                        <>
                          <Button variant="outline" size="sm" onClick={() => setApproveTarget(m)}>
                            <Check className="h-3.5 w-3.5 text-green-600 mr-1" /> Approve
                          </Button>
                          <Button variant="ghost" size="sm" onClick={() => setRejectTarget(m)}>
                            <X className="h-3.5 w-3.5 text-destructive mr-1" /> Reject
                          </Button>
                        </>
                      )}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {activeTab === 'compare' && <ModelComparisonMatrix comparisonResult={comparisonResult} />}
      {activeTab === 'drift' && <ModelDriftTab />}
      {activeTab === 'shadow' && <ShadowReportView shadowReport={shadowReport} />}

      <ApproveModal target={approveTarget} onClose={() => setApproveTarget(null)} onConfirm={handleApprove} />
      <RejectModal target={rejectTarget} onClose={() => setRejectTarget(null)} onConfirm={handleReject} />
      <TrainModelModal
        isOpen={trainModalOpen}
        onClose={() => setTrainModalOpen(false)}
        onTrainingStarted={(tid) => { setActiveJobId(tid); setJobProgress({ task_id: tid, state: 'PROGRESS', progress: 5.0, current_step: 'Queued' }); }}
      />
      <ModelCardModal model={cardModel} onClose={() => setCardModel(null)} />
    </div>
  );
};
