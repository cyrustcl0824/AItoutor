import { create } from 'zustand'
import type { Student } from './api'

type AppState = { currentStudent: Student | null; setStudent: (student: Student | null) => void }
export const useAppStore = create<AppState>((set) => ({ currentStudent: null, setStudent: (currentStudent) => set({ currentStudent }) }))

