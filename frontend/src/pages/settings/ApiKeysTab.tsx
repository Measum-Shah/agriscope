import React, { useState, useEffect, useCallback } from 'react';
import { Plus, Trash2, ShieldAlert, Copy, Check, BarChart2 } from 'lucide-react';
import { apiKeysApi, ApiKeyItem, ApiKeyCreatedResponse, ApiKeyUsageStats } from '../../api/apiKeys';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { Badge } from '../../components/ui/Badge';
import { useToast } from '../../components/ui/Toast';

export const ApiKeysTab: React.FC = () => {
  const { user, entitlements } = useAuth();
  const { toast } = useToast();

  const [keys, setKeys] = useState<ApiKeyItem[]>([]);
  const [loading, setLoading] = useState(false);
  const [createModalOpen, setCreateModalOpen] = useState(false);
  const [createdKeyData, setCreatedKeyData] = useState<ApiKeyCreatedResponse | null>(null);
  const [newKeyName, setNewKeyName] = useState('');
  const [selectedScopes, setSelectedScopes] = useState<string[]>(['predict:read']);
  const [creating, setCreating] = useState(false);
  const [copied, setCopied] = useState(false);

  // Usage modal
  const [usageModalOpen, setUsageModalOpen] = useState(false);
  const [activeUsage, setActiveUsage] = useState<ApiKeyUsageStats | null>(null);
  const [usageLoading, setUsageLoading] = useState(false);

  const isProOrAdmin = Boolean(
    entitlements?.features?.api_access ||
    user?.plan === 'pro' ||
    user?.plan === 'admin'
  );

  const loadKeys = useCallback(async () => {
    if (!isProOrAdmin) return;
    setLoading(true);
    try {
      const data = await apiKeysApi.list();
      setKeys(data);
    } catch {
      toast({
        type: 'error',
        title: 'Error',
        description: 'Failed to load API keys.',
      });
    } finally {
      setLoading(false);
    }
  }, [isProOrAdmin, toast]);

  useEffect(() => {
    loadKeys();
  }, [loadKeys]);

  const handleCreateKey = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newKeyName.trim()) return;

    setCreating(true);
    try {
      const res = await apiKeysApi.create({
        name: newKeyName.trim(),
        scopes: selectedScopes,
      });
      setCreatedKeyData(res);
      setNewKeyName('');
      setSelectedScopes(['predict:read']);
      await loadKeys();
    } catch (err: unknown) {
      const msg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to generate API key.';
      toast({
        type: 'error',
        title: 'Error',
        description: msg,
      });
    } finally {
      setCreating(false);
    }
  };

  const handleRevoke = async (id: string, name: string) => {
    if (!window.confirm(`Are you sure you want to revoke key "${name}"? This cannot be undone.`)) {
      return;
    }
    try {
      await apiKeysApi.revoke(id);
      toast({
        type: 'success',
        title: 'Key Revoked',
        description: `API key ${name} was deactivated.`,
      });
      await loadKeys();
    } catch {
      toast({
        type: 'error',
        title: 'Revoke Failed',
        description: 'Unable to revoke API key.',
      });
    }
  };

  const handleViewUsage = async (id: string) => {
    setUsageLoading(true);
    setUsageModalOpen(true);
    try {
      const stats = await apiKeysApi.getUsage(id);
      setActiveUsage(stats);
    } catch {
      toast({
        type: 'error',
        title: 'Error',
        description: 'Unable to fetch usage analytics for key.',
      });
      setUsageModalOpen(false);
    } finally {
      setUsageLoading(false);
    }
  };

  const copyToClipboard = () => {
    if (!createdKeyData?.raw_key) return;
    navigator.clipboard.writeText(createdKeyData.raw_key);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const toggleScope = (scope: string) => {
    setSelectedScopes((prev) =>
      prev.includes(scope) ? prev.filter((s) => s !== scope) : [...prev, scope]
    );
  };

  if (!isProOrAdmin) {
    return (
      <Card className="border-amber-500/30 bg-amber-500/5">
        <CardContent className="pt-6">
          <div className="flex flex-col items-center justify-center text-center p-6 space-y-4">
            <div className="rounded-full bg-amber-500/20 p-3 text-amber-600 dark:text-amber-400">
              <ShieldAlert className="h-8 w-8" />
            </div>
            <div className="space-y-1">
              <h3 className="text-lg font-semibold">Researcher API Keys (Pro Feature)</h3>
              <p className="text-sm text-muted-foreground max-w-md">
                Programmatic REST access with custom scopes, high rate limits, and batch prediction endpoints is reserved for Pro and Enterprise subscribers.
              </p>
            </div>
          </div>
        </CardContent>
      </Card>
    );
  }

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Researcher API Keys</CardTitle>
            <CardDescription>
              Generate secret keys to query AgriScope ML models, field ET time series, and batch jobs via the public REST API.
            </CardDescription>
          </div>
          <Button onClick={() => { setCreatedKeyData(null); setCreateModalOpen(true); }} className="gap-2">
            <Plus className="h-4 w-4" />
            Generate New Key
          </Button>
        </CardHeader>
        <CardContent>
          {loading ? (
            <p className="text-sm text-muted-foreground py-6 text-center">Loading API keys...</p>
          ) : keys.length === 0 ? (
            <div className="text-center py-8 text-muted-foreground text-sm border border-dashed rounded-lg">
              No API keys found. Click "Generate New Key" to create your first researcher access token.
            </div>
          ) : (
            <div className="divide-y divide-border rounded-lg border border-border">
              {keys.map((k) => (
                <div key={k.id} className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 gap-4">
                  <div className="space-y-1">
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-foreground text-sm">{k.name}</span>
                      <code className="text-xs bg-muted px-1.5 py-0.5 rounded font-mono text-muted-foreground">
                        {k.key_prefix}...
                      </code>
                      <Badge variant={k.is_active ? 'default' : 'secondary'} className="text-[10px] uppercase">
                        {k.is_active ? 'Active' : 'Revoked'}
                      </Badge>
                    </div>
                    <div className="flex flex-wrap gap-1 pt-1">
                      {k.scopes.map((s) => (
                        <span key={s} className="text-[10px] bg-secondary/80 text-secondary-foreground px-1.5 py-0.5 rounded">
                          {s}
                        </span>
                      ))}
                    </div>
                    <p className="text-xs text-muted-foreground pt-1">
                      Created: {new Date(k.created_at).toLocaleDateString()} • Last used: {k.last_used_at ? new Date(k.last_used_at).toLocaleDateString() : 'Never'}
                    </p>
                  </div>
                  <div className="flex items-center gap-2 self-end sm:self-center">
                    <Button variant="outline" size="sm" onClick={() => handleViewUsage(k.id)} className="gap-1">
                      <BarChart2 className="h-3.5 w-3.5" />
                      Usage
                    </Button>
                    {k.is_active && (
                      <Button variant="destructive" size="sm" onClick={() => handleRevoke(k.id, k.name)} className="gap-1">
                        <Trash2 className="h-3.5 w-3.5" />
                        Revoke
                      </Button>
                    )}
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Create Key Modal */}
      <Modal
        open={createModalOpen}
        onOpenChange={(open) => {
          if (!open) setCreatedKeyData(null);
          setCreateModalOpen(open);
        }}
        title={createdKeyData ? 'API Key Generated' : 'Create Researcher API Key'}
        description={
          createdKeyData
            ? 'Save this key now. For security purposes, you will not be able to view it again.'
            : 'Provide a name and select allowed scopes for this API key.'
        }
        size="md"
      >
        {createdKeyData ? (
          <div className="space-y-4">
            <div className="p-3 bg-muted rounded-md border font-mono text-sm break-all flex items-center justify-between gap-2">
              <span className="text-foreground select-all">{createdKeyData.raw_key}</span>
              <Button size="sm" variant="ghost" onClick={copyToClipboard} className="shrink-0">
                {copied ? <Check className="h-4 w-4 text-emerald-500" /> : <Copy className="h-4 w-4" />}
              </Button>
            </div>
            <p className="text-xs text-destructive font-medium">
              ⚠️ {createdKeyData.warning}
            </p>
            <div className="flex justify-end pt-2">
              <Button onClick={() => setCreateModalOpen(false)}>Done</Button>
            </div>
          </div>
        ) : (
          <form onSubmit={handleCreateKey} className="space-y-4">
            <Input
              label="Key Name / Identifier"
              placeholder="e.g., Drone Telemetry Ingestion"
              value={newKeyName}
              onChange={(e) => setNewKeyName(e.target.value)}
              required
            />

            <div>
              <label className="text-sm font-medium text-foreground block mb-2">Allowed Scopes</label>
              <div className="space-y-2">
                {[
                  { id: 'predict:read', label: 'predict:read — Query single ET0 inference models' },
                  { id: 'batch:write', label: 'batch:write — Submit async CSV prediction jobs' },
                  { id: 'weather:read', label: 'weather:read — Query weather coordinates prefill' },
                  { id: 'fields:read', label: 'fields:read — Query field polygons & ET time series' },
                ].map((s) => (
                  <label key={s.id} className="flex items-center gap-2 text-sm text-foreground cursor-pointer">
                    <input
                      type="checkbox"
                      className="rounded border-border"
                      checked={selectedScopes.includes(s.id)}
                      onChange={() => toggleScope(s.id)}
                    />
                    <span>{s.label}</span>
                  </label>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <Button type="button" variant="outline" onClick={() => setCreateModalOpen(false)}>
                Cancel
              </Button>
              <Button type="submit" loading={creating} disabled={!newKeyName.trim()}>
                Generate Key
              </Button>
            </div>
          </form>
        )}
      </Modal>

      {/* Usage Analytics Modal */}
      <Modal
        open={usageModalOpen}
        onOpenChange={setUsageModalOpen}
        title="API Key Usage Statistics"
        description="Daily request consumption and rate metrics."
        size="md"
      >
        {usageLoading || !activeUsage ? (
          <p className="text-sm text-muted-foreground py-4 text-center">Loading metrics...</p>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 text-sm">
              <div className="p-3 border rounded bg-muted/40">
                <span className="text-muted-foreground text-xs block">Requests Today</span>
                <span className="text-xl font-bold">{activeUsage.requests_today} / {activeUsage.daily_limit}</span>
              </div>
              <div className="p-3 border rounded bg-muted/40">
                <span className="text-muted-foreground text-xs block">Rate Limit</span>
                <span className="text-xl font-bold">{activeUsage.rate_limit_per_min} req / min</span>
              </div>
            </div>
            <div>
              <h4 className="text-xs font-semibold uppercase text-muted-foreground mb-2">Endpoints Called</h4>
              {Object.keys(activeUsage.endpoints).length === 0 ? (
                <p className="text-xs text-muted-foreground italic">No endpoint activity recorded yet.</p>
              ) : (
                <div className="space-y-1">
                  {Object.entries(activeUsage.endpoints).map(([ep, count]) => (
                    <div key={ep} className="flex justify-between text-xs py-1 border-b">
                      <code>{ep}</code>
                      <span className="font-semibold">{count}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
            <div className="flex justify-end pt-2">
              <Button variant="outline" onClick={() => setUsageModalOpen(false)}>Close</Button>
            </div>
          </div>
        )}
      </Modal>
    </div>
  );
};
