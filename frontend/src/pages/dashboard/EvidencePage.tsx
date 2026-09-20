import { useState } from 'react';
import { Upload, File, FileText, Image, Film, Music, Archive, Download, Trash2, Eye, FolderOpen } from 'lucide-react';
import { formatDate } from '@/lib/utils';
import { useCrimeReports } from '@/hooks/useCrimeReports';
import {
  useReportEvidence,
  useUploadEvidence,
  useDeleteEvidence,
  evidenceService,
} from '@/hooks/useEvidence';
import type { Evidence } from '@/types/evidence';
import { formatFileSize } from '@/types/evidence';
import { Card } from '@/components/ui/Card';
import { Dropdown } from '@/components/ui/Dropdown';
import { Modal, ConfirmDialog } from '@/components/ui/Modal';
import { Button } from '@/components/ui/Button';
import { EmptyState } from '@/components/ui/EmptyState';
import { Skeleton } from '@/components/ui/Skeleton';
import { toast } from 'sonner';

function getFileIcon(type: string) {
  if (type.startsWith('image/')) return <Image size={18} className="text-emerald-400" />;
  if (type.startsWith('video/')) return <Film size={18} className="text-purple-400" />;
  if (type.startsWith('audio/')) return <Music size={18} className="text-blue-400" />;
  if (type.includes('pdf')) return <FileText size={18} className="text-red-400" />;
  if (type.includes('zip') || type.includes('archive') || type.includes('tar'))
    return <Archive size={18} className="text-amber-400" />;
  return <File size={18} className="text-muted-foreground" />;
}

