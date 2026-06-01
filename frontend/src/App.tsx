import { useState } from 'react'
import { ClipboardList, Sparkles, Upload, User } from 'lucide-react'
import { About } from './components/About'
import { BatchUpload } from './components/BatchUpload'
import { ManualForm } from './components/ManualForm'

type Tab = 'manual' | 'batch' | 'about'

function App() {
  const [tab, setTab] = useState<Tab>('manual')

  const tabs: { id: Tab; label: string; icon: typeof ClipboardList }[] = [
    { id: 'manual', label: 'Manual entry', icon: ClipboardList },
    { id: 'batch', label: 'Excel batch', icon: Upload },
    { id: 'about', label: 'About', icon: User },
  ]

  return (
    <div className="min-h-screen">
      <header className="sticky top-0 z-10 border-b border-white/60 bg-white/40 backdrop-blur-md">
        <div className="mx-auto flex max-w-5xl flex-wrap items-center justify-between gap-4 px-4 py-5 sm:px-6">
          <div className="flex items-center gap-3">
            <span className="flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br from-teal-400 to-rose-400 text-2xl shadow-lg shadow-teal-500/20">
              🫁
            </span>
            <div>
              <h1 className="font-display text-2xl font-bold tracking-tight text-teal-900">
                GLI PFT Calculator
              </h1>
              <p className="text-sm text-teal-700/70">
                Spirometry · Lung volumes · LLN & z-scores
              </p>
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-1 rounded-full bg-teal-100/80 p-1 ring-1 ring-teal-200/80">
            {tabs.map(({ id, label, icon: Icon }) => (
              <button
                key={id}
                type="button"
                onClick={() => setTab(id)}
                className={`inline-flex items-center gap-2 rounded-full px-4 py-2 text-sm font-medium transition ${
                  tab === id
                    ? 'bg-white text-teal-800 shadow-sm'
                    : 'text-teal-700 hover:text-teal-900'
                }`}
              >
                <Icon className="h-4 w-4" />
                {label}
              </button>
            ))}
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-5xl px-4 py-10 sm:px-6">
        {/* Keep panels mounted so tab switches preserve form / upload state */}
        <div className={tab === 'manual' ? 'mb-8' : 'mb-8 hidden'}>
          <div className="flex items-start gap-3 rounded-2xl bg-white/60 px-5 py-4 ring-1 ring-teal-100">
            <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
            <p className="text-sm leading-relaxed text-teal-800/90">
              Enter patient demographics and optional measured values to compute{' '}
              <strong>GLI-2022</strong> spirometry and <strong>GLI-2021</strong> lung volume
                reference values, LLN, ULN, % predicted, z-scores, and pattern
                classification (normal / obstruction / restriction / mixed).
            </p>
          </div>
        </div>
        <div className={tab === 'batch' ? 'mb-8' : 'mb-8 hidden'}>
          <div className="flex items-start gap-3 rounded-2xl bg-white/60 px-5 py-4 ring-1 ring-teal-100">
            <Sparkles className="mt-0.5 h-5 w-5 shrink-0 text-rose-400" />
            <p className="text-sm leading-relaxed text-teal-800/90">
              Upload your PFT Excel file. We append <strong>GLI_*</strong> columns (Predicted,
              LLN, ULN, z, % pred, Status) to each row and download{' '}
              <strong>your_file_GLI.xlsx</strong> — all original columns are kept.
            </p>
          </div>
        </div>

        <div className={tab === 'manual' ? undefined : 'hidden'} aria-hidden={tab !== 'manual'}>
          <ManualForm />
        </div>
        <div className={tab === 'batch' ? undefined : 'hidden'} aria-hidden={tab !== 'batch'}>
          <BatchUpload />
        </div>
        <div className={tab === 'about' ? undefined : 'hidden'} aria-hidden={tab !== 'about'}>
          <About />
        </div>
      </main>

      <footer className="mx-auto max-w-5xl px-4 pb-12 text-center text-xs text-teal-600/60">
        GLI-2022 spirometry (Bowerman et al.) · GLI-2021 lung volumes (Hall et al.) · Alireza
        Keshavarzian
      </footer>
    </div>
  )
}

export default App
