import type { PaginationParams, SortParams } from './api';

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

export interface CrimeLocationCreate {
  address?: string;
  city: string;
  district?: string;
  state: string;
  zip_code?: string;
  latitude?: number;
  longitude?: number;
  landmark?: string;
}

export interface CrimeLocationUpdate {
  address?: string;
  city?: string;
  district?: string;
  state?: string;
  zip_code?: string;
  latitude?: number;
  longitude?: number;
  landmark?: string;
}

export interface CrimeLocationFilters extends PaginationParams, SortParams {
  q?: string;
  city?: string;
  district?: string;
  state?: string;
}

export const INDIAN_STATES = [
  'Andhra Pradesh', 'Arunachal Pradesh', 'Assam', 'Bihar', 'Chhattisgarh',
  'Goa', 'Gujarat', 'Haryana', 'Himachal Pradesh', 'Jharkhand', 'Karnataka',
  'Kerala', 'Madhya Pradesh', 'Maharashtra', 'Manipur', 'Meghalaya', 'Mizoram',
  'Nagaland', 'Odisha', 'Punjab', 'Rajasthan', 'Sikkim', 'Tamil Nadu',
  'Telangana', 'Tripura', 'Uttar Pradesh', 'Uttarakhand', 'West Bengal',
  'Andaman and Nicobar Islands', 'Chandigarh', 'Dadra and Nagar Haveli and Daman and Diu',
  'Delhi', 'Jammu and Kashmir', 'Ladakh', 'Lakshadweep', 'Puducherry',
] as const;
