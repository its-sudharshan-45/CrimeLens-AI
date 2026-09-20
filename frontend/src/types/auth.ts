// Authentication types
export interface User {
  id: string;
  email: string;
  full_name?: string;
  avatar_url?: string;
  email_confirmed_at?: string | null;
  created_at?: string;
}

export interface AuthState {
  user: User | null;
  session: Session | null;
  loading: boolean;
  isAuthenticated: boolean;
  isEmailVerified: boolean;
}

export interface Session {
  access_token: string;
  refresh_token: string;
  expires_at?: number;
  user: User;
}

// Form data types
export interface LoginFormData {
  email: string;
  password: string;
  rememberMe?: boolean;
}

export interface SignupFormData {
  fullName: string;
  email: string;
  password: string;
  confirmPassword: string;
}

export interface ForgotPasswordFormData {
  email: string;
}

export interface ResetPasswordFormData {
  password: string;
  confirmPassword: string;
}

// Auth context methods
export interface AuthContextType extends AuthState {
  signIn: (data: LoginFormData) => Promise<void>;
  signUp: (data: SignupFormData) => Promise<void>;
  signOut: () => Promise<void>;
  signInWithGoogle: () => Promise<void>;
  resetPassword: (data: ForgotPasswordFormData) => Promise<void>;
  updatePassword: (data: ResetPasswordFormData) => Promise<void>;
  resendVerification: () => Promise<void>;
}

// Password strength
export type PasswordStrength = 'weak' | 'fair' | 'good' | 'strong';

export interface PasswordStrengthResult {
  strength: PasswordStrength;
  score: number; // 0-4
  label: string;
  color: string;
}
