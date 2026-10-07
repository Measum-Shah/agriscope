import React from 'react';
import { useSearchParams } from 'react-router-dom';
import { LayoutDashboard, Users, Database, Sliders, Cpu } from 'lucide-react';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '../../components/ui/Tabs';
import { AdminOverviewPage } from './AdminOverviewPage';
import { AdminUsersPage } from './AdminUsersPage';
import { AdminDatasetsPage } from './AdminDatasetsPage';
import { AdminSystemPage } from './AdminSystemPage';
import { AdminModelsPage } from './AdminModelsPage';

export const AdminPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const currentTab = searchParams.get('tab') || 'overview';

  const handleTabChange = (value: string) => {
    setSearchParams({ tab: value });
  };

  return (
    <div className="space-y-6">
      <div className="border-b pb-4">
        <h1 className="text-3xl font-extrabold tracking-tight text-foreground">
          AgriScope Administration Console
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Centralized command console for user administration, ML dataset validation, model lifecycle, platform metrics, and system governance.
        </p>
      </div>

      <Tabs value={currentTab} onValueChange={handleTabChange} className="w-full">
        <TabsList className="grid w-full grid-cols-5 max-w-2xl">
          <TabsTrigger value="overview" className="flex items-center gap-2">
            <LayoutDashboard className="h-4 w-4" />
            <span>Overview</span>
          </TabsTrigger>
          <TabsTrigger value="users" className="flex items-center gap-2">
            <Users className="h-4 w-4" />
            <span>Users</span>
          </TabsTrigger>
          <TabsTrigger value="datasets" className="flex items-center gap-2">
            <Database className="h-4 w-4" />
            <span>Datasets</span>
          </TabsTrigger>
          <TabsTrigger value="models" className="flex items-center gap-2">
            <Cpu className="h-4 w-4" />
            <span>Models</span>
          </TabsTrigger>
          <TabsTrigger value="system" className="flex items-center gap-2">
            <Sliders className="h-4 w-4" />
            <span>System</span>
          </TabsTrigger>
        </TabsList>

        <TabsContent value="overview" className="mt-6">
          <AdminOverviewPage />
        </TabsContent>

        <TabsContent value="users" className="mt-6">
          <AdminUsersPage />
        </TabsContent>

        <TabsContent value="datasets" className="mt-6">
          <AdminDatasetsPage />
        </TabsContent>

        <TabsContent value="models" className="mt-6">
          <AdminModelsPage />
        </TabsContent>

        <TabsContent value="system" className="mt-6">
          <AdminSystemPage />
        </TabsContent>
      </Tabs>
    </div>
  );
};
