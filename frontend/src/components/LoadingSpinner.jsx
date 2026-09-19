export default function LoadingSpinner({ message = 'Analyzing your skin tone...' }) {
  return (
    <div className="flex flex-col items-center justify-center gap-5 py-12 animate-fade-in">
      {/* Animated rings */}
      <div className="relative w-16 h-16">
        <div className="absolute inset-0 rounded-full border-4 border-neutral-800" />
        <div className="absolute inset-0 rounded-full border-4 border-brand-500 border-t-transparent animate-spin-slow" />
        <div className="absolute inset-2 rounded-full border-2 border-brand-300 border-t-transparent animate-spin" style={{ animationDirection: 'reverse', animationDuration: '0.8s' }} />
      </div>

      {/* Message */}
      <div className="text-center">
        <p className="text-neutral-200 font-semibold text-base">{message}</p>
        <p className="text-neutral-500 text-sm mt-1">This may take a few seconds</p>
      </div>

      {/* Animated dots */}
      <div className="flex gap-1.5">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="w-2 h-2 rounded-full bg-brand-500"
            style={{
              animation: `pulse 1.4s ease-in-out ${i * 0.2}s infinite`,
            }}
          />
        ))}
      </div>

      <style>{`
        @keyframes pulse {
          0%, 80%, 100% { opacity: 0.2; transform: scale(0.8); }
          40% { opacity: 1; transform: scale(1); }
        }
      `}</style>
    </div>
  )
}
