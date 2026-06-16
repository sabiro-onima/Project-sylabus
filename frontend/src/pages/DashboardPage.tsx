import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { BookOpen, CheckCircle, Clock, Archive, Plus, ArrowRight, Activity } from 'lucide-react'
import { syllabiApi } from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function DashboardPage() {
  const { user } = useAuthStore()
  const [stats, setStats] = useState({ total: 0, approved: 0, pending: 0, draft: 0 })
  const [recent, setRecent] = useState<any[]>([])

  useEffect(() => {
    Promise.all([
      syllabiApi.list({ size: 6 }),
      syllabiApi.list({ size: 1, page: 1 }),
      syllabiApi.list({ status: 'approved', size: 1 }),
      syllabiApi.list({ status: 'pending',  size: 1 }),
      syllabiApi.list({ status: 'draft',    size: 1 }),
    ]).then(([recentRes, allRes, approvedRes, pendingRes, draftRes]) => {
      setRecent(recentRes.data.items || [])
      setStats({
        total:    allRes.data.total      ?? 0,
        approved: approvedRes.data.total ?? 0,
        pending:  pendingRes.data.total  ?? 0,
        draft:    draftRes.data.total    ?? 0,
      })
    }).catch(() => {})
  }, [])

  const statCards = [
    { label: 'Łącznie',       value: stats.total,    icon: BookOpen,    accent: 'text-brand-500',  bar: 'bg-brand-300' },
    { label: 'Zatwierdzone',  value: stats.approved, icon: CheckCircle, accent: 'text-green-400',  bar: 'bg-green-500' },
    { label: 'Oczekujące',    value: stats.pending,  icon: Clock,       accent: 'text-amber-400',  bar: 'bg-amber-500' },
    { label: 'Szkice',        value: stats.draft,    icon: Archive,     accent: 'text-ink-600',    bar: 'bg-ink-500' },
  ]

  return (
    <div className="animate-fade-in space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-ink-900">
            Cześć, {user?.full_name?.split(' ')[0]}
          </h1>
          <p className="text-ink-600 text-sm mt-0.5">Przegląd systemu · {new Date().toLocaleDateString('pl-PL', { weekday: 'long', day: 'numeric', month: 'long' })}</p>
        </div>
        <Link to="/syllabi/new" className="btn-primary">
          <Plus size={14} /> Nowy sylabuz
        </Link>
      </div>

      {/* Stats row */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {statCards.map(({ label, value, icon: Icon, accent, bar }) => (
          <div key={label} className="card p-5 relative overflow-hidden">
            <div className={`absolute top-0 left-0 w-full h-0.5 ${bar}`} />
            <div className="flex items-start justify-between mb-3">
              <span className="text-ink-600 text-xs font-medium uppercase tracking-wider">{label}</span>
              <Icon size={14} className={accent} />
            </div>
            <div className={`text-3xl font-display font-semibold ${accent} tabular-nums`}>{value}</div>
          </div>
        ))}
      </div>

      {/* Content */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        {/* Recent list */}
        <div className="lg:col-span-2 card overflow-hidden">
          <div className="px-5 py-3.5 border-b border-ink-300 flex items-center justify-between">
            <div className="flex items-center gap-2">
              <Activity size={14} className="text-brand-500" />
              <span className="text-ink-900 font-medium text-sm">Ostatnia aktywność</span>
            </div>
            <Link to="/syllabi" className="text-brand-500 hover:text-brand-400 text-xs flex items-center gap-1 transition-colors">
              Wszystkie <ArrowRight size={11} />
            </Link>
          </div>

          {recent.length === 0 ? (
            <div className="py-14 text-center">
              <BookOpen size={28} className="mx-auto mb-2 text-ink-500 opacity-40" />
              <p className="text-ink-600 text-sm">Brak sylabusów.{' '}
                <Link to="/syllabi/new" className="text-brand-500 hover:underline">Utwórz pierwszy</Link>
              </p>
            </div>
          ) : (
            <div>
              {recent.map((s, i) => (
                <Link key={s.id} to={`/syllabi/${s.id}`}
                  className="flex items-center justify-between px-5 py-3.5 border-b border-ink-300 last:border-0 hover:bg-ink-300 transition-colors group">
                  <div className="flex items-center gap-3 min-w-0">
                    <span className="text-ink-500 text-xs font-mono w-5 shrink-0">{String(i + 1).padStart(2, '0')}</span>
                    <div className="min-w-0">
                      <div className="text-ink-900 text-sm font-medium truncate group-hover:text-brand-500 transition-colors">
                        {s.latest_version?.title_pl || s.course_code}
                      </div>
                      <div className="text-ink-600 text-xs font-mono mt-0.5">
                        {s.course_code} / {s.latest_version?.academic_year}
                      </div>
                    </div>
                  </div>
                  <StatusBadge status={s.latest_version?.status} />
                </Link>
              ))}
            </div>
          )}
        </div>

        {/* Side panel */}
        <div className="space-y-4">
          {/* Quick nav */}
          <div className="card p-5">
            <p className="text-ink-600 text-xs font-medium uppercase tracking-wider mb-3">Skróty</p>
            <div className="space-y-1.5">
              {[
                { label: 'Nowy sylabuz', to: '/syllabi/new', primary: true },
                { label: 'Lista sylabusów', to: '/syllabi', primary: false },
                { label: 'Siatka przedmiotów', to: '/grid', primary: false },
              ].map(({ label, to, primary }) => (
                <Link key={to} to={to}
                  className={primary ? 'btn-primary w-full justify-center text-xs py-2 block text-center' : 'btn-secondary w-full justify-center text-xs py-2 block text-center'}>
                  {label}
                </Link>
              ))}
            </div>
          </div>

          {/* Status legend */}
          <div className="card p-5">
            <p className="text-ink-600 text-xs font-medium uppercase tracking-wider mb-3">Statusy</p>
            <div className="space-y-2">
              {[
                { label: 'Zatwierdzone', cls: 'badge-approved', pct: stats.total ? Math.round(stats.approved / stats.total * 100) : 0 },
                { label: 'Oczekujące',  cls: 'badge-pending',  pct: stats.total ? Math.round(stats.pending  / stats.total * 100) : 0 },
                { label: 'Szkice',      cls: 'badge-draft',    pct: stats.total ? Math.round(stats.draft    / stats.total * 100) : 0 },
              ].map(({ label, cls, pct }) => (
                <div key={label} className="flex items-center gap-3">
                  <span className={`badge ${cls} w-24 justify-center shrink-0`}>{label}</span>
                  <div className="flex-1 h-1 bg-ink-400 rounded-full overflow-hidden">
                    <div className="h-full bg-brand rounded-full transition-all duration-500" style={{ width: `${pct}%` }} />
                  </div>
                  <span className="text-ink-600 text-xs font-mono w-8 text-right">{pct}%</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}

function StatusBadge({ status }: { status?: string }) {
  const map: Record<string, string> = {
    draft: 'badge-draft', pending: 'badge-pending',
    approved: 'badge-approved', archived: 'badge-archived',
  }
  const labels: Record<string, string> = {
    draft: 'Szkic', pending: 'Oczekuje', approved: 'Zatwierdzone', archived: 'Archiwum',
  }
  return <span className={`badge ${map[status || 'draft']}`}>{labels[status || 'draft']}</span>
}
