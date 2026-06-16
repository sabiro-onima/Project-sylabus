import { useState, useEffect } from 'react'
import { useNavigate, Link } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, Loader2 } from 'lucide-react'
import { syllabiApi, unitsApi } from '../api/client'

const CURRENT_YEAR = new Date().getFullYear()
const DEFAULT_ACADEMIC_YEAR = `${CURRENT_YEAR}/${CURRENT_YEAR + 1}`

interface AcademicUnit {
  id: string
  name: string
  code: string
}

const defaultForm = {
  course_code: '',
  academic_unit_id: '',
  initial_version: {
    title_pl: '', title_en: '', course_type: 'lecture', semester: 'winter',
    semester_number: 1, ects_credits: 5, language: 'pl', academic_year: DEFAULT_ACADEMIC_YEAR,
    description: '', learning_objectives: '', prerequisites: '',
    hours_lecture: 30, hours_laboratory: 0, hours_exercise: 0,
    hours_seminar: 0, hours_project: 0, hours_self_study: 95,
    learning_outcomes: [{ code: 'EK1', description: '', category: 'knowledge' }],
    assessment_methods: [{ method: 'exam', weight: 60, description: '' }, { method: 'project', weight: 40, description: '' }],
    bibliography: [{ type: 'primary', citation: '', url: '' }],
  }
}

