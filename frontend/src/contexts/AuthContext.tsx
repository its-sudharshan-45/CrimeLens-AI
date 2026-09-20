import React, { createContext, useCallback, useEffect, useRef, useState } from 'react';
import type { Session as SupabaseSession, User as SupabaseUser } from '@supabase/supabase-js';
import { authService } from '@/services/authService';
import type {
  AuthContextType,
  ForgotPasswordFormData,
  LoginFormData,
  ResetPasswordFormData,
  SignupFormData,
  User,
} from '@/types/auth';

export const AuthContext = createContext<AuthContextType | null>(null);

function mapSupabaseUser(supabaseUser: SupabaseUser): User {
  return {
    id: supabaseUser.id,
    email: supabaseUser.email ?? '',
    full_name: supabaseUser.user_metadata?.full_name ?? supabaseUser.user_metadata?.name ?? '',
    avatar_url: supabaseUser.user_metadata?.avatar_url ?? '',
    email_confirmed_at: supabaseUser.email_confirmed_at ?? null,
    created_at: supabaseUser.created_at,
  };
}

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [session, setSession] = useState<{
    access_token: string;
    refresh_token: string;
    expires_at?: number;
    user: User;
  } | null>(null);
  const [loading, setLoading] = useState(true);
  const pendingEmailRef = useRef<string | null>(null);

  useEffect(() => {
    // Hydrate session on mount
    authService.getSession().then((s) => {
      if (s) {
        const mappedUser = mapSupabaseUser(s.user as SupabaseUser);
        setUser(mappedUser);
        setSession({
          access_token: s.access_token,
          refresh_token: s.refresh_token,
          expires_at: s.expires_at,
          user: mappedUser,
        });
      }
      setLoading(false);
    }).catch(() => {
      setLoading(false);
    });

    // Subscribe to auth state changes
    const { data: { subscription } } = authService.onAuthStateChange(
      async (_event: string, supabaseSession: SupabaseSession | null) => {
        if (supabaseSession) {
          const mappedUser = mapSupabaseUser(supabaseSession.user as SupabaseUser);
          setUser(mappedUser);
          setSession({
            access_token: supabaseSession.access_token,
            refresh_token: supabaseSession.refresh_token,
            expires_at: supabaseSession.expires_at,
            user: mappedUser,
          });
        } else {
          setUser(null);
          setSession(null);
        }
        setLoading(false);
      }
    );

    return () => subscription.unsubscribe();
  }, []);

  const signIn = useCallback(async (data: LoginFormData) => {
    await authService.signIn(data);
  }, []);

  const signUp = useCallback(async (data: SignupFormData) => {
    pendingEmailRef.current = data.email;
    await authService.signUp(data);
  }, []);

  const signOut = useCallback(async () => {
    await authService.signOut();
    setUser(null);
    setSession(null);
  }, []);

  const signInWithGoogle = useCallback(async () => {
    await authService.signInWithGoogle();
  }, []);

  const resetPassword = useCallback(async (data: ForgotPasswordFormData) => {
    await authService.resetPassword(data);
  }, []);

  const updatePassword = useCallback(async (data: ResetPasswordFormData) => {
    await authService.updatePassword(data);
  }, []);

  const resendVerification = useCallback(async () => {
    const email = user?.email ?? pendingEmailRef.current ?? '';
    if (!email) throw new Error('No email address found. Please sign in again.');
    await authService.resendVerification(email);
  }, [user]);

  const isAuthenticated = !!user && !!session;
  const isEmailVerified = !!user?.email_confirmed_at;

  const value: AuthContextType = {
    user,
    session,
    loading,
    isAuthenticated,
    isEmailVerified,
    signIn,
    signUp,
    signOut,
    signInWithGoogle,
    resetPassword,
    updatePassword,
    resendVerification,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}
