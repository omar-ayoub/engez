import { create } from "zustand";
import { persist } from "zustand/middleware";

export interface UserInfo {
  id: string;
  email: string;
  name: string;
  name_ar: string;
  role: string;
  company_id: string;
  company_name: string;
  company_name_ar: string;
}

interface AuthState {
  user: UserInfo | null;
  accessToken: string | null;
  isAuthenticated: boolean;
  login: (accessToken: string, user: UserInfo) => void;
  logout: () => void;
  setAccessToken: (token: string) => void;
}

export const useAuthStore = create<AuthState>()(
  persist(
    (set) => ({
      user: null,
      accessToken: null,
      isAuthenticated: false,
      login: (accessToken, user) =>
        set({ accessToken, user, isAuthenticated: true }),
      logout: () =>
        set({ accessToken: null, user: null, isAuthenticated: false }),
      setAccessToken: (token) => set({ accessToken: token }),
    }),
    {
      name: "engez-auth",
      partialize: (state) => ({
        user: state.user,
        isAuthenticated: state.isAuthenticated,
      }),
    }
  )
);