export default function SyllabusFormPage() {
  const navigate = useNavigate()
  const [form, setForm] = useState(defaultForm)
  const [units, setUnits] = useState<AcademicUnit[]>([])
  const [unitsLoading, setUnitsLoading] = useState(true)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    unitsApi.list()
      .then(({ data }) => {
        setUnits(data)
        if (data.length > 0) {
          setForm(f => ({ ...f, academic_unit_id: data[0].id }))
        }
      })
      .catch(() => setError('Nie udało się załadować jednostek akademickich.'))
      .finally(() => setUnitsLoading(false))
  }, [])

  const v = form.initial_version
  const setV = (patch: Partial<typeof v>) =>
    setForm(f => ({ ...f, initial_version: { ...f.initial_version, ...patch } }))

  const totalHours = v.hours_lecture + v.hours_laboratory + v.hours_exercise + v.hours_seminar + v.hours_project + v.hours_self_study
  const expectedMin = Math.round(v.ects_credits * 25)
  const expectedMax = Math.round(v.ects_credits * 30)
  const hoursOk = totalHours >= expectedMin && totalHours <= expectedMax
  const weightsSum = v.assessment_methods.reduce((s, m) => s + (Number(m.weight) || 0), 0)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (!form.academic_unit_id) { setError('Wybierz jednostkę akademicką.'); return }
    if (!hoursOk) { setError(`Godziny (${totalHours}) muszą być między ${expectedMin} a ${expectedMax} dla ${v.ects_credits} ECTS.`); return }
    if (weightsSum !== 100) { setError(`Suma wag metod oceniania musi wynosić 100% (aktualnie ${weightsSum}%).`); return }
    setLoading(true)
    try {
      const { data } = await syllabiApi.create(form)
      navigate(`/syllabi/${data.id}`)
    } catch (err: any) {
      const detail = err.response?.data?.detail
      if (Array.isArray(detail)) {
        setError(detail.map((d: any) => d.msg || d.message || JSON.stringify(d)).join(', '))
      } else if (typeof detail === 'string') {
        setError(detail)
      } else {
        setError('Błąd zapisu. Sprawdź poprawność danych i spróbuj ponownie.')
      }
    } finally { setLoading(false) }
  }

  return (
    <div className="p-8 max-w-4xl animate-fade-in">
      <Link to="/syllabi" className="btn-ghost mb-6 inline-flex"><ArrowLeft size={14} /> Powrót</Link>
      <h1 className="text-2xl font-bold text-ink-800 mb-6">Nowy sylabuz</h1>

      <form onSubmit={handleSubmit} className="space-y-6">
        {/* Podstawowe */}
        <div className="card p-6">
          <h2 className="font-semibold text-ink-700 mb-4">Dane podstawowe</h2>
          <div className="grid grid-cols-2 gap-4">
            <div>
              <label className="label">Kod przedmiotu *</label>
              <input className="input font-mono" placeholder="INF001" value={form.course_code}
                onChange={(e) => setForm(f => ({ ...f, course_code: e.target.value }))} required />
            </div>
            <div>
              <label className="label">Rok akademicki *</label>
              <input className="input" placeholder={DEFAULT_ACADEMIC_YEAR} value={v.academic_year}
                onChange={(e) => setV({ academic_year: e.target.value })} required />
            </div>
            <div className="col-span-2">
              <label className="label">Jednostka akademicka *</label>
              {unitsLoading ? (
                <div className="input flex items-center gap-2 text-ink-400">
                  <Loader2 size={14} className="animate-spin" /> Ładowanie...
                </div>
              ) : units.length === 0 ? (
                <div className="input text-red-500 text-sm">Brak jednostek akademickich w systemie. Skontaktuj się z administratorem.</div>
              ) : (
                <select className="input" value={form.academic_unit_id}
                  onChange={(e) => setForm(f => ({ ...f, academic_unit_id: e.target.value }))} required>
                  {units.map(u => (
                    <option key={u.id} value={u.id}>{u.name} ({u.code})</option>
                  ))}
                </select>
              )}
            </div>
            <div className="col-span-2">
              <label className="label">Tytuł (polski) *</label>
              <input className="input" placeholder="Algorytmy i struktury danych" value={v.title_pl}
                onChange={(e) => setV({ title_pl: e.target.value })} required />
            </div>
            <div className="col-span-2">
              <label className="label">Tytuł (angielski)</label>
              <input className="input" placeholder="Algorithms and Data Structures" value={v.title_en}
                onChange={(e) => setV({ title_en: e.target.value })} />
            </div>
            <div>
              <label className="label">Forma zajęć *</label>
              <select className="input" value={v.course_type} onChange={(e) => setV({ course_type: e.target.value })}>
                {['lecture','laboratory','exercise','seminar','project','practicum'].map(t =>
                  <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <div>
              <label className="label">Semestr *</label>
              <select className="input" value={v.semester} onChange={(e) => setV({ semester: e.target.value })}>
                <option value="winter">Zimowy</option>
                <option value="summer">Letni</option>
              </select>
            </div>
            <div>
              <label className="label">Numer semestru (1–12) *</label>
              <input type="number" className="input" min={1} max={12} value={v.semester_number}
                onChange={(e) => setV({ semester_number: Number(e.target.value) })} required />
            </div>
            <div>
              <label className="label">Punkty ECTS *</label>
              <input type="number" className="input" min={0.5} max={30} step={0.5} value={v.ects_credits}
                onChange={(e) => setV({ ects_credits: Number(e.target.value) })} required />
            </div>
          </div>
        </div>

        {/* Treść */}
        <div className="card p-6">
          <h2 className="font-semibold text-ink-700 mb-4">Treść</h2>
          <div className="space-y-4">
            {[
              ['Opis przedmiotu', 'description', 'Krótki opis tematyki i zakresu przedmiotu...'],
              ['Cele kształcenia', 'learning_objectives', 'Po ukończeniu przedmiotu student...'],
              ['Wymagania wstępne', 'prerequisites', 'Wymagana znajomość...'],
            ].map(([label, field, placeholder]) => (
              <div key={field}>
                <label className="label">{label}</label>
                <textarea className="input min-h-20 resize-y" placeholder={placeholder as string}
                  value={(v as any)[field]}
                  onChange={(e) => setV({ [field]: e.target.value } as any)} />
              </div>
            ))}
          </div>
        </div>

        {/* Godziny */}
        <div className="card p-6">
          <h2 className="font-semibold text-ink-700 mb-1">Godziny</h2>
          <p className={`text-xs mb-4 ${hoursOk ? 'text-green-600' : 'text-amber-600'}`}>
            Łącznie: {totalHours}h · Wymagane dla {v.ects_credits} ECTS: {expectedMin}–{expectedMax}h
          </p>
          <div className="grid grid-cols-3 gap-4">
            {[
              ['Wykład', 'hours_lecture'],
              ['Laboratorium', 'hours_laboratory'],
              ['Ćwiczenia', 'hours_exercise'],
              ['Seminarium', 'hours_seminar'],
              ['Projekt', 'hours_project'],
              ['Samodzielna nauka', 'hours_self_study'],
            ].map(([label, field]) => (
              <div key={field}>
                <label className="label">{label}</label>
                <input type="number" className="input" min={0} value={(v as any)[field]}
                  onChange={(e) => setV({ [field]: Number(e.target.value) } as any)} />
              </div>
            ))}
          </div>
        </div>

        {/* Efekty kształcenia */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-ink-700">Efekty kształcenia</h2>
            <button type="button" className="btn-ghost text-xs" onClick={() =>
              setV({ learning_outcomes: [...v.learning_outcomes, { code: `EK${v.learning_outcomes.length + 1}`, description: '', category: 'knowledge' }] })}>
              <Plus size={13} /> Dodaj
            </button>
          </div>
          <div className="space-y-3">
            {v.learning_outcomes.map((o, i) => (
              <div key={i} className="flex gap-2 items-start">
                <input className="input w-20 font-mono text-xs" placeholder="EK1" value={o.code}
                  onChange={(e) => { const arr = [...v.learning_outcomes]; arr[i] = { ...arr[i], code: e.target.value }; setV({ learning_outcomes: arr }) }} />
                <select className="input w-36" value={o.category}
                  onChange={(e) => { const arr = [...v.learning_outcomes]; arr[i] = { ...arr[i], category: e.target.value }; setV({ learning_outcomes: arr }) }}>
                  <option value="knowledge">Wiedza</option>
                  <option value="skills">Umiejętności</option>
                  <option value="competences">Kompetencje</option>
                </select>
                <input className="input flex-1" placeholder="Opis efektu kształcenia..." value={o.description}
                  onChange={(e) => { const arr = [...v.learning_outcomes]; arr[i] = { ...arr[i], description: e.target.value }; setV({ learning_outcomes: arr }) }} />
                <button type="button" className="btn-ghost text-red-400 px-2" onClick={() =>
                  setV({ learning_outcomes: v.learning_outcomes.filter((_, j) => j !== i) })}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Metody oceniania */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-1">
            <h2 className="font-semibold text-ink-700">Metody oceniania</h2>
            <button type="button" className="btn-ghost text-xs" onClick={() =>
              setV({ assessment_methods: [...v.assessment_methods, { method: 'quiz', weight: 0, description: '' }] })}>
              <Plus size={13} /> Dodaj
            </button>
          </div>
          <p className={`text-xs mb-4 ${weightsSum === 100 ? 'text-green-600' : 'text-amber-600'}`}>
            Suma wag: {weightsSum}% {weightsSum === 100 ? '✓' : `(brakuje ${100 - weightsSum}%)`}
          </p>
          <div className="space-y-3">
            {v.assessment_methods.map((m, i) => (
              <div key={i} className="flex gap-2 items-start">
                <select className="input w-36" value={m.method}
                  onChange={(e) => { const arr = [...v.assessment_methods]; arr[i] = { ...arr[i], method: e.target.value }; setV({ assessment_methods: arr }) }}>
                  {['exam','project','quiz','report','presentation','attendance'].map(t => <option key={t} value={t}>{t}</option>)}
                </select>
                <div className="relative w-24">
                  <input type="number" className="input pr-6" min={0} max={100} value={m.weight}
                    onChange={(e) => { const arr = [...v.assessment_methods]; arr[i] = { ...arr[i], weight: Number(e.target.value) }; setV({ assessment_methods: arr }) }} />
                  <span className="absolute right-3 top-1/2 -translate-y-1/2 text-ink-300 text-xs">%</span>
                </div>
                <input className="input flex-1" placeholder="Opis metody..." value={m.description}
                  onChange={(e) => { const arr = [...v.assessment_methods]; arr[i] = { ...arr[i], description: e.target.value }; setV({ assessment_methods: arr }) }} />
                <button type="button" className="btn-ghost text-red-400 px-2"
                  onClick={() => setV({ assessment_methods: v.assessment_methods.filter((_, j) => j !== i) })}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Literatura */}
        <div className="card p-6">
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-semibold text-ink-700">Literatura</h2>
            <button type="button" className="btn-ghost text-xs"
              onClick={() => setV({ bibliography: [...v.bibliography, { type: 'supplementary', citation: '', url: '' }] })}>
              <Plus size={13} /> Dodaj
            </button>
          </div>
          <div className="space-y-3">
            {v.bibliography.map((b, i) => (
              <div key={i} className="flex gap-2 items-start">
                <select className="input w-36" value={b.type}
                  onChange={(e) => { const arr = [...v.bibliography]; arr[i] = { ...arr[i], type: e.target.value }; setV({ bibliography: arr }) }}>
                  <option value="primary">Podstawowa</option>
                  <option value="supplementary">Uzupełniająca</option>
                </select>
                <input className="input flex-1" placeholder="Autor, Tytuł, Wydawnictwo, rok..." value={b.citation}
                  onChange={(e) => { const arr = [...v.bibliography]; arr[i] = { ...arr[i], citation: e.target.value }; setV({ bibliography: arr }) }} />
                <input className="input w-40" placeholder="URL (opcjonalnie)" value={b.url}
                  onChange={(e) => { const arr = [...v.bibliography]; arr[i] = { ...arr[i], url: e.target.value }; setV({ bibliography: arr }) }} />
                <button type="button" className="btn-ghost text-red-400 px-2"
                  onClick={() => setV({ bibliography: v.bibliography.filter((_, j) => j !== i) })}>
                  <Trash2 size={14} />
                </button>
              </div>
            ))}
          </div>
        </div>

        {error && (
          <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-lg text-red-700 text-sm">{error}</div>
        )}

        <div className="flex gap-3">
          <button type="submit" className="btn-primary" disabled={loading || unitsLoading || units.length === 0}>
            {loading && <Loader2 size={15} className="animate-spin" />}
            Zapisz sylabuz
          </button>
          <Link to="/syllabi" className="btn-secondary">Anuluj</Link>
        </div>
      </form>
    </div>
  )
}
