// Shared API response shapes

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface ApiError {
  status: number;
  detail?: string;
  message: string;
}

export interface SortParams {
  sort_by?: string;
  order?: 'asc' | 'desc';
}

export interface PaginationParams {
  page?: number;
  page_size?: number;
}
