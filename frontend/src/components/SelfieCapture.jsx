import { useRef, useEffect, useState, useCallback } from 'react'

const SUPPORTED = !!(
  navigator.mediaDevices && navigator.mediaDevices.getUserMedia
)

/**
 * Webcam capture component.
 * Shows a live viewfinder and a "Capture" button.
 * On capture, calls onCapture(file) with a File object.
 * Calls onUnsupported() if the browser doesn't support camera access.
 *
 * @param {{ onCapture: (file: File) => void, onClose: () => void, onUnsupported?: () => void }} props
 */
export default function SelfieCapture({ onCapture, onClose, onUnsupported }) {
  const videoRef = useRef(null)
  const canvasRef = useRef(null)
  const streamRef = useRef(null)

  const [error, setError] = useState(null)
  const [mirrored, setMirrored] = useState(true)
  const [facingMode, setFacingMode] = useState('user')
  const [captured, setCaptured] = useState(false)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [capturedFile, setCapturedFile] = useState(null)

  const startCamera = useCallback(async (mode = 'user') => {
    // Stop any existing stream
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
    }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { facingMode: mode, width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      })
      streamRef.current = stream
      if (videoRef.current) {
        videoRef.current.srcObject = stream
      }
      setError(null)
    } catch (err) {
      if (err.name === 'NotAllowedError') {
        setError('Camera permission was denied. Please allow camera access and try again.')
      } else if (err.name === 'NotFoundError') {
        setError('No camera found on this device.')
        onUnsupported?.()
      } else {
        setError('Could not start the camera: ' + err.message)
      }
    }
  }, [onUnsupported])

  useEffect(() => {
    if (!SUPPORTED) {
      setError('Your browser does not support webcam access.')
      onUnsupported?.()
      return
    }
    startCamera(facingMode)
    return () => {
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCapture = () => {
    const video = videoRef.current
    const canvas = canvasRef.current
    if (!video || !canvas) return

    canvas.width = video.videoWidth
    canvas.height = video.videoHeight
    const ctx = canvas.getContext('2d')

    // Mirror canvas to match the flipped video display
    if (mirrored) {
      ctx.translate(canvas.width, 0)
      ctx.scale(-1, 1)
    }
    ctx.drawImage(video, 0, 0)

    canvas.toBlob((blob) => {
      const file = new File([blob], 'selfie.jpg', { type: 'image/jpeg' })
      const url = URL.createObjectURL(blob)
      setCapturedFile(file)
      setPreviewUrl(url)
      setCaptured(true)
      // Stop camera
      streamRef.current?.getTracks().forEach((t) => t.stop())
    }, 'image/jpeg', 0.92)
  }

  const handleRetake = () => {
    setCaptured(false)
    setPreviewUrl(null)
    setCapturedFile(null)
    startCamera(facingMode)
  }

  const handleFlip = () => {
    const nextMode = facingMode === 'user' ? 'environment' : 'user'
    setFacingMode(nextMode)
    setMirrored(nextMode === 'user')
    startCamera(nextMode)
  }

  const handleUse = () => {
    if (capturedFile) onCapture(capturedFile)
  }

  return (
    <div className="fixed inset-0 z-50 flex items-end sm:items-center justify-center bg-black/80 backdrop-blur-sm animate-fade-in">
      <div className="bg-neutral-900 border border-neutral-800 rounded-t-3xl sm:rounded-3xl w-full sm:max-w-lg overflow-hidden shadow-2xl">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-800">
          <h2 className="font-semibold text-neutral-100">Take a Selfie</h2>
          <button
            onClick={onClose}
            className="text-neutral-400 hover:text-neutral-100 transition-colors p-1"
            aria-label="Close camera"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Viewfinder / Preview */}
        <div className="relative bg-black aspect-[4/3] overflow-hidden">
          {error ? (
            <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 p-6 text-center">
              <svg className="w-12 h-12 text-neutral-600" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.235a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
              </svg>
              <p className="text-neutral-400 text-sm">{error}</p>
            </div>
          ) : captured ? (
            <img
              src={previewUrl}
              alt="Captured selfie"
              className="w-full h-full object-cover"
            />
          ) : (
            <video
              ref={videoRef}
              autoPlay
              playsInline
              muted
              className="w-full h-full object-cover"
              style={{ transform: mirrored ? 'scaleX(-1)' : 'none' }}
            />
          )}

          {/* Face guide overlay */}
          {!captured && !error && (
            <div className="absolute inset-0 flex items-center justify-center pointer-events-none">
              <div className="w-40 h-48 rounded-full border-2 border-white/30 border-dashed" />
            </div>
          )}
        </div>

        {/* Hidden canvas for capture */}
        <canvas ref={canvasRef} className="hidden" />

        {/* Controls */}
        <div className="px-5 py-4 flex gap-3">
          {captured ? (
            <>
              <button onClick={handleRetake} className="btn-secondary flex-1">
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Retake
              </button>
              <button onClick={handleUse} className="btn-primary flex-1">
                Use this photo
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                </svg>
              </button>
            </>
          ) : (
            <>
              {/* Flip camera (mobile) */}
              <button
                onClick={handleFlip}
                disabled={!!error}
                className="btn-secondary px-4"
                aria-label="Flip camera"
              >
                <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
              </button>

              {/* Capture button */}
              <button
                onClick={handleCapture}
                disabled={!!error}
                className="flex-1 flex items-center justify-center gap-2 bg-white hover:bg-neutral-100 active:bg-neutral-200 text-neutral-900 font-bold rounded-2xl py-3 px-6 transition-all duration-150 disabled:opacity-40 disabled:cursor-not-allowed shadow-lg"
              >
                <span className="w-5 h-5 rounded-full bg-brand-500 inline-block ring-2 ring-brand-300" />
                Capture
              </button>
            </>
          )}
        </div>

        {/* Tip */}
        {!captured && !error && (
          <p className="text-center text-xs text-neutral-500 pb-4 px-5">
            Face the light source for best results. Natural daylight is ideal.
          </p>
        )}
      </div>
    </div>
  )
}
