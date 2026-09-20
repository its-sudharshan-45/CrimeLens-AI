import { useState } from 'react';
import { useForm, Controller } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, MapPin, Edit2, Trash2 } from 'lucide-react';
import {
  useCrimeLocations,
  useCreateCrimeLocation,
  useUpdateCrimeLocation,
  useDeleteCrimeLocation,
} from '@/hooks/useCrimeLocations';
import type { CrimeLocation } from '@/types/crimeLocation';
import { INDIAN_STATES } from '@/types/crimeLocation';
import { Table, type Column } from '@/components/ui/Table';
import { Pagination } from '@/components/ui/Pagination';
import { SearchBar } from '@/components/ui/SearchBar';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { Dropdown } from '@/components/ui/Dropdown';
import { Button } from '@/components/ui/Button';
import { Card } from '@/components/ui/Card';
import { EmptyState } from '@/components/ui/EmptyState';

const locationSchema = z.object({
  address: z.string().optional(),
  city: z.string().min(2, 'City is required'),
  district: z.string().optional(),
  state: z.string().min(2, 'State is required'),
  zip_code: z.string().regex(/^\d{6}$/, 'Must be a 6-digit PIN code').optional().or(z.literal('')),
  latitude: z.coerce.number().min(6).max(38).optional().or(z.literal('')),
  longitude: z.coerce.number().min(68).max(98).optional().or(z.literal('')),
  landmark: z.string().optional(),
});
type LocationFormData = z.infer<typeof locationSchema>;

const STATE_OPTIONS = INDIAN_STATES.map((s) => ({ label: s, value: s }));

function LocationForm({
  defaultValues,
  onSubmit,
  loading,
}: {
  defaultValues?: Partial<LocationFormData>;
  onSubmit: (data: LocationFormData) => void;
  loading: boolean;
}) {
  const { register, handleSubmit, control, formState: { errors } } = useForm<LocationFormData>({
    resolver: zodResolver(locationSchema),
    defaultValues: { state: 'Maharashtra', ...defaultValues },
  });
  const fieldClass = 'w-full h-9 px-3 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 transition-colors';
  const labelClass = 'block text-xs font-medium text-muted-foreground mb-1';
  const errorClass = 'text-[11px] text-red-400 mt-1';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className={labelClass}>Street Address</label>
        <input {...register('address')} placeholder="123 Main Street" className={fieldClass} />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>City *</label>
          <input {...register('city')} placeholder="Mumbai" className={fieldClass} />
          {errors.city && <p className={errorClass}>{errors.city.message}</p>}
        </div>
        <div>
          <label className={labelClass}>District</label>
          <input {...register('district')} placeholder="Mumbai Suburban" className={fieldClass} />
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>State *</label>
          <Controller
            name="state"
            control={control}
            render={({ field }) => (
              <Dropdown
                value={field.value ?? ''}
                onChange={field.onChange}
                options={STATE_OPTIONS}
                placeholder="Select state"
              />
            )}
          />
          {errors.state && <p className={errorClass}>{errors.state.message}</p>}
        </div>
        <div>
          <label className={labelClass}>PIN Code</label>
          <input {...register('zip_code')} placeholder="400001" maxLength={6} className={fieldClass} />
          {errors.zip_code && <p className={errorClass}>{errors.zip_code.message}</p>}
        </div>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Latitude (6°N–38°N)</label>
          <input type="number" step="any" {...register('latitude')} placeholder="18.9733" className={fieldClass} />
          {errors.latitude && <p className={errorClass}>{errors.latitude.message as string}</p>}
        </div>
        <div>
          <label className={labelClass}>Longitude (68°E–98°E)</label>
          <input type="number" step="any" {...register('longitude')} placeholder="72.8236" className={fieldClass} />
          {errors.longitude && <p className={errorClass}>{errors.longitude.message as string}</p>}
        </div>
      </div>
      <div>
        <label className={labelClass}>Landmark</label>
        <input {...register('landmark')} placeholder="Near CST Railway Station" className={fieldClass} />
      </div>
      <div className="flex justify-end pt-2 border-t border-border">
        <Button type="submit" loading={loading} size="md">
          {defaultValues ? 'Update Location' : 'Create Location'}
        </Button>
      </div>
    </form>
  );
}