export default function EvidencePage() {
  const [selectedReportId, setSelectedReportId] = useState<string>('');
  const [uploadOpen, setUploadOpen] = useState(false);
  const [file, setFile] = useState<File | null>(null);
  const [description, setDescription] = useState('');
  const [uploadProgress, setUploadProgress] = useState(0);
  const [deleteId, setDeleteId] = useState<string | null>(null);
  const [previewEvidence, setPreviewEvidence] = useState<Evidence | null>(null);

  const { data: reportsData, isLoading: reportsLoading } = useCrimeReports({ page: 1, page_size: 100 });
  const reports = reportsData?.items ?? [];

  const { data: evidenceData, isLoading: evidenceLoading } = useReportEvidence(
    selectedReportId || null,
    1,
    50
  );
  const evidenceItems = evidenceData?.items ?? [];

  const uploadMutation = useUploadEvidence();
  const deleteMutation = useDeleteEvidence();

  const handleUpload = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!file || !selectedReportId) return;

    try {
      await uploadMutation.mutateAsync({
        reportId: selectedReportId,
        file,
        description,
        onProgress: (pct) => setUploadProgress(pct),
      });
      setUploadOpen(false);
      setFile(null);
      setDescription('');
      setUploadProgress(0);
    } catch {
      // toast handled in hook
    }
  };

  const handleDownload = async (item: Evidence) => {
    try {
      const url = await evidenceService.getDownloadUrl(item.id);
      window.open(url, '_blank');
    } catch (err: any) {
      toast.error(err.message || 'Failed to generate download URL');
    }
  };

  return (
    <div className="space-y-5 animate-fade-in">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold text-foreground">Evidence Management</h1>
          <p className="text-sm text-muted-foreground mt-0.5">
            Secure digital chain of custody & file repository
          </p>
        </div>
        <Button
          onClick={() => setUploadOpen(true)}
          disabled={!selectedReportId}
          size="md"
        >
          <Upload size={14} />
          Upload Evidence
        </Button>
      </div>

      <Card className="p-5">
        <div className="max-w-md">
          <label className="block text-xs font-medium text-muted-foreground mb-1">
            Select Crime Report *
          </label>
          <Dropdown
            value={selectedReportId}
            onChange={(v) => setSelectedReportId(v)}
            options={reports.map((r) => ({
              label: `${r.crime_number} - ${r.title}`,
              value: r.id,
            }))}
            placeholder={reportsLoading ? 'Loading reports...' : 'Choose a crime report to view evidence'}
          />
        </div>
      </Card>

      {!selectedReportId ? (
        <EmptyState
          icon={<FolderOpen size={24} />}
          title="No Report Selected"
          description="Please select a crime report above to view or upload associated evidence files."
        />
      ) : evidenceLoading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="bg-card border border-border rounded-xl p-4 space-y-3">
              <Skeleton className="h-4 w-3/4" />
              <Skeleton className="h-3 w-1/2" />
              <Skeleton className="h-10 w-full" />
            </div>
          ))}
        </div>
      ) : evidenceItems.length === 0 ? (
        <EmptyState
          icon={<File size={24} />}
          title="No Evidence Files Uploaded"
          description="This report currently has no evidence attached. Upload relevant photos, documents, or media."
          action={
            <Button onClick={() => setUploadOpen(true)} size="sm">
              <Upload size={13} />
              Upload Evidence
            </Button>
          }
        />
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {evidenceItems.map((item) => (
            <Card key={item.id} className="p-4 flex flex-col justify-between hover:border-emerald-500/30 transition-colors">
              <div>
                <div className="flex items-start justify-between gap-3 mb-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <div className="p-2 rounded-lg bg-secondary shrink-0">
                      {getFileIcon(item.content_type)}
                    </div>
                    <div className="min-w-0">
                      <p className="text-sm font-medium text-foreground truncate" title={item.file_name}>
                        {item.file_name}
                      </p>
                      <p className="text-[11px] text-muted-foreground">
                        {formatFileSize(item.file_size)} • {formatDate(item.created_at)}
                      </p>
                    </div>
                  </div>
                </div>
                {item.description && (
                  <p className="text-xs text-muted-foreground mb-3 line-clamp-2">
                    {item.description}
                  </p>
                )}
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-border mt-3">
                <span className="text-[10px] text-muted-foreground font-mono">
                  ID: {item.id.slice(0, 8)}
                </span>
                <div className="flex items-center gap-1">
                  {item.content_type.startsWith('image/') && (
                    <button
                      onClick={() => setPreviewEvidence(item)}
                      className="p-1.5 rounded text-muted-foreground hover:text-foreground hover:bg-secondary transition-colors"
                      title="Preview"
                    >
                      <Eye size={13} />
                    </button>
                  )}
                  <button
                    onClick={() => handleDownload(item)}
                    className="p-1.5 rounded text-muted-foreground hover:text-emerald-400 hover:bg-emerald-500/10 transition-colors"
                    title="Download"
                  >
                    <Download size={13} />
                  </button>
                  <button
                    onClick={() => setDeleteId(item.id)}
                    className="p-1.5 rounded text-muted-foreground hover:text-red-400 hover:bg-red-500/10 transition-colors"
                    title="Delete"
                  >
                    <Trash2 size={13} />
                  </button>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Upload Modal */}
      <Modal
        open={uploadOpen}
        onClose={() => setUploadOpen(false)}
        title="Upload Evidence File"
        size="md"
      >
        <form onSubmit={handleUpload} className="space-y-4">
          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              File *
            </label>
            <input
              type="file"
              onChange={(e) => setFile(e.target.files?.[0] || null)}
              className="w-full text-xs text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-xs file:font-semibold file:bg-emerald-500/10 file:text-emerald-400 hover:file:bg-emerald-500/20 cursor-pointer"
              required
            />
          </div>

          <div>
            <label className="block text-xs font-medium text-muted-foreground mb-1">
              Description
            </label>
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
              placeholder="Context or notes about this piece of evidence..."
              className="w-full px-3 py-2 bg-secondary border border-border rounded-lg text-sm text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1 focus:ring-emerald-500/50 resize-none"
            />
          </div>

          {uploadMutation.isPending && (
            <div className="space-y-1">
              <div className="flex justify-between text-xs text-muted-foreground">
                <span>Uploading...</span>
                <span>{uploadProgress}%</span>
              </div>
              <div className="w-full h-1.5 bg-secondary rounded-full overflow-hidden">
                <div
                  className="h-full bg-emerald-500 transition-all duration-150"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          <div className="flex justify-end pt-2 border-t border-border">
            <Button
              type="submit"
              loading={uploadMutation.isPending}
              disabled={!file}
              size="md"
            >
              Upload
            </Button>
          </div>
        </form>
      </Modal>

      {/* Delete Confirmation */}
      <ConfirmDialog
        open={!!deleteId}
        onClose={() => setDeleteId(null)}
        onConfirm={async () => {
          if (deleteId) {
            await deleteMutation.mutateAsync(deleteId);
            setDeleteId(null);
          }
        }}
        title="Delete Evidence"
        description="Are you sure you want to delete this evidence record? This action will remove the digital record."
        confirmLabel="Delete"
        danger
        loading={deleteMutation.isPending}
      />

      {/* Image Preview Modal */}
      <Modal
        open={!!previewEvidence}
        onClose={() => setPreviewEvidence(null)}
        title={previewEvidence?.file_name || 'Evidence Preview'}
        size="lg"
      >
        {previewEvidence && (
          <div className="flex flex-col items-center justify-center p-2">
            <div className="max-h-[70vh] overflow-hidden rounded-lg border border-border">
              <img
                src={`${import.meta.env.VITE_API_URL || 'http://localhost:8000/api/v1'}/evidence/${previewEvidence.id}/download`}
                alt={previewEvidence.file_name}
                className="max-h-[65vh] w-auto object-contain"
                onError={(e) => {
                  (e.target as HTMLElement).style.display = 'none';
                }}
              />
            </div>
            {previewEvidence.description && (
              <p className="text-sm text-muted-foreground mt-3 text-center">
                {previewEvidence.description}
              </p>
            )}
          </div>
        )}
      </Modal>
    </div>
  );
}
