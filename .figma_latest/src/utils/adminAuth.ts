const STORAGE_KEY = 'dsp_admin'

// Credentials intentionally kept minimal for a demo SPA.
// In a production deployment these would be validated server-side.
const VALID = { e: 'admin@dspai.in', p: 'dsp@admin2026' }

export function verifyAdminCredentials(email: string, password: string): boolean {
  return email === VALID.e && password === VALID.p
}

export function setAdminSession() {
  sessionStorage.setItem(STORAGE_KEY, '1')
}

export function isAdminAuthed(): boolean {
  return sessionStorage.getItem(STORAGE_KEY) === '1'
}

export function clearAdminSession() {
  sessionStorage.removeItem(STORAGE_KEY)
}
