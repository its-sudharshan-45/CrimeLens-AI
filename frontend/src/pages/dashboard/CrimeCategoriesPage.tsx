import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';
import { Plus, Tag, Edit2, Trash2 } from 'lucide-react';
import {
  useCrimeCategories,
  useCreateCrimeCategory,
  useUpdateCrimeCategory,
  useDeleteCrimeCategory,
} from '@/hooks/useCrimeCategories';
import type { CrimeCategory } from '@/types/crimeCategory';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { SearchBar } from '@/components/ui/SearchBar';
import { Pagination } from '@/components/ui/Pagination';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';

const categorySchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  description: z.string().optional(),
  severity_level: z.coerce.number().int().min(1).max(10),
  color_code: z.string().regex(/^#[0-9A-Fa-f]{6}$/, 'Must be a valid hex color').optional().or(z.literal('')),
});
type CategoryFormData = z.infer<typeof categorySchema>;

const SEVERITY_COLORS = [
  { min: 1, max: 3, class: 'bg-blue-500', text: 'Low' },
  { min: 4, max: 6, class: 'bg-amber-500', text: 'Medium' },
  { min: 7, max: 8, class: 'bg-orange-500', text: 'High' },
  { min: 9, max: 10, class: 'bg-red-600', text: 'Critical' },
];

function getSeverityClass(level: number) {
  return SEVERITY_COLORS.find((s) => level >= s.min && level <= s.max)?.class ?? 'bg-slate-500';
}
function getSeverityText(level: number) {
  return SEVERITY_COLORS.find((s) => level >= s.min && level <= s.max)?.text ?? '';
}

function CategoryForm({
  defaultValues,
  onSubmit,
  loading,
}: {
  defaultValues?: Partial<CategoryFormData>;
  onSubmit: (data: CategoryFormData) => void;
  loading: boolean;
}) {
  const { register, handleSubmit, formState: { errors } } = useForm<CategoryFormData>({
    resolver: zodResolver(categorySchema),
    defaultValues: { severity_level: 5, color_code: '#10b981', ...defaultValues },
  });
  const fieldClass = 'w-full h-9 px-3 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 transition-colors';
  const labelClass = 'block text-xs font-medium text-muted-foreground mb-1';
  const errorClass = 'text-[11px] text-red-400 mt-1';

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <div>
        <label className={labelClass}>Category Name *</label>
        <input {...register('name')} placeholder="e.g. Theft" className={fieldClass} />
        {errors.name && <p className={errorClass}>{errors.name.message}</p>}
      </div>
      <div>
        <label className={labelClass}>Description</label>
        <textarea
          {...register('description')}
          rows={3}
          placeholder="Brief description of this crime category…"
          className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 resize-none"
        />
      </div>
      <div className="grid grid-cols-2 gap-4">
        <div>
          <label className={labelClass}>Severity Level (1–10) *</label>
          <input type="number" min={1} max={10} {...register('severity_level')} className={fieldClass} />
          {errors.severity_level && <p className={errorClass}>{errors.severity_level.message}</p>}
        </div>
        <div>
          <label className={labelClass}>Color Code</label>
          <input type="text" {...register('color_code')} placeholder="#10b981" className={fieldClass} />
          {errors.color_code && <p className={errorClass}>{errors.color_code.message}</p>}
        </div>
      </div>
      <div className="flex justify-end pt-2 border-t border-border">
        <Button type="submit" loading={loading} size="md">
          {defaultValues ? 'Update Category' : 'Create Category'}
        </Button>
      </div>
    </form>
  );
}

