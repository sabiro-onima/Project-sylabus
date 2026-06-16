import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Download, Send, CheckCircle, Clock, Edit, History } from 'lucide-react'
import { syllabiApi, exportApi } from '../api/client'
import { useAuthStore } from '../store/authStore'

export default function SyllabusDetailPage() {
  const { id } = useParams<{ id: string }>()
  const { user } = useAuthStore()
  const [syllabus, setSyllabus] = useState<any>(null)
  const [versions, setVersions] = useState<any[]>([])
  const [activeVersion, setActiveVersion] = useState<any>(null)
  const [tab, setTab] = useState<'info' | 'outcomes' | 'hours' | 'assessment' | 'bibliography'>('info')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    Promise.all([syllabiApi.get(id), syllabiApi.versions(id)])
      .then(([s, v]) => {
        setSyllabus(s.data)
        setVersions(v.data)
        setActiveVersion(v.data[0] || s.data.latest_version)
      })
      .finally(() => setLoading(false))
  }, [id])

  const download = async (format: 'pdf' | 'docx') => {
    if (!activeVersion) return
    const { data } = format === 'pdf' ? await exportApi.pdf(activeVersion.id) : await exportApi.docx(activeVersion.id)
    const url = URL.createObjectURL(new Blob([data]))
    const a = document.createElement('a'); a.href = url
    a.download = `${syllabus?.course_code}_v${activeVersion.version_number}.${format}`; a.click()
    URL.revokeObjectURL(url)
  }

  const submitVersion = async () => {
    if (!activeVersion) return
    await syllabiApi.submit(activeVersion.id)
    setActiveVersion({ ...activeVersion, status: 'pending' })
  }

  const approveVersion = async () => {
    if (!activeVersion) return
    await syllabiApi.approve(activeVersion.id)
    setActiveVersion({ ...activeVersion, status: 'approved' })
  }

  if (loading) return <div className="p-8 text-ink-400">Ładowanie...</div>
  if (!syllabus) return <div className="p-8 text-ink-400">Nie znaleziono syllabusa.</div>

  const tabs = [
    { key: 'info', label: 'Informacje' },
    { key: 'outcomes', label: 'Efekty kształcenia' },
    { key: 'hours', label: 'Godziny' },
    { key: 'assessment', label: 'Ocenianie' },
    { key: 'bibliography', label: 'Literatura' },
  ]

  return (
    <div className="p-8 animate-fade-in max-w-5xl">
      {/* Back */}
      <Link to="/syllabi" className="btn-ghost mb-6 inline-flex">
        <ArrowLeft size={14} /> Powrót do listy
      </Link>

      {/* Header */}
      <div className="flex items-start justify-between mb-6 gap-4">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <span className="font-mono text-xs text-ink-400 bg-ink-100 px-2 py-0.5 rounded">
              {syllabus.course_code}
            </span>
            <StatusBadge status={activeVersion?.status} />
          </div>
          <h1 className="text-2xl font-bold text-ink-800">{activeVersion?.title_pl}</h1>
          {activeVersion?.title_en && <p className="text-ink-400 text-sm mt-0.5 italic">{activeVersion.title_en}</p>}
        </div>

        <div className="flex items-center gap-2 shrink-0">
          {/* Version selector */}
          {versions.length > 1 && (
            <select className="input w-auto text-xs" value={activeVersion?.id}
              onChange={(e) => setActiveVersion(versions.find(v => v.id === e.target.value))}>
              {versions.map((v) => (
                <option key={v.id} value={v.id}>v{v.version_number} · {v.academic_year}</option>
              ))}
            </select>
          )}

          <button onClick={() => download('pdf')} className="btn-secondary text-xs">
            <Download size={13} /> PDF
          </button>
          <button onClick={() => download('docx')} className="btn-secondary text-xs">
            <Download size={13} /> DOCX
          </button>

          {activeVersion?.status === 'draft' && (
            <button onClick={submitVersion} className="btn-primary text-xs">
              <Send size={13} /> Wyślij do zatwierdzenia
            </button>
          )}
          {activeVersion?.status === 'pending' && (user?.role === 'admin' || user?.role === 'coordinator') && (
            <button onClick={approveVersion} className="btn-primary text-xs bg-green-600 hover:bg-green-700">
              <CheckCircle size={13} /> Zatwierdź
            </button>
          )}
          <Link to={`/syllabi/${id}/edit`} className="btn-ghost text-xs">
            <Edit size={13} /> Edytuj
          </Link>
          <Link to={`/syllabi/${id}/history`} className="btn-ghost text-xs">
            <History size={13} /> Historia zmian
          </Link>
        </div>
      </div>

      {/* Tabs */}
      <div className="flex gap-1 border-b border-ink-200 mb-6">
        {tabs.map(({ key, label }) => (
          <button key={key} onClick={() => setTab(key as any)}
            className={`px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px ${
              tab === key ? 'border-brand text-brand' : 'border-transparent text-ink-400 hover:text-ink-700'
            }`}>
            {label}
          </button>
        ))}
      </div>

      {/* Tab content */}
      <div className="animate-fade-in">
        {tab === 'info' && <InfoTab v={activeVersion} />}
        {tab === 'outcomes' && <OutcomesTab v={activeVersion} />}
        {tab === 'hours' && <HoursTab v={activeVersion} />}
        {tab === 'assessment' && <AssessmentTab v={activeVersion} />}
        {tab === 'bibliography' && <BibliographyTab v={activeVersion} />}
      </div>
    </div>
  )
}

