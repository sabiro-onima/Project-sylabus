import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import { Plus, Search, BookOpen, ChevronLeft, ChevronRight, X, Download } from 'lucide-react'
import { syllabiApi, exportApi } from '../api/client'

const STATUS_OPTIONS = ['', 'draft', 'pending', 'approved', 'archived']
const STATUS_LABELS: Record<string, string> = {
  '': 'Wszystkie statusy', draft: 'Szkic', pending: 'Oczekuje',
  approved: 'Zatwierdzone', archived: 'Archiwum',
}
const TYPE_OPTIONS = ['', 'lecture', 'laboratory', 'exercise', 'seminar', 'project', 'practicum']
const TYPE_LABELS: Record<string, string> = {
  '': 'Wszystkie typy', lecture: 'Wykład', laboratory: 'Laboratorium',
  exercise: 'Ćwiczenia', seminar: 'Seminarium', project: 'Projekt', practicum: 'Praktyki',
}
const SEMESTER_OPTIONS = ['', '1', '2', '3', '4', '5', '6', '7', '8', '9', '10']

export default function SyllabiListPage() {
  const [syllabi, setSyllabi] = useState<any[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('')
  const [courseType, setCourseType] = useState('')
  const [semesterNumber, setSemesterNumber] = useState('')
  const [academicYear, setAcademicYear] = useState('')
  const [loading, setLoading] = useState(true)
  const size = 15

  const load = useCallback(() => {
    setLoading(true)
    syllabiApi.list({
      search: search || undefined, status: status || undefined,
      course_type: courseType || undefined,
      semester_number: semesterNumber ? Number(semesterNumber) : undefined,
      academic_year: academicYear || undefined, page, size,
    })
      .then(({ data }) => { setSyllabi(data.items || []); setTotal(data.total || 0) })
      .catch(() => { setSyllabi([]); setTotal(0) })
      .finally(() => setLoading(false))
  }, [search, status, courseType, semesterNumber, academicYear, page, size])

  useEffect(() => { load() }, [load])
  useEffect(() => { setPage(1) }, [search, status, courseType, semesterNumber, academicYear])

  const clearFilters = () => {
    setSearch(''); setStatus(''); setCourseType(''); setSemesterNumber(''); setAcademicYear(''); setPage(1)
  }
  const hasFilters = search || status || courseType || semesterNumber || academicYear

  const downloadFile = async (versionId: string, format: 'pdf' | 'docx', filename: string) => {
    try {
      const { data } = format === 'pdf' ? await exportApi.pdf(versionId) : await exportApi.docx(versionId)
      const url = URL.createObjectURL(new Blob([data]))
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
      URL.revokeObjectURL(url)
    } catch {}
  }

  const totalPages = Math.ceil(total / size)

  return (
    <div className="animate-fade-in space-y-5">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-display font-semibold text-ink-900">Sylabusy</h1>
          <p className="text-ink-600 text-sm mt-0.5 font-mono">{total} rekordów</p>
        </div>
        <Link to="/syllabi/new" className="btn-primary"><Plus size={14} /> Nowy sylabuz</Link>
      </div>

      {/* Filters bar */}
      <div className="bg-ink-100 border border-ink-300 rounded-lg p-4 space-y-3">
        <div className="relative">
          <Search size={13} className="absolute left-3 top-1/2 -translate-y-1/2 text-ink-600" />
          <input className="input pl-9" placeholder="Szukaj po tytule lub kodzie..."
            value={search} onChange={(e) => setSearch(e.target.value)} />
        </div>
        <div className="flex flex-wrap gap-2 items-center">
          <select className="input w-auto text-xs py-1.5" value={status}
            onChange={(e) => { setStatus(e.target.value); setPage(1) }}>
            {STATUS_OPTIONS.map(s => <option key={s} value={s}>{STATUS_LABELS[s]}</option>)}
          </select>
          <select className="input w-auto text-xs py-1.5" value={courseType}
            onChange={(e) => { setCourseType(e.target.value); setPage(1) }}>
            {TYPE_OPTIONS.map(t => <option key={t} value={t}>{TYPE_LABELS[t]}</option>)}
          </select>
          <select className="input w-auto text-xs py-1.5" value={semesterNumber}
            onChange={(e) => { setSemesterNumber(e.target.value); setPage(1) }}>
            <option value="">Wszystkie semestry</option>
            {SEMESTER_OPTIONS.filter(Boolean).map(s => <option key={s} value={s}>Semestr {s}</option>)}
          </select>
          <input className="input w-32 text-xs py-1.5" placeholder="Rok: 2024/25"
            value={academicYear} onChange={(e) => { setAcademicYear(e.target.value); setPage(1) }} />
          {hasFilters && (
            <button onClick={clearFilters} className="btn-ghost text-xs text-red-400 hover:text-red-300 py-1.5">
              <X size={12} /> Wyczyść
            </button>
          )}
        </div>
      </div>

      {/* Table */}
      <div className="card overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-ink-300 bg-ink-100">
              <th className="text-left px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider">Przedmiot</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider">Kod</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider">Rok / Sem.</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider">ECTS</th>
              <th className="text-left px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider">Status</th>
              <th className="px-5 py-3 text-xs font-medium text-ink-600 uppercase tracking-wider text-right">Export</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-ink-300">
            {loading ? (
              <tr><td colSpan={6} className="px-5 py-12 text-center text-ink-600 text-sm">Ładowanie...</td></tr>
            ) : syllabi.length === 0 ? (
              <tr><td colSpan={6} className="px-5 py-12 text-center">
                <BookOpen size={24} className="mx-auto mb-2 text-ink-500 opacity-30" />
                <p className="text-ink-600 text-sm">Brak wyników{hasFilters ? ' dla wybranych filtrów' : ''}</p>
                {hasFilters && <button onClick={clearFilters} className="mt-2 text-brand-500 text-xs hover:underline">Wyczyść filtry</button>}
              </td></tr>
            ) : syllabi.map((s) => (
              <tr key={s.id} className="hover:bg-ink-300 transition-colors group">
                <td className="px-5 py-3.5">
                  <Link to={`/syllabi/${s.id}`} className="font-medium text-ink-900 hover:text-brand-500 transition-colors group-hover:text-brand-400">
                    {s.latest_version?.title_pl || '—'}
                  </Link>
                </td>
                <td className="px-5 py-3.5 font-mono text-xs text-ink-600">{s.course_code}</td>
                <td className="px-5 py-3.5 text-ink-600 text-xs font-mono">
                  <div>{s.latest_version?.academic_year || '—'}</div>
                  {s.latest_version?.semester_number && <div className="text-ink-500">sem. {s.latest_version.semester_number}</div>}
                </td>
                <td className="px-5 py-3.5 text-ink-600 font-mono text-xs">{s.latest_version?.ects_credits ?? '—'}</td>
                <td className="px-5 py-3.5"><StatusBadge status={s.latest_version?.status} /></td>
                <td className="px-5 py-3.5">
                  {s.latest_version && (
                    <div className="flex items-center gap-1 justify-end">
                      <button onClick={() => downloadFile(s.latest_version.id, 'pdf', `${s.course_code}.pdf`)}
                        className="btn-ghost text-xs px-2 py-1 font-mono">PDF</button>
                      <button onClick={() => downloadFile(s.latest_version.id, 'docx', `${s.course_code}.docx`)}
                        className="btn-ghost text-xs px-2 py-1 font-mono">DOCX</button>
                    </div>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>

        {totalPages > 1 && (
          <div className="px-5 py-3 border-t border-ink-300 flex items-center justify-between bg-ink-100">
            <span className="text-xs text-ink-600 font-mono">Strona {page} / {totalPages} · {total} wyników</span>
            <div className="flex gap-1">
              <button className="btn-ghost px-2 py-1" onClick={() => setPage(p => Math.max(1, p - 1))} disabled={page === 1}>
                <ChevronLeft size={13} />
              </button>
              <button className="btn-ghost px-2 py-1" onClick={() => setPage(p => Math.min(totalPages, p + 1))} disabled={page === totalPages}>
                <ChevronRight size={13} />
              </button>
            </div>
          </div>
        )}
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
  return <span className={`badge ${map[status || 'draft']}`}>{labels[status || 'draft'] || status}</span>
}
