import React, { useEffect, useState, useCallback } from 'react';
import { Unlock, LogOut, Trash2, History, CheckCircle, Ban } from 'lucide-react';
import { adminApi, AdminUserItem, AdminUserAuditItem } from '../../api/admin';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import { Card, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { Modal } from '../../components/ui/Modal';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import { useToast } from '../../components/ui/Toast';

export const AdminUsersPage: React.FC = () => {
  const { toast } = useToast();
  const [users, setUsers] = useState<AdminUserItem[]>([]);
  const [search, setSearch] = useState('');
  const [page, setPage] = useState(1);

  // Modals & Dialogs
  const [auditUser, setAuditUser] = useState<AdminUserItem | null>(null);
  const [auditLogs, setAuditLogs] = useState<AdminUserAuditItem[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const [deleteTarget, setDeleteTarget] = useState<AdminUserItem | null>(null);
  const [statusTarget, setStatusTarget] = useState<{ user: AdminUserItem; newStatus: string } | null>(null);

  const loadUsers = useCallback(async () => {
    try {
      const res = await adminApi.listUsers({ search: search.trim() || undefined, page, size: 10 });
      setUsers(res.items);
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to load users.' });
    }
  }, [search, page, toast]);

  useEffect(() => {
    loadUsers();
  }, [loadUsers]);

  const handleRolePlanChange = async (userId: string, role: string, plan: string) => {
    try {
      await adminApi.updateRolePlan(userId, { role, plan });
      toast({ type: 'success', title: 'Updated', description: 'User role & plan saved.' });
      await loadUsers();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Could not update user privileges.' });
    }
  };

  const confirmStatusChange = async () => {
    if (!statusTarget) return;
    try {
      await adminApi.updateStatus(statusTarget.user.id, statusTarget.newStatus);
      toast({ type: 'success', title: 'Status Changed', description: `User marked as ${statusTarget.newStatus}.` });
      setStatusTarget(null);
      await loadUsers();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Status update failed.' });
    }
  };

  const handleUnlock = async (userId: string) => {
    try {
      await adminApi.unlockUser(userId);
      toast({ type: 'success', title: 'User Unlocked', description: 'Lockout removed and failed attempts reset.' });
      await loadUsers();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Unlock failed.' });
    }
  };

  const handleForceLogout = async (userId: string) => {
    try {
      const res = await adminApi.forceLogout(userId);
      toast({ type: 'info', title: 'Sessions Terminated', description: `Revoked ${res.revoked_sessions} session(s).` });
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Force logout failed.' });
    }
  };

  const confirmDelete = async () => {
    if (!deleteTarget) return;
    try {
      await adminApi.deleteUser(deleteTarget.id);
      toast({ type: 'success', title: 'User Deleted', description: 'Account permanently purged.' });
      setDeleteTarget(null);
      await loadUsers();
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Deletion failed.' });
    }
  };

  const openAudit = async (user: AdminUserItem) => {
    setAuditUser(user);
    setAuditLoading(true);
    try {
      const logs = await adminApi.getUserAudit(user.id);
      setAuditLogs(logs);
    } catch {
      toast({ type: 'error', title: 'Error', description: 'Failed to load audit history.' });
    } finally {
      setAuditLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold tracking-tight text-foreground">User Administration</h2>
          <p className="text-sm text-muted-foreground mt-1">
            Manage roles, entitlements, lockout releases, and user session lifecycles.
          </p>
        </div>
        <div className="w-full sm:w-72">
          <Input
            placeholder="Search by name or email..."
            value={search}
            onChange={(e) => { setSearch(e.target.value); setPage(1); }}
          />
        </div>
      </div>

      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-muted/50 border-b text-xs uppercase font-semibold text-muted-foreground">
                <tr>
                  <th className="p-4">User</th>
                  <th className="p-4">Role & Plan</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Security</th>
                  <th className="p-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y">
                {users.map((u) => (
                  <tr key={u.id} className="hover:bg-muted/20">
                    <td className="p-4">
                      <div className="font-medium text-foreground">{u.name}</div>
                      <div className="text-xs text-muted-foreground">{u.email}</div>
                    </td>
                    <td className="p-4 space-y-1">
                      <div className="flex items-center gap-1.5">
                        <select
                          className="text-xs border rounded px-1.5 py-0.5 bg-background"
                          value={u.role}
                          onChange={(e) => handleRolePlanChange(u.id, e.target.value, u.plan)}
                        >
                          <option value="farmer">Farmer</option>
                          <option value="researcher">Researcher</option>
                          <option value="admin">Admin</option>
                        </select>
                        <select
                          className="text-xs border rounded px-1.5 py-0.5 bg-background font-semibold"
                          value={u.plan}
                          onChange={(e) => handleRolePlanChange(u.id, u.role, e.target.value)}
                        >
                          <option value="free">Free</option>
                          <option value="pro">Pro</option>
                          <option value="admin">Admin</option>
                        </select>
                      </div>
                    </td>
                    <td className="p-4">
                      <Badge variant={u.status === 'active' ? 'default' : 'destructive'} className="uppercase text-[10px]">
                        {u.status}
                      </Badge>
                    </td>
                    <td className="p-4 text-xs text-muted-foreground">
                      {u.locked_until ? (
                        <span className="text-destructive font-semibold">Locked</span>
                      ) : (
                        <span>Attempts: {u.failed_attempts}</span>
                      )}
                    </td>
                    <td className="p-4 text-right">
                      <div className="flex items-center justify-end gap-1.5">
                        {u.status === 'active' ? (
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Suspend user"
                            onClick={() => setStatusTarget({ user: u, newStatus: 'suspended' })}
                          >
                            <Ban className="h-3.5 w-3.5 text-amber-500" />
                          </Button>
                        ) : (
                          <Button
                            variant="ghost"
                            size="sm"
                            title="Activate user"
                            onClick={() => setStatusTarget({ user: u, newStatus: 'active' })}
                          >
                            <CheckCircle className="h-3.5 w-3.5 text-emerald-500" />
                          </Button>
                        )}
                        <Button variant="ghost" size="sm" title="Unlock account" onClick={() => handleUnlock(u.id)}>
                          <Unlock className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Force Logout" onClick={() => handleForceLogout(u.id)}>
                          <LogOut className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" title="View Audit Trail" onClick={() => openAudit(u)}>
                          <History className="h-3.5 w-3.5" />
                        </Button>
                        <Button variant="ghost" size="sm" title="Delete Account" onClick={() => setDeleteTarget(u)}>
                          <Trash2 className="h-3.5 w-3.5 text-destructive" />
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </CardContent>
      </Card>

      {/* Audit Log Modal */}
      <Modal
        open={Boolean(auditUser)}
        onOpenChange={(open) => !open && setAuditUser(null)}
        title={`Audit Trail: ${auditUser?.email || ''}`}
        description="Immutable record of security and administrative operations."
        size="lg"
      >
        <div className="max-h-96 overflow-y-auto space-y-2">
          {auditLoading ? (
            <p className="text-center text-sm text-muted-foreground py-4">Loading audit logs...</p>
          ) : auditLogs.length === 0 ? (
            <p className="text-center text-sm text-muted-foreground py-4">No audit events recorded.</p>
          ) : (
            auditLogs.map((l) => (
              <div key={l.id} className="text-xs p-2 rounded border bg-muted/20 flex justify-between">
                <div>
                  <span className="font-semibold text-foreground">{l.action}</span>
                  <span className="text-muted-foreground ml-2">by {l.actor}</span>
                </div>
                <span className="text-muted-foreground">{new Date(l.timestamp).toLocaleString()}</span>
              </div>
            ))
          )}
        </div>
      </Modal>

      {/* Confirm Status Change */}
      <ConfirmDialog
        open={Boolean(statusTarget)}
        onOpenChange={(open) => !open && setStatusTarget(null)}
        title="Confirm Status Change"
        description={`Are you sure you want to change status of ${statusTarget?.user.email} to ${statusTarget?.newStatus}?`}
        onConfirm={confirmStatusChange}
      />

      {/* Confirm Deletion */}
      <ConfirmDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => !open && setDeleteTarget(null)}
        title="Permanently Delete User"
        description={`This action will permanently delete user ${deleteTarget?.email} and cannot be undone.`}
        confirmVariant="destructive"
        onConfirm={confirmDelete}
      />
    </div>
  );
};
