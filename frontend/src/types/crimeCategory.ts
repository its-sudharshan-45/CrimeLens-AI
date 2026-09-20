import type { PaginationParams, SortParams } from './api';

export interface CrimeCategory {
  id: string;
  name: string;
  description?: string;
  severity_level: number;
  color_code?: string;
  created_at: string;
  updated_at: string;
}

export interface CrimeCategoryCreate {
  name: string;
  description?: string;
  severity_level: number;
  color_code?: string;
}

export interface CrimeCategoryUpdate {
  name?: string;
  description?: string;
  severity_level?: number;
  color_code?: string;
}

export interface CrimeCategoryFilters extends PaginationParams, SortParams {
  q?: string;
}
