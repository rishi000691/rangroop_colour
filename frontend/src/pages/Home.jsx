import { useState, useRef } from 'react'
import SelfieCapture from '../components/SelfieCapture'
import LoadingSpinner from '../components/LoadingSpinner'
import { analyzeImage } from '../api/client'

const ACCEPTED_TYPES = ['image/jpeg', 'image/png', 'image/webp']
const MAX_BYTES = 10 * 1024 * 1024 // 10 MB

function friendlyError(err) {
  const code = err?.code || ''
  if (code === 'NO_FACE_DETECTED') return "We couldn't find a face in that photo. Make sure your face is clearly visible and well-lit."
  if (code === 'MULTIPLE_FACES_DETECTED') return 'More than one face was detected. Please use a photo with only you in frame.'
  if (code === 'POOR_IMAGE_QUALITY') return "The photo quality was too low to analyse. Try a clearer photo in better lighting."
  if (code === 'INVALID_IMAGE_FORMAT') return 'That file type isn\'t supported. Please upload a JPEG, PNG, or WebP image.'
  if (code === 'FILE_TOO_LARGE') return 'That photo is too large (max 10 MB). Please use a smaller file.'
  return err.message || 'Something went wrong. Please try again.'
}

export default function Home({ onResult }) {
  const fileInputRef = useRef(null)

  const [selectedFile, setSelectedFile] = useState(null)
  const [previewUrl, setPreviewUrl] = useState(null)
  const [showCamera, setShowCamera] = useState(false)
  const [cameraUnsupported, setCameraUnsupported] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)

  const handleFileSelect = (file) => {
    setError(null)
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setError('Only JPEG, PNG, and WebP images are supported.')
      return
    }
    if (file.size > MAX_BYTES) {
      setError('File is too large. Maximum size is 10 MB.')
      return
    }
    setSelectedFile(file)
    setPreviewUrl(URL.createObjectURL(file))
  }

  const handleInputChange = (e) => {
    const file = e.target.files?.[0]
    if (file) handleFileSelect(file)
    // Reset so the same file can be re-selected
    e.target.value = ''
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files?.[0]
    if (file) handleFileSelect(file)
  }

  const handleSelfieCapture = (file) => {
    setShowCamera(false)
    handleFileSelect(file)
  }

  const handleClear = () => {
    setSelectedFile(null)
    setPreviewUrl(null)
    setError(null)
  }

  const handleSubmit = async () => {
    if (!selectedFile || loading) return
    setLoading(true)
    setError(null)
    try {
      const result = await analyzeImage(selectedFile)
      onResult(result)
    } catch (err) {
      setError(friendlyError(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="px-6 py-5 flex items-center justify-between border-b border-neutral-900">
        <div className="flex items-center gap-3">
          {/* Logo mark */}
          <div className="w-8 h-8 rounded-xl bg-gradient-to-br from-brand-400 to-brand-600 flex items-center justify-center shadow-lg shadow-brand-500/30">
            <svg className="w-4 h-4 text-white" viewBox="0 0 24 24" fill="currentColor">
              <circle cx="6" cy="12" r="3" />
              <circle cx="14" cy="7" r="3" opacity="0.6" />
              <circle cx="14" cy="17" r="3" opacity="0.8" />
            </svg>
          </div>
          <span className="font-bold text-lg tracking-tight text-neutral-100">rangroop</span>
        </div>
      </header>

      {/* Main */}
      <main className="flex-1 flex flex-col items-center justify-center px-4 py-10 max-w-xl mx-auto w-full">
        {loading ? (
          <LoadingSpinner />
        ) : (
          <div className="w-full animate-slide-up">
            {/* Hero text */}
            <div className="text-center mb-10">
              <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-neutral-50 mb-3 leading-tight">
                Discover which{' '}
                <span className="bg-gradient-to-r from-brand-400 to-brand-300 bg-clip-text text-transparent">
                  colors suit
                </span>{' '}
                you best
              </h1>
              <p className="text-neutral-400 text-base max-w-sm mx-auto">
                Upload a selfie and get a personalised colour palette based on your skin tone in seconds.
              </p>
            </div>

            {/* Privacy note */}
            <div className="flex items-start gap-2.5 bg-neutral-900 border border-neutral-800 rounded-2xl px-4 py-3 mb-7 text-sm text-neutral-400">
              <svg className="w-4 h-4 text-brand-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
              </svg>
              <span>Your photo is analysed instantly and <strong className="text-neutral-200">never stored</strong> on our servers.</span>
            </div>

            {/* Photo area */}
            {!selectedFile ? (
              <>
                {/* Drop zone */}
                <div
                  onDrop={handleDrop}
                  onDragOver={(e) => e.preventDefault()}
                  className="border-2 border-dashed border-neutral-700 hover:border-brand-500/60 rounded-3xl p-8 text-center transition-colors duration-200 mb-5 cursor-pointer group"
                  onClick={() => fileInputRef.current?.click()}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === 'Enter' && fileInputRef.current?.click()}
                  aria-label="Click or drop an image to upload"
                >
                  <div className="flex flex-col items-center gap-3">
                    <div className="w-14 h-14 rounded-2xl bg-neutral-800 group-hover:bg-neutral-700 flex items-center justify-center transition-colors">
                      <svg className="w-7 h-7 text-neutral-400 group-hover:text-brand-400 transition-colors" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5m-13.5-9L12 3m0 0l4.5 4.5M12 3v13.5" />
                      </svg>
                    </div>
                    <div>
                      <p className="text-neutral-200 font-semibold text-sm">Drop your photo here, or click to browse</p>
                      <p className="text-neutral-500 text-xs mt-1">JPEG, PNG, WebP · Max 10 MB</p>
                    </div>
                  </div>
                </div>

                <input
                  ref={fileInputRef}
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  className="hidden"
                  onChange={handleInputChange}
                />

                {/* Divider */}
                <div className="flex items-center gap-3 my-5">
                  <div className="flex-1 h-px bg-neutral-800" />
                  <span className="text-neutral-600 text-xs">or</span>
                  <div className="flex-1 h-px bg-neutral-800" />
                </div>

                {/* Webcam button */}
                {cameraUnsupported ? (
                  <p className="text-center text-sm text-neutral-500">
                    Webcam not available on this browser — please upload a photo instead.
                  </p>
                ) : (
                  <button
                    onClick={() => setShowCamera(true)}
                    className="btn-outline w-full"
                  >
                    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.8}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M15 10l4.553-2.069A1 1 0 0121 8.882v6.235a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h8a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
                    </svg>
                    Take a Selfie
                  </button>
                )}
              </>
            ) : (
              /* Photo preview */
              <div className="flex flex-col gap-4 animate-fade-in">
                <div className="relative rounded-3xl overflow-hidden bg-neutral-900 border border-neutral-800 aspect-[4/3]">
                  <img
                    src={previewUrl}
                    alt="Selected photo"
                    className="w-full h-full object-cover"
                  />
                  {/* Remove button */}
                  <button
                    onClick={handleClear}
                    className="absolute top-3 right-3 w-8 h-8 rounded-full bg-black/60 backdrop-blur-sm flex items-center justify-center text-white hover:bg-black/80 transition-colors"
                    aria-label="Remove photo"
                  >
                    <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>

                <button
                  onClick={handleSubmit}
                  disabled={loading}
                  className="btn-primary w-full text-base py-4"
                >
                  <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z" />
                  </svg>
                  Analyse My Colours
                </button>

                <button onClick={handleClear} className="text-sm text-neutral-500 hover:text-neutral-300 transition-colors text-center">
                  Choose a different photo
                </button>
              </div>
            )}

            {/* Error message */}
            {error && (
              <div className="mt-5 flex items-start gap-3 bg-red-950/60 border border-red-800/60 rounded-2xl px-4 py-3 animate-fade-in">
                <svg className="w-5 h-5 text-red-400 mt-0.5 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M12 9v3.75m-9.303 3.376c-.866 1.5.217 3.374 1.948 3.374h14.71c1.73 0 2.813-1.874 1.948-3.374L13.949 3.378c-.866-1.5-3.032-1.5-3.898 0L2.697 16.126zM12 15.75h.007v.008H12v-.008z" />
                </svg>
                <p className="text-red-300 text-sm">{error}</p>
              </div>
            )}
          </div>
        )}
      </main>

      {/* Camera modal */}
      {showCamera && (
        <SelfieCapture
          onCapture={handleSelfieCapture}
          onClose={() => setShowCamera(false)}
          onUnsupported={() => {
            setCameraUnsupported(true)
            setShowCamera(false)
          }}
        />
      )}
    </div>
  )
}
