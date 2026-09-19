import { useState } from 'react'
import Home from './pages/Home'
import Results from './pages/Results'

export default function App() {
  const [result, setResult] = useState(null)

  const handleResult = (data) => {
    setResult(data)
    // Scroll to top when switching to results
    window.scrollTo({ top: 0, behavior: 'smooth' })
  }

  const handleReset = () => {
    setResult(null)
    window.scrollTo({ top: 0, behavior: 'instant' })
  }

  if (result) {
    return <Results data={result} onReset={handleReset} />
  }

  return <Home onResult={handleResult} />
}
