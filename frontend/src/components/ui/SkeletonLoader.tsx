import React from 'react';
import { cn } from '../../lib/utils';

interface SkeletonProps {
  className?: string;
}

export const Skeleton: React.FC<SkeletonProps> = ({ className }) => (
  <div
    role="status"
    aria-label="Loading"
    className={cn('animate-pulse rounded-md bg-muted', className)}
  />
);

export const SkeletonCard: React.FC = () => (
  <div className="rounded-xl border bg-card p-4 space-y-3" aria-busy="true">
    <Skeleton className="h-4 w-3/4" />
    <Skeleton className="h-8 w-1/2" />
    <Skeleton className="h-3 w-full" />
    <Skeleton className="h-3 w-2/3" />
  </div>
);

export const SkeletonTable: React.FC<{ rows?: number }> = ({ rows = 5 }) => (
  <div className="space-y-2" aria-busy="true" role="status" aria-label="Loading table">
    <Skeleton className="h-8 w-full" />
    {Array.from({ length: rows }).map((_, i) => (
      <Skeleton key={i} className="h-10 w-full" />
    ))}
  </div>
);
