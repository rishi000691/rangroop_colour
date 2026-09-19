import { useState } from 'react'
import ColorSwatch from '../components/ColorSwatch'
import ClothingCard from '../components/ClothingCard'

function StatPill({ label, value, sub }) {
  return (
    <div className="flex flex-col gap-1 bg-neutral-800/60 rounded-2xl px-4 py-3 min-w-0">
      <span className="text-xs text-neutral-500 font-medium uppercase tracking-wide">{label}</span>
      <span className="text-neutral-100 font-bold text-sm leading-tight">{value}</span>
      {sub && <span className="text-xs text-neutral-500 leading-tight">{sub}</span>}
    </div>
  )
}

function Section({ title, children, className = '' }) {
  return (
    <section className={`flex flex-col gap-4 ${className}`}>
      <h2 className="text-lg font-bold text-neutral-100 flex items-center gap-2">
        {title}
      </h2>
      {children}
    </section>
  )
}

function confidenceLabel(raw) {
  if (!raw) return null
  if (raw === 'high') return 'High confidence'
  if (raw === 'medium') return 'Moderate confidence'
  return 'Low confidence — try in better lighting'
}

export default function Results({ data, onReset }) {
  const [contrastOpen, setContrastOpen] = useState(false)

  const {
    skin_type,
    season,
    depth_bucket,
    undertone,
    undertone_confidence,
    recommended_colors = [],
    avoid_colors = [],
    explanation,
    illuminant_bias,
    confidence_notes,
    audit,
    recommended_clothing,
  } = data

  const contrastScores = audit?.recommended_contrast_scores ?? {}
  const clothingItems = recommended_clothing?.matched_items ?? []
  const tooFewItems = clothingItems.length > 0 && clothingItems.length <= 2

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-neutral-900 sticky top-0 bg-neutral-950/80 backdrop-blur-md z-10">
        <div className="flex items-center gap-3">
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/30">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="6" cy="12" r="3" />
              <circle cx="14" cy="7" r="3" opacity="0.6" />
              <circle cx="14" cy="17" r="3" opacity="0.8" />
            </svg>
          </div>
          <span className="font-bold text-lg tracking-tight text-neutral-100">rangroop</span>
        </div>
        <button onClick={onReset} className="btn-secondary text-xs px-4 py-2">
          Analyse Another
        </button>
      </header>

      {/* Body */}
      <main className="flex-1 px-4 py-8 max-w-2xl mx-auto w-full flex flex-col gap-10 animate-slide-up">

        {/* Page heading */}
        <div>
          <h1 className="text-2xl sm:text-3xl font-extrabold text-neutral-50 mb-1">Your Colour Profile</h1>
          <p className="text-neutral-500 text-sm">Based on your skin tone analysis</p>
        </div>

        {/* Lighting warning */}
        {illuminant_bias != null && illuminant_bias > 6 && (
          <div className="flex items-start gap-3 bg-amber-950/60 border border-amber-700/50 rounded-2xl px-4 py-3 animate-fade-in">
            <span className="text-lg mt-0.5">⚠️</span>
            <p className="text-amber-300 text-sm">
              Your photo had strong artificial lighting — results may be less accurate.
              Try retaking in natural daylight for best results.
            </p>
          </div>
        )}

        {/* Stats grid */}
        <Section title="Profile Summary">
          <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
            <StatPill label="Skin Type" value={skin_type ?? '—'} />
            <StatPill label="Season" value={season ?? '—'} />
            <StatPill label="Depth" value={depth_bucket ? depth_bucket.charAt(0).toUpperCase() + depth_bucket.slice(1) : '—'} />
            <StatPill
              label="Undertone"
              value={undertone ?? '—'}
              sub={confidenceLabel(undertone_confidence)}
            />
          </div>
          {confidence_notes && (
            <p className="text-xs text-neutral-500 italic px-1">{confidence_notes}</p>
          )}
        </Section>

        {/* Recommended colours */}
        <Section title="✨ Recommended Colours">
          {recommended_colors.length > 0 ? (
            <div className="card">
              <div className="flex flex-wrap gap-4 justify-start">
                {recommended_colors.map((hex) => (
                  <ColorSwatch key={hex} hex={hex} size="lg" />
                ))}
              </div>
            </div>
          ) : (
            <p className="text-neutral-500 text-sm">No recommended colours available.</p>
          )}
        </Section>

        {/* Avoid colours */}
        <Section title="🚫 Colours to Avoid">
          {avoid_colors.length > 0 ? (
            <div className="card">
              <div className="flex flex-wrap gap-4 justify-start">
                {avoid_colors.map((hex) => (
                  <div key={hex} className="relative">
                    <ColorSwatch hex={hex} size="lg" />
                    {/* Crossed out line */}
                    <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
                      <div className="w-full h-0.5 bg-white/40 rotate-45 absolute" />
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-xs text-neutral-500 mt-4">
                These colours can clash with your skin tone or wash it out.
              </p>
            </div>
          ) : (
            <p className="text-neutral-500 text-sm">No colours to avoid listed.</p>
          )}
        </Section>

        {/* Explanation */}
        {explanation && (
          <Section title="📖 Why These Colours?">
            <div className="card">
              <p className="text-neutral-300 text-sm leading-relaxed">{explanation}</p>
            </div>
          </Section>
        )}

        {/* Clothing matches */}
        <Section title="👗 Matching Clothing Items">
          {clothingItems.length === 0 ? (
            <div className="card text-center py-8">
              <p className="text-neutral-400 text-sm">No clothing matches found for your profile yet.</p>
              <p className="text-neutral-600 text-xs mt-1">More items coming soon for your colour profile.</p>
            </div>
          ) : (
            <>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {clothingItems.map((item) => (
                  <ClothingCard key={item.id} item={item} />
                ))}
              </div>
              {tooFewItems && (
                <p className="text-xs text-neutral-500 text-center">
                  More items coming soon for your colour profile.
                </p>
              )}
            </>
          )}
        </Section>

        {/* Contrast scores — collapsible */}
        {Object.keys(contrastScores).length > 0 && (
          <Section title="">
            <button
              onClick={() => setContrastOpen((o) => !o)}
              className="flex items-center gap-2 text-sm text-neutral-400 hover:text-neutral-200 transition-colors self-start"
              aria-expanded={contrastOpen}
            >
              <svg
                className={`w-4 h-4 transition-transform duration-200 ${contrastOpen ? 'rotate-90' : ''}`}
                fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}
              >
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 5l7 7-7 7" />
              </svg>
              Advanced: Contrast Scores (ΔE)
            </button>

            {contrastOpen && (
              <div className="card animate-fade-in">
                <p className="text-xs text-neutral-500 mb-4">
                  Delta-E (ΔE) measures perceptual colour distance between the recommended colour and your skin tone.
                  Higher = more contrast. Anything above ~50 will stand out clearly.
                </p>
                <div className="flex flex-col gap-2">
                  {Object.entries(contrastScores).map(([hex, score]) => (
                    <div key={hex} className="flex items-center gap-3">
                      <div
                        className="w-6 h-6 rounded-lg shrink-0 ring-1 ring-white/10"
                        style={{ backgroundColor: hex }}
                      />
                      <span className="font-mono text-xs text-neutral-400 w-20 shrink-0">{hex}</span>
                      <div className="flex-1 bg-neutral-800 rounded-full h-1.5 overflow-hidden">
                        <div
                          className="h-full bg-brand-500 rounded-full transition-all"
                          style={{ width: `${Math.min(score / 1.5, 100)}%` }}
                        />
                      </div>
                      <span className="text-xs text-neutral-400 w-12 text-right tabular-nums">{score.toFixed(1)}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </Section>
        )}

        {/* CTA */}
        <div className="flex flex-col items-center gap-4 pt-4 pb-8">
          <button onClick={onReset} className="btn-primary px-8">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            Analyse Another Photo
          </button>

          <p className="text-xs text-neutral-600 text-center max-w-sm">
            This is a suggestion based on colour theory, not a definitive rule.
            Lighting and camera quality can affect the analysis.
          </p>
        </div>
      </main>
    </div>
  )
}
