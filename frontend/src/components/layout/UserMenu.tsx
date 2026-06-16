import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { LogOut, Shield, ChevronDown, Settings, User } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import clsx from 'clsx'

export default function UserMenu() {
  const { user, logout } = useAuthStore()
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)
  const navigate = useNavigate()

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [])

  const isAdmin = user?.role === 'admin'
  const initials = user?.full_name?.split(' ').map((n) => n[0]).slice(0, 2).join('').toUpperCase() ?? '?'

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((v) => !v)}
        className={clsx(
          'flex items-center gap-2 px-2.5 py-1.5 rounded border transition-all duration-150',
          open
            ? 'bg-ink-300 border-ink-500'
            : 'bg-ink-200 border-ink-400 hover:bg-ink-300 hover:border-ink-500'
        )}
      >
        <div className="relative">
          <div className="w-6 h-6 bg-brand-200 rounded flex items-center justify-center text-brand-600 text-xs font-display font-semibold">
            {initials}
          </div>
          {isAdmin && (
            <span className="absolute -top-1 -right-1 w-3 h-3 bg-amber-400 rounded-full flex items-center justify-center">
              <Shield size={7} className="text-black" />
            </span>
          )}
        </div>
        <span className="text-ink-800 text-xs font-medium max-w-24 truncate">{user?.full_name?.split(' ')[0]}</span>
        <ChevronDown size={11} className={clsx('text-ink-600 transition-transform', open && 'rotate-180')} />
      </button>

      {open && (
        <div className="absolute right-0 top-full mt-1.5 w-52 bg-ink-200 border border-ink-400 rounded-lg shadow-2xl shadow-black/50 overflow-hidden z-50 animate-slide-up">
          <div className="px-3 py-2.5 border-b border-ink-300 bg-ink-100">
            <div className="text-ink-900 text-xs font-medium">{user?.full_name}</div>
            <div className="text-ink-600 text-xs truncate mt-0.5">{user?.email}</div>
          </div>

          <div className="py-1">
            <button onClick={() => { setOpen(false); navigate('/profile') }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-ink-800 hover:bg-ink-300 hover:text-ink-900 transition-colors">
              <User size={13} className="text-ink-600" /> Mój profil
            </button>
            <button onClick={() => { setOpen(false); navigate('/settings') }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-ink-800 hover:bg-ink-300 hover:text-ink-900 transition-colors">
              <Settings size={13} className="text-ink-600" /> Ustawienia
            </button>
            {isAdmin && (
              <button onClick={() => { setOpen(false); navigate('/admin') }}
                className="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-amber-400 hover:bg-ink-300 transition-colors">
                <Shield size={13} /> Panel administratora
              </button>
            )}
          </div>

          <div className="border-t border-ink-300 py-1">
            <button onClick={() => { setOpen(false); logout() }}
              className="flex items-center gap-2.5 w-full px-3 py-2 text-xs text-red-400 hover:bg-ink-300 transition-colors">
              <LogOut size={13} /> Wyloguj się
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
