import React from 'react';
import { Outlet, Link } from 'react-router-dom';
import { Sprout, Sun, Moon } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import { Button } from '../components/ui/Button';

export const AuthLayout: React.FC = () => {
  const { resolvedTheme, toggleTheme } = useTheme();

  return (
    <div className="flex min-h-screen flex-col bg-muted/30 dark:bg-background">
      {/* Top minimal bar */}
      <header className="flex h-16 items-center justify-between px-6 border-b border-border/40 bg-background/80 backdrop-blur-sm">
        <Link to="/" className="flex items-center space-x-2.5">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-primary text-primary-foreground shadow-sm">
            <Sprout className="h-5 w-5" />
          </div>
          <span className="text-xl font-bold tracking-tight text-foreground">
            Agri<span className="text-primary">Scope</span>
          </span>
        </Link>
        <div className="flex items-center space-x-2">
          <Button
            variant="ghost"
            size="icon"
            onClick={toggleTheme}
            aria-label={`Switch to ${resolvedTheme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {resolvedTheme === 'dark' ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
          </Button>
        </div>
      </header>

      {/* Main content body */}
      <main className="flex flex-1 items-center justify-center p-4 sm:p-8">
        <div className="w-full max-w-md animate-in fade-in-50 zoom-in-95 duration-200">
          <Outlet />
        </div>
      </main>

      {/* Footer with data-provenance slot */}
      <footer className="border-t border-border/40 py-4 px-6 text-center text-xs text-muted-foreground">
        <p className="mb-1">
          &copy; {new Date().getFullYear()} AgriScope Platform. Science-grade ET intelligence.
        </p>
        <p className="text-[11px] opacity-75">
          Meteorological calculations strictly adhere to the FAO-56 Penman-Monteith standard.
        </p>
      </footer>
    </div>
  );
};
