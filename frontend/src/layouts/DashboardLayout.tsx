import React, { useState } from 'react';
import { Outlet, Link, useLocation, useNavigate } from 'react-router-dom';
import {
  Sprout,
  LayoutDashboard,
  MapPin,
  Calculator,
  Satellite,
  Droplets,
  FileText,
  Layers,
  History,
  Settings,
  LogOut,
  Sun,
  Moon,
  Menu,
  X,
  User as UserIcon,
  ShieldAlert,
} from 'lucide-react';
import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';
import { NotificationCenter } from '../components/ui/NotificationCenter';
import { AnnouncementBanner } from '../components/feedback/AnnouncementBanner';
import { Button } from '../components/ui/Button';
import { Badge } from '../components/ui/Badge';
import { LanguageSwitcher } from '../components/ui/LanguageSwitcher';
import { cn } from '../lib/utils';

interface NavItem {
  label: string;
  href: string;
  icon: React.ReactNode;
  badge?: string;
}

export const DashboardLayout: React.FC = () => {
  const { user, entitlements, logout } = useAuth();
  const { resolvedTheme, toggleTheme } = useTheme();
  const location = useLocation();
  const navigate = useNavigate();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const navItems: NavItem[] = [
    {
      label: 'Dashboard',
      href: '/dashboard',
      icon: <LayoutDashboard className="h-4 w-4" />,
    },
    {
      label: 'Fields & Polygons',
      href: '/fields',
      icon: <MapPin className="h-4 w-4" />,
    },
    {
      label: 'ET Estimation',
      href: '/predict',
      icon: <Calculator className="h-4 w-4" />,
    },
    {
      label: 'Remote Sensing',
      href: '/remote-sensing',
      icon: <Satellite className="h-4 w-4" />,
      badge: 'Sentinel-2',
    },
    {
      label: 'Irrigation Scheduling',
      href: '/irrigation',
      icon: <Droplets className="h-4 w-4" />,
    },
    {
      label: 'Batch Predictions',
      href: '/batch',
      icon: <Layers className="h-4 w-4" />,
      badge: 'CSV',
    },
    {
      label: 'Reports & Export',
      href: '/reports',
      icon: <FileText className="h-4 w-4" />,
    },
    {
      label: 'Prediction History',
      href: '/history',
      icon: <History className="h-4 w-4" />,
    },
    {
      label: 'Settings & Security',
      href: '/settings',
      icon: <Settings className="h-4 w-4" />,
    },
    ...(user?.role === 'admin'
      ? [
          {
            label: 'Admin Console',
            href: '/admin',
            icon: <ShieldAlert className="h-4 w-4 text-destructive" />,
            badge: 'Admin',
          },
        ]
      : []),
  ];

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const planBadgeVariant =
    user?.plan === 'pro' ? 'default' : user?.plan === 'admin' ? 'destructive' : 'secondary';

  return (
    <div className="flex min-h-screen bg-muted/20 text-foreground">
      {/* Skip to main content — WCAG 2.4.1 Bypass Blocks */}
      <a
        href="#main-content"
        className="sr-only focus:not-sr-only focus:fixed focus:top-2 focus:left-2 focus:z-50 focus:bg-primary focus:text-white focus:px-4 focus:py-2 focus:rounded"
      >
        Skip to main content
      </a>
      {/* Mobile Sidebar Backdrop */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={() => setMobileMenuOpen(false)}
        />
      )}

      {/* Sidebar Desktop & Mobile Drawer */}
      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-card shadow-sm transition-transform duration-200 lg:static lg:translate-x-0',
          mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
        )}
      >
        {/* Brand */}
        <div className="flex h-16 items-center justify-between border-b border-border px-6">
          <Link
            to="/dashboard"
            className="flex items-center space-x-2.5 font-bold tracking-tight text-foreground"
          >
            <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
              <Sprout className="h-5 w-5" />
            </div>
            <span className="text-lg">
              Agri<span className="text-primary">Scope</span>
            </span>
          </Link>
          <Button
            variant="ghost"
            size="icon"
            className="lg:hidden"
            onClick={() => setMobileMenuOpen(false)}
            aria-label="Close navigation"
          >
            <X className="h-5 w-5" />
          </Button>
        </div>

        {/* Navigation list */}
        <nav className="flex-1 space-y-1 overflow-y-auto px-3 py-4">
          {navItems.map((item) => {
            const isActive =
              location.pathname === item.href ||
              (item.href !== '/dashboard' && location.pathname.startsWith(item.href));

            return (
              <Link
                key={item.href}
                to={item.href}
                onClick={() => setMobileMenuOpen(false)}
                className={cn(
                  'flex items-center justify-between rounded-md px-3 py-2 text-sm font-medium transition-colors',
                  isActive
                    ? 'bg-primary text-primary-foreground font-semibold shadow-xs'
                    : 'text-muted-foreground hover:bg-accent hover:text-accent-foreground'
                )}
              >
                <div className="flex items-center space-x-3">
                  {item.icon}
                  <span>{item.label}</span>
                </div>
                {item.badge && (
                  <Badge
                    variant={isActive ? 'outline' : 'secondary'}
                    className="text-[10px] px-1.5 py-0"
                  >
                    {item.badge}
                  </Badge>
                )}
              </Link>
            );
          })}
        </nav>

        {/* User Card at bottom of sidebar */}
        <div className="border-t border-border p-4 bg-muted/30">
          <div className="flex items-center justify-between mb-2">
            <span className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
              Account
            </span>
            <Badge variant={planBadgeVariant} className="uppercase text-[10px] px-2">
              {user?.plan || 'Free'}
            </Badge>
          </div>
          <div className="flex items-center space-x-3 truncate">
            <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-primary">
              <UserIcon className="h-4 w-4" />
            </div>
            <div className="truncate">
              <p className="text-xs font-medium text-foreground truncate">{user?.name || 'User'}</p>
              <p className="text-[11px] text-muted-foreground truncate">{user?.email}</p>
            </div>
          </div>
        </div>
      </aside>

      {/* Main Page Area */}
      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Top Header Bar */}
        <header className="flex h-16 items-center justify-between border-b border-border bg-card px-4 sm:px-6">
          <div className="flex items-center space-x-3">
            <Button
              variant="ghost"
              size="icon"
              className="lg:hidden"
              onClick={() => setMobileMenuOpen(true)}
              aria-label="Open navigation menu"
            >
              <Menu className="h-5 w-5" />
            </Button>
            <h1 className="text-lg font-semibold text-foreground hidden sm:block">
              Agricultural ET Intelligence
            </h1>
          </div>

          {/* Right Header: Quota badge + Theme Toggle + Logout */}
          <div className="flex items-center space-x-3">
            {/* Daily Quota Counter */}
            {entitlements && entitlements.daily_prediction_limit !== null && (
              <div className="hidden md:flex items-center space-x-1.5 text-xs bg-muted/60 border border-border rounded-full px-3 py-1">
                <span className="text-muted-foreground">Daily Quota:</span>
                <span className="font-semibold text-foreground">
                  {entitlements.predictions_used_today} / {entitlements.daily_prediction_limit}
                </span>
              </div>
            )}

            {/* In-app Notification Center with SSE listener */}
            <NotificationCenter />

            {/* Language Switcher */}
            <LanguageSwitcher />

            {/* Dark / Light Toggle */}
            <Button
              variant="ghost"
              size="icon"
              onClick={toggleTheme}
              aria-label={`Toggle to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
            >
              {resolvedTheme === 'dark' ? (
                <Sun className="h-4 w-4" />
              ) : (
                <Moon className="h-4 w-4" />
              )}
            </Button>

            {/* Logout button */}
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="flex items-center space-x-1.5"
            >
              <LogOut className="h-3.5 w-3.5" />
              <span className="hidden sm:inline">Log out</span>
            </Button>
          </div>
        </header>

        {/* Content Body */}
        <main id="main-content" className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8 space-y-4">
          <AnnouncementBanner />
          <Outlet />
        </main>

        {/* Footer with Data-Provenance slot */}
        <footer className="border-t border-border bg-card/60 px-6 py-3.5 text-xs text-muted-foreground flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2">
          <div>
            &copy; {new Date().getFullYear()} AgriScope. Operational agricultural meteorology
            platform.
          </div>
          <div className="text-[11px] text-muted-foreground/90 italic">
            Calculated using FAO-56 Penman-Monteith & Satellite remote-sensing pipelines. Weather
            data sourced from validated station reanalyses.
          </div>
        </footer>
      </div>
    </div>
  );
};
