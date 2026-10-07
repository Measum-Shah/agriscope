import React, { useEffect, useState } from 'react';
import { ToggleLeft, ToggleRight, Plus } from 'lucide-react';
import { adminApi, FeatureFlagItem, AnnouncementItem, SystemLimitsConfig, AdminUserAuditItem } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { useToast } from '../../components/ui/Toast';

export const AdminSystemPage: React.FC = () => {
  const { toast } = useToast();

  // Flags
  const [flags, setFlags] = useState<FeatureFlagItem[]>([]);
  const [flagModalOpen, setFlagModalOpen] = useState(false);
  const [newFlagName, setNewFlagName] = useState('');
  const [newFlagDesc, setNewFlagDesc] = useState('');

  // Announcements
  const [announcements, setAnnouncements] = useState<AnnouncementItem[]>([]);
  const [annModalOpen, setAnnModalOpen] = useState(false);
  const [annTitle, setAnnTitle] = useState('');
  const [annMsg, setAnnMsg] = useState('');
  const [annType, setAnnType] = useState('info');

  // Limits
  const [limits, setLimits] = useState<SystemLimitsConfig | null>(null);
  const [limitsLoading, setLimitsLoading] = useState(false);

  // Global Audit Logs
  const [auditLogs, setAuditLogs] = useState<AdminUserAuditItem[]>([]);

  const loadData = async () => {
    try {
      const [fData, aData, lData, auditData] = await Promise.all([
        adminApi.listFeatureFlags(),
        adminApi.listAnnouncements(),
        adminApi.getSystemLimits(),
        adminApi.listAuditLogs({ size: 30 }),
      ]);
      setFlags(fData);
      setAnnouncements(aData);
      setLimits(lData);
      setAuditLogs(auditData.items);
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to load system settings.' });
    }
  };

  useEffect(() => {
    loadData();
  }, []);

  const handleToggleFlag = async (flag: FeatureFlagItem) => {
    try {
      await adminApi.updateFeatureFlag({
        name: flag.name,
        is_enabled: !flag.is_enabled,
        description: flag.description || undefined,
      });
      toast({ type: 'success', title: 'Flag Updated', description: `${flag.name} toggled.` });
      await loadData();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Flag update failed.' });
    }
  };

  const handleCreateFlag = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.updateFeatureFlag({
        name: newFlagName.trim(),
        is_enabled: false,
        description: newFlagDesc.trim(),
      });
      toast({ type: 'success', title: 'Feature Flag Created', description: newFlagName });
      setFlagModalOpen(false);
      setNewFlagName('');
      setNewFlagDesc('');
      await loadData();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to create feature flag.' });
    }
  };

  const handleToggleAnnouncement = async (id: string, current: boolean) => {
    try {
      await adminApi.toggleAnnouncement(id, !current);
      toast({ type: 'info', title: 'Banner Updated', description: 'Visibility toggled.' });
      await loadData();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Announcement update failed.' });
    }
  };

  const handleCreateAnnouncement = async (e: React.FormEvent) => {
    e.preventDefault();
    try {
      await adminApi.createAnnouncement({
        title: annTitle.trim(),
        message: annMsg.trim(),
        type: annType,
        is_active: true,
      });
      toast({ type: 'success', title: 'Banner Published', description: 'Active for all users.' });
      setAnnModalOpen(false);
      setAnnTitle('');
      setAnnMsg('');
      await loadData();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to create announcement.' });
    }
  };

  const handleSaveLimits = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!limits) return;
    setLimitsLoading(true);
    try {
      const updated = await adminApi.updateSystemLimits(limits);
      setLimits(updated);
      toast({ type: 'success', title: 'Limits Updated', description: 'Global quotas persisted.' });
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Limits update failed.' });
    } finally {
      setLimitsLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">System Governance</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Manage runtime feature toggles, app-wide announcements, global resource quotas, and platform audit history.
        </p>
      </div>

      <Tabs defaultValue="flags" className="w-full">
        <TabsList className="grid w-full grid-cols-4 max-w-xl">
          <TabsTrigger value="flags">Feature Flags</TabsTrigger>
          <TabsTrigger value="announcements">Banners</TabsTrigger>
          <TabsTrigger value="limits">Quotas & Limits</TabsTrigger>
          <TabsTrigger value="audit">Audit Log</TabsTrigger>
        </TabsList>

        {/* Feature Flags */}
        <TabsContent value="flags" className="mt-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-semibold">Dynamic Runtime Toggles</h3>
            <Button size="sm" onClick={() => setFlagModalOpen(true)} className="gap-1">
              <Plus className="h-4 w-4" /> New Flag
            </Button>
          </div>
          <Card>
            <CardContent className="divide-y p-0">
              {flags.map((f) => (
                <div key={f.id} className="flex items-center justify-between p-4">
                  <div>
                    <span className="font-semibold text-sm">{f.name}</span>
                    <p className="text-xs text-muted-foreground">{f.description || 'No description'}</p>
                  </div>
                  <button onClick={() => handleToggleFlag(f)} className="cursor-pointer">
                    {f.is_enabled ? (
                      <ToggleRight className="h-7 w-7 text-primary" />
                    ) : (
                      <ToggleLeft className="h-7 w-7 text-muted-foreground" />
                    )}
                  </button>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Announcements */}
        <TabsContent value="announcements" className="mt-6 space-y-4">
          <div className="flex justify-between items-center">
            <h3 className="text-base font-semibold">App-Wide Announcements & Banners</h3>
            <Button size="sm" onClick={() => setAnnModalOpen(true)} className="gap-1">
              <Plus className="h-4 w-4" /> New Announcement
            </Button>
          </div>
          <Card>
            <CardContent className="divide-y p-0">
              {announcements.map((a) => (
                <div key={a.id} className="flex items-center justify-between p-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-sm">{a.title}</span>
                      <Badge variant={a.type === 'warning' ? 'destructive' : 'secondary'} className="text-[10px] uppercase">
                        {a.type}
                      </Badge>
                    </div>
                    <p className="text-xs text-muted-foreground">{a.message}</p>
                  </div>
                  <Button variant="outline" size="sm" onClick={() => handleToggleAnnouncement(a.id, a.is_active)}>
                    {a.is_active ? 'Active' : 'Hidden'}
                  </Button>
                </div>
              ))}
            </CardContent>
          </Card>
        </TabsContent>

        {/* Global Limits */}
        <TabsContent value="limits" className="mt-6">
          {limits && (
            <Card>
              <CardHeader>
                <CardTitle>Global Quotas and Thresholds</CardTitle>
                <CardDescription>Configure baseline operational caps across plans.</CardDescription>
              </CardHeader>
              <CardContent>
                <form onSubmit={handleSaveLimits} className="space-y-4 max-w-md">
                  <Input
                    label="Free Tier Daily Prediction Limit"
                    type="number"
                    value={limits.free_daily_prediction_limit}
                    onChange={(e) => setLimits({ ...limits, free_daily_prediction_limit: Number(e.target.value) })}
                  />
                  <Input
                    label="Pro Tier Daily Prediction Limit"
                    type="number"
                    value={limits.pro_daily_prediction_limit}
                    onChange={(e) => setLimits({ ...limits, pro_daily_prediction_limit: Number(e.target.value) })}
                  />
                  <Input
                    label="Batch Prediction Max CSV Rows"
                    type="number"
                    value={limits.batch_max_rows}
                    onChange={(e) => setLimits({ ...limits, batch_max_rows: Number(e.target.value) })}
                  />
                  <Button type="submit" loading={limitsLoading}>Save Configuration</Button>
                </form>
              </CardContent>
            </Card>
          )}
        </TabsContent>

        {/* Audit Log */}
        <TabsContent value="audit" className="mt-6 space-y-4">
          <Card>
            <CardHeader>
              <CardTitle>Platform Security & Operational Audit Log</CardTitle>
              <CardDescription>Chronological events across auth, settings, predictions, and admin actions.</CardDescription>
            </CardHeader>
            <CardContent className="p-0">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-muted border-b uppercase font-semibold text-muted-foreground">
                    <tr>
                      <th className="p-3">Action</th>
                      <th className="p-3">Actor</th>
                      <th className="p-3">Target</th>
                      <th className="p-3">Timestamp</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y">
                    {auditLogs.map((l) => (
                      <tr key={l.id} className="hover:bg-muted/20">
                        <td className="p-3 font-semibold text-foreground">{l.action}</td>
                        <td className="p-3 text-muted-foreground">{l.actor}</td>
                        <td className="p-3 font-mono">{l.target || '—'}</td>
                        <td className="p-3 text-muted-foreground">{new Date(l.timestamp).toLocaleString()}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>

      {/* Flag Modal */}
      <Modal open={flagModalOpen} onOpenChange={setFlagModalOpen} title="Create Feature Flag" description="Add a new toggleable feature flag.">
        <form onSubmit={handleCreateFlag} className="space-y-4">
          <Input label="Flag Name" placeholder="e.g. experimental_models" value={newFlagName} onChange={(e) => setNewFlagName(e.target.value)} required />
          <Input label="Description" placeholder="Purpose of this flag..." value={newFlagDesc} onChange={(e) => setNewFlagDesc(e.target.value)} />
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setFlagModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={!newFlagName.trim()}>Create</Button>
          </div>
        </form>
      </Modal>

      {/* Announcement Modal */}
      <Modal open={annModalOpen} onOpenChange={setAnnModalOpen} title="New System Banner" description="Broadcast a banner across the application.">
        <form onSubmit={handleCreateAnnouncement} className="space-y-4">
          <Input label="Banner Title" placeholder="e.g., Scheduled Maintenance" value={annTitle} onChange={(e) => setAnnTitle(e.target.value)} required />
          <Input label="Message" placeholder="Detailed message..." value={annMsg} onChange={(e) => setAnnMsg(e.target.value)} required />
          <div>
            <label className="text-sm font-medium text-foreground block mb-1">Banner Type</label>
            <select className="w-full border rounded p-2 text-sm bg-background" value={annType} onChange={(e) => setAnnType(e.target.value)}>
              <option value="info">Info</option>
              <option value="warning">Warning / Alert</option>
              <option value="maintenance">Maintenance</option>
            </select>
          </div>
          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setAnnModalOpen(false)}>Cancel</Button>
            <Button type="submit" disabled={!annTitle.trim() || !annMsg.trim()}>Publish Banner</Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
