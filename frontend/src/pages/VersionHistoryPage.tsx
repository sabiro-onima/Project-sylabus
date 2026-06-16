import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Clock, User, ChevronDown, ChevronUp } from 'lucide-react'
import { syllabiApi } from '../api/client'

const FIELD_LABELS: Record<string, string> = {
  title_pl: 'Tytuł (PL)', title_en: 'Tytuł (EN)', description: 'Opis',
  learning_objectives: 'Cele kształcenia', prerequisites: 'Wymagania wstępne',
  hours_lecture: 'Godz. wykład', hours_laboratory: 'Godz. laboratorium',
  hours_exercise: 'Godz. ćwiczenia', hours_seminar: 'Godz. seminarium',
  hours_project: 'Godz. projekt', hours_self_study: 'Godz. samodzielna nauka',
  ects_credits: 'Punkty ECTS', semester_number: 'Numer semestru',
  course_type: 'Forma zajęć', semester: 'Semestr', language: 'Język',
  assessment_methods: 'Metody oceniania', learning_outcomes: 'Efekty kształcenia',
  bibliography: 'Literatura', status: 'Status',
}

export default function VersionHistoryPage() {
  const { id } = useParams<{ id: string }>()
  const [syllabus, setSyllabus] = useState<any>(null)
  const [versions, setVersions] = useState<any[]>([])
  const [changes, setChanges] = useState<Record<string, any[]>>({})
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([syllabiApi.get(id), syllabiApi.versions(id)])
      .then(async ([s, v]) => {
        setSyllabus(s.data)
        const vers = v.data
        setVersions(vers)
        // Załaduj zmiany dla każdej wersji
        const changesMap: Record<string, any[]> = {}
        await Promise.all(
          vers.map(async (ver: any) => {
            try {
              const { data } = await syllabiApi.versionChanges(ver.id)
              changesMap[ver.id] = data
            } catch {
              changesMap[ver.id] = []
            }
          })
        )
        setChanges(changesMap)
        // Rozwiń pierwszą wersję automatycznie
        if (vers.length > 0) setExpanded({ [vers[0].id]: true })
      })
      .finally(() => setLoading(false))
  }, [id])

  const toggle = (verId: string) =>
    setExpanded(e => ({ ...e, [verId]: !e[verId] }))

  const formatValue = (val: any): string => {
    if (val === null || val === undefined) return '—'
    if (typeof val === 'object' && 'value' in val) return String(val.value)
    if (Array.isArray(val)) return `[${val.length} elementów]`
    if (typeof val === 'object') return JSON.stringify(val)
    return String(val)
  }

  if (loading) return <div className="p-8 text-ink-400">Ładowanie...</div>

  return (
    <div className="p-8 max-w-4xl animate-fade-in">
      <Link to={`/syllabi/${id}`} className="btn-ghost mb-6 inline-flex">
        <ArrowLeft size={14} /> Powrót do syllabusa
      </Link>

      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-800">Historia zmian</h1>
        <p className="text-ink-400 text-sm mt-0.5">
          {syllabus?.latest_version?.title_pl || syllabus?.course_code}
        </p>
      </div>

      {versions.length === 0 ? (
        <div className="card p-12 text-center text-ink-300">Brak wersji.</div>
      ) : (
        <div className="space-y-4">
          {versions.map((ver) => (
            <div key={ver.id} className="card overflow-hidden">
              {/* Version header */}
              <button
                onClick={() => toggle(ver.id)}
                className="w-full flex items-center justify-between px-6 py-4 hover:bg-ink-50 transition-colors text-left"
              >
                <div className="flex items-center gap-3">
                  <div className="w-8 h-8 bg-brand-50 text-brand rounded-lg flex items-center justify-center text-sm font-bold">
                    v{ver.version_number}
                  </div>
                  <div>
                    <div className="font-medium text-ink-800 text-sm">
                      Wersja {ver.version_number} · {ver.academic_year}
                    </div>
                    <div className="text-ink-400 text-xs flex items-center gap-2 mt-0.5">
                      <Clock size={11} />
                      {new Date(ver.created_at).toLocaleString('pl-PL')}
                      {ver.changelog_note && (
                        <span className="italic">· {ver.changelog_note}</span>
                      )}
                    </div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <StatusBadge status={ver.status} />
                  <span className="text-ink-400 text-xs">
                    {changes[ver.id]?.length ?? 0} zmian
                  </span>
                  {expanded[ver.id]
                    ? <ChevronUp size={16} className="text-ink-400" />
                    : <ChevronDown size={16} className="text-ink-400" />
                  }
                </div>
              </button>

              {/* Changes list */}
              {expanded[ver.id] && (
                <div className="border-t border-ink-100">
                  {!changes[ver.id] || changes[ver.id].length === 0 ? (
                    <div className="px-6 py-4 text-ink-400 text-sm">
                      Brak zapisanych zmian dla tej wersji.
                    </div>
                  ) : (
                    <div className="divide-y divide-ink-50">
                      {changes[ver.id].map((change, i) => (
                        <div key={i} className="px-6 py-3 flex gap-4 items-start">
                          <div className="flex items-center gap-1.5 text-xs text-ink-400 w-36 shrink-0 mt-0.5">
                            <User size={11} />
                            {change.user?.full_name || 'System'}
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="text-xs font-medium text-ink-600 mb-1">
                              {FIELD_LABELS[change.field_name] || change.field_name}
                            </div>
                            <div className="flex gap-2 items-center flex-wrap">
                              <span className="text-xs text-red-500 bg-red-50 px-2 py-0.5 rounded line-through max-w-xs truncate">
                                {formatValue(change.old_value)}
                              </span>
                              <span className="text-ink-300">→</span>
                              <span className="text-xs text-green-700 bg-green-50 px-2 py-0.5 rounded max-w-xs truncate">
                                {formatValue(change.new_value)}
                              </span>
                            </div>
                          </div>
                          <div className="text-xs text-ink-300 shrink-0 mt-0.5">
                            {new Date(change.changed_at).toLocaleString('pl-PL')}
                          </div>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          ))}
        </div>
      )}
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
  return <span className={`badge ${map[status || 'draft']}`}>{labels[status || 'draft'] || status}</span>
}
