import { useEffect, useState } from 'react'
import { Shield, Users, BookOpen, CheckCircle, XCircle, Search, ChevronDown, Trash2, UserCheck, UserX } from 'lucide-react'
import api from '../api/client'

interface User {
  id: string
  email: string
  full_name: string
  role: string
  is_active: boolean
  auth_provider: string
  created_at: string
}

const ROLE_LABELS: Record<string, string> = {
  admin: 'Admin',
  coordinator: 'Koordynator',
  lecturer: 'Wykładowca',
  student: 'Student',
}

const ROLE_COLORS: Record<string, string> = {
  admin: 'bg-yellow-900/40 text-yellow-300',
  coordinator: 'bg-purple-900/40 text-purple-300',
  lecturer: 'bg-blue-900/40 text-blue-300',
  student: 'bg-green-900/40 text-green-300',
}

export default function AdminPanelPage() {
  const [users, setUsers] = useState<User[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [roleFilter, setRoleFilter] = useState('')
  const [stats, setStats] = useState({ total: 0, active: 0, admins: 0, syllabi: 0 })
  const [actionLoading, setActionLoading] = useState<string | null>(null)
  const [error, setError] = useState('')

  const loadUsers = async () => {
    setLoading(true)
    try {
      const { data } = await api.get('/admin/users', {
        params: { search: search || undefined, role: roleFilter || undefined },
      })
      setUsers(data.items || data)
      setStats({
        total: data.total ?? data.length,
        active: (data.items || data).filter((u: User) => u.is_active).length,
        admins: (data.items || data).filter((u: User) => u.role === 'admin').length,
        syllabi: 0,
      })
    } catch {
      setError('Nie udało się załadować użytkowników.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadUsers() }, [search, roleFilter])

  const changeRole = async (userId: string, role: string) => {
    setActionLoading(userId + '-role')
    try {
      await api.patch(`/admin/users/${userId}`, { role })
      setUsers((prev) => prev.map((u) => u.id === userId ? { ...u, role } : u))
    } catch { setError('Nie udało się zmienić roli.') }
    finally { setActionLoading(null) }
  }

  const toggleActive = async (user: User) => {
    setActionLoading(user.id + '-active')
    try {
      await api.patch(`/admin/users/${user.id}`, { is_active: !user.is_active })
      setUsers((prev) => prev.map((u) => u.id === user.id ? { ...u, is_active: !u.is_active } : u))
    } catch { setError('Nie udało się zmienić statusu.') }
    finally { setActionLoading(null) }
  }

  return (
    <div className="p-6 max-w-6xl mx-auto">
      {/* Header */}
      <div className="flex items-center gap-3 mb-6">
        <div className="w-10 h-10 bg-yellow-400 rounded-xl flex items-center justify-center">
          <Shield size={20} className="text-yellow-900" />
        </div>
        <div>
          <h1 className="text-xl font-bold text-ink-900">Panel Administratora</h1>
          <p className="text-ink-500 text-sm">Zarządzanie użytkownikami i systemem</p>
        </div>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {[
          { icon: Users, label: 'Wszyscy użytkownicy', value: stats.total, color: 'text-blue-400 bg-blue-900/30' },
          { icon: CheckCircle, label: 'Aktywni', value: stats.active, color: 'text-green-400 bg-green-900/30' },
          { icon: Shield, label: 'Administratorzy', value: stats.admins, color: 'text-yellow-400 bg-yellow-900/30' },
          { icon: BookOpen, label: 'Sylabusy', value: '–', color: 'text-purple-400 bg-purple-900/30' },
        ].map(({ icon: Icon, label, value, color }) => (
          <div key={label} className="bg-ink-200 rounded-xl border border-ink-300 p-4">
            <div className={`w-8 h-8 rounded-lg flex items-center justify-center mb-2 ${color}`}>
              <Icon size={16} />
            </div>
            <div className="text-2xl font-bold text-ink-900 tabular-nums">{value}</div>
            <div className="text-xs text-ink-500">{label}</div>
          </div>
        ))}
      </div>

      {/* Filters */}
      <div className="bg-ink-200 rounded-xl border border-ink-300 p-4 mb-4">
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="relative flex-1">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-400" />
            <input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Szukaj użytkownika..."
              className="w-full pl-8 pr-3 py-2 text-sm bg-ink-100 border border-ink-400 text-ink-900 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand placeholder:text-ink-600"
            />
          </div>
          <select
            value={roleFilter}
            onChange={(e) => setRoleFilter(e.target.value)}
            className="px-3 py-2 text-sm bg-ink-100 border border-ink-400 text-ink-900 rounded-lg focus:outline-none focus:ring-1 focus:ring-brand focus:border-brand"
          >
            <option value="">Wszystkie role</option>
            {Object.entries(ROLE_LABELS).map(([v, l]) => (
              <option key={v} value={v}>{l}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Error */}
      {error && (
        <div className="mb-4 p-3 bg-red-900/30 text-red-400 text-sm rounded-lg border border-red-800/50">
          {error}
        </div>
      )}

      {/* Users table */}
      <div className="bg-ink-200 rounded-xl border border-ink-300 overflow-hidden">
        <div className="px-4 py-3 border-b border-ink-300 flex items-center justify-between">
          <h2 className="text-sm font-semibold text-ink-800">Użytkownicy</h2>
          <span className="text-xs text-ink-400">{users.length} rekordów</span>
        </div>

        {loading ? (
          <div className="p-8 text-center text-ink-400 text-sm">Ładowanie...</div>
        ) : users.length === 0 ? (
          <div className="p-8 text-center text-ink-400 text-sm">Brak użytkowników</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-ink-300 border-b border-ink-400">
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-500 uppercase tracking-wide">Użytkownik</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-500 uppercase tracking-wide">Rola</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-500 uppercase tracking-wide">Status</th>
                  <th className="text-left px-4 py-2.5 text-xs font-semibold text-ink-500 uppercase tracking-wide">Provider</th>
                  <th className="text-right px-4 py-2.5 text-xs font-semibold text-ink-500 uppercase tracking-wide">Akcje</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-ink-300">
                {users.map((user) => (
                  <tr key={user.id} className="hover:bg-ink-300 transition-colors">
                    <td className="px-4 py-3">
                      <div className="font-medium text-ink-900">{user.full_name}</div>
                      <div className="text-xs text-ink-400">{user.email}</div>
                    </td>
                    <td className="px-4 py-3">
                      <select
                        value={user.role}
                        disabled={actionLoading === user.id + '-role'}
                        onChange={(e) => changeRole(user.id, e.target.value)}
                        className={`text-xs font-semibold px-2 py-1 rounded-full border-0 cursor-pointer focus:outline-none focus:ring-2 focus:ring-brand/30 ${ROLE_COLORS[user.role]}`}
                      >
                        {Object.entries(ROLE_LABELS).map(([v, l]) => (
                          <option key={v} value={v}>{l}</option>
                        ))}
                      </select>
                    </td>
                    <td className="px-4 py-3">
                      <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${user.is_active ? 'bg-green-900/40 text-green-400' : 'bg-red-900/40 text-red-400'}`}>
                        {user.is_active ? <CheckCircle size={10} /> : <XCircle size={10} />}
                        {user.is_active ? 'Aktywny' : 'Nieaktywny'}
                      </span>
                    </td>
                    <td className="px-4 py-3">
                      <span className="text-xs text-ink-500 capitalize">{user.auth_provider}</span>
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-1">
                        <button
                          onClick={() => toggleActive(user)}
                          disabled={actionLoading === user.id + '-active'}
                          title={user.is_active ? 'Dezaktywuj' : 'Aktywuj'}
                          className="p-1.5 rounded-lg text-ink-400 hover:text-ink-700 hover:bg-ink-100 transition-colors"
                        >
                          {user.is_active ? <UserX size={14} /> : <UserCheck size={14} />}
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}
