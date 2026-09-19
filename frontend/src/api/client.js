const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

/**
 * POST /analyze
 * Sends an image File to the backend and returns the full analysis JSON.
 * @param {File} imageFile
 * @returns {Promise<object>}
 */
export async function analyzeImage(imageFile) {
  const formData = new FormData()
  formData.append('file', imageFile)

  let response
  try {
    response = await fetch(`${API_URL}/analyze`, {
      method: 'POST',
      body: formData,
    })
  } catch (networkErr) {
    throw new Error(
      'Could not reach the server. Please check your connection and try again.'
    )
  }

  let data
  try {
    data = await response.json()
  } catch {
    throw new Error('Received an unexpected response from the server.')
  }

  if (!response.ok) {
    // Surface the API's error message if available
    const msg =
      data?.detail?.message ||
      data?.message ||
      `Server error (${response.status})`
    const code = data?.detail?.error || data?.error || 'UNKNOWN'
    const err = new Error(msg)
    err.code = code
    err.status = response.status
    throw err
  }

  return data
}
