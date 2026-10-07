import React, { useEffect, useState, useCallback } from 'react';
import { useSearchParams, Link } from 'react-router-dom';
import { CheckCircle2, XCircle, MailCheck } from 'lucide-react';
import { authApi } from '../../api/auth';
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
import { Spinner } from '../../components/ui/Spinner';
import { useToast } from '../../components/ui/Toast';

export const VerifyEmailPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const tokenFromQuery = searchParams.get('token');
  const emailFromQuery = searchParams.get('email');
  const { toast } = useToast();

  const [tokenInput, setTokenInput] = useState(tokenFromQuery || '');
  const [resendEmail, setResendEmail] = useState(emailFromQuery || '');
  const [loading, setLoading] = useState(false);
  const [resendLoading, setResendLoading] = useState(false);
  const [verified, setVerified] = useState(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const handleVerify = useCallback(
    async (token: string) => {
      if (!token.trim()) return;
      setLoading(true);
      setErrorMsg(null);
      try {
        await authApi.verifyEmail(token.trim());
        setVerified(true);
        toast({
          type: 'success',
          title: 'Email Verified!',
          description: 'Your email has been confirmed. You may now log in.',
        });
      } catch (err: unknown) {
        const msg =
          (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail ||
          'Verification token is invalid or has expired.';
        setErrorMsg(msg);
        toast({
          type: 'error',
          title: 'Verification Failed',
          description: msg,
        });
      } finally {
        setLoading(false);
      }
    },
    [toast]
  );

  useEffect(() => {
    if (tokenFromQuery) {
      handleVerify(tokenFromQuery);
    }
  }, [tokenFromQuery, handleVerify]);

  const handleResend = async () => {
    if (!resendEmail.trim()) {
      toast({
        type: 'error',
        title: 'Email required',
        description: 'Please enter your email to resend verification link.',
      });
      return;
    }
    setResendLoading(true);
    try {
      await authApi.resendVerification(resendEmail.trim());
      toast({
        type: 'info',
        title: 'Link Dispatched',
        description: 'If an unverified account matches that address, a new link was sent.',
      });
    } catch {
      toast({
        type: 'info',
        title: 'Link Dispatched',
        description: 'If an unverified account matches that address, a new link was sent.',
      });
    } finally {
      setResendLoading(false);
    }
  };

  return (
    <Card className="shadow-lg border-border text-center">
      <CardHeader className="space-y-1">
        {verified ? (
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-emerald-500/10 text-emerald-600">
            <CheckCircle2 className="h-6 w-6" />
          </div>
        ) : errorMsg ? (
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-destructive/10 text-destructive">
            <XCircle className="h-6 w-6" />
          </div>
        ) : (
          <div className="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
            <MailCheck className="h-6 w-6" />
          </div>
        )}
        <CardTitle className="text-2xl font-bold tracking-tight">
          {verified ? 'Email Verified' : 'Verify Email Address'}
        </CardTitle>
        <CardDescription>
          {verified
            ? 'Your account is now fully active.'
            : 'Confirming your email address to unlock full system capabilities.'}
        </CardDescription>
      </CardHeader>

      <CardContent className="space-y-4">
        {loading && (
          <div className="flex flex-col items-center justify-center py-6 space-y-2">
            <Spinner size="lg" className="text-primary" />
            <p className="text-sm text-muted-foreground">Validating token...</p>
          </div>
        )}

        {verified && (
          <div className="rounded-md bg-emerald-50 dark:bg-emerald-950/60 p-4 border border-emerald-500/20 text-emerald-800 dark:text-emerald-200 text-sm">
            Thank you! Your email address has been successfully verified. You can now access your
            dashboard.
          </div>
        )}

        {!verified && !loading && (
          <div className="space-y-4 text-left">
            {errorMsg && (
              <div className="rounded-md bg-destructive/10 p-3 text-xs text-destructive">
                {errorMsg}
              </div>
            )}

            <div className="space-y-2">
              <Input
                label="Verification Token"
                placeholder="Paste your token from the email"
                value={tokenInput}
                onChange={(e) => setTokenInput(e.target.value)}
              />
              <Button
                type="button"
                className="w-full"
                onClick={() => handleVerify(tokenInput)}
                disabled={!tokenInput.trim() || loading}
              >
                Verify Token
              </Button>
            </div>

            <div className="border-t border-border pt-4 space-y-2">
              <p className="text-xs text-muted-foreground">
                Didn&apos;t receive a verification email? Request a new one:
              </p>
              <div className="flex gap-2">
                <Input
                  type="email"
                  placeholder="your.email@example.com"
                  value={resendEmail}
                  onChange={(e) => setResendEmail(e.target.value)}
                  className="flex-1"
                />
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleResend}
                  loading={resendLoading}
                >
                  Resend
                </Button>
              </div>
            </div>
          </div>
        )}
      </CardContent>

      <CardFooter className="flex justify-center">
        {verified ? (
          <Link to="/login" className="w-full">
            <Button className="w-full">Proceed to Sign In</Button>
          </Link>
        ) : (
          <Link to="/login" className="text-xs text-primary hover:underline">
            Back to Sign In
          </Link>
        )}
      </CardFooter>
    </Card>
  );
};
