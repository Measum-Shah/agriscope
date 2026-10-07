import React, { useState, useEffect, useCallback } from 'react';
import { CreditCard, Check, Zap, ExternalLink, ArrowRight } from 'lucide-react';
import { billingApi, SubscriptionInfo } from '../../api/billing';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/Button';
import { Card, CardHeader, CardTitle, CardDescription, CardContent } from '../../components/ui/Card';
import { Badge } from '../../components/ui/Badge';
import { useToast } from '../../components/ui/Toast';

export const BillingTab: React.FC = () => {
  const { user, refreshUser } = useAuth();
  const { toast } = useToast();

  const [sub, setSub] = useState<SubscriptionInfo | null>(null);
  const [actionLoading, setActionLoading] = useState(false);

  const loadSub = useCallback(async () => {
    try {
      const data = await billingApi.getSubscription();
      setSub(data);
    } catch {
      // Fallback
    }
  }, []);

  useEffect(() => {
    loadSub();
  }, [loadSub]);

  const handleCheckoutOrMock = async (targetPlan: 'pro') => {
    setActionLoading(true);
    try {
      // Attempt Stripe checkout session first
      const checkout = await billingApi.createCheckoutSession(targetPlan);
      if (checkout?.checkout_url && checkout.checkout_url.startsWith('http')) {
        window.location.href = checkout.checkout_url;
        return;
      }
    } catch {
      // If Stripe not configured or in mock mode, use mock upgrade directly
    }

    try {
      const res = await billingApi.mockUpgrade(targetPlan);
      toast({
        type: 'success',
        title: 'Plan Upgraded',
        description: res.message || 'You have upgraded to Pro tier!',
      });
      await refreshUser();
      await loadSub();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Upgrade failed';
      toast({ type: 'error', title: 'Upgrade Failed', description: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const handleManageOrDowngrade = async () => {
    setActionLoading(true);
    try {
      const portal = await billingApi.createPortalSession();
      if (portal?.portal_url && portal.portal_url.startsWith('http')) {
        window.location.href = portal.portal_url;
        return;
      }
    } catch {
      // Fallback to mock downgrade
    }

    try {
      const res = await billingApi.mockDowngrade();
      toast({
        type: 'info',
        title: 'Plan Updated',
        description: res.message || 'Switched back to Free tier.',
      });
      await refreshUser();
      await loadSub();
    } catch (err: unknown) {
      const msg = (err as { response?: { data?: { detail?: string } } })?.response?.data?.detail || 'Downgrade failed';
      toast({ type: 'error', title: 'Action Failed', description: msg });
    } finally {
      setActionLoading(false);
    }
  };

  const currentPlan = (sub?.plan || user?.plan || 'free').toLowerCase();
  const isPro = currentPlan === 'pro' || currentPlan === 'enterprise';

  return (
    <div className="space-y-6">
      {/* Current Subscription Card */}
      <Card>
        <CardHeader>
          <div className="flex items-center justify-between">
            <div className="space-y-1">
              <CardTitle>Subscription & Billing</CardTitle>
              <CardDescription>
                Manage your AgriScope subscription plan, payment methods, and invoices
              </CardDescription>
            </div>
            <Badge variant={isPro ? 'default' : 'secondary'} className="uppercase px-3 py-1">
              {currentPlan} Plan
            </Badge>
          </div>
        </CardHeader>
        <CardContent>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between p-4 rounded-lg border bg-muted/30 gap-4">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <CreditCard className="h-5 w-5 text-primary" />
                <span className="font-semibold text-foreground capitalize">
                  AgriScope {currentPlan} Tier
                </span>
                <span className="text-xs text-muted-foreground">
                  ({sub?.status || 'Active'})
                </span>
              </div>
              <p className="text-xs text-muted-foreground">
                {isPro
                  ? 'Unlimited ET0 predictions, batch CSV processing, satellite analytics, and researcher API keys.'
                  : 'Basic Penman-Monteith physics, 10 predictions per day, 1 field boundary.'}
              </p>
            </div>
            <div className="flex gap-2">
              {isPro ? (
                <Button variant="outline" size="sm" onClick={handleManageOrDowngrade} loading={actionLoading} className="gap-1">
                  Manage / Downgrade <ExternalLink className="h-3.5 w-3.5" />
                </Button>
              ) : (
                <Button size="sm" onClick={() => handleCheckoutOrMock('pro')} loading={actionLoading} className="gap-1">
                  Upgrade to Pro <Zap className="h-3.5 w-3.5" />
                </Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Plan Comparison Table */}
      <div className="grid gap-6 md:grid-cols-2">
        {/* Free Plan */}
        <Card className={`relative ${!isPro ? 'border-primary ring-1 ring-primary' : ''}`}>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl">Free Tier</CardTitle>
                <CardDescription>Essential evapotranspiration monitoring</CardDescription>
              </div>
              <span className="text-2xl font-bold">$0<span className="text-xs font-normal text-muted-foreground">/mo</span></span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2 text-sm text-muted-foreground">
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-500" /> 10 predictions / day</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-500" /> 1 Field polygon tracking</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-500" /> Basic FAO-56 Penman-Monteith</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-emerald-500" /> 7-day weather prefill</li>
              <li className="flex items-center gap-2 text-muted-foreground/60">✕ Async batch CSV inference</li>
              <li className="flex items-center gap-2 text-muted-foreground/60">✕ Researcher API keys</li>
              <li className="flex items-center gap-2 text-muted-foreground/60">✕ Sentinel-2 NDVI remote sensing</li>
            </ul>
            {!isPro ? (
              <Button disabled variant="outline" className="w-full">Current Plan</Button>
            ) : (
              <Button variant="outline" className="w-full" onClick={handleManageOrDowngrade} loading={actionLoading}>
                Switch to Free
              </Button>
            )}
          </CardContent>
        </Card>

        {/* Pro Plan */}
        <Card className={`relative ${isPro ? 'border-primary ring-1 ring-primary' : ''}`}>
          <div className="absolute -top-3 right-4 bg-primary text-primary-foreground text-xs font-semibold px-2.5 py-0.5 rounded-full uppercase">
            Recommended
          </div>
          <CardHeader>
            <div className="flex justify-between items-start">
              <div>
                <CardTitle className="text-xl">Pro Researcher</CardTitle>
                <CardDescription>Full ML stack, satellite indices, & API</CardDescription>
              </div>
              <span className="text-2xl font-bold">$29<span className="text-xs font-normal text-muted-foreground">/mo</span></span>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            <ul className="space-y-2 text-sm text-foreground">
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Unlimited predictions</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Unlimited field boundaries</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Sentinel-2 STAC satellite NDVI/EVI</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Batch CSV inference (up to 10k rows)</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Researcher REST API keys (60 req/min)</li>
              <li className="flex items-center gap-2"><Check className="h-4 w-4 text-primary" /> Branded PDF & XLSX report exports</li>
            </ul>
            {isPro ? (
              <Button disabled variant="outline" className="w-full">Current Plan</Button>
            ) : (
              <Button className="w-full gap-2" onClick={() => handleCheckoutOrMock('pro')} loading={actionLoading}>
                Upgrade to Pro <ArrowRight className="h-4 w-4" />
              </Button>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
};
