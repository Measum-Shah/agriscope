import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from './components/ui/Toast';
import { ThemeProvider } from './context/ThemeContext';
import { AuthProvider } from './context/AuthContext';
import { ProtectedRoute } from './routes/ProtectedRoute';
import { PlanRoute } from './routes/PlanRoute';
import { RoleRoute } from './routes/RoleRoute';
import { AuthLayout } from './layouts/AuthLayout';
import { DashboardLayout } from './layouts/DashboardLayout';
import { LoginPage } from './pages/auth/Login';
import { RegisterPage } from './pages/auth/Register';
import { VerifyEmailPage } from './pages/auth/VerifyEmail';
import { ForgotPasswordPage } from './pages/auth/ForgotPassword';
import { ResetPasswordPage } from './pages/auth/ResetPassword';
import { DashboardPage } from './pages/dashboard/DashboardPage';
import { SettingsPage } from './pages/settings/SettingsPage';
import { PredictPage } from './pages/predict/PredictPage';
import { HistoryPage } from './pages/history/HistoryPage';
import { FieldsPage } from './pages/fields/FieldsPage';
import { RemoteSensingPage } from './pages/remote-sensing/RemoteSensingPage';
import { IrrigationPage } from './pages/irrigation/IrrigationPage';
import { BatchPage } from './pages/batch/BatchPage';
import { ReportsPage } from './pages/reports/ReportsPage';
import { AdminPage } from './pages/admin/AdminPage';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: 1,
      refetchOnWindowFocus: false,
    },
  },
});

export const App: React.FC = () => {
  return (
    <QueryClientProvider client={queryClient}>
      <ThemeProvider>
        <ToastProvider>
          <AuthProvider>
            <BrowserRouter>
              <Routes>
                {/* Public Auth Routes */}
                <Route element={<AuthLayout />}>
                  <Route path="/login" element={<LoginPage />} />
                  <Route path="/register" element={<RegisterPage />} />
                  <Route path="/verify-email" element={<VerifyEmailPage />} />
                  <Route path="/forgot-password" element={<ForgotPasswordPage />} />
                  <Route path="/reset-password" element={<ResetPasswordPage />} />
                </Route>

                {/* Protected Dashboard Routes */}
                <Route
                  element={
                    <ProtectedRoute>
                      <DashboardLayout />
                    </ProtectedRoute>
                  }
                >
                  <Route path="/" element={<Navigate to="/dashboard" replace />} />
                  <Route path="/dashboard" element={<DashboardPage />} />
                  {/* Core ET Inference & History Routes */}
                  <Route path="/predict" element={<PredictPage />} />
                  <Route path="/history" element={<HistoryPage />} />
                  <Route path="/settings" element={<SettingsPage />} />

                  {/* Field Management, Remote Sensing & Irrigation Routes */}
                  <Route path="/fields" element={<FieldsPage />} />
                  <Route
                    path="/remote-sensing"
                    element={
                      <PlanRoute requiredFeature="satellite_indices">
                        <RemoteSensingPage />
                      </PlanRoute>
                    }
                  />
                  <Route path="/irrigation" element={<IrrigationPage />} />
                  <Route
                    path="/batch"
                    element={
                      <PlanRoute requiredFeature="export_csv">
                        <BatchPage />
                      </PlanRoute>
                    }
                  />
                  <Route
                    path="/reports"
                    element={
                      <PlanRoute requiredFeature="pdf_report">
                        <ReportsPage />
                      </PlanRoute>
                    }
                  />

                  {/* Admin Console Route */}
                  <Route
                    path="/admin"
                    element={
                      <RoleRoute allowedRoles={['admin']}>
                        <AdminPage />
                      </RoleRoute>
                    }
                  />
                </Route>

                {/* Catch-all */}
                <Route path="*" element={<Navigate to="/dashboard" replace />} />
              </Routes>
            </BrowserRouter>
          </AuthProvider>
        </ToastProvider>
      </ThemeProvider>
    </QueryClientProvider>
  );
};

export default App;
