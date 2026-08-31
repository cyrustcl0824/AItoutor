import { describe, expect, it } from 'vitest'
import { useAppStore } from './store'

describe('student selection', () => {
  it('stores and clears the active student', () => {
    const student = { id: 's1', name: 'Amy', display_name: 'Amy', grade: 3, preferences: {}, active: true }
    useAppStore.getState().setStudent(student)
    expect(useAppStore.getState().currentStudent?.id).toBe('s1')
    useAppStore.getState().setStudent(null)
    expect(useAppStore.getState().currentStudent).toBeNull()
  })
})

