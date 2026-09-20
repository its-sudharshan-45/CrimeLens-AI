import type { PaginationParams, SortParams } from './api';

export type CrimeStatus = 'OPEN' | 'UNDER_INVESTIGATION' | 'CLOSED' | 'ARCHIVED';
export type Priority = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface CrimeCategory {
  id: string;
  name: string;
  description?: string;
  severity_level: number;
  color_code?: string;
  created_at: string;
  updated_at: string;
}

export interface CrimeLocation {
  id: string;
  address?: string;
  city: string;
  district?: string;
  state: string;
  zip_code?: string;
  latitude?: number;
  longitude?: number;
  landmark?: string;
  created_at: string;
  updated_at: string;
}

export interface Reporter {
  id: string;
  email: string;
  full_name?: string;
}

export interface CrimeReport {
  id: string;
  crime_number: string;
  title: string;
  description?: string;
  status: CrimeStatus;
  priority: Priority;
  incident_date: string;
  report_date: string;
  victim_count?: number;
  estimated_loss?: number;
  officer_name?: string;
  reporter_id: string;
  reporter?: Reporter;
  category_id: string;
  category?: CrimeCategory;
  location_id: string;
  location?: CrimeLocation;
  created_at: string;
  updated_at: string;
}

export interface CrimeReportCreate {
  title: string;
  description?: string;
  priority: Priority;
  incident_date: string;
  victim_count?: number;
  estimated_loss?: number;
  officer_name?: string;
  category_id: string;
  location_id: string;
}

export interface CrimeReportUpdate {
  title?: string;
  description?: string;
  priority?: Priority;
  status?: CrimeStatus;
  incident_date?: string;
  victim_count?: number;
  estimated_loss?: number;
  officer_name?: string;
  category_id?: string;
  location_id?: string;
}

export interface CrimeReportFilters extends PaginationParams, SortParams {
  q?: string;
  status?: CrimeStatus | '';
  priority?: Priority | '';
  category_id?: string;
  reporter_id?: string;
  date_from?: string;
  date_to?: string;
}
