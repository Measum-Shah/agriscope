import React from 'react';
import { Navigate } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { Entitlements } from '../types/auth';
import {
  Card,
  CardHeader,
  CardTitle,
  CardDescription,
  CardContent,
  CardFooter,
} from '../components/ui/Card';
import { Button } from '../components/ui/Button';
import { Sparkles, Check } from 'lucide-react';

export interface PlanRouteProps {
  requiredFeature: keyof Entitlements['features'];
  children?: React.ReactNode;
}

export const PlanRoute: React.FC<PlanRouteProps> = ({ requiredFeature, children }) => {
  const { user, entitlements, isAuthenticated, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!isAuthenticated || !user) {
    return <Navigate to="/login" replace />;
  }

  const hasAccess =
    user.role === 'admin' ||
    user.plan === 'admin' ||
    (entitlements?.features && entitlements.features[requiredFeature]);

  if (!hasAccess) {
    return (
      <div className="flex min-h-[60vh] items-center justify-center p-4">
        <Card className="max-w-lg border-primary/20 shadow-lg">
          <CardHeader className="text-center">
            <div className="mx-auto mb-2 flex h-12 w-12 items-center justify-center rounded-full bg-primary/10 text-primary">
              <Sparkles className="h-6 w-6" />
            </div>
            <CardTitle className="text-2xl font-bold">Pro Feature</CardTitle>
            <CardDescription className="text-base mt-2">
              The feature <strong>{String(requiredFeature).replace('_', ' ')}</strong> is available
              exclusively on the AgriScope Pro and Enterprise plans.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <div className="rounded-lg bg-muted/60 p-4 space-y-2">
              <p className="text-sm font-semibold text-foreground">Pro Plan Includes:</p>
              <ul className="text-sm text-muted-foreground space-y-1.5">
                <li className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-primary" />
                  <span>Unlimited daily meteorological ET estimations</span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-primary" />
                  <span>
                    High-resolution Sentinel-2 satellite vegetation indices (NDVI/EVI/NDWI)
                  </span>
                </li>
                <li className="flex items-center space-x-2">
                  <Check className="h-4 w-4 text-primary" />
                  <span>GeoJSON polygon imports and publication-ready PDF reports</span>
                </li>
              </ul>
            </div>
          </CardContent>
          <CardFooter className="flex justify-between">
            <Button variant="outline" onClick={() => window.history.back()}>
              Go Back
            </Button>
            <Button
              variant="default"
              onClick={() => {
                alert('Upgrade requests will be enabled in billing workflow.');
              }}
            >
              Upgrade to Pro
            </Button>
          </CardFooter>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
};
