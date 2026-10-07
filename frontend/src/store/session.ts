import { create } from 'zustand';
import { persist, createJSONStorage } from 'zustand/middleware';
import type { Language } from '@/lib/i18n';

export type Role = 'student' | 'parent';

export interface FamilyPartner {
  role: Role;
  name: string;
}

export interface FamilySession {
  code: string;
  token: string;
  partner: FamilyPartner | null;
}

export interface SessionState {
  role: Role | null;
  name: string;
  lang: Language;
  langChosen: boolean;
  family: FamilySession | null;
  hasHydrated: boolean;
  setRole: (role: Role | null) => void;
  setName: (name: string) => void;
  setLang: (lang: Language) => void;
  setFamily: (family: FamilySession | null) => void;
  setPartner: (partner: FamilyPartner | null) => void;
  setSession: (
    data: Partial<
      Pick<SessionState, 'role' | 'name' | 'lang' | 'langChosen' | 'family'>
    >
  ) => void;
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
      family: null,
      hasHydrated: false,
      setRole: (role) => set({ role }),
      setName: (name) => set({ name }),
      setLang: (lang) => set({ lang, langChosen: true }),
      setFamily: (family) => set({ family }),
      setPartner: (partner) =>
        set((state) => ({
          family: state.family
            ? { ...state.family, partner }
            : null,
        })),
      setSession: (data) => set((state) => ({ ...state, ...data })),
      clearSession: () =>
        set({
          role: null,
          name: '',
          lang: 'en',
          langChosen: false,
          family: null,
        }),
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