function InfoTab({ v }: { v: any }) {
  if (!v) return null
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
      <div className="card p-5 space-y-4">
        <h3 className="font-semibold text-ink-700 text-sm">Dane podstawowe</h3>
        {[
          ['Rok akademicki', v.academic_year],
          ['Forma zajęć', v.course_type],
          ['Semestr', `${v.semester} (sem. ${v.semester_number})`],
          ['ECTS', v.ects_credits],
          ['Język', v.language],
        ].map(([label, value]) => (
          <div key={label as string}>
            <div className="text-xs text-ink-400 mb-0.5">{label}</div>
            <div className="text-sm font-medium text-ink-700">{value}</div>
          </div>
        ))}
      </div>
      <div className="space-y-4">
        {v.description && <div className="card p-5">
          <div className="text-xs text-ink-400 mb-2">Opis przedmiotu</div>
          <p className="text-sm text-ink-700 leading-relaxed">{v.description}</p>
        </div>}
        {v.learning_objectives && <div className="card p-5">
          <div className="text-xs text-ink-400 mb-2">Cele kształcenia</div>
          <p className="text-sm text-ink-700 leading-relaxed">{v.learning_objectives}</p>
        </div>}
        {v.prerequisites && <div className="card p-5">
          <div className="text-xs text-ink-400 mb-2">Wymagania wstępne</div>
          <p className="text-sm text-ink-700 leading-relaxed">{v.prerequisites}</p>
        </div>}
      </div>
    </div>
  )
}

function OutcomesTab({ v }: { v: any }) {
  const outcomes = v?.learning_outcomes || []
  const groups = ['knowledge', 'skills', 'competences']
  const labels: Record<string, string> = { knowledge: 'Wiedza', skills: 'Umiejętności', competences: 'Kompetencje' }
  return (
    <div className="space-y-5">
      {groups.map((g) => {
        const items = outcomes.filter((o: any) => o.category === g)
        if (!items.length) return null
        return (
          <div key={g} className="card p-5">
            <h3 className="font-semibold text-ink-700 mb-3 text-sm">{labels[g]}</h3>
            <div className="space-y-2">
              {items.map((o: any) => (
                <div key={o.code} className="flex gap-3">
                  <span className="font-mono text-xs text-brand bg-brand-50 px-2 py-1 rounded shrink-0 h-fit">{o.code}</span>
                  <p className="text-sm text-ink-700 leading-relaxed">{o.description}</p>
                </div>
              ))}
            </div>
          </div>
        )
      })}
      {outcomes.length === 0 && <p className="text-ink-400 text-sm">Brak efektów kształcenia.</p>}
    </div>
  )
}

