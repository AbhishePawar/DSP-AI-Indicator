import { createContext, useContext, useState, useCallback, type ReactNode } from 'react'

interface AuthUser {
  name: string
  email: string
  initials: string
  plan: string
}

interface AuthContextValue {
  isLoggedIn: boolean
  user: AuthUser | null
  login: (user?: Partial<AuthUser>) => void
  logout: () => void
}

const DEFAULT_USER: AuthUser = {
  name: 'Demo User',
  email: 'demo@dspai.in',
  initials: 'DU',
  plan: 'Pro Plan',
}

const STORAGE_KEY = 'dsp_auth'

function loadFromStorage(): { isLoggedIn: boolean; user: AuthUser | null } {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (!raw) return { isLoggedIn: true, user: DEFAULT_USER }
    const parsed = JSON.parse(raw)
    // Replace any stale demo name with current default
    if (['Rahul Sharma', 'Abhishek Pawar'].includes(parsed.user?.name) || ['RS', 'AP'].includes(parsed.user?.initials)) {
      localStorage.removeItem(STORAGE_KEY)
      return { isLoggedIn: true, user: DEFAULT_USER }
    }
    return parsed
  } catch {
    return { isLoggedIn: true, user: DEFAULT_USER }
  }
}

const AuthContext = createContext<AuthContextValue>({
  isLoggedIn: false,
  user: null,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: ReactNode }) {
  const stored = loadFromStorage()
  const [isLoggedIn, setIsLoggedIn] = useState(stored.isLoggedIn)
  const [user, setUser] = useState<AuthUser | null>(stored.user)

  const login = useCallback((partial?: Partial<AuthUser>) => {
    const u = { ...DEFAULT_USER, ...partial }
    setIsLoggedIn(true)
    setUser(u)
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ isLoggedIn: true, user: u }))
  }, [])

  const logout = useCallback(() => {
    setIsLoggedIn(false)
    setUser(null)
    localStorage.removeItem(STORAGE_KEY)
  }, [])

  return (
    <AuthContext.Provider value={{ isLoggedIn, user, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
