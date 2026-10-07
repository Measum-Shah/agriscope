import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { User, Shield, CreditCard, Key, Receipt } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { ProfileTab } from './ProfileTab';
import { SecurityTab } from './SecurityTab';
import { AccountTab } from './AccountTab';
import { ApiKeysTab } from './ApiKeysTab';
import { BillingTab } from './BillingTab';

export const SettingsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'profile';

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value });
  };

  return (
    <div className="mx-auto max-w-5xl space-y-6">
      <div>
        <h2 className="text-2xl font-bold tracking-tight text-foreground">Settings & Subscriptions</h2>
        <p className="text-sm text-muted-foreground mt-1">
          Manage your personal details, credentials, API keys, billing subscriptions, and entitlements.
        </p>
      </div>

      <Tabs value={currentTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-5 max-w-2xl">
          <TabsTrigger value="profile" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <User className="h-4 w-4" />
            <span>Profile</span>
          </TabsTrigger>
          <TabsTrigger value="security" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <Shield className="h-4 w-4" />
            <span>Security</span>
          </TabsTrigger>
          <TabsTrigger value="account" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <CreditCard className="h-4 w-4" />
            <span>Account</span>
          </TabsTrigger>
          <TabsTrigger value="api-keys" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <Key className="h-4 w-4" />
            <span>API Keys</span>
          </TabsTrigger>
          <TabsTrigger value="billing" className="flex items-center gap-1.5 text-xs sm:text-sm">
            <Receipt className="h-4 w-4" />
            <span>Billing</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="profile" className="mt-6">
          <ProfileTab />
        </TabsContent>

        <TabsContent value="security" className="mt-6">
          <SecurityTab />
        </TabsContent>

        <TabsContent value="account" className="mt-6">
          <AccountTab />
        </TabsContent>

        <TabsContent value="api-keys" className="mt-6">
          <ApiKeysTab />
        </TabsContent>

        <TabsContent value="billing" className="mt-6">
          <BillingTab />
        </TabsContent>
      </Tabs>
    </div>
  );
};
