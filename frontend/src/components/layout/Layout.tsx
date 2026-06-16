import { Outlet, NavLink } from 'react-router-dom'
import { LayoutGrid, BookOpen, GraduationCap, Shield } from 'lucide-react'
import { useAuthStore } from '../../store/authStore'
import UserMenu from './UserMenu'
import clsx from 'clsx'

const nav = [
  { to: '/',        icon: LayoutGrid,    label: 'Dashboard' },
  { to: '/syllabi', icon: BookOpen,      label: 'Sylabusy' },
  { to: '/grid',    icon: GraduationCap, label: 'Siatka' },
]

export default function Layout() {
  const user = useAuthStore((s) => s.user)
  const isAdmin = user?.role === 'admin'

  return (
    <div className="min-h-screen bg-ink-50 flex flex-col">
      {/* ── Top navbar ── */}
      <header className="bg-ink-100 border-b border-ink-300 sticky top-0 z-40">
        <div className="max-w-7xl mx-auto px-6 h-14 flex items-center gap-8">
          {/* Logo */}
          <div className="flex items-center gap-2.5 shrink-0 mr-4">
            <div className="w-7 h-7 bg-brand rounded flex items-center justify-center">
              <BookOpen size={14} className="text-white" />
            </div>
            <span className="text-ink-900 font-display font-semibold text-sm tracking-tight">SylabusApp</span>
          </div>

          {/* Nav links */}
          <nav className="flex items-center gap-1 flex-1">
            {nav.map(({ to, icon: Icon, label }) => (
              <NavLink
                key={to}
                to={to}
                end={to === '/'}
                className={({ isActive }) => clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all duration-150',
                  isActive
                    ? 'bg-brand text-white font-medium'
                    : 'text-ink-700 hover:bg-ink-300 hover:text-ink-900'
                )}
              >
                <Icon size={14} />
                {label}
              </NavLink>
            ))}

            {isAdmin && (
              <NavLink
                to="/admin"
                className={({ isActive }) => clsx(
                  'flex items-center gap-2 px-3 py-1.5 rounded text-sm transition-all duration-150',
                  isActive
                    ? 'bg-amber-500 text-black font-medium'
                    : 'text-amber-400 hover:bg-ink-300 hover:text-amber-300'
                )}
              >
                <Shield size={14} />
                Admin
              </NavLink>
            )}
          </nav>

          {/* Right: user menu */}
          <div className="shrink-0">
            <UserMenu />
          </div>
        </div>
      </header>

      {/* ── Page content ── */}
      <main className="flex-1">
        <div className="max-w-7xl mx-auto px-6 py-8">
          <Outlet />
        </div>
      </main>
    </div>
  )
}
