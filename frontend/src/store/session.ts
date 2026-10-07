import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Language } from '@/lib/i18n';

export type Role = 'student' | 'parent';

export interface SessionState {
  role: Role | null;
  name: string;
  lang: Language;
  langChosen: boolean;
  hasHydrated: boolean;
  setRole: (role: Role | null) => void;
  setName: (name: string) => void;
  setLang: (lang: Language) => void;
  setSession: (data: Partial<Pick<SessionState, 'role' | 'name' | 'lang' | 'langChosen'>>) => void;
  clearSession: () => void;
  setHasHydrated: (hydrated: boolean) => void;
}

export const useSessionStore = create<SessionState>()(
  persist(
    (set) => ({
      role: null,
      name: '',
      lang: 'en',
      langChosen: false,
      hasHydrated: false,
      setRole: (role) => set({ role }),
      setName: (name) => set({ name }),
      setLang: (lang) => set({ lang, langChosen: true }),
      setSession: (data) => set((state) => ({ ...state, ...data })),
      clearSession: () =>
        set({ role: null, name: '', lang: 'en', langChosen: false }),
      setHasHydrated: (hasHydrated) => set({ hasHydrated }),
    }),
    {
      name: 'udaan_session',
      storage: createJSONStorage(() => {
        if (typeof window !== 'undefined') {
          return sessionStorage;
        }
        return {
          getItem: () => null,
          setItem: () => {},
          removeItem: () => {},
        };
      }),
      skipHydration: true,
      onRehydrateStorage: () => (state) => {
        state?.setHasHydrated(true);
      },
    }
  )
);
