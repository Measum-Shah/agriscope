import React, { useState, useEffect, useCallback } from 'react';
import { ShieldCheck, ShieldAlert, Smartphone, Copy, Check, Trash2 } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../api/users';
import { authApi } from '../../api/auth';
import { SessionInfo, AuditLogItem, TOTPSetupResponse } from '../../types/auth';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../components/ui/Card';
import { Modal } from '../../components/ui/Modal';
import { ConfirmDialog } from '../../components/ui/ConfirmDialog';
import {
  Table,
  TableHeader,
  TableBody,
  TableRow,
  TableHead,
  TableCell,
} from '../../components/ui/Table';
import { Badge } from '../../components/ui/Badge';
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';

export const SecurityTab: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { toast } = useToast();

  // 2FA state
  const [setupModalOpen, setSetupModalOpen] = useState(false);
  const [setupData, setSetupData] = useState<TOTPSetupResponse | null>(null);
  const [setupLoading, setSetupLoading] = useState(false);
  const [verifyCode, setVerifyCode] = useState('');
  const [verifyLoading, setVerifyLoading] = useState(false);
  const [recoveryCodes, setRecoveryCodes] = useState<string[] | null>(null);
  const [copiedCodes, setCopiedCodes] = useState(false);

  // Disable 2FA state
  const [disableModalOpen, setDisableModalOpen] = useState(false);
  const [disablePassword, setDisablePassword] = useState('');
  const [disableLoading, setDisableLoading] = useState(false);

  // Sessions state
  const [sessions, setSessions] = useState<SessionInfo[]>([]);
  const [sessionsLoading, setSessionsLoading] = useState(false);
  const [sessionToRevoke, setSessionToRevoke] = useState<string | null>(null);

  // Audit logs state
  const [auditLogs, setAuditLogs] = useState<AuditLogItem[]>([]);
  const [auditLoading, setAuditLoading] = useState(false);

  const fetchSessions = useCallback(async () => {
    setSessionsLoading(true);
    try {
      const data = await authApi.getSessions();
      setSessions(data);
    } catch {
      // ignore
    } finally {
      setSessionsLoading(false);
    }
  }, []);

  const fetchAuditLogs = useCallback(async () => {
    setAuditLoading(true);
    try {
      const data = await usersApi.getAuditLogs();
      setAuditLogs(data);
    } catch {
      // ignore
    } finally {
      setAuditLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSessions();
    fetchAuditLogs();
  }, [fetchSessions, fetchAuditLogs]);

  // Start 2FA setup
  const handleStartSetup = async () => {
    setSetupLoading(true);
    setVerifyCode('');
    setRecoveryCodes(null);
    try {
      const res = await usersApi.setup2FA();
      setSetupData(res);
      setSetupModalOpen(true);
    } catch (err: unknown) {
      toast({
        type: 'error',
        title: '2FA Setup Failed',
        description:
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Unable to generate 2FA secret.',
      });
    } finally {
      setSetupLoading(false);
    }
  };

  // Verify and enable 2FA
  const handleVerify2FA = async () => {
    if (!verifyCode.trim()) return;
    setVerifyLoading(true);
    try {
      const res = await usersApi.verify2FA(verifyCode.trim());
      setRecoveryCodes(res.recovery_codes);
      await refreshUser();
      toast({
        type: 'success',
        title: 'Two-Factor Authentication Enabled',
        description: 'Save your backup recovery codes in a secure location.',
      });
    } catch (err: unknown) {
      toast({
        type: 'error',
        title: 'Invalid Code',
        description:
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'The 6-digit authentication code was incorrect.',
      });
    } finally {
      setVerifyLoading(false);
    }
  };

  // Disable 2FA
  const handleDisable2FA = async () => {
    if (!disablePassword) return;
    setDisableLoading(true);
    try {
      await usersApi.disable2FA({ password: disablePassword });
      setDisableModalOpen(false);
      setDisablePassword('');
      await refreshUser();
      toast({
        type: 'success',
        title: '2FA Disabled',
        description: 'Two-factor authentication has been turned off.',
      });
    } catch (err: unknown) {
      toast({
        type: 'error',
        title: 'Failed to disable 2FA',
        description:
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Incorrect password.',
      });
    } finally {
      setDisableLoading(false);
    }
  };

  // Revoke session
  const handleRevokeSession = async () => {
    if (!sessionToRevoke) return;
    try {
      await authApi.revokeSession(sessionToRevoke);
      toast({
        type: 'success',
        title: 'Session Revoked',
        description: 'The selected device session has been invalidated.',
      });
      setSessionToRevoke(null);
      await fetchSessions();
    } catch {
      toast({
        type: 'error',
        title: 'Error',
        description: 'Failed to revoke session.',
      });
    }
  };

  const handleCopyCodes = () => {
    if (recoveryCodes) {
      navigator.clipboard.writeText(recoveryCodes.join('\n'));
      setCopiedCodes(true);
      setTimeout(() => setCopiedCodes(false), 2000);
      toast({
        type: 'info',
        title: 'Copied',
        description: 'Recovery codes copied to clipboard.',
      });
    }
  };

  return (
    <div className="space-y-6">
      {/* 2FA Configuration */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle className="flex items-center gap-2">
                <Smartphone className="h-5 w-5 text-primary" />
                Two-Factor Authentication (TOTP)
              </CardTitle>
              <CardDescription>
                Add an extra layer of security using an authenticator app (Google Authenticator,
                Authy, etc.)
              </CardDescription>
            </div>
            {user?.totp_enabled ? (
              <Badge variant="success" className="gap-1 px-3 py-1">
                <ShieldCheck className="h-3.5 w-3.5" />
                Enabled
              </Badge>
            ) : (
              <Badge variant="warning" className="gap-1 px-3 py-1">
                <ShieldAlert className="h-3.5 w-3.5" />
                Disabled
              </Badge>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {user?.totp_enabled ? (
            <div className="flex items-center justify-between rounded-lg border border-border p-4 bg-muted/30">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-foreground">
                  Your account is protected by 2FA
                </p>
                <p className="text-xs text-muted-foreground">
                  Signing in requires both your password and an authenticator verification code.
                </p>
              </div>
              <Button variant="destructive" size="sm" onClick={() => setDisableModalOpen(true)}>
                Disable 2FA
              </Button>
            </div>
          ) : (
            <div className="flex items-center justify-between rounded-lg border border-dashed border-border p-4">
              <div className="space-y-1">
                <p className="text-sm font-semibold text-foreground">
                  Two-factor authentication is not configured
                </p>
                <p className="text-xs text-muted-foreground">
                  Protect your agricultural data and models from unauthorized credential stuffing.
                </p>
              </div>
              <Button variant="default" size="sm" onClick={handleStartSetup} loading={setupLoading}>
                Configure 2FA
              </Button>
            </div>
          )}
        </CardContent>
      </Card>

      {/* 2FA Setup Modal */}
      <Modal
        open={setupModalOpen}
        onOpenChange={setSetupModalOpen}
        title={recoveryCodes ? 'Backup Recovery Codes' : 'Configure Two-Factor Authenticator'}
        description={
          recoveryCodes
            ? 'Store these one-time recovery codes in a secure place. Each can be used once if you lose device access.'
            : 'Scan the QR code below using your authenticator application, then enter the 6-digit confirmation code.'
        }
        size="md"
      >
        {!recoveryCodes ? (
          <div className="space-y-4">
            {setupData && (
              <>
                <div className="flex justify-center p-3 bg-white rounded-lg border w-fit mx-auto">
                  <img
                    src={setupData.qr_code_base64}
                    alt="AgriScope 2FA QR Code"
                    className="h-44 w-44"
                  />
                </div>
                <div className="text-center">
                  <p className="text-xs text-muted-foreground">Manual Setup Key:</p>
                  <code className="text-xs font-mono font-semibold bg-muted px-2 py-1 rounded select-all">
                    {setupData.secret}
                  </code>
                </div>
                <div className="space-y-2">
                  <Input
                    label="6-Digit Verification Code"
                    placeholder="123456"
                    maxLength={6}
                    value={verifyCode}
                    onChange={(e) => setVerifyCode(e.target.value)}
                    helperText="Enter the code shown in your authenticator app"
                  />
                  <Button
                    className="w-full"
                    onClick={handleVerify2FA}
                    loading={verifyLoading}
                    disabled={verifyCode.length < 6}
                  >
                    Verify & Activate 2FA
                  </Button>
                </div>
              </>
            )}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-2 bg-muted/60 p-4 rounded-lg font-mono text-xs">
              {recoveryCodes.map((code, idx) => (
                <div key={idx} className="p-1 bg-card rounded text-center border">
                  {code}
                </div>
              ))}
            </div>
            <div className="flex gap-2">
              <Button variant="outline" className="w-full gap-2 text-xs" onClick={handleCopyCodes}>
                {copiedCodes ? <Check className="h-4 w-4" /> : <Copy className="h-4 w-4" />}
                {copiedCodes ? 'Copied' : 'Copy All Codes'}
              </Button>
              <Button
                variant="default"
                className="w-full text-xs"
                onClick={() => setSetupModalOpen(false)}
              >
                Done
              </Button>
            </div>
          </div>
        )}
      </Modal>

      {/* Disable 2FA Modal */}
      <Modal
        open={disableModalOpen}
        onOpenChange={setDisableModalOpen}
        title="Disable Two-Factor Authentication"
        description="Please confirm your account password to remove two-factor protection."
        size="sm"
      >
        <div className="space-y-4">
          <Input
            label="Password"
            type="password"
            placeholder="Account password"
            value={disablePassword}
            onChange={(e) => setDisablePassword(e.target.value)}
          />
          <div className="flex justify-end gap-2">
            <Button variant="outline" onClick={() => setDisableModalOpen(false)}>
              Cancel
            </Button>
            <Button
              variant="destructive"
              onClick={handleDisable2FA}
              loading={disableLoading}
              disabled={!disablePassword}
            >
              Confirm Disable
            </Button>
          </div>
        </div>
      </Modal>

      {/* Active Sessions */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle>Active Device Sessions</CardTitle>
              <CardDescription>
                Devices and browsers currently authenticated to your account
              </CardDescription>
            </div>
            <Button
              variant="outline"
              size="sm"
              onClick={async () => {
                await authApi.logoutAll();
                toast({
                  type: 'info',
                  title: 'All sessions logged out',
                  description: 'All other active sessions have been terminated.',
                });
                await fetchSessions();
              }}
            >
              Log Out All Other Devices
            </Button>
          </div>
        </CardHeader>
        <CardContent>
          {sessionsLoading ? (
            <div className="flex justify-center py-6">
              <Spinner size="md" />
            </div>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Device / User Agent</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Started</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Action</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {sessions.map((sess) => (
                  <TableRow key={sess.id}>
                    <TableCell className="font-mono text-xs max-w-xs truncate">
                      {sess.user_agent || 'Unknown Client'}
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {sess.ip_address || '127.0.0.1'}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {new Date(sess.created_at).toLocaleString()}
                    </TableCell>
                    <TableCell>
                      {sess.is_current ? (
                        <Badge variant="success">Current Session</Badge>
                      ) : (
                        <Badge variant="outline">Active</Badge>
                      )}
                    </TableCell>
                    <TableCell className="text-right">
                      {!sess.is_current && (
                        <Button
                          variant="ghost"
                          size="sm"
                          className="text-destructive hover:bg-destructive/10"
                          onClick={() => setSessionToRevoke(sess.id)}
                        >
                          <Trash2 className="h-3.5 w-3.5" />
                        </Button>
                      )}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>

      {/* Revoke Session Confirm Dialog */}
      <ConfirmDialog
        open={!!sessionToRevoke}
        onOpenChange={(open) => !open && setSessionToRevoke(null)}
        title="Revoke Session"
        description="Are you sure you want to terminate this device session? The user will be required to log in again."
        confirmText="Revoke Session"
        confirmVariant="destructive"
        onConfirm={handleRevokeSession}
      />

      {/* Security Audit Log */}
      <Card>
        <CardHeader>
          <CardTitle>Security Audit History</CardTitle>
          <CardDescription>
            Chronological record of account events, authentication, and security modifications
          </CardDescription>
        </CardHeader>
        <CardContent>
          {auditLoading ? (
            <div className="flex justify-center py-6">
              <Spinner size="md" />
            </div>
          ) : auditLogs.length === 0 ? (
            <p className="text-xs text-muted-foreground py-4 text-center">
              No recent security logs recorded.
            </p>
          ) : (
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Event Action</TableHead>
                  <TableHead>IP Address</TableHead>
                  <TableHead>Target</TableHead>
                  <TableHead className="text-right">Timestamp</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {auditLogs.slice(0, 15).map((log) => (
                  <TableRow key={log.id}>
                    <TableCell className="font-medium text-xs">
                      <Badge variant="outline" className="font-mono text-[11px]">
                        {log.action}
                      </Badge>
                    </TableCell>
                    <TableCell className="font-mono text-xs">
                      {log.ip_address || '127.0.0.1'}
                    </TableCell>
                    <TableCell className="text-xs text-muted-foreground">
                      {log.target || user?.email}
                    </TableCell>
                    <TableCell className="text-right text-xs text-muted-foreground">
                      {new Date(log.timestamp).toLocaleString()}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          )}
        </CardContent>
      </Card>
    </div>
  );
};
