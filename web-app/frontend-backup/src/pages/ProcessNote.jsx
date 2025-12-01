import { useState } from 'react'
import axios from 'axios'

function ProcessNote() {
  const [noteText, setNoteText] = useState('')
  const [cleanedNote, setCleanedNote] = useState('')
  const [processing, setProcessing] = useState(false)
  const [error, setError] = useState(null)
  const [success, setSuccess] = useState(false)

  const handleProcess = async () => {
    if (!noteText.trim()) {
      setError('Please enter a note to process')
      return
    }

    try {
      setProcessing(true)
      setError(null)
      setSuccess(false)

      const response = await axios.post('/api/process', {
        note_text: noteText
      })

      setCleanedNote(response.data.cleaned_note)
      setSuccess(true)
    } catch (err) {
      setError(err.response?.data?.detail || 'Failed to process note')
      console.error(err)
    } finally {
      setProcessing(false)
    }
  }

  const handleClear = () => {
    setNoteText('')
    setCleanedNote('')
    setError(null)
    setSuccess(false)
  }

  const handleCopy = () => {
    navigator.clipboard.writeText(cleanedNote)
    alert('Cleaned note copied to clipboard!')
  }

  return (
    <div className="page">
      <h1 className="page-title">Process Note</h1>

      <p style={{ marginBottom: '1.5rem', color: '#666' }}>
        Paste a medical note below to process it with OpenAI. The note will be cleaned and formatted
        in APSO format (Assessment, Plan, Recommendations, Counseling, Subjective, Objective) with
        no AI language.
      </p>

      {error && <div className="error">{error}</div>}
      {success && <div className="success">Note processed successfully!</div>}

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2rem' }}>
        <div>
          <div className="form-group">
            <label className="form-label">Original Note</label>
            <textarea
              className="form-control"
              value={noteText}
              onChange={(e) => setNoteText(e.target.value)}
              placeholder="Paste your medical note here..."
            />
          </div>

          <div style={{ display: 'flex', gap: '1rem' }}>
            <button
              className="btn btn-primary"
              onClick={handleProcess}
              disabled={processing || !noteText.trim()}
            >
              {processing ? 'Processing...' : 'Process Note'}
            </button>
            <button
              className="btn"
              onClick={handleClear}
              disabled={processing}
            >
              Clear
            </button>
          </div>
        </div>

        <div>
          <div className="form-group">
            <label className="form-label">
              Cleaned Note (APSO Format)
              {cleanedNote && (
                <button
                  style={{
                    marginLeft: '1rem',
                    padding: '0.25rem 0.75rem',
                    fontSize: '0.9rem'
                  }}
                  className="btn btn-success"
                  onClick={handleCopy}
                >
                  Copy to Clipboard
                </button>
              )}
            </label>
            <textarea
              className="form-control"
              value={cleanedNote}
              readOnly
              placeholder="Processed note will appear here..."
            />
          </div>

          {cleanedNote && (
            <div style={{ marginTop: '1rem', padding: '1rem', backgroundColor: '#f0f8ff', borderRadius: '4px' }}>
              <h4 style={{ marginBottom: '0.5rem', fontSize: '1rem' }}>Note Format:</h4>
              <ul style={{ marginLeft: '1.5rem', lineHeight: '1.8' }}>
                <li>✅ APSO Order (Assessment → Plan → Recommendations → Counseling → Subjective → Objective)</li>
                <li>✅ No AI Language</li>
                <li>✅ Provider Voice (First Person)</li>
                <li>✅ Medically Accurate</li>
                <li>✅ Legally Compliant</li>
              </ul>
            </div>
          )}
        </div>
      </div>

      {processing && (
        <div className="loading" style={{ marginTop: '2rem' }}>
          <div className="spinner"></div>
          <p style={{ marginTop: '1rem', color: '#666' }}>Processing note with OpenAI...</p>
        </div>
      )}
    </div>
  )
}

export default ProcessNote
