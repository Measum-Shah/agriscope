import React from 'react';
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { render, screen, fireEvent, waitFor } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ToastProvider } from '../components/ui/Toast';
import { BatchPage } from '../pages/batch/BatchPage';
import { ReportsPage } from '../pages/reports/ReportsPage';
import { NotificationCenter } from '../components/ui/NotificationCenter';
import { jobsApi } from '../api/jobs';

vi.mock('../api/jobs', () => ({
  jobsApi: {
    getTemplate: vi.fn().mockResolvedValue({
      filename: 'et0_batch_template.csv',
      csv_content: 'temp_max,temp_min,humidity,wind_speed\n35,22,50,2.1',
    }),
    uploadBatchCsv: vi.fn().mockResolvedValue({
      job_id: 'job-123',
      status: 'pending',
      total_rows: 10,
      message: 'Batch prediction job queued successfully.',
    }),
    getBatchStatus: vi.fn().mockResolvedValue({
      id: 'job-123',
      status: 'completed',
      total_rows: 10,
      processed_rows: 10,
      error_summary: {
        total_processed: 10,
        failed_count: 0,
        errors_sample: [],
      },
      created_at: '2026-10-07T04:00:00Z',
      updated_at: '2026-10-07T04:01:00Z',
    }),
    getBatchDownloadUrl: vi.fn().mockResolvedValue({
      download_url: 'https://storage.agriscope.local/batch-result.csv',
      filename: 'batch_predictions_job-123.csv',
    }),
    listReports: vi.fn().mockResolvedValue([
      {
        id: 'rep-001',
        title: 'Weekly ET0 Summary',
        format: 'pdf',
        file_size_bytes: 45000,
        status: 'completed',
        download_url: 'https://storage.agriscope.local/weekly-summary.pdf',
        created_at: '2026-10-07T04:00:00Z',
      },
    ]),
    generateReport: vi.fn().mockResolvedValue({
      id: 'rep-002',
      title: 'Monthly Water Balance',
      format: 'xlsx',
      file_size_bytes: 12000,
      status: 'completed',
      download_url: 'https://storage.agriscope.local/monthly-balance.xlsx',
      created_at: '2026-10-07T04:05:00Z',
    }),
    listNotifications: vi.fn().mockResolvedValue([
      {
        id: 'notif-001',
        title: 'Batch Completed',
        message: 'Your batch prediction of 10 rows is ready.',
        type: 'info',
        is_read: false,
        metadata_json: {},
        created_at: '2026-10-07T04:10:00Z',
      },
    ]),
    markRead: vi.fn().mockResolvedValue({ id: 'notif-001', is_read: true }),
    markAllRead: vi.fn().mockResolvedValue({ ok: true, marked_count: 1 }),
  },
}));

// Mock EventSource
global.EventSource = vi.fn().mockImplementation(() => ({
  addEventListener: vi.fn(),
  removeEventListener: vi.fn(),
  close: vi.fn(),
})) as unknown as typeof EventSource;

const createWrapper = () => {
  const queryClient = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
    },
  });
  return ({ children }: { children: React.ReactNode }) => (
    <QueryClientProvider client={queryClient}>
      <ToastProvider>
        <BrowserRouter>{children}</BrowserRouter>
      </ToastProvider>
    </QueryClientProvider>
  );
};

describe('Task 13: Jobs and Delivery Frontend', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('renders BatchPage and allows CSV file selection & upload', async () => {
    const Wrapper = createWrapper();
    render(<BatchPage />, { wrapper: Wrapper });

    expect(screen.getByText(/Asynchronous Batch Prediction/i)).toBeDefined();
    expect(screen.getByText(/Download CSV Template/i)).toBeDefined();

    // Trigger CSV template download
    const templateBtn = screen.getByText(/Download CSV Template/i);
    fireEvent.click(templateBtn);
    await waitFor(() => {
      expect(jobsApi.getTemplate).toHaveBeenCalled();
    });

    // Simulate file input
    const file = new File(['temp_max,temp_min,humidity,wind_speed\n35,22,50,2.1'], 'test.csv', {
      type: 'text/csv',
    });
    const fileInput = document.querySelector('#batch-csv-input') as HTMLInputElement;
    expect(fileInput).not.toBeNull();

    Object.defineProperty(fileInput, 'files', {
      value: [file],
      writable: false,
    });
    fireEvent.change(fileInput);

    expect(await screen.findByText(/test.csv/i)).toBeDefined();

    // Submit batch job
    const runBtn = screen.getByRole('button', { name: /Submit Batch Job/i });
    fireEvent.click(runBtn);

    await waitFor(() => {
      expect(jobsApi.uploadBatchCsv).toHaveBeenCalled();
    });
  });

  it('renders ReportsPage and opens create export modal', async () => {
    const Wrapper = createWrapper();
    render(<ReportsPage />, { wrapper: Wrapper });

    expect(await screen.findByText(/Reports & Analytical Exports/i)).toBeDefined();
    expect(await screen.findByText(/Weekly ET0 Summary/i)).toBeDefined();

    // Click "Generate Report" header button
    const generateBtn = screen.getByRole('button', { name: /Generate Report/i });
    fireEvent.click(generateBtn);

    // Modal should be open
    expect(await screen.findByText(/Generate Analytical Export/i)).toBeDefined();
    expect(screen.getByText(/Export Format/i)).toBeDefined();

    // Fill title
    const titleInput = screen.getByPlaceholderText(/e\.g\. October 2026 Evapotranspiration Summary/i);
    fireEvent.change(titleInput, { target: { value: 'Seasonal Review' } });

    // Submit export creation button in modal
    const submitBtn = screen.getByRole('button', { name: /Create Export/i });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(jobsApi.generateReport).toHaveBeenCalled();
    });
  });

  it('renders NotificationCenter, opens dropdown, and marks notification as read', async () => {
    const Wrapper = createWrapper();
    render(<NotificationCenter />, { wrapper: Wrapper });

    // Bell button should be rendered with 1 unread badge
    const bellBtn = screen.getByRole('button', { name: /Open notifications/i });
    expect(bellBtn).toBeDefined();

    // Open dropdown
    fireEvent.click(bellBtn);

    expect(await screen.findByText(/Batch Completed/i)).toBeDefined();
    expect(screen.getByText(/Your batch prediction of 10 rows is ready/i)).toBeDefined();

    // Mark as read button click
    const markReadBtn = screen.getByTitle('Mark as read');
    fireEvent.click(markReadBtn);

    await waitFor(() => {
      expect(jobsApi.markRead).toHaveBeenCalledWith('notif-001');
    });
  });
});
