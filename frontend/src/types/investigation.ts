import type { PaginationParams, SortParams } from './api';

export type InvestigationStatus =
  | 'OPEN'
  | 'UNDER_INVESTIGATION'
  | 'WAITING_FOR_EVIDENCE'
  | 'ON_HOLD'
  | 'CLOSED'
  | 'ARCHIVED';

export const INVESTIGATION_STATUS_OPTIONS: { label: string; value: InvestigationStatus }[] = [
  { label: 'Open', value: 'OPEN' },
  { label: 'Under Investigation', value: 'UNDER_INVESTIGATION' },
  { label: 'Waiting for Evidence', value: 'WAITING_FOR_EVIDENCE' },
  { label: 'On Hold', value: 'ON_HOLD' },
  { label: 'Closed', value: 'CLOSED' },
  { label: 'Archived', value: 'ARCHIVED' },
];

export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface InvestigationAssignment {
  id: string;
  investigator_id: string;
  investigator?: { id: string; email: string; full_name?: string };
  assigned_at: string;
  is_active: boolean;
}

export interface Investigation {
  id: string;
  report_id: string;
  report?: {
    id: string;
    crime_number: string;
    title: string;
    status: string;
  };
  status: InvestigationStatus;
  priority: Priority;
  notes?: string;
  investigator_id?: string;
  investigator?: { id: string; email: string; full_name?: string };
  assignments?: InvestigationAssignment[];
  created_at: string;
  updated_at: string;
  closed_at?: string;
}

export interface InvestigationCreate {
  report_id: string;
  investigator_id?: string;
  priority: Priority;
  notes?: string;
}

export interface InvestigationStatusUpdate {
  status: InvestigationStatus;
}

export interface InvestigationAssign {
  investigator_id: string;
}

export interface InvestigationNote {
  id: string;
  investigation_id: string;
  author_id: string;
  author?: { id: string; email: string; full_name?: string };
  note: string;
  attachment_evidence_id?: string;
  created_at: string;
  updated_at: string;
}

export interface InvestigationNoteCreate {
  note: string;
  attachment_evidence_id?: string;
}

export interface InvestigationNoteUpdate {
  note: string;
}

export interface InvestigationTimeline {
  id: string;
  investigation_id: string;
  actor_id?: string;
  actor?: { id: string; email: string; full_name?: string };
  event_type: string;
  description: string;
  created_at: string;
}

export interface InvestigationFilters extends PaginationParams, SortParams {
  q?: string;
  status?: InvestigationStatus | '';
  priority?: Priority | '';
  investigator_id?: string;
  report_id?: string;
  date_from?: string;
  date_to?: string;
}
