import { useState } from 'react'
import { syllabiApi } from '../api/client'
import { Search } from 'lucide-react'

const UNIT_ID = '00000000-0000-0000-0000-000000000001'

export default function SubjectGridPage() {
  const [year, setYear] = useState('2024/2025')
  const [grid, setGrid] = useState<Record<number, any[]>>({})
  const [loaded, setLoaded] = useState(false)
  const [loading, setLoading] = useState(false)

  const load = async () => {
    setLoading(true)
    try {
      const { data } = await syllabiApi.grid({ academic_unit_id: UNIT_ID, academic_year: year })
      setGrid(data)
      setLoaded(true)
    } catch {}
    finally { setLoading(false) }
  }

  const semesters = Object.keys(grid).map(Number).sort((a, b) => a - b)
  const TYPE_COLORS: Record<string, string> = {
    lecture: 'bg-brand-50 border-brand-200 text-brand-700',
    laboratory: 'bg-green-50 border-green-200 text-green-700',
    exercise: 'bg-purple-50 border-purple-200 text-purple-700',
    seminar: 'bg-amber-50 border-amber-200 text-amber-700',
    project: 'bg-pink-50 border-pink-200 text-pink-700',
  }

  return (
    <div className="p-8 animate-fade-in">
      <div className="mb-6">
        <h1 className="text-2xl font-bold text-ink-800">Siatka przedmiotów</h1>
        <p className="text-ink-400 text-sm mt-0.5">Widok przedmiotów według semestrów</p>
      </div>

      {/* Filter */}
      <div className="card p-4 mb-6 flex gap-3 items-end">
        <div>
          <label className="label">Rok akademicki</label>
          <input className="input w-36" placeholder="2024/2025" value={year}
            onChange={(e) => setYear(e.target.value)} />
        </div>
        <button className="btn-primary" onClick={load} disabled={loading}>
          <Search size={14} /> {loading ? 'Ładowanie...' : 'Wyszukaj'}
        </button>
      </div>

      {/* Legend */}
      <div className="flex gap-3 mb-5 flex-wrap">
        {Object.entries(TYPE_COLORS).map(([type, cls]) => (
          <span key={type} className={`badge border ${cls} capitalize`}>{type}</span>
        ))}
      </div>

      {/* Grid */}
      {!loaded ? (
        <div className="card p-12 text-center text-ink-300">
          Wybierz rok akademicki i kliknij Wyszukaj
        </div>
      ) : semesters.length === 0 ? (
        <div className="card p-12 text-center text-ink-300">
          Brak zatwierdzonych sylabusów dla wybranego roku.
        </div>
      ) : (
        <div className="space-y-6">
          {semesters.map((sem) => (
            <div key={sem}>
              <div className="flex items-center gap-3 mb-3">
                <div className="w-8 h-8 bg-ink-800 text-white rounded-lg flex items-center justify-center text-sm font-bold">
                  {sem}
                </div>
                <h2 className="font-semibold text-ink-700">Semestr {sem}</h2>
                <span className="text-xs text-ink-400">
                  {grid[sem].length} przedmiotów ·{' '}
                  {grid[sem].reduce((s, c) => s + c.ects_credits, 0)} ECTS ·{' '}
                  {grid[sem].reduce((s, c) => s + c.total_hours, 0)}h łącznie
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-3">
                {grid[sem].map((course, i) => (
                  <div key={i} className={`card p-4 border ${TYPE_COLORS[course.course_type] || 'bg-ink-50 border-ink-200 text-ink-700'}`}>
                    <div className="font-mono text-xs opacity-60 mb-1">{course.course_code}</div>
                    <div className="font-semibold text-sm leading-tight mb-2">{course.title_pl}</div>
                    <div className="flex gap-3 text-xs opacity-70">
                      <span>{course.ects_credits} ECTS</span>
                      <span>{course.total_hours}h</span>
                    </div>
                    <div className="mt-2 flex gap-1 flex-wrap">
                      {course.hours_lecture > 0 && <span className="text-xs opacity-60">W:{course.hours_lecture}</span>}
                      {course.hours_laboratory > 0 && <span className="text-xs opacity-60">L:{course.hours_laboratory}</span>}
                      {course.hours_exercise > 0 && <span className="text-xs opacity-60">Ć:{course.hours_exercise}</span>}
                      {course.hours_project > 0 && <span className="text-xs opacity-60">P:{course.hours_project}</span>}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
