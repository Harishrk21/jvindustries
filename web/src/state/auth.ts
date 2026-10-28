import { create } from "zustand";
import { persist } from "zustand/middleware";
import type { User } from "../lib/api";
import * as api from "../lib/api";

type AuthState = {
  token: string | null;
  user: User | null;
  login: (userId: string, password: string) => Promise<void>;
  setUser: (user: User) => void;
  logout: () => void;
};

export const useAuth = create<AuthState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      login: async (userId, password) => {
        const res = await api.login(userId, password);
        set({ token: res.access_token, user: res.user });
      },
      setUser: (user) => set({ user }),
      logout: () => set({ token: null, user: null }),
    }),
    { name: "jvoms-auth" },
  ),
);
