import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useNavigate } from 'react-router-dom';
import { Download, AlertOctagon } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../api/users';
import { deleteAccountSchema, DeleteAccountFormData } from '../../utils/validators';
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
import { Badge } from '../../components/ui/Badge';
import { useToast } from '../../components/ui/Toast';

export const AccountTab: React.FC = () => {
  const { user, entitlements, logout } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

  const [exportLoading, setExportLoading] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [deleteLoading, setDeleteLoading] = useState(false);

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<DeleteAccountFormData>({
    resolver: zodResolver(deleteAccountSchema),
    defaultValues: {
      password: '',
      confirmText: '' as unknown as 'DELETE',
    },
  });

  const handleExportData = async () => {
    setExportLoading(true);
    try {
      const data = await usersApi.exportData();
      const blob = new Blob([JSON.stringify(data, null, 2)], {
        type: 'application/json',
      });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `agriscope-export-${user?.id || 'account'}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);

      toast({
        type: 'success',
        title: 'Export Generated',
        description: 'Your account data has been downloaded as JSON.',
      });
    } catch {
      toast({
        type: 'error',
        title: 'Export Failed',
        description: 'Unable to package account data. Please try again.',
      });
    } finally {
      setExportLoading(false);
    }
  };

  const handleDeleteAccount = async (data: DeleteAccountFormData) => {
    setDeleteLoading(true);
    try {
      await usersApi.deleteAccount(data.password);
      toast({
        type: 'info',
        title: 'Account Deleted',
        description: 'Your account has been deleted and sessions terminated.',
      });
      await logout();
      navigate('/login');
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Incorrect password.';
      toast({
        type: 'error',
        title: 'Deletion Failed',
        description: errorMsg,
      });
    } finally {
      setDeleteLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Current Plan Overview */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle>Subscription Plan & Entitlements</CardTitle>
              <CardDescription>
                Your current tier limits, inference quotas, and unlocked features
              </CardDescription>
            </div>
            <Badge variant="default" className="uppercase text-xs px-3 py-1">
              {entitlements?.plan || user?.plan || 'Free'} Tier
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="grid gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Daily Prediction Quota</p>
              <p className="text-2xl font-bold text-foreground mt-1">
                {entitlements?.daily_prediction_limit === null
                  ? 'Unlimited'
                  : `${entitlements?.predictions_used_today || 0} / ${
                      entitlements?.daily_prediction_limit || 10
                    }`}
              </p>
              <p className="text-xs text-muted-foreground mt-1">Resets daily at 00:00 UTC</p>
            </div>

            <div className="rounded-lg border border-border p-4">
              <p className="text-xs text-muted-foreground">Account Status</p>
              <p className="text-lg font-semibold text-emerald-600 dark:text-emerald-400 mt-1 capitalize">
                {user?.status || 'Active'}
              </p>
              <p className="text-xs text-muted-foreground mt-1">
                Registered on{' '}
                {user?.registration_date
                  ? new Date(user.registration_date).toLocaleDateString()
                  : 'N/A'}
              </p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* GDPR Data Export */}
      <Card>
        <CardHeader>
          <CardTitle>GDPR Data Export</CardTitle>
          <CardDescription>
            Download a portable machine-readable copy of your profile, fields, predictions, and logs
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-lg border border-border p-4">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">
                Export Account Archive (.json)
              </p>
              <p className="text-xs text-muted-foreground">
                Includes your registered details, active and past sessions, and security history.
              </p>
            </div>
            <Button
              variant="outline"
              size="sm"
              className="gap-2"
              onClick={handleExportData}
              loading={exportLoading}
            >
              <Download className="h-4 w-4" />
              Download Archive
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Danger Zone */}
      <Card className="border-destructive/30">
        <CardHeader>
          <div className="flex items-center gap-2 text-destructive">
            <AlertOctagon className="h-5 w-5" />
            <CardTitle className="text-destructive">Danger Zone</CardTitle>
          </div>
          <CardDescription>
            Irreversible actions regarding your account data and access
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center justify-between rounded-lg border border-destructive/20 bg-destructive/5 p-4">
            <div className="space-y-1">
              <p className="text-sm font-semibold text-foreground">Delete AgriScope Account</p>
              <p className="text-xs text-muted-foreground">
                Permanently deactivates your account, revokes sessions, and queues personal data for
                purging.
              </p>
            </div>
            <Button
              variant="destructive"
              size="sm"
              onClick={() => {
                reset();
                setDeleteModalOpen(true);
              }}
            >
              Delete Account
            </Button>
          </div>
        </CardContent>
      </Card>

      {/* Deletion Confirmation Modal */}
      <Modal
        open={deleteModalOpen}
        onOpenChange={setDeleteModalOpen}
        title="Delete AgriScope Account"
        description="This action is permanent and cannot be undone. Please confirm by providing your password and typing DELETE."
        size="md"
      >
        <form onSubmit={handleSubmit(handleDeleteAccount)} className="space-y-4">
          <Input
            label="Current Password"
            type="password"
            error={errors.password?.message}
            {...register('password')}
          />

          <Input
            label="Type DELETE to confirm"
            placeholder="DELETE"
            error={errors.confirmText?.message}
            {...register('confirmText')}
          />

          <div className="flex justify-end gap-2 pt-2">
            <Button type="button" variant="outline" onClick={() => setDeleteModalOpen(false)}>
              Cancel
            </Button>
            <Button type="submit" variant="destructive" loading={deleteLoading}>
              Permanently Delete Account
            </Button>
          </div>
        </form>
      </Modal>
    </div>
  );
};
