import React, { useEffect, useState } from 'react';
import { AlertTriangle, Info, X } from 'lucide-react';
import { apiClient } from '../../api/client';

export interface PublicAnnouncement {
  id: string;
  title: string;
  message: string;
  type: string;
  is_active: boolean;
}

export const AnnouncementBanner: React.FC = () => {
  const [announcements, setAnnouncements] = useState<PublicAnnouncement[]>([]);
  const [dismissed, setDismissed] = useState<string[]>([]);

  useEffect(() => {
    const fetchAnnouncements = async () => {
      try {
        const res = await apiClient.get<PublicAnnouncement[]>('/notifications/announcements');
        setAnnouncements(res.data);
      } catch {
        // Silently fail if offline
      }
    };
    fetchAnnouncements();
  }, []);

  const activeVisible = announcements.filter(
    (a) => a.is_active && !dismissed.includes(a.id)
  );

  if (activeVisible.length === 0) return null;

  return (
    <div className="space-y-2">
      {activeVisible.map((ann) => {
        const isWarning = ann.type === 'warning' || ann.type === 'maintenance';
        return (
          <div
            key={ann.id}
            className={`flex items-center justify-between px-4 py-2 text-sm font-medium ${
              isWarning
                ? 'bg-amber-500/15 border-b border-amber-500/30 text-amber-900 dark:text-amber-200'
                : 'bg-primary/10 border-b border-primary/20 text-primary-foreground dark:text-primary-foreground'
            }`}
          >
            <div className="flex items-center gap-2">
              {isWarning ? (
                <AlertTriangle className="h-4 w-4 shrink-0 text-amber-600 dark:text-amber-400" />
              ) : (
                <Info className="h-4 w-4 shrink-0 text-primary" />
              )}
              <span>
                <strong>{ann.title}:</strong> {ann.message}
              </span>
            </div>
            <button
              onClick={() => setDismissed((prev) => [...prev, ann.id])}
              className="text-muted-foreground hover:text-foreground transition-colors"
              aria-label="Dismiss banner"
            >
              <X className="h-4 w-4" />
            </button>
          </div>
        );
      })}
    </div>
  );
};
