import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuthStore } from '../store/authStore'
import { BookOpen, Loader2 } from 'lucide-react'

export default function LoginPage() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const { login, loading } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      await login(email, password)
      navigate('/')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Błąd logowania. Sprawdź dane.')
    }
  }

  return (
    <div className="min-h-screen bg-ink-50 flex items-center justify-center p-4">
      {/* Subtle grid bg */}
      <div className="fixed inset-0 pointer-events-none"
        style={{ backgroundImage: 'linear-gradient(rgba(59,130,246,0.03) 1px, transparent 1px), linear-gradient(90deg, rgba(59,130,246,0.03) 1px, transparent 1px)', backgroundSize: '48px 48px' }} />

      <div className="w-full max-w-sm relative animate-fade-in">
        {/* Logo */}
        <div className="flex items-center gap-3 mb-10">
          <div className="w-9 h-9 bg-brand rounded-lg flex items-center justify-center">
            <BookOpen size={18} className="text-white" />
          </div>
          <div>
            <div className="text-ink-900 font-display font-semibold text-base leading-none">SylabusApp</div>
            <div className="text-ink-600 text-xs mt-0.5">System zarządzania sylabusami</div>
          </div>
        </div>

        {/* Card */}
        <div className="bg-ink-200 border border-ink-300 rounded-xl p-7">
          <h1 className="text-ink-900 font-display font-semibold text-xl mb-1">Logowanie</h1>
          <p className="text-ink-600 text-sm mb-6">Wpisz dane swojego konta</p>

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Email</label>
              <input type="email" className="input" placeholder="jan.kowalski@uczelnia.pl"
                value={email} onChange={(e) => setEmail(e.target.value)} required />
            </div>
            <div>
              <label className="label">Hasło</label>
              <input type="password" className="input" placeholder="••••••••"
                value={password} onChange={(e) => setPassword(e.target.value)} required />
            </div>

            {error && (
              <div className="px-3 py-2.5 bg-red-950/50 border border-red-800/50 rounded-md text-red-400 text-xs">
                {error}
              </div>
            )}

            <button type="submit" className="btn-primary w-full justify-center py-2.5 mt-2" disabled={loading}>
              {loading ? <Loader2 size={14} className="animate-spin" /> : null}
              Zaloguj się
            </button>
          </form>
        </div>

        <p className="mt-4 text-center text-ink-600 text-sm">
          Nie masz konta?{' '}
          <Link to="/register" className="text-brand-500 hover:text-brand-400 font-medium transition-colors">
            Zarejestruj się
          </Link>
        </p>
      </div>
    </div>
  )
}
