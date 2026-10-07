import React, { useState } from 'react';
import { useSearchParams, Link, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { LockKeyhole, CheckCircle2 } from 'lucide-react';
import { authApi } from '../../api/auth';
import { resetPasswordSchema, ResetPasswordFormData } from '../../utils/validators';
import { Button } from '../../components/ui/Button';
import { Input } from '../../components/ui/Input';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../../components/ui/Card';
import { useToast } from '../../components/ui/Toast';

export const ResetPasswordPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const tokenFromQuery = searchParams.get('token') || '';
  const [token, setToken] = useState(tokenFromQuery);
  const navigate = useNavigate();
  const { toast } = useToast();

  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormData>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      new_password: '',
      confirmPassword: '',
    },
  });

  const onSubmit = async (data: ResetPasswordFormData) => {
    if (!token.trim()) {
      toast({
        type: 'error',
        title: 'Missing Token',
        description: 'A reset token is required. Check the link in your email.',
      });
      return;
    }

    setLoading(true);
    try {
      await authApi.resetPassword({
        token: token.trim(),
        new_password: data.new_password,
      });
      setSuccess(true);
      toast({
        type: 'success',
        title: 'Password updated',
        description: 'All active sessions have been invalidated. Please sign in.',
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Reset token is invalid or has expired.';
      toast({
        type: 'error',
        title: 'Reset Failed',
        description: errorMsg,
      });
    } finally {
      setLoading(false);
    }
  };

  if (success) {
    return (
      <Card className="shadow-lg border-border text-center">
        <CardHeader className="space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">
            Password Reset Complete
          </CardTitle>
          <CardDescription>
            Your account credentials were changed successfully. All previous sessions have been
            securely logged out.
          </CardDescription>
        </CardHeader>
        <CardFooter className="flex justify-center">
          <Button className="w-full" onClick={() => navigate('/login', { replace: true })}>
            Sign In with New Password
          </Button>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-border">
      <CardHeader className="space-y-1">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <LockKeyhole className="h-6 w-6" />
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight text-center">
          Choose a new password
        </CardTitle>
        <CardDescription className="text-center">
          Set a strong password for your AgriScope account
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {!tokenFromQuery && (
            <Input
              label="Reset Token"
              placeholder="Paste token from email link"
              value={token}
              onChange={(e) => setToken(e.target.value)}
              helperText="Supplied in the email link received from password recovery"
            />
          )}

          <Input
            label="New Password"
            type="password"
            autoComplete="new-password"
            helperText="At least 8 characters, 1 uppercase letter, and 1 digit"
            error={errors.new_password?.message}
            {...register('new_password')}
          />

          <Input
            label="Confirm New Password"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" loading={loading}>
            Update Password
          </Button>

          <Link to="/login" className="text-xs text-primary hover:underline text-center">
            Back to Sign In
          </Link>
        </CardFooter>
      </form>
    </Card>
  );
};
