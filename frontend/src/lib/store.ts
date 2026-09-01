import { create } from "zustand";

type UiState = { studentId?: string; setStudentId: (id: string) => void };
export const useUiStore = create<UiState>((set) => ({ setStudentId: (studentId) => set({ studentId }) }));
