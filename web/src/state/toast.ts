import { create } from "zustand";

export type ToastKind = "success" | "error" | "info";

export type ToastItem = {
  id: string;
  kind: ToastKind;
  title: string;
  detail?: string;
};

type ToastState = {
  items: ToastItem[];
  push: (kind: ToastKind, title: string, detail?: string) => void;
  success: (title: string, detail?: string) => void;
  error: (title: string, detail?: string) => void;
  info: (title: string, detail?: string) => void;
  dismiss: (id: string) => void;
};

let seq = 0;

export const useToast = create<ToastState>((set, get) => ({
  items: [],
  push: (kind, title, detail) => {
    const id = `t-${Date.now()}-${++seq}`;
    set({ items: [...get().items.slice(-3), { id, kind, title, detail }] });
    window.setTimeout(() => get().dismiss(id), kind === "error" ? 5200 : 3200);
  },
  success: (title, detail) => get().push("success", title, detail),
  error: (title, detail) => get().push("error", title, detail),
  info: (title, detail) => get().push("info", title, detail),
  dismiss: (id) => set({ items: get().items.filter((t) => t.id !== id) }),
}));
