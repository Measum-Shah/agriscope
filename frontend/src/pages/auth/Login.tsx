import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link, useNavigate, useLocation } from 'react-router-dom';
import { ShieldCheck, KeyRound } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { loginSchema, LoginFormData } from '../../utils/validators';
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

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [requires2FA, setRequires2FA] = useState(false);
  const [useRecoveryCode, setUseRecoveryCode] = useState(false);

  const from = (location.state as { from?: { pathname: string } })?.from?.pathname || '/dashboard';

  const {
    register,
    handleSubmit,
    setValue,
    formState: { errors },
  } = useForm<LoginFormData>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      email: '',
      password: '',
      totp_code: '',
      recovery_code: '',
    },
  });

  const onSubmit = async (data: LoginFormData) => {
    setLoading(true);
    try {
      const result = await login(data);
      if (result.requires2FA) {
        setRequires2FA(true);
        toast({
          type: 'info',
          title: 'Two-Factor Authentication Required',
          description: 'Please enter the verification code from your authenticator app.',
        });
      } else {
        toast({
          type: 'success',
          title: 'Welcome back!',
          description: 'Signed in successfully.',
        });
        navigate(from, { replace: true });
      }
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Invalid email or password. Please try again.';
      toast({
        type: 'error',
        title: 'Sign In Failed',
        description: errorMsg,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="shadow-lg border-border">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight">
          {requires2FA ? 'Two-Factor Verification' : 'Sign in to AgriScope'}
        </CardTitle>
        <CardDescription>
          {requires2FA
            ? 'Enter your authentication code to verify your identity'
            : 'Enter your credentials below to access your account'}
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-4">
          {!requires2FA ? (
            <>
              <Input
                label="Email address"
                type="email"
                placeholder="agronomist@farm.org"
                autoComplete="email"
                error={errors.email?.message}
                {...register('email')}
              />

              <div className="space-y-1">
                <div className="flex items-center justify-between">
                  <label htmlFor="password" className="block text-sm font-medium text-foreground">
                    Password
                  </label>
                  <Link to="/forgot-password" className="text-xs text-primary hover:underline">
                    Forgot password?
                  </Link>
                </div>
                <Input
                  id="password"
                  type="password"
                  autoComplete="current-password"
                  error={errors.password?.message}
                  {...register('password')}
                />
              </div>
            </>
          ) : (
            <div className="space-y-4 animate-in fade-in-50">
              <div className="flex items-center justify-center p-3 rounded-md bg-muted/60">
                <ShieldCheck className="h-8 w-8 text-primary" />
              </div>

              {!useRecoveryCode ? (
                <div className="space-y-2">
                  <Input
                    label="6-Digit Authenticator Code"
                    placeholder="123456"
                    maxLength={6}
                    autoFocus
                    autoComplete="one-time-code"
                    error={errors.totp_code?.message}
                    {...register('totp_code')}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setUseRecoveryCode(true);
                      setValue('totp_code', '');
                    }}
                    className="text-xs text-primary hover:underline flex items-center gap-1"
                  >
                    <KeyRound className="h-3 w-3" />
                    Use a single-use backup recovery code instead
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Input
                    label="Backup Recovery Code"
                    placeholder="ABCD-EFGH"
                    autoFocus
                    error={errors.recovery_code?.message}
                    {...register('recovery_code')}
                  />
                  <button
                    type="button"
                    onClick={() => {
                      setUseRecoveryCode(false);
                      setValue('recovery_code', '');
                    }}
                    className="text-xs text-primary hover:underline"
                  >
                    Use standard 6-digit authenticator code instead
                  </button>
                </div>
              )}
            </div>
          )}
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" loading={loading}>
            {requires2FA ? 'Confirm & Sign In' : 'Sign In'}
          </Button>

          {requires2FA && (
            <Button
              type="button"
              variant="ghost"
              size="sm"
              className="w-full text-xs"
              onClick={() => {
                setRequires2FA(false);
                setValue('totp_code', '');
                setValue('recovery_code', '');
              }}
            >
              Back to credentials
            </Button>
          )}

          {!requires2FA && (
            <p className="text-center text-xs text-muted-foreground">
              Don&apos;t have an account?{' '}
              <Link to="/register" className="font-medium text-primary hover:underline">
                Create an account
              </Link>
            </p>
          )}
        </CardFooter>
      </form>
    </Card>
  );
};
