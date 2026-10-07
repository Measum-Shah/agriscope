import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useAuth } from '../../context/AuthContext';
import { usersApi } from '../../api/users';
import {
  updateProfileSchema,
  UpdateProfileFormData,
  changeEmailSchema,
  ChangeEmailFormData,
  changePasswordSchema,
  ChangePasswordFormData,
} from '../../utils/validators';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
} from '../../components/ui/Card';
import { useToast } from '../../components/ui/Toast';

export const ProfileTab: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { toast } = useToast();

  const [profileLoading, setProfileLoading] = useState(false);
  const [emailLoading, setEmailLoading] = useState(false);
  const [passwordLoading, setPasswordLoading] = useState(false);
  const [emailSentNotice, setEmailSentNotice] = useState<string | null>(null);

  // Profile Form
  const {
    register: registerProfile,
    handleSubmit: handleSubmitProfile,
    formState: { errors: profileErrors },
  } = useForm<UpdateProfileFormData>({
    resolver: zodResolver(updateProfileSchema),
    defaultValues: {
      name: user?.name || '',
    },
  });

  const onUpdateProfile = async (data: UpdateProfileFormData) => {
    setProfileLoading(true);
    try {
      await usersApi.updateProfile({ name: data.name });
      await refreshUser();
      toast({
        type: 'success',
        title: 'Profile updated',
        description: 'Your account name has been updated.',
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to update profile';
      toast({
        type: 'error',
        title: 'Update Failed',
        description: errorMsg,
      });
    } finally {
      setProfileLoading(false);
    }
  };

  // Email Change Form
  const {
    register: registerEmail,
    handleSubmit: handleSubmitEmail,
    reset: resetEmail,
    formState: { errors: emailErrors },
  } = useForm<ChangeEmailFormData>({
    resolver: zodResolver(changeEmailSchema),
    defaultValues: {
      new_email: '',
      password: '',
    },
  });

  const onChangeEmail = async (data: ChangeEmailFormData) => {
    setEmailLoading(true);
    setEmailSentNotice(null);
    try {
      await usersApi.changeEmail({
        new_email: data.new_email,
        password: data.password,
      });
      setEmailSentNotice(data.new_email);
      resetEmail();
      toast({
        type: 'info',
        title: 'Confirmation Sent',
        description: `A verification link was sent to ${data.new_email}.`,
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to request email change';
      toast({
        type: 'error',
        title: 'Email Change Failed',
        description: errorMsg,
      });
    } finally {
      setEmailLoading(false);
    }
  };

  // Password Change Form
  const {
    register: registerPassword,
    handleSubmit: handleSubmitPassword,
    reset: resetPassword,
    formState: { errors: passwordErrors },
  } = useForm<ChangePasswordFormData>({
    resolver: zodResolver(changePasswordSchema),
    defaultValues: {
      current_password: '',
      new_password: '',
      confirmPassword: '',
    },
  });

  const onChangePassword = async (data: ChangePasswordFormData) => {
    setPasswordLoading(true);
    try {
      await usersApi.changePassword({
        current_password: data.current_password,
        new_password: data.new_password,
      });
      resetPassword();
      toast({
        type: 'success',
        title: 'Password changed',
        description: 'Your password was updated and other sessions revoked.',
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to change password. Check your current password.';
      toast({
        type: 'error',
        title: 'Password Change Failed',
        description: errorMsg,
      });
    } finally {
      setPasswordLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Basic Profile */}
      <Card>
        <CardHeader>
          <CardTitle>Personal Information</CardTitle>
          <CardDescription>Update your display name and basic account details</CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmitProfile(onUpdateProfile)} className="space-y-4 max-w-lg">
            <Input
              label="Full Name"
              error={profileErrors.name?.message}
              {...registerProfile('name')}
            />
            <Input
              label="Current Email Address"
              value={user?.email || ''}
              disabled
              helperText="To change your email, use the email change section below."
            />
            <Button type="submit" loading={profileLoading}>
              Save Changes
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Change Email */}
      <Card>
        <CardHeader>
          <CardTitle>Change Email Address</CardTitle>
          <CardDescription>
            An activation link will be sent to the new email address to complete verification
          </CardDescription>
        </CardHeader>
        <CardContent>
          {emailSentNotice && (
            <div className="mb-4 rounded-md bg-sky-50 dark:bg-sky-950/60 p-3 text-xs text-sky-800 dark:text-sky-200 border border-sky-500/20">
              A verification email has been dispatched to <strong>{emailSentNotice}</strong>. Your
              current email remains active until the new address is verified.
            </div>
          )}
          <form onSubmit={handleSubmitEmail(onChangeEmail)} className="space-y-4 max-w-lg">
            <Input
              label="New Email Address"
              type="email"
              placeholder="new.email@agri.org"
              error={emailErrors.new_email?.message}
              {...registerEmail('new_email')}
            />
            <Input
              label="Current Password"
              type="password"
              placeholder="Confirm identity with password"
              error={emailErrors.password?.message}
              {...registerEmail('password')}
            />
            <Button type="submit" variant="secondary" loading={emailLoading}>
              Request Email Change
            </Button>
          </form>
        </CardContent>
      </Card>

      {/* Change Password */}
      <Card>
        <CardHeader>
          <CardTitle>Change Password</CardTitle>
          <CardDescription>
            Updating your password will revoke all active sessions on other devices
          </CardDescription>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmitPassword(onChangePassword)} className="space-y-4 max-w-lg">
            <Input
              label="Current Password"
              type="password"
              error={passwordErrors.current_password?.message}
              {...registerPassword('current_password')}
            />
            <Input
              label="New Password"
              type="password"
              helperText="Min 8 characters, 1 uppercase letter, 1 digit"
              error={passwordErrors.new_password?.message}
              {...registerPassword('new_password')}
            />
            <Input
              label="Confirm New Password"
              type="password"
              error={passwordErrors.confirmPassword?.message}
              {...registerPassword('confirmPassword')}
            />
            <Button type="submit" variant="default" loading={passwordLoading}>
              Update Password
            </Button>
          </form>
        </CardContent>
      </Card>
    </div>
  );
};