function CategoryCard({ cat, onEdit, onDelete }: { cat: CrimeCategory; onEdit: () => void; onDelete: () => void }) {
  return (
    <div className="bg-card border border-border rounded-xl p-5 hover:border-emerald-500/20 transition-all duration-200 group">
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2">
          {cat.color_code && (
            <div className="w-3 h-3 rounded-full shrink-0" style={{ background: cat.color_code }} />
          )}
          <h3 className="font-semibold text-foreground text-sm">{cat.name}</h3>
        </div>
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={onEdit} className="p-1.5 rounded text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors">
            <Edit2 size={12} />
          </button>
          <button onClick={onDelete} className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors">
            <Trash2 size={12} />
          </button>
        </div>
      </div>
      {cat.description && (
        <p className="text-xs text-muted-foreground mb-3 line-clamp-2">{cat.description}</p>
      )}
      <div className="flex items-center gap-2">
        <div className="flex-1 h-1.5 bg-secondary rounded-full overflow-hidden">
          <div
            className={`h-full rounded-full transition-all ${getSeverityClass(cat.severity_level)}`}
            style={{ width: `${cat.severity_level * 10}%` }}
          />
        </div>
        <span className="text-[11px] font-medium text-muted-foreground">
          {cat.severity_level}/10 · {getSeverityText(cat.severity_level)}
        </span>
      </div>
    </div>
  );
}

export default function CrimeCategoriesPage() {
  const [filters, setFilters] = useState({ page: 1, page_size: 20, q: '' });
  const [createOpen, setCreateOpen] = useState(false);
  const [editCat, setEditCat] = useState<CrimeCategory | null>(null);
  const [deleteCat, setDeleteCat] = useState<string | null>(null);

  const { data, isLoading } = useCrimeCategories(filters);
  const createMutation = useCreateCrimeCategory();
  const updateMutation = useUpdateCrimeCategory();
  const deleteMutation = useDeleteCrimeCategory();

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Crime Categories</h1>
          <p className="text-sm text-muted-foreground mt-0.5">{data?.total ?? 0} categories</p>
        </div>
        <Button onClick={() => setCreateOpen(true)} size="md">
          <Plus size={14} />New Category
        </Button>
      </div>

      <div className="flex gap-3">
        <SearchBar
          value={filters.q}
          onChange={(q) => setFilters((f) => ({ ...f, q, page: 1 }))}
          placeholder="Search categories…"
          className="flex-1 max-w-sm"
        />
      </div>

      {isLoading ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
          {Array.from({ length: 8 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-5 space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-full" />
              <Skeleton className="h-1.5 w-full rounded-full" />
            </div>
          ))}
        </div>
      ) : (data?.items ?? []).length === 0 ? (
        <EmptyState
          icon={<Tag size={24} />}
          title="No categories found"
          description="Create your first crime category."
          action={<Button onClick={() => setCreateOpen(true)} size="sm"><Plus size={13} />Create Category</Button>}
        />
      ) : (
        <>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
            {(data?.items ?? []).map((cat) => (
              <CategoryCard
                key={cat.id}
                cat={cat}
                onEdit={() => setEditCat(cat)}
                onDelete={() => setDeleteCat(cat.id)}
              />
            ))}
          </div>
          {data && (
            <Pagination
              page={data.page}
              totalPages={data.total_pages}
              total={data.total}
              pageSize={data.page_size}
              onPageChange={(p) => setFilters((f) => ({ ...f, page: p }))}
            />
          )}
        </>
      )}

      <Modal open={createOpen} onClose={() => setCreateOpen(false)} title="New Crime Category">
        <CategoryForm
          loading={createMutation.isPending}
          onSubmit={async (data) => { await createMutation.mutateAsync(data); setCreateOpen(false); }}
        />
      </Modal>

      <Modal open={!!editCat} onClose={() => setEditCat(null)} title="Edit Category">
        {editCat && (
          <CategoryForm
            loading={updateMutation.isPending}
            defaultValues={{ name: editCat.name, description: editCat.description, severity_level: editCat.severity_level, color_code: editCat.color_code }}
            onSubmit={async (data) => { await updateMutation.mutateAsync({ id: editCat.id, payload: data }); setEditCat(null); }}
          />
        )}
      </Modal>

      <ConfirmDialog
        open={!!deleteCat}
        onClose={() => setDeleteCat(null)}
        onConfirm={async () => { if (deleteCat) { await deleteMutation.mutateAsync(deleteCat); setDeleteCat(null); } }}
        title="Delete Category"
        description="This will permanently remove the category. Reports using it may be affected."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
      />
    </div>
  );
}
