import { useState, useCallback } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, FileText, Edit2, Trash2, Eye } from 'lucide-react';
import { formatDate } from '@/lib/utils';

import { useCrimeReports, useCreateCrimeReport, useUpdateCrimeReport, useDeleteCrimeReport } from '@/hooks/useCrimeReports';
import { useCrimeCategories } from '@/hooks/useCrimeCategories';
import { useCrimeLocations } from '@/hooks/useCrimeLocations';
import type { CrimeReport, CrimeReportFilters, CrimeStatus, Priority } from '@/types/crimeReport';

import { Table, type Column } from '@/components/ui/Table';
import { Pagination } from '@/components/ui/Pagination';
import { SearchBar } from '@/components/ui/SearchBar';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { Drawer } from '@/components/ui/Drawer';
import { Dropdown } from '@/components/ui/Dropdown';
import { CrimeStatusBadge, PriorityBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';

// ─── Schema ──────────────────────────────────────────────────────────────────

const reportSchema = z.object({
  title: z.string().min(3, 'Title must be at least 3 characters'),
  description: z.string().optional(),
  priority: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  incident_date: z.string().min(1, 'Incident date is required'),
  victim_count: z.coerce.number().int().min(0).optional(),
  estimated_loss: z.coerce.number().min(0).optional(),
  officer_name: z.string().optional(),
  category_id: z.string().uuid('Select a category'),
  location_id: z.string().uuid('Select a location'),
});
type ReportFormData = z.infer<typeof reportSchema>;

const STATUS_OPTIONS = [
  { label: 'All Statuses', value: '' },
  { label: 'Open', value: 'OPEN' },
  { label: 'Under Investigation', value: 'UNDER_INVESTIGATION' },
  { label: 'Closed', value: 'CLOSED' },
  { label: 'Archived', value: 'ARCHIVED' },
];
const PRIORITY_OPTIONS = [
  { label: 'All Priorities', value: '' },
  { label: 'Low', value: 'LOW' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'High', value: 'HIGH' },
  { label: 'Critical', value: 'CRITICAL' },
];

// ─── Form ─────────────────────────────────────────────────────────────────────

function ReportForm({
  defaultValues,
  onSubmit,
  loading,
  categories,
  locations,
}: {
  defaultValues?: Partial<ReportFormData>;
  onSubmit: (data: ReportFormData) => void;
  loading: boolean;
  categories: { id: string; name: string }[];
  locations: { id: string; city: string; state: string }[];
}) {
  const { register, handleSubmit, control, formState: { errors } } = useForm<ReportFormData>({
    resolver: zodResolver(reportSchema),
    defaultValues: {
      priority: 'MEDIUM',
      victim_count: 0,
      ...defaultValues,
    },
  });

  const fieldClass = 'w-full h-9 px-3 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 focus:border-emerald-500/50 transition-colors';
  const labelClass = 'block text-xs font-medium text-muted-foreground mb-1';
  const errorClass = 'text-[11px] text-red-400 mt-1';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className={labelClass}>Title *</label>
        <input {...register('title')} placeholder="e.g. Vehicle Theft on MG Road" className={fieldClass} />
        {errors.title && <p className={errorClass}>{errors.title.message}</p>}
      </div>

      <div>
        <label className={labelClass}>Description</label>
        <textarea
          {...register('description')}
          rows={3}
          placeholder="Detailed description of the incident…"
          className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 resize-none"
        />
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Priority *</label>
          <Controller
            name="priority"
            control={control}
            render={({ field }) => (
              <Dropdown
                value={field.value}
                onChange={field.onChange}
                options={PRIORITY_OPTIONS.filter((o) => o.value !== '')}
              />
            )}
          />
        </div>
        <div>
          <label className={labelClass}>Incident Date *</label>
          <input type="date" {...register('incident_date')} max={new Date().toISOString().split('T')[0]} className={fieldClass} />
          {errors.incident_date && <p className={errorClass}>{errors.incident_date.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Category *</label>
          <Controller
            name="category_id"
            control={control}
            render={({ field }) => (
              <Dropdown
                value={field.value ?? ''}
                onChange={field.onChange}
                placeholder="Select category"
                options={categories.map((c) => ({ label: c.name, value: c.id }))}
              />
            )}
          />
          {errors.category_id && <p className={errorClass}>{errors.category_id.message}</p>}
        </div>
        <div>
          <label className={labelClass}>Location *</label>
          <Controller
            name="location_id"
            control={control}
            render={({ field }) => (
              <Dropdown
                value={field.value ?? ''}
                onChange={field.onChange}
                placeholder="Select location"
                options={locations.map((l) => ({ label: `${l.city}, ${l.state}`, value: l.id }))}
              />
            )}
          />
          {errors.location_id && <p className={errorClass}>{errors.location_id.message}</p>}
        </div>
      </div>

      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Victims</label>
          <input type="number" min={0} {...register('victim_count')} className={fieldClass} />
        </div>
        <div>
          <label className={labelClass}>Estimated Loss (₹)</label>
          <input type="number" min={0} step={0.01} {...register('estimated_loss')} className={fieldClass} />
        </div>
      </div>

      <div>
        <label className={labelClass}>Officer Name</label>
        <input {...register('officer_name')} placeholder="Assigned officer" className={fieldClass} />
      </div>

      <div className="flex gap-3 justify-end pt-2 border-t border-border">
        <Button type="submit" loading={loading} size="md">
          {defaultValues ? 'Update Report' : 'Create Report'}
        </Button>
      </div>
    </form>
  );
}

// ─── Detail Drawer ────────────────────────────────────────────────────────────

function ReportDetail({ report }: { report: CrimeReport }) {
  const fields: { label: string; value: React.ReactNode }[] = [
    { label: 'Crime Number', value: <span className="font-mono text-emerald-400">{report.crime_number}</span> },
    { label: 'Status', value: <CrimeStatusBadge status={report.status} /> },
    { label: 'Priority', value: <PriorityBadge priority={report.priority} /> },
    { label: 'Category', value: report.category?.name ?? '—' },
    { label: 'Location', value: report.location ? `${report.location.city}, ${report.location.state}` : '—' },
    { label: 'Incident Date', value: formatDate(report.incident_date) },
    { label: 'Victims', value: report.victim_count ?? '—' },
    { label: 'Estimated Loss', value: report.estimated_loss ? `₹${report.estimated_loss.toLocaleString()}` : '—' },
    { label: 'Officer', value: report.officer_name ?? '—' },
    { label: 'Reporter', value: report.reporter?.full_name ?? report.reporter?.email ?? '—' },
    { label: 'Reported On', value: formatDate(report.report_date ?? report.created_at) },
  ];

  return (
    <div className="space-y-5">
      <div>
        <h3 className="text-base font-semibold text-foreground">{report.title}</h3>
        {report.description && (
          <p className="mt-2 text-sm text-muted-foreground leading-relaxed">{report.description}</p>
        )}
      </div>
      <div className="grid grid-cols-2 gap-x-4 gap-y-3">
        {fields.map(({ label, value }) => (
          <div key={label}>
            <p className="text-[11px] text-muted-foreground uppercase tracking-wider mb-0.5">{label}</p>
            <div className="text-sm text-foreground">{value}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main Page ────────────────────────────────────────────────────────────────

export default function CrimeReportsPage() {
  const [filters, setFilters] = useState<CrimeReportFilters>({ page: 1, page_size: 20 });
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [createOpen, setCreateOpen] = useState(false);
  const [editReport, setEditReport] = useState<CrimeReport | null>(null);
  const [detailReport, setDetailReport] = useState<CrimeReport | null>(null);
  const [deleteId, setDeleteId] = useState<string | null>(null);

  const { data, isLoading, isError, error } = useCrimeReports({ ...filters, sort_by: sortBy, order: sortOrder });
  const { data: catData } = useCrimeCategories({ page: 1, page_size: 100 });
  const { data: locData } = useCrimeLocations({ page: 1, page_size: 100 });
  const createMutation = useCreateCrimeReport();
  const updateMutation = useUpdateCrimeReport();
  const deleteMutation = useDeleteCrimeReport();

  const categories = catData?.items ?? [];
  const locations = locData?.items ?? [];

  const handleSort = useCallback((key: string) => {
    if (key === sortBy) setSortOrder((o) => o === 'asc' ? 'desc' : 'asc');
    else { setSortBy(key); setSortOrder('asc'); }
  }, [sortBy]);

  const columns: Column<CrimeReport & Record<string, unknown>>[] = [
    {
      key: 'crime_number', header: 'Crime #', sortable: true, width: '130px',
      render: (v) => <span className="font-mono text-xs text-emerald-400">{String(v)}</span>,
    },
    {
      key: 'title', header: 'Title', sortable: true,
      render: (v) => <span className="font-medium">{String(v)}</span>,
    },
    {
      key: 'status', header: 'Status', sortable: true, width: '160px',
      render: (v) => <CrimeStatusBadge status={v as CrimeStatus} />,
    },
    {
      key: 'priority', header: 'Priority', sortable: true, width: '100px',
      render: (v) => <PriorityBadge priority={v as Priority} />,
    },
    {
      key: 'incident_date', header: 'Incident Date', sortable: true, width: '120px',
      render: (v) => formatDate(v as string),
    },
    {
      key: 'id', header: 'Actions', width: '100px',
      render: (_, row) => (
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <button
            onClick={() => setDetailReport(row as unknown as CrimeReport)}
            className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
            title="View"
          >
            <Eye size={13} />
          </button>
          <button
            onClick={() => setEditReport(row as unknown as CrimeReport)}
            className="p-1.5 rounded text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
            title="Edit"
          >
            <Edit2 size={13} />
          </button>
          <button
            onClick={() => setDeleteId(row.id as string)}
            className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
            title="Delete"
          >
            <Trash2 size={13} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Crime Reports</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data?.total ?? 0} total reports
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="md">
          <Plus size={14} />
          New Report
        </Button>
      </div>

      {/* Filters */}
      <Card>
        <div className="px-5 py-4 flex flex-wrap gap-3">
          <SearchBar
            value={filters.q ?? ''}
            onChange={(q) => setFilters((f) => ({ ...f, q, page: 1 }))}
            placeholder="Search by title, description, crime number…"
            className="flex-1 min-w-[200px]"
          />
          <Dropdown
            value={filters.status ?? ''}
            onChange={(v) => setFilters((f) => ({ ...f, status: v as CrimeStatus | '', page: 1 }))}
            options={STATUS_OPTIONS}
            className="w-44"
          />
          <Dropdown
            value={filters.priority ?? ''}
            onChange={(v) => setFilters((f) => ({ ...f, priority: v as Priority | '', page: 1 }))}
            options={PRIORITY_OPTIONS}
            className="w-36"
          />
        </div>
      </Card>

      {/* Table */}
      <Card>
        {isError ? (
          <EmptyState
            icon={<FileText size={24} />}
            title="Could not load crime reports"
            description={error instanceof Error ? error.message : 'API request failed. Sign in again or refresh the page.'}
          />
        ) : (!isLoading && (data?.items ?? []).length === 0) ? (
          <EmptyState
            icon={<FileText size={24} />}
            title="No crime reports found"
            description="Create your first crime report to get started."
            action={
              <Button onClick={() => setCreateOpen(true)} size="sm">
                <Plus size={13} />Create Report
              </Button>
            }
          />
        ) : (
          <>
            <Table
              columns={columns as Column<Record<string, unknown>>[]}
              data={(data?.items ?? []) as unknown as Record<string, unknown>[]}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              onRowClick={(row) => setDetailReport(row as unknown as CrimeReport)}
              loading={isLoading}
              emptyMessage="No reports match your filters."
            />
            {data && (
              <div className="px-5 py-3 border-t border-border">
                <Pagination
                  page={data.page}
                  totalPages={data.total_pages}
                  total={data.total}
                  pageSize={data.page_size}
                  onPageChange={(p) => setFilters((f) => ({ ...f, page: p }))}
                  onPageSizeChange={(s) => setFilters((f) => ({ ...f, page_size: s, page: 1 }))}
                />
              </div>
            )}
          </>
        )}
      </Card>

      {/* Create Modal */}
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New Crime Report" size="lg">
        <ReportForm
          categories={categories}
          locations={locations}
          loading={createMutation.isPending}
          onSubmit={async (data) => {
            await createMutation.mutateAsync(data);
            setCreateOpen(false);
          }}
        />
      </Modal>

      {/* Edit Modal */}
      <Modal
        open={!!editReport}
        onClose={() => setEditReport(null)}
        title="Edit Crime Report"
        size="lg"
      >
        {editReport && (
          <ReportForm
            categories={categories}
            locations={locations}
            loading={updateMutation.isPending}
            defaultValues={{
              title: editReport.title,
              description: editReport.description,
              priority: editReport.priority,
              incident_date: editReport.incident_date?.split('T')[0],
              victim_count: editReport.victim_count,
              estimated_loss: editReport.estimated_loss,
              officer_name: editReport.officer_name,
              category_id: editReport.category_id,
              location_id: editReport.location_id,
            }}
            onSubmit={async (data) => {
              await updateMutation.mutateAsync({ id: editReport.id, payload: data });
              setEditReport(null);
            }}
          />
        )}
      </Modal>

      {/* Detail Drawer */}
      <Drawer
        open={!!detailReport}
        onClose={() => setDetailReport(null)}
        title="Report Details"
        width="md"
      >
        {detailReport && <ReportDetail report={detailReport} />}
      </Drawer>

      {/* Delete Confirm */}
      <ConfirmDialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={async () => {
          if (deleteId) {
            await deleteMutation.mutateAsync(deleteId);
            setDeleteId(null);
          }
        }}
        title="Delete Crime Report"
        description="This action cannot be undone. The report will be soft-deleted and removed from all views."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
