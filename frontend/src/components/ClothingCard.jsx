const CATEGORY_COLORS = {
  shirt:  'bg-sky-900/60 text-sky-300',
  blouse: 'bg-pink-900/60 text-pink-300',
  blazer: 'bg-violet-900/60 text-violet-300',
  dress:  'bg-fuchsia-900/60 text-fuchsia-300',
  pants:  'bg-teal-900/60 text-teal-300',
  skirt:  'bg-rose-900/60 text-rose-300',
  other:  'bg-neutral-800 text-neutral-400',
}

/**
 * Card displaying a single clothing item match.
 * @param {{ item: object }} props
 */
export default function ClothingCard({ item }) {
  const badgeClass = CATEGORY_COLORS[item.category] ?? CATEGORY_COLORS.other

  return (
    <div className="card flex flex-col gap-4 hover:border-neutral-600 transition-colors duration-200 animate-fade-in">
      {/* Color preview bar */}
      <div
        className="w-full h-24 rounded-2xl shadow-inner ring-1 ring-white/10"
        style={{ backgroundColor: item.color_hex }}
        aria-label={`Color ${item.color_hex}`}
      />

      <div className="flex flex-col gap-2">
        {/* Category badge */}
        <span className={`badge w-fit capitalize ${badgeClass}`}>
          {item.category}
        </span>

        {/* Item name */}
        <p className="text-neutral-100 font-semibold text-sm leading-snug">
          {item.name}
        </p>

        {/* Hex + contrast */}
        <div className="flex items-center justify-between">
          <span className="font-mono text-xs text-neutral-500">{item.color_hex}</span>
          {item.skin_de != null && (
            <span
              className="text-xs text-neutral-500 tabular-nums"
              title="Delta-E contrast against your skin tone (higher = more contrast)"
            >
              ΔE {item.skin_de.toFixed(1)}
            </span>
          )}
        </div>
      </div>
    </div>
  )
}
