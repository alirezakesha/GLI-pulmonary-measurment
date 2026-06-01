import { Building2, Mail, User } from 'lucide-react'

export function About() {
  return (
    <div className="mx-auto max-w-2xl space-y-8">
      <div className="overflow-hidden rounded-3xl bg-white/80 shadow-xl shadow-teal-900/5 ring-1 ring-teal-100">
        <div className="bg-gradient-to-br from-teal-500 to-rose-400 px-8 py-10 text-white">
          <div className="flex items-center gap-4">
            <span className="flex h-16 w-16 items-center justify-center rounded-2xl bg-white/20 text-3xl backdrop-blur">
              👋
            </span>
            <div>
              <p className="text-sm font-medium text-teal-50/90">About</p>
              <h2 className="font-display text-3xl font-bold">Alireza Keshavarzian</h2>
            </div>
          </div>
        </div>
        <div className="space-y-6 px-8 py-8">
          <p className="leading-relaxed text-teal-800/90">
            This application computes <strong>GLI-2022</strong> spirometry and{' '}
            <strong>GLI-2021</strong> lung volume reference values — predicted medians,
            lower and upper limits of normal (LLN / ULN), percent predicted, and z-scores —
            plus interpretive <strong>PFT pattern classification</strong> (normal, obstruction,
            restriction, or mixed) from FEV₁/FVC and TLC relative to GLI LLN.
          </p>

          <div className="rounded-2xl bg-teal-50/80 px-5 py-4 ring-1 ring-teal-100">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-teal-600">
              <Building2 className="h-4 w-4" />
              Affiliation
            </h3>
            <p className="mt-2 text-sm leading-relaxed text-teal-800/90">
              Developed under the supervision of <strong>Dr. Chow</strong> at{' '}
              <strong>University Health Network (UHN)</strong>, Toronto.
            </p>
          </div>

          <div className="space-y-3">
            <h3 className="flex items-center gap-2 text-sm font-semibold uppercase tracking-wide text-teal-600">
              <User className="h-4 w-4" />
              Contact
            </h3>
            <ul className="space-y-2">
              <li>
                <a
                  href="mailto:keshavarzian.alireza@gmail.com"
                  className="inline-flex items-center gap-2 rounded-xl bg-teal-50 px-4 py-3 text-teal-800 transition hover:bg-teal-100"
                >
                  <Mail className="h-4 w-4 text-teal-600" />
                  keshavarzian.alireza@gmail.com
                </a>
              </li>
              <li>
                <a
                  href="mailto:alireza.keshavarzian@uhn.ca"
                  className="inline-flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-3 text-teal-800 transition hover:bg-rose-100"
                >
                  <Mail className="h-4 w-4 text-rose-500" />
                  alireza.keshavarzian@uhn.ca
                </a>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  )
}
