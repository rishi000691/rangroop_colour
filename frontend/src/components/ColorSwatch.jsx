/**
 * A single color swatch with optional label.
 * @param {{ hex: string, label?: string, size?: 'sm'|'md'|'lg' }} props
 */
export default function ColorSwatch({ hex, label, size = 'md' }) {
  const sizeClasses = {
    sm: 'w-10 h-10 rounded-xl',
    md: 'w-14 h-14 rounded-2xl',
    lg: 'w-20 h-20 rounded-3xl',
  }

  return (
    <div className="flex flex-col items-center gap-1.5 group">
      <div
        className={`${sizeClasses[size]} shadow-lg ring-2 ring-white/5 transition-transform duration-150 group-hover:scale-110 cursor-default`}
        style={{ backgroundColor: hex }}
        title={hex}
        aria-label={`Color swatch ${hex}`}
      />
      {label !== false && (
        <span className="text-xs font-mono text-neutral-400 group-hover:text-neutral-200 transition-colors">
          {label ?? hex}
        </span>
      )}
    </div>
  )
}
