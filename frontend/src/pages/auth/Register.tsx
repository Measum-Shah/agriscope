import React, { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { Link } from 'react-router-dom';
import { MailCheck } from 'lucide-react';
import { useAuth } from '../../context/AuthContext';
import { registerSchema, RegisterFormData } from '../../utils/validators';
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

export const RegisterPage: React.FC = () => {
  const { register: registerUser } = useAuth();
  const { toast } = useToast();
  const [loading, setLoading] = useState(false);
  const [registeredEmail, setRegisteredEmail] = useState<string | null>(null);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormData>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      name: '',
      email: '',
      password: '',
      confirmPassword: '',
    },
  });

  const onSubmit = async (data: RegisterFormData) => {
    setLoading(true);
    try {
      await registerUser({
        name: data.name,
        email: data.email,
        password: data.password,
      });
      setRegisteredEmail(data.email);
      toast({
        type: 'success',
        title: 'Account created!',
        description: 'Verification link sent to your email address.',
      });
    } catch (err: unknown) {
      const errorMsg =
        (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
        'Failed to create account. Please try again.';
      toast({
        type: 'error',
        title: 'Registration Failed',
        description: errorMsg,
      });
    } finally {
      setLoading(false);
    }
  };

  if (registeredEmail) {
    return (
      <Card className="shadow-lg border-border text-center">
        <CardHeader className="space-y-2">
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <MailCheck className="h-6 w-6" />
          </div>
          <CardTitle className="text-2xl font-bold tracking-tight">Check your email</CardTitle>
          <CardDescription className="text-sm">
            We sent a verification link to <strong>{registeredEmail}</strong>. Please click the link
            to activate your account.
          </CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-xs text-muted-foreground">
            In development, open Mailpit at{' '}
            <code className="rounded bg-muted px-1.5 py-0.5 text-foreground">localhost:8025</code>{' '}
            to inspect received emails.
          </p>
        </CardContent>
        <CardFooter className="flex flex-col space-y-2">
          <Link to="/login" className="w-full">
            <Button variant="default" className="w-full">
              Proceed to Sign In
            </Button>
          </Link>
          <Link to={`/verify-email?email=${encodeURIComponent(registeredEmail)}`}>
            <Button variant="ghost" size="sm" className="w-full text-xs">
              Enter verification code manually
            </Button>
          </Link>
        </CardFooter>
      </Card>
    );
  }

  return (
    <Card className="shadow-lg border-border">
      <CardHeader className="space-y-1">
        <CardTitle className="text-2xl font-bold tracking-tight">Create an account</CardTitle>
        <CardDescription>
          Join AgriScope to estimate ET and manage precision agricultural irrigation
        </CardDescription>
      </CardHeader>

      <form onSubmit={handleSubmit(onSubmit)}>
        <CardContent className="space-y-3.5">
          <Input
            label="Full Name"
            placeholder="Dr. Tariq Khan"
            autoComplete="name"
            error={errors.name?.message}
            {...register('name')}
          />

          <Input
            label="Email address"
            type="email"
            placeholder="tariq@agri-research.org"
            autoComplete="email"
            error={errors.email?.message}
            {...register('email')}
          />

          <Input
            label="Password"
            type="password"
            autoComplete="new-password"
            helperText="At least 8 characters, 1 uppercase letter, and 1 digit"
            error={errors.password?.message}
            {...register('password')}
          />

          <Input
            label="Confirm Password"
            type="password"
            autoComplete="new-password"
            error={errors.confirmPassword?.message}
            {...register('confirmPassword')}
          />
        </CardContent>

        <CardFooter className="flex flex-col space-y-4">
          <Button type="submit" className="w-full" loading={loading}>
            Create Account
          </Button>

          <p className="text-center text-xs text-muted-foreground">
            Already have an account?{' '}
            <Link to="/login" className="font-medium text-primary hover:underline">
              Sign In
            </Link>
          </p>
        </CardFooter>
      </form>
    </Card>
  );
};
