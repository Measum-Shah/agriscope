import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { KeyRound, ArrowLeft } from 'lucide-react';
import { authApi } from '../../api/auth';
import { forgotPasswordSchema, ForgotPasswordFormData } from '../../utils/validators';
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

export const ForgotPasswordPage: React.FC = () => {
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [submitted, setSubmitted] = useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormData>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: {
      email: '',
    },
  });

  const onSubmit = async (data: ForgotPasswordFormData) => {
    setLoading(true);
    try {
      await authApi.forgotPassword(data.email);
      setSubmitted(true);
      toast({
        type: 'info',
        title: 'Reset instructions sent',
        description: 'If an account exists with that email, instructions were dispatched.',
      });
    } catch {
      setSubmitted(true);
      toast({
        type: 'info',
        title: 'Reset instructions sent',
        description: 'If an account exists with that email, instructions were dispatched.',
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card className="shadow-lg border-border">
      <CardHeader className="space-y-1">
        <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
          <KeyRound className="h-6 w-6" />
        </div>
        <CardTitle className="text-2xl font-bold tracking-tight text-center">
          Reset password
        </CardTitle>
        <CardDescription className="text-center">
          {submitted
            ? 'Check your inbox for password reset instructions'
            : 'Enter your registered email address to receive a secure reset link'}
        </CardDescription>
      </CardHeader>

      {!submitted ? (
        <form onSubmit={handleSubmit(onSubmit)}>
          <CardContent className="space-y-4">
            <Input
              label="Email address"
              type="email"
              placeholder="farmer@domain.com"
              autoComplete="email"
              error={errors.email?.message}
              {...register('email')}
            />
          </CardContent>

          <CardFooter className="flex flex-col space-y-4">
            <Button type="submit" className="w-full" loading={loading}>
              Send Reset Link
            </Button>

            <Link
              to="/login"
              className="flex items-center justify-center text-xs text-primary hover:underline gap-1"
            >
              <ArrowLeft className="h-3 w-3" />
              Back to Sign In
            </Link>
          </CardFooter>
        </form>
      ) : (
        <>
          <CardContent className="space-y-3">
            <div className="rounded-md bg-muted/60 p-4 text-xs text-muted-foreground space-y-1">
              <p>
                Reset links expire within <strong>1 hour</strong> and are single-use.
              </p>
              <p>
                In local development, review sent emails inside the Mailpit web client (port 8025).
              </p>
            </div>
          </CardContent>
          <CardFooter className="flex justify-center">
            <Link to="/login" className="w-full">
              <Button variant="outline" className="w-full">
                Return to Sign In
              </Button>
            </Link>
          </CardFooter>
        </>
      )}
    </Card>
  );
};