function HoursTab({ v }: { v: any }) {
  if (!v) return null
  const rows = [
    ['Wykład', v.hours_lecture],
    ['Laboratorium', v.hours_laboratory],
    ['Ćwiczenia', v.hours_exercise],
    ['Seminarium', v.hours_seminar],
    ['Projekt', v.hours_project],
    ['Samodzielna nauka', v.hours_self_study],
  ]
  const total = rows.reduce((s, [, h]) => s + (h as number), 0)
  return (
    <div className="card overflow-hidden max-w-md">
      <table className="w-full text-sm">
        <thead><tr className="bg-ink-50 border-b border-ink-100">
          <th className="text-left px-5 py-3 text-xs font-semibold text-ink-400 uppercase">Forma</th>
          <th className="text-right px-5 py-3 text-xs font-semibold text-ink-400 uppercase">Godziny</th>
        </tr></thead>
        <tbody className="divide-y divide-ink-50">
          {rows.map(([label, hours]) => (
            <tr key={label as string}>
              <td className="px-5 py-3 text-ink-700">{label}</td>
              <td className="px-5 py-3 text-right font-mono text-ink-600">{hours}</td>
            </tr>
          ))}
          <tr className="bg-ink-50 font-semibold">
            <td className="px-5 py-3 text-ink-800">ŁĄCZNIE</td>
            <td className="px-5 py-3 text-right font-mono text-brand">{total}</td>
          </tr>
        </tbody>
      </table>
    </div>
  )
}

function AssessmentTab({ v }: { v: any }) {
  const methods = v?.assessment_methods || []
  return (
    <div className="card overflow-hidden max-w-2xl">
      <table className="w-full text-sm">
        <thead><tr className="bg-ink-50 border-b border-ink-100">
          <th className="text-left px-5 py-3 text-xs font-semibold text-ink-400 uppercase">Metoda</th>
          <th className="text-left px-5 py-3 text-xs font-semibold text-ink-400 uppercase">Waga</th>
          <th className="text-left px-5 py-3 text-xs font-semibold text-ink-400 uppercase">Opis</th>
        </tr></thead>
        <tbody className="divide-y divide-ink-50">
          {methods.map((m: any, i: number) => (
            <tr key={i}>
              <td className="px-5 py-3 font-medium text-ink-700 capitalize">{m.method}</td>
              <td className="px-5 py-3">
                <span className="badge bg-brand-50 text-brand">{m.weight}%</span>
              </td>
              <td className="px-5 py-3 text-ink-500">{m.description || '—'}</td>
            </tr>
          ))}
          {methods.length === 0 && <tr><td colSpan={3} className="px-5 py-6 text-center text-ink-300">Brak metod oceniania.</td></tr>}
        </tbody>
      </table>
    </div>
  )
}

function BibliographyTab({ v }: { v: any }) {
  const bibliography = v?.bibliography || []
  const primary = bibliography.filter((b: any) => b.type === 'primary')
  const supplementary = bibliography.filter((b: any) => b.type === 'supplementary')
  return (
    <div className="space-y-5 max-w-2xl">
      {primary.length > 0 && <div className="card p-5">
        <h3 className="font-semibold text-ink-700 mb-3 text-sm">Literatura podstawowa</h3>
        <ul className="space-y-2">
          {primary.map((b: any, i: number) => (
            <li key={i} className="text-sm text-ink-700 flex gap-2">
              <span className="text-ink-300 shrink-0">{i + 1}.</span>
              <span>{b.citation}{b.url && <a href={b.url} className="ml-2 text-brand text-xs hover:underline" target="_blank">↗ Link</a>}</span>
            </li>
          ))}
        </ul>
      </div>}
      {supplementary.length > 0 && <div className="card p-5">
        <h3 className="font-semibold text-ink-700 mb-3 text-sm">Literatura uzupełniająca</h3>
        <ul className="space-y-2">
          {supplementary.map((b: any, i: number) => (
            <li key={i} className="text-sm text-ink-700 flex gap-2">
              <span className="text-ink-300 shrink-0">{i + 1}.</span>
              <span>{b.citation}</span>
            </li>
          ))}
        </ul>
      </div>}
      {bibliography.length === 0 && <p className="text-ink-400 text-sm">Brak literatury.</p>}
    </div>
  )
}

function StatusBadge({ status }: { status?: string }) {
  const map: Record<string, string> = { draft: 'badge-draft', pending: 'badge-pending', approved: 'badge-approved', archived: 'badge-archived' }
  const labels: Record<string, string> = { draft: 'Szkic', pending: 'Oczekuje', approved: 'Zatwierdzone', archived: 'Archiwum' }
  return <span className={`badge ${map[status || 'draft']}`}>{labels[status || 'draft'] || status}</span>
}
