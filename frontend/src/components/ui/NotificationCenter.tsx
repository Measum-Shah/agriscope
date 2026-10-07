import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { Bell, Check, Info, AlertTriangle, AlertCircle } from 'lucide-react';
import { Button } from './Button';
import { Badge } from './Badge';
import { jobsApi } from '../../api/jobs';
import { useToast } from './Toast';

export const NotificationCenter: React.FC = () => {
  const [isOpen, setIsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const queryClient = useQueryClient();
  const { toast } = useToast();

  // Notifications Query
  const { data: notifications = [] } = useQuery({
    queryKey: ['notifications'],
    queryFn: () => jobsApi.listNotifications(false),
  });

  // Setup Server-Sent Events (SSE) Live Connection
  useEffect(() => {
    // In dev / production, connect to SSE stream
    const eventSource = new EventSource('/api/v1/notifications/stream');

    eventSource.addEventListener('notification', (e: MessageEvent) => {
      try {
        const payload = JSON.parse(e.data);
        queryClient.invalidateQueries({ queryKey: ['notifications'] });
        toast({
          type: payload.type === 'alert' ? 'error' : payload.type === 'warning' ? 'warning' : 'info',
          title: payload.title,
          description: payload.message,
        });
      } catch (err) {
        // Ignore parse error
      }
    });

    eventSource.addEventListener('batch_completed', (e: MessageEvent) => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      queryClient.invalidateQueries({ queryKey: ['batch-status'] });
      try {
        const data = JSON.parse(e.data);
        toast({
          type: 'success',
          title: 'Batch Prediction Complete',
          description: `Processed ${data.total_rows} rows (${data.failed_count} errors).`,
        });
      } catch {}
    });

    return () => {
      eventSource.close();
    };
  }, [queryClient, toast]);

  // Click outside to close dropdown
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const markReadMutation = useMutation({
    mutationFn: (id: string) => jobsApi.markRead(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['notifications'] }),
  });

  const markAllReadMutation = useMutation({
    mutationFn: () => jobsApi.markAllRead(),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['notifications'] });
      toast({ type: 'success', title: 'Cleared', description: 'All notifications marked as read.' });
    },
  });

  const unreadCount = notifications.filter((n) => !n.is_read).length;

  const getTypeIcon = (type: string) => {
    switch (type) {
      case 'warning':
        return <AlertTriangle className="h-4 w-4 text-amber-500 shrink-0" />;
      case 'alert':
        return <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />;
      default:
        return <Info className="h-4 w-4 text-emerald-600 shrink-0" />;
    }
  };

  return (
    <div className="relative" ref={dropdownRef}>
      {/* Bell Button */}
      <Button
        variant="ghost"
        size="icon"
        onClick={() => setIsOpen(!isOpen)}
        aria-label="Open notifications"
        className="relative"
      >
        <Bell className="h-4 w-4 text-neutral-600 dark:text-neutral-300" />
        {unreadCount > 0 && (
          <span className="absolute top-1.5 right-1.5 flex h-4 min-w-[16px] items-center justify-center rounded-full bg-emerald-600 px-1 text-[10px] font-bold text-white shadow-xs">
            {unreadCount > 99 ? '99+' : unreadCount}
          </span>
        )}
      </Button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-80 sm:w-96 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900 shadow-xl z-50 overflow-hidden text-neutral-900 dark:text-neutral-100">
          <div className="flex items-center justify-between border-b border-neutral-100 dark:border-neutral-800 p-3 bg-neutral-50 dark:bg-neutral-800/50">
            <div className="flex items-center gap-2">
              <span className="text-xs font-semibold">Notifications</span>
              {unreadCount > 0 && (
                <Badge variant="outline" className="text-[10px] bg-emerald-50 text-emerald-700">
                  {unreadCount} unread
                </Badge>
              )}
            </div>
            {unreadCount > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => markAllReadMutation.mutate()}
                className="h-6 text-[11px] px-2 text-neutral-500 hover:text-neutral-900"
              >
                Mark all read
              </Button>
            )}
          </div>

          <div className="max-h-80 overflow-y-auto divide-y divide-neutral-100 dark:divide-neutral-800">
            {notifications.length === 0 ? (
              <div className="p-8 text-center text-xs text-neutral-400">
                No notifications right now.
              </div>
            ) : (
              notifications.map((notif) => (
                <div
                  key={notif.id}
                  className={`p-3 text-xs transition-colors flex items-start gap-2.5 ${
                    notif.is_read
                      ? 'opacity-70 hover:bg-neutral-50 dark:hover:bg-neutral-800/30'
                      : 'bg-emerald-50/40 dark:bg-emerald-950/20 hover:bg-emerald-50/60'
                  }`}
                >
                  {getTypeIcon(notif.type)}
                  <div className="flex-1 min-w-0">
                    <p className="font-semibold text-neutral-900 dark:text-neutral-100">{notif.title}</p>
                    <p className="text-neutral-600 dark:text-neutral-400 mt-0.5 leading-relaxed break-words">
                      {notif.message}
                    </p>
                    <span className="text-[10px] text-neutral-400 mt-1 block">
                      {new Date(notif.created_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                    </span>
                  </div>
                  {!notif.is_read && (
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => markReadMutation.mutate(notif.id)}
                      className="h-6 w-6 p-0 text-neutral-400 hover:text-emerald-600"
                      title="Mark as read"
                    >
                      <Check className="h-3.5 w-3.5" />
                    </Button>
                  )}
                </div>
              ))
            )}
          </div>
        </div>
      )}
    </div>
  );
};
