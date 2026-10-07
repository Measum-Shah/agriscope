/**
 * Locale-aware formatting utilities for AgriScope.
 * Uses native Intl APIs — no external dependencies needed.
 */

export const formatNumber = (n: number, locale?: string, opts?: Intl.NumberFormatOptions): string =>
  new Intl.NumberFormat(locale || 'en-US', { maximumFractionDigits: 3, ...opts }).format(n);

export const formatPercent = (n: number, locale?: string): string =>
  new Intl.NumberFormat(locale || 'en-US', {
    style: 'percent',
    maximumFractionDigits: 1,
  }).format(n);

export const formatDate = (d: string | Date, locale?: string): string =>
  new Intl.DateTimeFormat(locale || 'en-US', { dateStyle: 'medium' }).format(new Date(d));

export const formatDateTime = (d: string | Date, locale?: string): string =>
  new Intl.DateTimeFormat(locale || 'en-US', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(d));

export const formatRelative = (d: string | Date, locale?: string): string => {
  const diff = Date.now() - new Date(d).getTime();
  const rtf = new Intl.RelativeTimeFormat(locale || 'en-US', { numeric: 'auto' });
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return rtf.format(-seconds, 'second');
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return rtf.format(-minutes, 'minute');
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return rtf.format(-hours, 'hour');
  return rtf.format(-Math.floor(hours / 24), 'day');
};

