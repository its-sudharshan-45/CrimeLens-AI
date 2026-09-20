import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Search, Eye, MessageSquare, Clock } from 'lucide-react';
import { formatDate, formatDateTime } from '@/lib/utils';
import {
  useInvestigations,
  useInvestigation,
  useInvestigationTimeline,
  useInvestigationNotes,
  useCreateInvestigation,
  useUpdateInvestigationStatus,
  useAddInvestigationNote,
} from '@/hooks/useInvestigations';
import { useCrimeReports } from '@/hooks/useCrimeReports';
import {
  INVESTIGATION_STATUS_OPTIONS,
  type Investigation,
  type InvestigationFilters,
  type InvestigationStatus,
  type Priority,
} from '@/types/investigation';
import { Table, type Column } from '@/components/ui/Table';
import { Pagination } from '@/components/ui/Pagination';
import { SearchBar } from '@/components/ui/SearchBar';
import { Modal } from '@/components/ui/Modal';
import { Drawer } from '@/components/ui/Drawer';
import { Dropdown } from '@/components/ui/Dropdown';
import { InvestigationStatusBadge, PriorityBadge } from '@/components/ui/Badge';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { Tabs } from '@/components/ui/Tabs';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';

const investigationSchema = z.object({
  report_id: z.string().uuid('Select a valid crime report'),
  priority: z.enum(['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']),
  notes: z.string().optional(),
});
type InvestigationFormData = z.infer<typeof investigationSchema>;

const STATUS_OPTIONS = [
  { label: 'All Statuses', value: '' },
  ...INVESTIGATION_STATUS_OPTIONS,
];

const PRIORITY_OPTIONS = [
  { label: 'All Priorities', value: '' },
  { label: 'Low', value: 'LOW' },
  { label: 'Medium', value: 'MEDIUM' },
  { label: 'High', value: 'HIGH' },
  { label: 'Critical', value: 'CRITICAL' },
];