export default function CrimeLocationsPage() {
  const [filters, setFilters] = useState({ page: 1, page_size: 20, q: '', state: '' });
  const [sortBy, setSortBy] = useState('created_at');
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>('desc');
  const [createOpen, setCreateOpen] = useState(false);
  const [editLoc, setEditLoc] = useState<CrimeLocation | null>(null);
  const [deleteLoc, setDeleteLoc] = useState<string | null>(null);

  const { data, isLoading } = useCrimeLocations({ ...filters, sort_by: sortBy, order: sortOrder });
  const createMutation = useCreateCrimeLocation();
  const updateMutation = useUpdateCrimeLocation();
  const deleteMutation = useDeleteCrimeLocation();

  const handleSort = (key: string) => {
    if (key === sortBy) setSortOrder((o) => (o === 'asc' ? 'desc' : 'asc'));
    else { setSortBy(key); setSortOrder('asc'); }
  };

  const columns: Column<CrimeLocation & Record<string, unknown>>[] = [
    { key: 'city', header: 'City', sortable: true },
    { key: 'district', header: 'District', sortable: true, render: (v) => String(v || '—') },
    { key: 'state', header: 'State', sortable: true },
    {
      key: 'latitude', header: 'Coordinates', width: '150px',
      render: (_, row) =>
        row.latitude && row.longitude
          ? <span className="font-mono text-xs text-muted-foreground">{Number(row.latitude).toFixed(4)}, {Number(row.longitude).toFixed(4)}</span>
          : '—',
    },
    {
      key: 'landmark', header: 'Landmark',
      render: (v) => <span className="text-muted-foreground text-xs">{String(v || '—')}</span>,
    },
    {
      key: 'id', header: 'Actions', width: '90px',
      render: (_, row) => (
        <div className="flex items-center gap-2" onClick={(e) => e.stopPropagation()}>
          <button onClick={() => setEditLoc(row as unknown as CrimeLocation)} className="p-1.5 rounded text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors" title="Edit">
            <Edit2 size={13} />
          </button>
          <button onClick={() => setDeleteLoc(row.id as string)} className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors" title="Delete">
            <Trash2 size={13} />
          </button>
        </div>
      ),
    },
  ];

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Crime Locations</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{data?.total ?? 0} locations</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="md">
          <Plus size={14} />New Location
        </Button>
      </div>

      <Card>
        <div className="px-5 py-4 flex flex-wrap gap-3">
          <SearchBar
            value={filters.q}
            onChange={(q) => setFilters((f) => ({ ...f, q, page: 1 }))}
            placeholder="Search city, district, landmark…"
            className="flex-1 min-w-[200px]"
          />
          <Dropdown
            value={filters.state}
            onChange={(v) => setFilters((f) => ({ ...f, state: v, page: 1 }))}
            options={[{ label: 'All States', value: '' }, ...STATE_OPTIONS]}
            className="w-52"
          />
        </div>
      </Card>

      <Card>
        {(!isLoading && (data?.items ?? []).length === 0) ? (
          <EmptyState
            icon={<MapPin size={24} />}
            title="No locations found"
            description="Add your first crime location."
            action={<Button onClick={() => setCreateOpen(true)} size="sm"><Plus size={13} />Add Location</Button>}
          />
        ) : (
          <>
            <Table
              columns={columns as Column<Record<string, unknown>>[]}
              data={(data?.items ?? []) as unknown as Record<string, unknown>[]}
              sortBy={sortBy}
              sortOrder={sortOrder}
              onSort={handleSort}
              loading={isLoading}
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

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New Crime Location" size="lg">
        <LocationForm
          loading={createMutation.isPending}
          onSubmit={async (data) => { await createMutation.mutateAsync(data as any); setCreateOpen(false); }}
        />
      </Modal>

      <Modal open={!!editLoc} onClose={() => setEditLoc(null)} title="Edit Location" size="lg">
        {editLoc && (
          <LocationForm
            loading={updateMutation.isPending}
            defaultValues={{ address: editLoc.address, city: editLoc.city, district: editLoc.district, state: editLoc.state, zip_code: editLoc.zip_code, latitude: editLoc.latitude as any, longitude: editLoc.longitude as any, landmark: editLoc.landmark }}
            onSubmit={async (data) => { await updateMutation.mutateAsync({ id: editLoc.id, payload: data as any }); setEditLoc(null); }}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={!!deleteLoc}
        onClose={() => setDeleteLoc(null)}
        onConfirm={async () => { if (deleteLoc) { await deleteMutation.mutateAsync(deleteLoc); setDeleteLoc(null); } }}
        title="Delete Location"
        description="This location will be removed. Reports linked to it may be affected."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
