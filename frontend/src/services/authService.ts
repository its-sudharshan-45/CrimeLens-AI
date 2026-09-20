import { supabase } from '@/lib/supabase';
import type { LoginFormData, SignupFormData, ForgotPasswordFormData, ResetPasswordFormData } from '@/types/auth';

const SITE_URL = import.meta.env.VITE_SITE_URL || window.location.origin;

// Normalize Supabase error messages for users
function normalizeError(error: unknown): string {
  if (!error) return 'An unexpected error occurred';
  const msg = (error as { message?: string }).message || String(error);

  if (msg.includes('Invalid login credentials')) return 'Invalid email or password. Please try again.';
  if (msg.includes('Email not confirmed')) return 'Please verify your email address before signing in.';
  if (msg.includes('User already registered')) return 'An account with this email already exists.';
  if (msg.includes('Password should be at least')) return 'Password must be at least 8 characters.';
  if (msg.includes('Unable to validate email')) return 'Please enter a valid email address.';
  if (msg.includes('rate limit')) return 'Too many attempts. Please wait before trying again.';
  if (msg.includes('network') || msg.includes('fetch')) return 'Network error. Please check your connection.';
  if (msg.includes('JWT expired') || msg.includes('session_not_found')) return 'Your session has expired. Please sign in again.';

  return msg;
}

export const authService = {
  async signIn({ email, password }: LoginFormData) {
    const { data, error } = await supabase.auth.signInWithPassword({ email, password });
    if (error) throw new Error(normalizeError(error));
    return data;
  },

  async signUp({ email, password, fullName }: SignupFormData) {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: { full_name: fullName },
        emailRedirectTo: `${SITE_URL}/verify-email`,
      },
    });
    if (error) throw new Error(normalizeError(error));
    return data;
  },

  async signOut() {
    const { error } = await supabase.auth.signOut();
    if (error) throw new Error(normalizeError(error));
  },

  async signInWithGoogle() {
    const { error } = await supabase.auth.signInWithOAuth({
      provider: 'google',
      options: {
        redirectTo: `${SITE_URL}/dashboard`,
        queryParams: {
          access_type: 'offline',
          prompt: 'consent',
        },
      },
    });
    if (error) throw new Error(normalizeError(error));
  },

  async resetPassword({ email }: ForgotPasswordFormData) {
    const { error } = await supabase.auth.resetPasswordForEmail(email, {
      redirectTo: `${SITE_URL}/reset-password`,
    });
    if (error) throw new Error(normalizeError(error));
  },

  async updatePassword({ password }: ResetPasswordFormData) {
    const { error } = await supabase.auth.updateUser({ password });
    if (error) throw new Error(normalizeError(error));
  },

  async resendVerification(email: string) {
    const { error } = await supabase.auth.resend({
      type: 'signup',
      email,
      options: {
        emailRedirectTo: `${SITE_URL}/verify-email`,
      },
    });
    if (error) throw new Error(normalizeError(error));
  },

  async getSession() {
    const { data, error } = await supabase.auth.getSession();
    if (error) throw new Error(normalizeError(error));
    return data.session;
  },

  onAuthStateChange(callback: Parameters<typeof supabase.auth.onAuthStateChange>[0]) {
    return supabase.auth.onAuthStateChange(callback);
  },
};