function InvestigationDetailDrawer({
  investigationId,
  onClose,
}: {
  investigationId: string | null;
  onClose: () => void;
}) {
  const [tab, setTab] = useState('overview');
  const [newNote, setNewNote] = useState('');

  const { data: inv, isLoading } = useInvestigation(investigationId);
  const { data: timeline } = useInvestigationTimeline(investigationId);
  const { data: notesData } = useInvestigationNotes(investigationId);
  const updateStatusMutation = useUpdateInvestigationStatus();
  const addNoteMutation = useAddInvestigationNote();

  if (!investigationId) return null;

  const handleAddNote = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newNote.trim()) return;
    await addNoteMutation.mutateAsync({
      id: investigationId,
      payload: { note: newNote },
    });
    setNewNote('');
  };

  const handleStatusChange = async (newStatus: string) => {
    if (!newStatus) return;
    await updateStatusMutation.mutateAsync({
      id: investigationId,
      payload: { status: newStatus as InvestigationStatus },
    });
  };

  return (
    <Drawer
      open={!!investigationId}
      onClose={onClose}
      title={inv ? `Case #${inv.id.slice(0, 8)}` : 'Investigation Details'}
      width="lg"
    >
      {isLoading || !inv ? (
        <div className="space-y-4">
          <Skeleton className="h-6 w-1/2" />
          <Skeleton className="h-20 w-full" />
        </div>
      ) : (
        <div className="space-y-6">
          {/* Header Info */}
          <div className="bg-secondary/40 border border-border rounded-xl p-4 space-y-3">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="font-semibold text-foreground text-sm">
                  {inv.report?.title || 'Report Associated'}
                </h3>
                <p className="text-xs text-emerald-400 font-mono mt-0.5">
                  {inv.report?.crime_number}
                </p>
              </div>
              <div className="flex gap-2">
                <InvestigationStatusBadge status={inv.status} />
                <PriorityBadge priority={inv.priority} />
              </div>
            </div>

            <div className="flex items-center gap-4 text-xs text-muted-foreground pt-2 border-t border-border/50">
              <div>
                Officer/Investigator:{' '}
                <span className="text-foreground font-medium">
                  {inv.investigator?.full_name || inv.investigator?.email || 'Unassigned'}
                </span>
              </div>
              <div>
                Opened:{' '}
                <span className="text-foreground font-medium">
                  {formatDate(inv.created_at)}
                </span>
              </div>
            </div>
          </div>

          {/* Quick Status Update */}
          <div className="flex items-center gap-3">
            <span className="text-xs font-medium text-muted-foreground">Update Status:</span>
            <Dropdown
              value={inv.status}
              onChange={handleStatusChange}
              options={INVESTIGATION_STATUS_OPTIONS}
              className="w-40"
            />
          </div>

          {/* Tabs */}
          <Tabs
            tabs={[
              { id: 'overview', label: 'Overview', icon: <Eye size={14} /> },
              { id: 'timeline', label: 'Timeline', icon: <Clock size={14} /> },
              { id: 'notes', label: 'Notes', icon: <MessageSquare size={14} />, count: notesData?.total },
            ]}
            activeTab={tab}
            onChange={setTab}
          />

          {tab === 'overview' && (
            <div className="space-y-4 text-sm">
              <div>
                <p className="text-xs font-medium text-muted-foreground uppercase tracking-wider mb-1">
                  Investigation Notes
                </p>
                <p className="text-foreground leading-relaxed">
                  {inv.notes || 'No initial notes provided for this investigation.'}
                </p>
              </div>
            </div>
          )}

          {tab === 'timeline' && (
            <div className="space-y-4">
              {(!timeline || timeline.length === 0) ? (
                <p className="text-xs text-muted-foreground py-4 text-center">No timeline events recorded.</p>
              ) : (
                <div className="relative pl-6 space-y-6 before:absolute before:left-2 before:top-2 before:bottom-2 before:w-0.5 before:bg-border">
                  {timeline.map((item) => (
                    <div key={item.id} className="relative">
                      <div className="absolute -left-6 top-1 w-2.5 h-2.5 rounded-full bg-emerald-500 ring-4 ring-card" />
                      <div className="flex items-baseline justify-between text-xs">
                        <span className="font-semibold text-foreground">{item.event_type}</span>
                        <span className="text-muted-foreground">
                          {formatDateTime(item.created_at)}
                        </span>
                      </div>
                      <p className="text-xs text-muted-foreground mt-1">{item.description}</p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {tab === 'notes' && (
            <div className="space-y-4">
              <form onSubmit={handleAddNote} className="space-y-2">
                <textarea
                  value={newNote}
                  onChange={(e) => setNewNote(e.target.value)}
                  placeholder="Add an investigation case note..."
                  rows={3}
                  className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 resize-none"
                />
                <div className="flex justify-end">
                  <Button type="submit" loading={addNoteMutation.isPending} size="sm">
                    Add Note
                  </Button>
                </div>
              </form>

              <div className="space-y-3 pt-2">
                {(notesData?.items ?? []).map((note) => (
                  <div key={note.id} className="p-3 bg-secondary/40 border border-border rounded-lg space-y-1">
                    <div className="flex items-center justify-between text-xs text-muted-foreground">
                      <span className="font-medium text-foreground">
                        {note.author?.full_name || 'Investigator'}
                      </span>
                      <span>{formatDateTime(note.created_at)}</span>
                    </div>
                    <p className="text-xs text-foreground/90">{note.note}</p>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      )}
    </Drawer>
  );
}

export default function InvestigationsPage() {
  const [filters, setFilters] = useState<InvestigationFilters>({ page: 1, page_size: 20 });
  const [createOpen, setCreateOpen] = useState(false);
  const [activeInvId, setActiveInvId] = useState<string | null>(null);

  const { data, isLoading } = useInvestigations(filters);
  const { data: reportsData } = useCrimeReports({ page: 1, page_size: 100 });
  const createMutation = useCreateInvestigation();

  const reports = reportsData?.items ?? [];

  const { register, handleSubmit, control, reset, formState: { errors } } = useForm<InvestigationFormData>({
    resolver: zodResolver(investigationSchema),
    defaultValues: { priority: 'MEDIUM' },
  });

  const handleCreate = async (formData: InvestigationFormData) => {
    await createMutation.mutateAsync(formData);
    setCreateOpen(false);
    reset();
  };

  const columns: Column<Investigation & Record<string, unknown>>[] = [
    {
      key: 'report',
      header: 'Crime Report',
      render: (_, row) => (
        <div>
          <p className="font-medium text-foreground">{row.report?.title || '—'}</p>
          <p className="text-xs text-emerald-400 font-mono">{row.report?.crime_number}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      width: '140px',
      render: (v) => <InvestigationStatusBadge status={v as InvestigationStatus} />,
    },
    {
      key: 'priority',
      header: 'Priority',
      width: '120px',
      render: (v) => <PriorityBadge priority={v as Priority} />,
    },
    {
      key: 'created_at',
      header: 'Created',
      width: '130px',
      render: (v) => formatDate(v as string),
    },
    {
      key: 'id',
      header: 'Actions',
      width: '80px',
      render: (_, row) => (
        <button
          onClick={(e) => {
            e.stopPropagation();
            setActiveInvId(row.id as string);
          }}
          className="p-1.5 rounded text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
          title="View Details"
        >
          <Eye size={14} />
        </button>
      ),
    },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Investigation Management</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            {data?.total ?? 0} active & historical cases
          </p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="md">
          <Plus size={14} />
          New Investigation
        </Button>
      </div>

      <Card>
        <div className="px-5 py-4 flex flex-wrap gap-3">
          <SearchBar
            value={filters.q ?? ''}
            onChange={(q) => setFilters((f) => ({ ...f, q, page: 1 }))}
            placeholder="Search investigations..."
            className="flex-1 min-w-[200px]"
          />
          <Dropdown
            value={filters.status ?? ''}
            onChange={(v) => setFilters((f) => ({ ...f, status: v as InvestigationStatus | '', page: 1 }))}
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

      <Card>
        {!isLoading && (data?.items ?? []).length === 0 ? (
          <EmptyState
            icon={<Search size={24} />}
            title="No investigations found"
            description="Create a new investigation case from an existing crime report."
            action={
              <Button onClick={() => setCreateOpen(true)} size="sm">
                <Plus size={13} />
                New Investigation
              </Button>
            }
          />
        ) : (
          <>
            <Table
              columns={columns as Column<Record<string, unknown>>[]}
              data={(data?.items ?? []) as unknown as Record<string, unknown>[]}
              onRowClick={(row) => setActiveInvId(row.id as string)}
              loading={isLoading}
              emptyMessage="No investigations match your filters."
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
      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="Open New Investigation">
        <form onSubmit={handleSubmit(handleCreate)} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Select Crime Report *
            </label>
            <Controller
              name="report_id"
              control={control}
              render={({ field }) => (
                <Dropdown
                  value={field.value}
                  onChange={field.onChange}
                  options={reports.map((r) => ({
                    label: `${r.crime_number} - ${r.title}`,
                    value: r.id,
                  }))}
                  placeholder="Select crime report"
                />
              )}
            />
            {errors.report_id && <p className="text-[11px] text-red-400 mt-1">{errors.report_id.message}</p>}
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Priority *
            </label>
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
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Initial Investigation Notes
            </label>
            <textarea
              {...register('notes')}
              rows={3}
              placeholder="Initial findings or instructions..."
              className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 resize-none"
            />
          </div>

          <div className="flex justify-end pt-2 border-t border-border">
            <Button type="submit" loading={createMutation.isPending} size="md">
              Create Case
            </Button>
          </div>
        </form>
      </Modal>

      {/* Detail Drawer */}
      <InvestigationDetailDrawer
        investigationId={activeInvId}
        onClose={() => setActiveInvId(null)}
      />
    </div>
  );
}
